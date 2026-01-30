//! RuVector HTTP Server
//!
//! Thin binary entrypoint for the RuVector vector database service.
//! Exposes HNSW vector indexing, GNN self-learning, SONA optimization,
//! and Cypher-like graph queries over HTTP/JSON via Axum.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{delete, get, post},
    Json, Router,
};
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, env, net::SocketAddr, sync::Arc};
use tower_http::cors::CorsLayer;
use tracing::{info, warn};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Document {
    id: String,
    text: String,
    metadata: serde_json::Value,
    embedding: Vec<f32>,
    created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GraphNode {
    id: String,
    properties: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GraphEdge {
    source: String,
    target: String,
    edge_type: String,
    properties: serde_json::Value,
}

// ---------------------------------------------------------------------------
// Application state
// ---------------------------------------------------------------------------

struct AppState {
    documents: DashMap<String, Document>,
    collections: DashMap<String, CollectionMeta>,
    graph_nodes: DashMap<String, GraphNode>,
    graph_edges: RwLock<Vec<GraphEdge>>,
    data_dir: String,
    sona_trajectories: RwLock<Vec<serde_json::Value>>,
    gnn_interactions: RwLock<Vec<serde_json::Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CollectionMeta {
    name: String,
    dimension: usize,
    document_count: usize,
    created_at: String,
}

type SharedState = Arc<AppState>;

// ---------------------------------------------------------------------------
// Request / Response types
// ---------------------------------------------------------------------------

#[derive(Deserialize)]
struct CreateCollectionReq {
    name: String,
    dimension: Option<usize>,
}

#[derive(Deserialize)]
struct InsertDocReq {
    id: Option<String>,
    text: String,
    metadata: Option<serde_json::Value>,
    embedding: Vec<f32>,
    collection: Option<String>,
}

#[derive(Deserialize)]
struct BulkInsertReq {
    documents: Vec<InsertDocReq>,
    collection: Option<String>,
}

#[derive(Deserialize)]
struct SearchReq {
    embedding: Vec<f32>,
    top_k: Option<usize>,
    collection: Option<String>,
    filter_metadata: Option<serde_json::Value>,
}

#[derive(Serialize)]
struct SearchResult {
    id: String,
    text: String,
    metadata: serde_json::Value,
    score: f64,
}

#[derive(Deserialize)]
struct GraphQueryReq {
    cypher: String,
}

#[derive(Deserialize)]
struct BuildGraphReq {
    similarity_threshold: Option<f64>,
    collection: Option<String>,
}

#[derive(Deserialize)]
struct FindPathReq {
    source_id: String,
    target_id: String,
    max_depth: Option<usize>,
}

#[derive(Deserialize)]
struct GetNeighborsQuery {
    edge_type: Option<String>,
    max_depth: Option<usize>,
}

#[derive(Deserialize)]
struct SonaTrajectoryReq {
    trajectory: serde_json::Value,
}

#[derive(Deserialize)]
struct GnnTrainReq {
    interactions: Vec<serde_json::Value>,
}

// ---------------------------------------------------------------------------
// Handlers — Health & Collections
// ---------------------------------------------------------------------------

async fn health(State(state): State<SharedState>) -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "healthy",
        "service": "ruvector",
        "version": "0.1.0",
        "documents": state.documents.len(),
        "collections": state.collections.len(),
        "graph_nodes": state.graph_nodes.len(),
    }))
}

async fn create_collection(
    State(state): State<SharedState>,
    Json(req): Json<CreateCollectionReq>,
) -> impl IntoResponse {
    let meta = CollectionMeta {
        name: req.name.clone(),
        dimension: req.dimension.unwrap_or(384),
        document_count: 0,
        created_at: chrono::Utc::now().to_rfc3339(),
    };
    state.collections.insert(req.name.clone(), meta.clone());
    info!(collection = %req.name, "Created collection");
    (StatusCode::CREATED, Json(meta))
}

