//! RuVector HTTP Server
//!
//! Thin binary entrypoint for the RuVector vector database service.
//! Exposes HNSW vector indexing, GNN self-learning, SONA optimization,
//! and Cypher-like graph queries over HTTP/JSON via Axum.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use dashmap::DashMap;
use parking_lot::{Mutex, RwLock};
use rusqlite::{params, Connection};
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
    #[serde(default)]
    parent_id: Option<String>,
    #[serde(default)]
    lineage_depth: u32,
    #[serde(default)]
    collection: Option<String>,
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
// Persistence (SQLite WAL)
// ---------------------------------------------------------------------------

struct Persistence {
    conn: Mutex<Connection>,
}

impl Persistence {
    fn open(data_dir: &str) -> Result<Self, rusqlite::Error> {
        let path = std::path::Path::new(data_dir).join("ruvector.db");
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let conn = Connection::open(&path)?;
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")?;
        let store = Self {
            conn: Mutex::new(conn),
        };
        store.create_tables()?;
        info!(path = %path.display(), "Opened persistence store");
        Ok(store)
    }

    fn create_tables(&self) -> Result<(), rusqlite::Error> {
        let conn = self.conn.lock();
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                embedding BLOB NOT NULL,
                created_at TEXT NOT NULL,
                parent_id TEXT,
                lineage_depth INTEGER NOT NULL DEFAULT 0,
                collection TEXT
            );
            CREATE TABLE IF NOT EXISTS collections (
                name TEXT PRIMARY KEY,
                dimension INTEGER NOT NULL DEFAULT 384,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                properties TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS graph_edges (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target);
            CREATE INDEX IF NOT EXISTS idx_docs_collection ON documents(collection);
            CREATE INDEX IF NOT EXISTS idx_docs_parent ON documents(parent_id);
            CREATE TABLE IF NOT EXISTS document_feedback (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                quality REAL,
                methylation_before REAL NOT NULL,
                methylation_after REAL NOT NULL,
                context_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_doc ON document_feedback(document_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_time ON document_feedback(created_at);",
        )?;
        Ok(())
    }

    fn save_document(&self, doc: &Document) {
        let conn = self.conn.lock();
        let embedding_bytes = embedding_to_bytes(&doc.embedding);
        let metadata_str = serde_json::to_string(&doc.metadata).unwrap_or_default();
        if let Err(e) = conn.execute(
            "INSERT OR REPLACE INTO documents (id, text, metadata, embedding, created_at, parent_id, lineage_depth, collection)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                doc.id,
                doc.text,
                metadata_str,
                embedding_bytes,
                doc.created_at,
                doc.parent_id,
                doc.lineage_depth,
                doc.collection,
            ],
        ) {
            warn!(error = %e, doc_id = %doc.id, "Failed to persist document");
        }
    }

    fn delete_document(&self, doc_id: &str) {
        let conn = self.conn.lock();
        if let Err(e) = conn.execute("DELETE FROM documents WHERE id = ?1", params![doc_id]) {
            warn!(error = %e, doc_id = %doc_id, "Failed to delete persisted document");
        }
    }

    fn save_collection(&self, meta: &CollectionMeta) {
        let conn = self.conn.lock();
        if let Err(e) = conn.execute(
            "INSERT OR REPLACE INTO collections (name, dimension, created_at)
             VALUES (?1, ?2, ?3)",
            params![meta.name, meta.dimension, meta.created_at],
        ) {
            warn!(error = %e, name = %meta.name, "Failed to persist collection");
        }
    }

    fn delete_collection(&self, name: &str) {
        let conn = self.conn.lock();
        if let Err(e) = conn.execute("DELETE FROM collections WHERE name = ?1", params![name]) {
            warn!(error = %e, name = %name, "Failed to delete persisted collection");
        }
    }

    fn save_graph_node(&self, node: &GraphNode) {
        let conn = self.conn.lock();
        let props = serde_json::to_string(&node.properties).unwrap_or_default();
        if let Err(e) = conn.execute(
            "INSERT OR REPLACE INTO graph_nodes (id, properties) VALUES (?1, ?2)",
            params![node.id, props],
        ) {
            warn!(error = %e, id = %node.id, "Failed to persist graph node");
        }
    }