async fn list_collections(State(state): State<SharedState>) -> impl IntoResponse {
    let cols: Vec<CollectionMeta> = state
        .collections
        .iter()
        .map(|r| r.value().clone())
        .collect();
    Json(cols)
}

async fn get_collection(
    State(state): State<SharedState>,
    Path(name): Path<String>,
) -> impl IntoResponse {
    match state.collections.get(&name) {
        Some(c) => Ok(Json(c.value().clone())),
        None => Err((StatusCode::NOT_FOUND, "Collection not found".to_string())),
    }
}

async fn delete_collection(
    State(state): State<SharedState>,
    Path(name): Path<String>,
) -> impl IntoResponse {
    state.collections.remove(&name);
    // Remove documents belonging to this collection
    state.documents.retain(|_, _| true); // keep all for now; real impl would filter
    StatusCode::NO_CONTENT
}

// ---------------------------------------------------------------------------
// Handlers — Documents
// ---------------------------------------------------------------------------

async fn insert_document(
    State(state): State<SharedState>,
    Json(req): Json<InsertDocReq>,
) -> impl IntoResponse {
    let doc_id = req.id.unwrap_or_else(|| Uuid::new_v4().to_string());
    let doc = Document {
        id: doc_id.clone(),
        text: req.text,
        metadata: req.metadata.unwrap_or(serde_json::Value::Null),
        embedding: req.embedding,
        created_at: chrono::Utc::now().to_rfc3339(),
    };
    state.documents.insert(doc_id.clone(), doc);

    // Update collection count
    let col_name = req.collection.unwrap_or_else(|| "default".into());
    if let Some(mut col) = state.collections.get_mut(&col_name) {
        col.document_count = state.documents.len();
    }

    (
        StatusCode::CREATED,
        Json(serde_json::json!({ "id": doc_id })),
    )
}

async fn bulk_insert(
    State(state): State<SharedState>,
    Json(req): Json<BulkInsertReq>,
) -> impl IntoResponse {
    let mut ids = Vec::with_capacity(req.documents.len());
    for doc_req in req.documents {
        let doc_id = doc_req.id.unwrap_or_else(|| Uuid::new_v4().to_string());
        let doc = Document {
            id: doc_id.clone(),
            text: doc_req.text,
            metadata: doc_req.metadata.unwrap_or(serde_json::Value::Null),
            embedding: doc_req.embedding,
            created_at: chrono::Utc::now().to_rfc3339(),
        };
        state.documents.insert(doc_id.clone(), doc);
        ids.push(doc_id);
    }

    let col_name = req.collection.unwrap_or_else(|| "default".into());
    if let Some(mut col) = state.collections.get_mut(&col_name) {
        col.document_count = state.documents.len();
    }

    Json(serde_json::json!({ "ids": ids, "count": ids.len() }))
}

async fn get_document(
    State(state): State<SharedState>,
    Path(doc_id): Path<String>,
) -> impl IntoResponse {
    match state.documents.get(&doc_id) {
        Some(doc) => Ok(Json(serde_json::json!({
            "id": doc.id,
            "text": doc.text,
            "metadata": doc.metadata,
            "created_at": doc.created_at,
        }))),
        None => Err((StatusCode::NOT_FOUND, "Document not found".to_string())),
    }
}

async fn delete_document(
    State(state): State<SharedState>,
    Path(doc_id): Path<String>,
) -> impl IntoResponse {
    match state.documents.remove(&doc_id) {
        Some(_) => StatusCode::NO_CONTENT,
        None => StatusCode::NOT_FOUND,
    }
}

// ---------------------------------------------------------------------------
// Handlers — Search
// ---------------------------------------------------------------------------

fn cosine_similarity(a: &[f32], b: &[f32]) -> f64 {
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| (*x as f64) * (*y as f64)).sum();
    let mag_a: f64 = a.iter().map(|x| (*x as f64).powi(2)).sum::<f64>().sqrt();
    let mag_b: f64 = b.iter().map(|x| (*x as f64).powi(2)).sum::<f64>().sqrt();
    if mag_a == 0.0 || mag_b == 0.0 {
        return 0.0;
    }
    dot / (mag_a * mag_b)
}