    fn save_graph_edge(&self, edge: &GraphEdge) {
        let conn = self.conn.lock();
        let props = serde_json::to_string(&edge.properties).unwrap_or_default();
        if let Err(e) = conn.execute(
            "INSERT INTO graph_edges (source, target, edge_type, properties) VALUES (?1, ?2, ?3, ?4)",
            params![edge.source, edge.target, edge.edge_type, props],
        ) {
            warn!(error = %e, "Failed to persist graph edge");
        }
    }

    fn clear_graph(&self) {
        let conn = self.conn.lock();
        let _ = conn.execute_batch("DELETE FROM graph_nodes; DELETE FROM graph_edges;");
    }

    fn clear_graph_for_ids(&self, ids: &[String]) {
        if ids.is_empty() {
            return;
        }
        let conn = self.conn.lock();
        // Build a comma-separated list of quoted IDs for SQL IN clause
        let placeholders: Vec<String> = ids.iter().map(|id| format!("'{}'", id.replace('\'', "''"))).collect();
        let in_clause = placeholders.join(",");
        let delete_nodes = format!("DELETE FROM graph_nodes WHERE id IN ({})", in_clause);
        let delete_edges = format!(
            "DELETE FROM graph_edges WHERE source IN ({0}) OR target IN ({0})",
            in_clause
        );
        let _ = conn.execute_batch(&format!("{};{};", delete_nodes, delete_edges));
    }

    fn save_feedback(
        &self,
        document_id: &str,
        feedback_type: &str,
        quality: Option<f64>,
        methylation_before: f64,
        methylation_after: f64,
        context_id: Option<&str>,
    ) {
        let conn = self.conn.lock();
        if let Err(e) = conn.execute(
            "INSERT INTO document_feedback (document_id, feedback_type, quality, methylation_before, methylation_after, context_id, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                document_id,
                feedback_type,
                quality,
                methylation_before,
                methylation_after,
                context_id,
                chrono::Utc::now().to_rfc3339(),
            ],
        ) {
            warn!(error = %e, doc_id = %document_id, "Failed to persist feedback");
        }
    }

    fn update_document_metadata(&self, doc_id: &str, metadata: &serde_json::Value) {
        let conn = self.conn.lock();
        let metadata_str = serde_json::to_string(metadata).unwrap_or_default();
        if let Err(e) = conn.execute(
            "UPDATE documents SET metadata = ?1 WHERE id = ?2",
            params![metadata_str, doc_id],
        ) {
            warn!(error = %e, doc_id = %doc_id, "Failed to update document metadata");
        }
    }

    fn count_feedback(&self, collection: Option<&str>) -> i64 {
        let conn = self.conn.lock();
        let count: i64 = if let Some(col) = collection {
            conn.query_row(
                "SELECT COUNT(*) FROM document_feedback df INNER JOIN documents d ON df.document_id = d.id WHERE d.collection = ?1",
                params![col],
                |row| row.get(0),
            )
            .unwrap_or(0)
        } else {
            conn.query_row(
                "SELECT COUNT(*) FROM document_feedback",
                [],
                |row| row.get(0),
            )
            .unwrap_or(0)
        };
        count
    }

    fn load_documents(&self) -> Vec<Document> {
        let conn = self.conn.lock();
        let mut stmt = match conn.prepare(
            "SELECT id, text, metadata, embedding, created_at, parent_id, lineage_depth, collection FROM documents",
        ) {
            Ok(s) => s,
            Err(e) => {
                warn!(error = %e, "Failed to load documents");
                return Vec::new();
            }
        };
        let result: Vec<Document> = stmt
            .query_map([], |row| {
                let metadata_str: String = row.get(2)?;
                let embedding_bytes: Vec<u8> = row.get(3)?;
                Ok(Document {
                    id: row.get(0)?,
                    text: row.get(1)?,
                    metadata: serde_json::from_str(&metadata_str)
                        .unwrap_or(serde_json::Value::Null),
                    embedding: bytes_to_embedding(&embedding_bytes),
                    created_at: row.get(4)?,
                    parent_id: row.get(5)?,
                    lineage_depth: row.get::<_, u32>(6).unwrap_or(0),
                    collection: row.get(7)?,
                })
            })
            .map(|rows| rows.filter_map(|r| r.ok()).collect())
            .unwrap_or_default();
        result
    }

    fn load_collections(&self) -> Vec<CollectionMeta> {
        let conn = self.conn.lock();
        let mut stmt = match conn.prepare("SELECT name, dimension, created_at FROM collections") {
            Ok(s) => s,
            Err(e) => {
                warn!(error = %e, "Failed to load collections");
                return Vec::new();
            }
        };
        let result: Vec<CollectionMeta> = stmt
            .query_map([], |row| {
                Ok(CollectionMeta {
                    name: row.get(0)?,
                    dimension: row.get(1)?,
                    document_count: 0,
                    created_at: row.get(2)?,
                })
            })
            .map(|rows| rows.filter_map(|r| r.ok()).collect())
            .unwrap_or_default();
        result
    }

    fn load_graph_nodes(&self) -> Vec<GraphNode> {
        let conn = self.conn.lock();
        let mut stmt = match conn.prepare("SELECT id, properties FROM graph_nodes") {
            Ok(s) => s,
            Err(e) => {
                warn!(error = %e, "Failed to load graph nodes");
                return Vec::new();
            }
        };
        let result: Vec<GraphNode> = stmt
            .query_map([], |row| {
                let props_str: String = row.get(1)?;
                Ok(GraphNode {
                    id: row.get(0)?,
                    properties: serde_json::from_str(&props_str)
                        .unwrap_or(serde_json::Value::Null),
                })
            })
            .map(|rows| rows.filter_map(|r| r.ok()).collect())
            .unwrap_or_default();
        result
    }

    fn load_graph_edges(&self) -> Vec<GraphEdge> {
        let conn = self.conn.lock();
        let mut stmt = match conn.prepare(
            "SELECT source, target, edge_type, properties FROM graph_edges",
        ) {
            Ok(s) => s,
            Err(e) => {
                warn!(error = %e, "Failed to load graph edges");
                return Vec::new();
            }
        };
        let result: Vec<GraphEdge> = stmt
            .query_map([], |row| {
                let props_str: String = row.get(3)?;
                Ok(GraphEdge {
                    source: row.get(0)?,
                    target: row.get(1)?,
                    edge_type: row.get(2)?,
                    properties: serde_json::from_str(&props_str)
                        .unwrap_or(serde_json::Value::Null),
                })
            })
            .map(|rows| rows.filter_map(|r| r.ok()).collect())
            .unwrap_or_default();
        result
    }
}