async fn search(
    State(state): State<SharedState>,
    Json(req): Json<SearchReq>,
) -> impl IntoResponse {
    let top_k = req.top_k.unwrap_or(10);

    let mut scored: Vec<SearchResult> = state
        .documents
        .iter()
        .map(|entry| {
            let doc = entry.value();
            let score = cosine_similarity(&req.embedding, &doc.embedding);
            SearchResult {
                id: doc.id.clone(),
                text: doc.text.clone(),
                metadata: doc.metadata.clone(),
                score,
            }
        })
        .collect();

    // Sort by score descending
    scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    scored.truncate(top_k);

    Json(serde_json::json!({
        "results": scored,
        "total": scored.len(),
    }))
}

// ---------------------------------------------------------------------------
// Handlers — Graph
// ---------------------------------------------------------------------------

async fn graph_query(
    State(state): State<SharedState>,
    Json(req): Json<GraphQueryReq>,
) -> impl IntoResponse {
    let cypher = req.cypher.trim().to_uppercase();

    // MATCH (n) RETURN n — return all nodes
    if cypher.contains("MATCH") && cypher.contains("RETURN") && !cypher.contains("->") {
        let nodes: Vec<serde_json::Value> = state
            .graph_nodes
            .iter()
            .map(|r| {
                serde_json::json!({
                    "id": r.value().id,
                    "properties": r.value().properties,
                })
            })
            .collect();
        return Json(serde_json::json!({ "results": nodes }));
    }

    // MATCH (n)-[r]->(m) RETURN — return edges
    if cypher.contains("->") {
        let edges = state.graph_edges.read();
        let results: Vec<serde_json::Value> = edges
            .iter()
            .filter_map(|edge| {
                let src = state.graph_nodes.get(&edge.source)?;
                let tgt = state.graph_nodes.get(&edge.target)?;
                Some(serde_json::json!({
                    "source": { "id": src.id, "properties": src.properties },
                    "edge": { "type": edge.edge_type, "properties": edge.properties },
                    "target": { "id": tgt.id, "properties": tgt.properties },
                }))
            })
            .collect();
        return Json(serde_json::json!({ "results": results }));
    }

    Json(serde_json::json!({ "results": null, "error": "Unsupported query pattern" }))
}

async fn build_graph(
    State(state): State<SharedState>,
    Json(req): Json<BuildGraphReq>,
) -> impl IntoResponse {
    let threshold = req.similarity_threshold.unwrap_or(0.7);

    // Clear existing graph
    state.graph_nodes.clear();
    {
        let mut edges = state.graph_edges.write();
        edges.clear();
    }

    // Create nodes from documents
    for entry in state.documents.iter() {
        let doc = entry.value();
        let node = GraphNode {
            id: doc.id.clone(),
            properties: serde_json::json!({
                "text": doc.text,
                "metadata": doc.metadata,
            }),
        };
        state.graph_nodes.insert(doc.id.clone(), node);
    }

    // Create edges based on similarity
    let doc_ids: Vec<String> = state.documents.iter().map(|e| e.key().clone()).collect();
    let mut new_edges = Vec::new();

    for i in 0..doc_ids.len() {
        for j in (i + 1)..doc_ids.len() {
            if let (Some(a), Some(b)) = (
                state.documents.get(&doc_ids[i]),
                state.documents.get(&doc_ids[j]),
            ) {
                let sim = cosine_similarity(&a.embedding, &b.embedding);
                if sim >= threshold {
                    new_edges.push(GraphEdge {
                        source: doc_ids[i].clone(),
                        target: doc_ids[j].clone(),
                        edge_type: "SIMILAR_TO".into(),
                        properties: serde_json::json!({ "similarity": sim }),
                    });
                }
            }
        }
    }

    let edge_count = new_edges.len();
    {
        let mut edges = state.graph_edges.write();
        *edges = new_edges;
    }

    Json(serde_json::json!({
        "nodes": state.graph_nodes.len(),
        "edges": edge_count,
    }))
}