fn embedding_to_bytes(embedding: &[f32]) -> Vec<u8> {
    embedding
        .iter()
        .flat_map(|f| f.to_le_bytes())
        .collect()
}

fn bytes_to_embedding(bytes: &[u8]) -> Vec<f32> {
    bytes
        .chunks_exact(4)
        .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
        .collect()
}

// ---------------------------------------------------------------------------
// Application state
// ---------------------------------------------------------------------------

struct AppState {
    documents: DashMap<String, Document>,
    collections: DashMap<String, CollectionMeta>,
    graph_nodes: DashMap<String, GraphNode>,
    graph_edges: RwLock<Vec<GraphEdge>>,
    persistence: Persistence,
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
    parent_id: Option<String>,
    lineage_depth: Option<u32>,
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
    #[allow(dead_code)]
    filter_metadata: Option<serde_json::Value>,
    decay_halflife_hours: Option<f64>,
}

#[derive(Serialize)]
struct SearchResult {
    id: String,
    text: String,
    metadata: serde_json::Value,
    score: f64,
    raw_score: f64,
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
struct CreateEdgeReq {
    source: String,
    target: String,
    edge_type: String,
    properties: Option<serde_json::Value>,
}

#[derive(Deserialize)]
struct FeedbackReq {
    feedback_type: String,
    quality: Option<f64>,
    context_id: Option<String>,
}

#[derive(Serialize)]
struct MethylationStats {
    collection: String,
    total_docs: usize,
    mean_methylation: f64,
    fully_active: usize,
    partially_silenced: usize,
    mostly_silenced: usize,
    feedback_count: i64,
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
    state.persistence.save_collection(&meta);
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
    state.persistence.delete_collection(&name);
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
    let col_name = req.collection.clone().unwrap_or_else(|| "default".into());

    // Compute lineage_depth: if parent_id given and no explicit depth, look up parent
    let lineage_depth = req.lineage_depth.unwrap_or_else(|| {
        if let Some(ref pid) = req.parent_id {
            state
                .documents
                .get(pid)
                .map(|p| p.lineage_depth + 1)
                .unwrap_or(1)
        } else {
            0
        }
    });