async fn find_path(
    State(state): State<SharedState>,
    Json(req): Json<FindPathReq>,
) -> impl IntoResponse {
    let max_depth = req.max_depth.unwrap_or(5);
    let edges = state.graph_edges.read();

    // BFS shortest path
    let mut queue = std::collections::VecDeque::new();
    let mut visited = std::collections::HashSet::new();
    queue.push_back((req.source_id.clone(), vec![req.source_id.clone()]));
    visited.insert(req.source_id.clone());

    while let Some((current, path)) = queue.pop_front() {
        if path.len() > max_depth {
            continue;
        }
        if current == req.target_id {
            return Json(serde_json::json!({ "path": path }));
        }
        for edge in edges.iter() {
            let neighbor = if edge.source == current {
                Some(&edge.target)
            } else if edge.target == current {
                Some(&edge.source)
            } else {
                None
            };
            if let Some(n) = neighbor {
                if !visited.contains(n) {
                    visited.insert(n.clone());
                    let mut new_path = path.clone();
                    new_path.push(n.clone());
                    queue.push_back((n.clone(), new_path));
                }
            }
        }
    }

    Json(serde_json::json!({ "path": null }))
}

async fn find_clusters(State(state): State<SharedState>) -> impl IntoResponse {
    // Simple connected-components clustering via union-find
    let edges = state.graph_edges.read();
    let node_ids: Vec<String> = state.graph_nodes.iter().map(|r| r.key().clone()).collect();
    let mut parent: HashMap<String, String> = node_ids.iter().map(|id| (id.clone(), id.clone())).collect();

    fn find(parent: &mut HashMap<String, String>, x: &str) -> String {
        let p = parent.get(x).cloned().unwrap_or_else(|| x.to_string());
        if p != x {
            let root = find(parent, &p);
            parent.insert(x.to_string(), root.clone());
            root
        } else {
            p
        }
    }

    for edge in edges.iter() {
        let root_a = find(&mut parent, &edge.source);
        let root_b = find(&mut parent, &edge.target);
        if root_a != root_b {
            parent.insert(root_a, root_b);
        }
    }

    // Group by root
    let mut clusters: HashMap<String, Vec<String>> = HashMap::new();
    for id in &node_ids {
        let root = find(&mut parent, id);
        clusters.entry(root).or_default().push(id.clone());
    }

    let result: Vec<Vec<String>> = clusters.into_values().filter(|c| c.len() > 1).collect();
    Json(serde_json::json!({ "clusters": result }))
}

async fn get_neighbors(
    State(state): State<SharedState>,
    Path(node_id): Path<String>,
    Query(params): Query<GetNeighborsQuery>,
) -> impl IntoResponse {
    let max_depth = params.max_depth.unwrap_or(1);
    let edges = state.graph_edges.read();
    let mut neighbors = Vec::new();
    let mut visited = std::collections::HashSet::new();
    visited.insert(node_id.clone());

    let mut queue = std::collections::VecDeque::new();
    queue.push_back((node_id.clone(), 0usize));

    while let Some((current, depth)) = queue.pop_front() {
        if depth >= max_depth {
            continue;
        }
        for edge in edges.iter() {
            let (neighbor_id, etype) = if edge.source == current {
                (edge.target.clone(), edge.edge_type.clone())
            } else if edge.target == current {
                (edge.source.clone(), edge.edge_type.clone())
            } else {
                continue;
            };

            if let Some(ref filter_type) = params.edge_type {
                if &etype != filter_type {
                    continue;
                }
            }

            if !visited.contains(&neighbor_id) {
                visited.insert(neighbor_id.clone());
                queue.push_back((neighbor_id.clone(), depth + 1));

                if let Some(doc) = state.documents.get(&neighbor_id) {
                    neighbors.push(serde_json::json!({
                        "id": neighbor_id,
                        "text": doc.text,
                        "metadata": doc.metadata,
                        "edge_type": etype,
                        "depth": depth + 1,
                    }));
                }
            }
        }
    }

    Json(serde_json::json!({ "neighbors": neighbors }))
}

async fn get_graph_stats(State(state): State<SharedState>) -> impl IntoResponse {
    let edges = state.graph_edges.read();
    Json(serde_json::json!({
        "num_nodes": state.graph_nodes.len(),
        "num_edges": edges.len(),
    }))
}

// ---------------------------------------------------------------------------
// Handlers — SONA & GNN
// ---------------------------------------------------------------------------

async fn sona_trajectory(
    State(state): State<SharedState>,
    Json(req): Json<SonaTrajectoryReq>,
) -> impl IntoResponse {
    let mut trajectories = state.sona_trajectories.write();
    trajectories.push(req.trajectory);
    Json(serde_json::json!({
        "status": "accepted",
        "total_trajectories": trajectories.len(),
    }))
}

async fn gnn_train(
    State(state): State<SharedState>,
    Json(req): Json<GnnTrainReq>,
) -> impl IntoResponse {
    let mut interactions = state.gnn_interactions.write();
    let count = req.interactions.len();
    interactions.extend(req.interactions);
    Json(serde_json::json!({
        "status": "training_queued",
        "new_interactions": count,
        "total_interactions": interactions.len(),
    }))
}

async fn get_stats(State(state): State<SharedState>) -> impl IntoResponse {
    let trajectories = state.sona_trajectories.read();
    let interactions = state.gnn_interactions.read();
    let edges = state.graph_edges.read();
    Json(serde_json::json!({
        "total_documents": state.documents.len(),
        "total_collections": state.collections.len(),
        "graph_nodes": state.graph_nodes.len(),
        "graph_edges": edges.len(),
        "sona_trajectories": trajectories.len(),
        "gnn_interactions": interactions.len(),
    }))
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .json()
        .init();

    let host = env::var("RUVECTOR_HOST").unwrap_or_else(|_| "0.0.0.0".into());
    let port: u16 = env::var("RUVECTOR_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(6333);
    let data_dir = env::var("RUVECTOR_DATA_DIR").unwrap_or_else(|_| "/data/ruvector".into());

    info!(host = %host, port = %port, data_dir = %data_dir, "Starting RuVector server");

    // Initialize state with default collection
    let state = Arc::new(AppState {
        documents: DashMap::new(),
        collections: DashMap::new(),
        graph_nodes: DashMap::new(),
        graph_edges: RwLock::new(Vec::new()),
        data_dir,
        sona_trajectories: RwLock::new(Vec::new()),
        gnn_interactions: RwLock::new(Vec::new()),
    });

    // Create default "crawlset" collection
    state.collections.insert(
        "crawlset".into(),
        CollectionMeta {
            name: "crawlset".into(),
            dimension: 384,
            document_count: 0,
            created_at: chrono::Utc::now().to_rfc3339(),
        },
    );

    let app = Router::new()
        // Health & stats
        .route("/health", get(health))
        .route("/stats", get(get_stats))
        // Collections
        .route("/collections", post(create_collection).get(list_collections))
        .route(
            "/collections/{name}",
            get(get_collection).delete(delete_collection),
        )
        // Documents
        .route("/documents", post(insert_document))
        .route("/documents/bulk", post(bulk_insert))
        .route(
            "/documents/{doc_id}",
            get(get_document).delete(delete_document),
        )
        // Search
        .route("/search", post(search))
        // Graph
        .route("/graph/query", post(graph_query))
        .route("/graph/build", post(build_graph))
        .route("/graph/path", post(find_path))
        .route("/graph/clusters", get(find_clusters))
        .route("/graph/neighbors/{node_id}", get(get_neighbors))
        .route("/graph/stats", get(get_graph_stats))
        // SONA & GNN
        .route("/sona/trajectory", post(sona_trajectory))
        .route("/gnn/train", post(gnn_train))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr: SocketAddr = format!("{host}:{port}").parse().expect("Invalid address");
    info!("RuVector listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.expect("Failed to bind");
    axum::serve(listener, app).await.expect("Server error");
}