    let doc = Document {
        id: doc_id.clone(),
        text: req.text,
        metadata: req.metadata.unwrap_or(serde_json::Value::Null),
        embedding: req.embedding,
        created_at: chrono::Utc::now().to_rfc3339(),
        parent_id: req.parent_id,
        lineage_depth,
        collection: Some(col_name.clone()),
    };

    state.persistence.save_document(&doc);
    state.documents.insert(doc_id.clone(), doc);

    // Update collection count (filtered to this collection only)
    if let Some(mut col) = state.collections.get_mut(&col_name) {
        col.document_count = state.documents.iter().filter(|d| d.collection.as_deref() == Some(&col_name)).count();
    }

    (
        StatusCode::CREATED,
        Json(serde_json::json!({ "id": doc_id, "lineage_depth": lineage_depth })),
    )
}

async fn bulk_insert(
    State(state): State<SharedState>,
    Json(req): Json<BulkInsertReq>,
) -> impl IntoResponse {
    let col_name = req.collection.unwrap_or_else(|| "default".into());
    let mut ids = Vec::with_capacity(req.documents.len());
    for doc_req in req.documents {
        let doc_id = doc_req.id.unwrap_or_else(|| Uuid::new_v4().to_string());
        let lineage_depth = doc_req.lineage_depth.unwrap_or_else(|| {
            if let Some(ref pid) = doc_req.parent_id {
                state.documents.get(pid).map(|p| p.lineage_depth + 1).unwrap_or(1)
            } else {
                0
            }
        });
        let doc = Document {
            id: doc_id.clone(),
            text: doc_req.text,
            metadata: doc_req.metadata.unwrap_or(serde_json::Value::Null),
            embedding: doc_req.embedding,
            created_at: chrono::Utc::now().to_rfc3339(),
            parent_id: doc_req.parent_id,
            lineage_depth,
            collection: Some(doc_req.collection.unwrap_or_else(|| col_name.clone())),
        };
        state.persistence.save_document(&doc);
        state.documents.insert(doc_id.clone(), doc);
        ids.push(doc_id);
    }

    if let Some(mut col) = state.collections.get_mut(&col_name) {
        col.document_count = state.documents.iter().filter(|d| d.collection.as_deref() == Some(&col_name)).count();
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
            "embedding": doc.embedding,
            "created_at": doc.created_at,
            "parent_id": doc.parent_id,
            "lineage_depth": doc.lineage_depth,
            "collection": doc.collection,
        }))),
        None => Err((StatusCode::NOT_FOUND, "Document not found".to_string())),
    }
}

async fn delete_document(
    State(state): State<SharedState>,
    Path(doc_id): Path<String>,
) -> impl IntoResponse {
    match state.documents.remove(&doc_id) {
        Some(_) => {
            state.persistence.delete_document(&doc_id);
            StatusCode::NO_CONTENT
        }
        None => StatusCode::NOT_FOUND,
    }
}

// ---------------------------------------------------------------------------
// Handlers — Search
// ---------------------------------------------------------------------------

fn cosine_similarity(a: &[f32], b: &[f32]) -> f64 {
    // Refuse to compare mismatched dimensions — zip() silently truncates
    if a.len() != b.len() {
        return 0.0;
    }
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
    let now = chrono::Utc::now();

    let mut scored: Vec<SearchResult> = state
        .documents
        .iter()
        .filter(|entry| {
            // Apply collection filter if specified
            if let Some(ref col) = req.collection {
                entry.value().collection.as_deref() == Some(col.as_str())
            } else {
                true
            }
        })
        .map(|entry| {
            let doc = entry.value();
            let raw_score = cosine_similarity(&req.embedding, &doc.embedding);

            // Methylation-weighted scoring
            let methylation = doc
                .metadata
                .get("methylation_score")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0)
                .clamp(0.0, 1.0);

            // Temporal decay: old methylation marks fade toward 0
            let effective_methylation = if let Some(halflife) = req.decay_halflife_hours {
                if halflife > 0.0 {
                    if let Some(last_adj) = doc.metadata.get("methylation_last_adjusted").and_then(|v| v.as_str()) {
                        if let Ok(last_time) = chrono::DateTime::parse_from_rfc3339(last_adj) {
                            let elapsed_hours = (now - last_time.with_timezone(&chrono::Utc))
                                .num_seconds() as f64
                                / 3600.0;
                            let elapsed_halflives = elapsed_hours / halflife;
                            let decay_factor = 0.5_f64.powf(elapsed_halflives);
                            methylation * decay_factor
                        } else {
                            methylation
                        }
                    } else {
                        methylation
                    }
                } else {
                    methylation
                }
            } else {
                methylation
            };

            let weighted_score = raw_score * (1.0 - effective_methylation);

            SearchResult {
                id: doc.id.clone(),
                text: doc.text.clone(),
                metadata: doc.metadata.clone(),
                score: weighted_score,
                raw_score,
            }
        })
        .collect();

    // Sort by weighted score descending
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

    // Collect document IDs scoped to the requested collection
    let scoped_doc_ids: Vec<String> = state
        .documents
        .iter()
        .filter(|entry| {
            if let Some(ref col) = req.collection {
                entry.value().collection.as_deref() == Some(col.as_str())
            } else {
                true
            }
        })
        .map(|e| e.key().clone())
        .collect();

    // Clear only the scoped nodes/edges (not the entire graph)
    if req.collection.is_some() {
        // Remove in-memory nodes for scoped docs
        for id in &scoped_doc_ids {
            state.graph_nodes.remove(id);
        }
        // Remove in-memory edges involving scoped docs
        {
            let mut edges = state.graph_edges.write();
            edges.retain(|e| {
                !scoped_doc_ids.contains(&e.source) && !scoped_doc_ids.contains(&e.target)
            });
        }
        // Remove persisted nodes/edges for scoped docs
        state.persistence.clear_graph_for_ids(&scoped_doc_ids);
    } else {
        // No collection filter — clear everything (legacy behavior)
        state.graph_nodes.clear();
        {
            let mut edges = state.graph_edges.write();
            edges.clear();
        }
        state.persistence.clear_graph();
    }

    // Create nodes from scoped documents
    for id in &scoped_doc_ids {
        if let Some(doc) = state.documents.get(id) {
            let node = GraphNode {
                id: doc.id.clone(),
                properties: serde_json::json!({
                    "text": doc.text,
                    "metadata": doc.metadata,
                }),
            };
            state.persistence.save_graph_node(&node);
            state.graph_nodes.insert(doc.id.clone(), node);
        }
    }

    // Create edges based on similarity (only within scoped documents)
    let mut new_edges = Vec::new();

    for i in 0..scoped_doc_ids.len() {
        for j in (i + 1)..scoped_doc_ids.len() {
            if let (Some(a), Some(b)) = (
                state.documents.get(&scoped_doc_ids[i]),
                state.documents.get(&scoped_doc_ids[j]),
            ) {
                let sim = cosine_similarity(&a.embedding, &b.embedding);
                if sim >= threshold {
                    let edge = GraphEdge {
                        source: scoped_doc_ids[i].clone(),
                        target: scoped_doc_ids[j].clone(),
                        edge_type: "SIMILAR_TO".into(),
                        properties: serde_json::json!({ "similarity": sim }),
                    };
                    state.persistence.save_graph_edge(&edge);
                    new_edges.push(edge);
                }
            }
        }
    }

    let new_edge_count = new_edges.len();
    {
        let mut edges = state.graph_edges.write();
        edges.extend(new_edges);
    }

    Json(serde_json::json!({
        "nodes": state.graph_nodes.len(),
        "edges": new_edge_count,
        "collection": req.collection,
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

async fn get_lineage(
    State(state): State<SharedState>,
    Path(doc_id): Path<String>,
) -> impl IntoResponse {
    let max_depth: u32 = 64; // Parent chain cap per upstream spec
    let mut chain = Vec::new();
    let mut current_id = Some(doc_id.clone());
    let mut depth = 0u32;

    while let Some(ref id) = current_id {
        if depth > max_depth {
            break;
        }
        match state.documents.get(id) {
            Some(doc) => {
                chain.push(serde_json::json!({
                    "id": doc.id,
                    "parent_id": doc.parent_id,
                    "lineage_depth": doc.lineage_depth,
                    "collection": doc.collection,
                    "created_at": doc.created_at,
                }));
                current_id = doc.parent_id.clone();
                depth += 1;
            }
            None => {
                // Parent not found — record broken link and stop
                if depth > 0 {
                    chain.push(serde_json::json!({
                        "id": id,
                        "error": "parent_not_found",
                    }));
                }
                break;
            }
        }
    }

    if chain.is_empty() {
        return Err((StatusCode::NOT_FOUND, "Document not found".to_string()));
    }

    Ok(Json(serde_json::json!({
        "doc_id": doc_id,
        "chain_length": chain.len(),
        "lineage": chain,
    })))
}

async fn create_edge(
    State(state): State<SharedState>,
    Json(req): Json<CreateEdgeReq>,
) -> impl IntoResponse {
    let edge = GraphEdge {
        source: req.source.clone(),
        target: req.target.clone(),
        edge_type: req.edge_type.clone(),
        properties: req.properties.unwrap_or(serde_json::Value::Null),
    };

    // Ensure graph nodes exist for both endpoints (create stubs if missing)
    for node_id in [&req.source, &req.target] {
        if !state.graph_nodes.contains_key(node_id) {
            let props = state
                .documents
                .get(node_id)
                .map(|doc| {
                    serde_json::json!({
                        "text": doc.text,
                        "metadata": doc.metadata,
                    })
                })
                .unwrap_or(serde_json::json!({}));
            let node = GraphNode {
                id: node_id.clone(),
                properties: props,
            };
            state.persistence.save_graph_node(&node);
            state.graph_nodes.insert(node_id.clone(), node);
        }
    }

    state.persistence.save_graph_edge(&edge);
    {
        let mut edges = state.graph_edges.write();
        edges.push(edge);
    }

    info!(
        source = %req.source,
        target = %req.target,
        edge_type = %req.edge_type,
        "Created graph edge"
    );

    (
        StatusCode::CREATED,
        Json(serde_json::json!({
            "source": req.source,
            "target": req.target,
            "edge_type": req.edge_type,
            "status": "created",
        })),
    )
}

// ---------------------------------------------------------------------------
// Handlers — Methylation Feedback
// ---------------------------------------------------------------------------

async fn document_feedback(
    State(state): State<SharedState>,
    Path(doc_id): Path<String>,
    Json(req): Json<FeedbackReq>,
) -> impl IntoResponse {
    let doc = match state.documents.get(&doc_id) {
        Some(d) => d.clone(),
        None => return Err((StatusCode::NOT_FOUND, "Document not found".to_string())),
    };

    let current_methylation = doc
        .metadata
        .get("methylation_score")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0)
        .clamp(0.0, 1.0);

    // Max methylation: civilization priors get resistance cap (default 1.0)
    let max_methylation = doc
        .metadata
        .get("methylation_resistance")
        .and_then(|v| v.as_f64())
        .unwrap_or(1.0)
        .clamp(0.0, 1.0);

    let new_methylation = match req.feedback_type.as_str() {
        "grounded" => {
            // Demethylate 10% — reward usefulness (like Olffr151 hypomethylation)
            let factor = req.quality.unwrap_or(0.90).clamp(0.5, 0.99);
            (current_methylation * factor).max(0.0)
        }
        "ignored" => {
            // Methylate 5% — penalize noise
            let increment = req.quality.map(|q| q * 0.1).unwrap_or(0.05);
            (current_methylation + increment).min(max_methylation)
        }
        "retrieved" => {
            // Neutral — just recording retrieval
            current_methylation
        }
        _ => {
            return Err((
                StatusCode::BAD_REQUEST,
                format!("Unknown feedback_type: '{}'. Expected: grounded, ignored, retrieved", req.feedback_type),
            ));
        }
    };

    // Update document metadata atomically
    let mut new_metadata = doc.metadata.clone();
    if let Some(obj) = new_metadata.as_object_mut() {
        obj.insert(
            "methylation_score".to_string(),
            serde_json::json!(new_methylation),
        );
        obj.insert(
            "methylation_last_adjusted".to_string(),
            serde_json::json!(chrono::Utc::now().to_rfc3339()),
        );
    }

    // Update in-memory document
    if let Some(mut entry) = state.documents.get_mut(&doc_id) {
        entry.metadata = new_metadata.clone();
    }

    // Persist metadata update
    state.persistence.update_document_metadata(&doc_id, &new_metadata);

    // Audit trail
    state.persistence.save_feedback(
        &doc_id,
        &req.feedback_type,
        req.quality,
        current_methylation,
        new_methylation,
        req.context_id.as_deref(),
    );

    info!(
        doc_id = %doc_id,
        feedback_type = %req.feedback_type,
        methylation_before = %current_methylation,
        methylation_after = %new_methylation,
        "Methylation feedback applied"
    );

    Ok(Json(serde_json::json!({
        "id": doc_id,
        "feedback_type": req.feedback_type,
        "methylation_before": current_methylation,
        "methylation_after": new_methylation,
        "max_methylation": max_methylation,
    })))
}

async fn methylation_stats(
    State(state): State<SharedState>,
    Path(collection): Path<String>,
) -> impl IntoResponse {
    let mut total_docs = 0usize;
    let mut methylation_sum = 0.0f64;
    let mut fully_active = 0usize;
    let mut partially_silenced = 0usize;
    let mut mostly_silenced = 0usize;

    for entry in state.documents.iter() {
        let doc = entry.value();
        if doc.collection.as_deref() != Some(collection.as_str()) {
            continue;
        }
        total_docs += 1;
        let score = doc
            .metadata
            .get("methylation_score")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        methylation_sum += score;
        if score < 0.05 {
            fully_active += 1;
        } else if score < 0.50 {
            partially_silenced += 1;
        } else {
            mostly_silenced += 1;
        }
    }

    let mean = if total_docs > 0 {
        methylation_sum / total_docs as f64
    } else {
        0.0
    };

    let feedback_count = state.persistence.count_feedback(Some(&collection));

    Json(MethylationStats {
        collection,
        total_docs,
        mean_methylation: (mean * 1000.0).round() / 1000.0,
        fully_active,
        partially_silenced,
        mostly_silenced,
        feedback_count,
    })
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

    // Open persistence store
    let persistence = Persistence::open(&data_dir).expect("Failed to open persistence store");

    // Load persisted data
    let documents = DashMap::new();
    let collections = DashMap::new();
    let graph_nodes = DashMap::new();

    for doc in persistence.load_documents() {
        documents.insert(doc.id.clone(), doc);
    }
    for col in persistence.load_collections() {
        collections.insert(col.name.clone(), col);
    }
    for node in persistence.load_graph_nodes() {
        graph_nodes.insert(node.id.clone(), node);
    }
    let persisted_edges = persistence.load_graph_edges();

    info!(
        documents = documents.len(),
        collections = collections.len(),
        graph_nodes = graph_nodes.len(),
        graph_edges = persisted_edges.len(),
        "Loaded persisted state"
    );

    // Update collection document counts from loaded data
    // Collect keys first to avoid DashMap deadlock (iter + get_mut on same map)
    let col_names: Vec<String> = collections.iter().map(|c| c.key().clone()).collect();
    for name in &col_names {
        let count = documents
            .iter()
            .filter(|d| d.collection.as_deref() == Some(name.as_str()))
            .count();
        if let Some(mut c) = collections.get_mut(name) {
            c.document_count = count;
        }
    }

    // Ensure default "crawlset" collection exists
    if !collections.contains_key("crawlset") {
        let meta = CollectionMeta {
            name: "crawlset".into(),
            dimension: 384,
            document_count: 0,
            created_at: chrono::Utc::now().to_rfc3339(),
        };
        persistence.save_collection(&meta);
        collections.insert("crawlset".into(), meta);
    }

    let state = Arc::new(AppState {
        documents,
        collections,
        graph_nodes,
        graph_edges: RwLock::new(persisted_edges),
        persistence,
        sona_trajectories: RwLock::new(Vec::new()),
        gnn_interactions: RwLock::new(Vec::new()),
    });

    let app = Router::new()
        // Health & stats
        .route("/health", get(health))
        .route("/stats", get(get_stats))
        // Collections
        .route("/collections", post(create_collection).get(list_collections))
        .route(
            "/collections/:name",
            get(get_collection).delete(delete_collection),
        )
        // Documents
        .route("/documents", post(insert_document))
        .route("/documents/bulk", post(bulk_insert))
        .route(
            "/documents/:doc_id",
            get(get_document).delete(delete_document),
        )
        // Search
        .route("/search", post(search))
        // Methylation feedback & stats
        .route("/documents/:doc_id/feedback", post(document_feedback))
        .route("/methylation/stats/:collection", get(methylation_stats))
        // Graph
        .route("/graph/query", post(graph_query))
        .route("/graph/build", post(build_graph))
        .route("/graph/path", post(find_path))
        .route("/graph/clusters", get(find_clusters))
        .route("/graph/neighbors/:node_id", get(get_neighbors))
        .route("/graph/stats", get(get_graph_stats))
        .route("/graph/edges", post(create_edge))
        // Lineage
        .route("/lineage/:doc_id", get(get_lineage))
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
