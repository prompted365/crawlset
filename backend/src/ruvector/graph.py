"""
Graph Operations for knowledge graph features in RuVector.

Provides entity relationship extraction, path finding, clustering,
and basic Cypher-like query support.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)


class GraphNode:
    """Represents a node in the knowledge graph."""

    def __init__(self, node_id: str, properties: Optional[Dict[str, Any]] = None):
        """
        Initialize graph node.

        Args:
            node_id: Unique node identifier
            properties: Node properties/attributes
        """
        self.node_id = node_id
        self.properties = properties or {}
        self.edges: List[GraphEdge] = []

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to this node."""
        self.edges.append(edge)

    def __repr__(self) -> str:
        return f"GraphNode(id={self.node_id}, edges={len(self.edges)})"


class GraphEdge:
    """Represents an edge in the knowledge graph."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize graph edge.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type/label of the relationship
            properties: Edge properties/attributes
        """
        self.source_id = source_id
        self.target_id = target_id
        self.edge_type = edge_type
        self.properties = properties or {}

    def __repr__(self) -> str:
        return f"GraphEdge({self.source_id}-[{self.edge_type}]->{self.target_id})"


class GraphOperations:
    """
    Graph operations for RuVector knowledge graph features.

    Features:
    - Entity relationship extraction
    - Path finding between documents
    - Cluster analysis using embeddings
    - Community detection
    - Basic Cypher-like query support
    """

    def __init__(self, client: Any):  # RuVectorClient
        """
        Initialize graph operations.

        Args:
            client: RuVectorClient instance
        """
        self.client = client
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

        logger.info("Initialized GraphOperations")

    async def extract_entities(
        self, text: str, entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from text.

        This is a placeholder for entity extraction. In production,
        you would use spaCy, BERT-based NER, or an LLM.

        Args:
            text: Input text
            entity_types: Filter by entity types (PERSON, ORG, etc.)

        Returns:
            List of extracted entities
        """
        # Placeholder: Simple pattern-based extraction
        # TODO: Integrate proper NER model (spaCy, transformers, etc.)

        entities = []

        # Simple heuristic: capitalized words/phrases
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        matches = re.findall(pattern, text)

        for match in set(matches):
            entities.append({
                "text": match,
                "type": "UNKNOWN",  # Would be determined by NER model
                "confidence": 0.5,
            })

        logger.debug(f"Extracted {len(entities)} entities from text")
        return entities

    async def build_graph_from_documents(
        self, similarity_threshold: float = 0.7
    ) -> None:
        """
        Build a graph from documents in the client.

        Creates nodes for each document and edges based on
        semantic similarity above the threshold.

        Args:
            similarity_threshold: Minimum similarity for creating an edge
        """
        if not self.client._initialized:
            await self.client.initialize()

        # Clear existing graph
        self.nodes.clear()
        self.edges.clear()

        # Create nodes for all documents
        for doc_id, doc in self.client._documents.items():
            node = GraphNode(
                node_id=doc_id,
                properties={
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                },
            )
            self.nodes[doc_id] = node

        # Create edges based on similarity
        doc_ids = list(self.client._documents.keys())
        for i, doc_id_a in enumerate(doc_ids):
            # Find similar documents
            results = await self.client.hybrid_search(
                query=self.client._documents[doc_id_a]["text"],
                top_k=20,
            )

            for result in results:
                doc_id_b = result["id"]
                if doc_id_a == doc_id_b:
                    continue

                score = result["score"]
                if score >= similarity_threshold:
                    edge = GraphEdge(
                        source_id=doc_id_a,
                        target_id=doc_id_b,
                        edge_type="SIMILAR_TO",
                        properties={"similarity": score},
                    )
                    self.edges.append(edge)
                    self.nodes[doc_id_a].add_edge(edge)

        logger.info(
            f"Built graph with {len(self.nodes)} nodes and {len(self.edges)} edges"
        )

    async def find_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> Optional[List[str]]:
        """
        Find shortest path between two documents using BFS.

        Args:
            source_id: Source document ID
            target_id: Target document ID
            max_depth: Maximum path length to search

        Returns:
            List of document IDs forming the path, or None if no path found
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        # BFS to find shortest path
        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        while queue:
            current_id, path = queue.popleft()

            if len(path) > max_depth:
                continue

            if current_id == target_id:
                return path

            # Explore neighbors
            current_node = self.nodes[current_id]
            for edge in current_node.edges:
                neighbor_id = edge.target_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return None

    async def find_clusters(
        self, eps: float = 0.3, min_samples: int = 2
    ) -> List[List[str]]:
        """
        Find clusters of similar documents using DBSCAN.

        Args:
            eps: Maximum distance between samples in a cluster
            min_samples: Minimum samples in a cluster

        Returns:
            List of clusters (each cluster is a list of doc IDs)
        """
        if not self.client._initialized:
            await self.client.initialize()

        if not self.client._documents:
            return []

        # Get embeddings for all documents
        doc_ids = list(self.client._documents.keys())
        embeddings = []

        for doc_id in doc_ids:
            label = self.client._id_to_label.get(doc_id)
            if label is not None and self.client._index:
                # Get embedding from index
                embedding = self.client._embedder._model.encode(
                    self.client._documents[doc_id]["text"]
                )
                embeddings.append(embedding)

        if not embeddings:
            return []

        # Perform DBSCAN clustering
        embeddings_array = np.array(embeddings)
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
        labels = clustering.fit_predict(embeddings_array)

        # Group documents by cluster
        clusters: Dict[int, List[str]] = defaultdict(list)
        for doc_id, label in zip(doc_ids, labels):
            if label != -1:  # -1 is noise in DBSCAN
                clusters[label].append(doc_id)

        result = list(clusters.values())
        logger.info(f"Found {len(result)} clusters")
        return result

    async def get_neighbors(
        self, doc_id: str, edge_type: Optional[str] = None, max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get neighboring documents in the graph.

        Args:
            doc_id: Document ID
            edge_type: Filter by edge type (optional)
            max_depth: Maximum depth to traverse

        Returns:
            List of neighbor documents with relationship info
        """
        if doc_id not in self.nodes:
            return []

        neighbors = []
        visited = {doc_id}
        queue = deque([(doc_id, 0)])

        while queue:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            current_node = self.nodes[current_id]
            for edge in current_node.edges:
                if edge_type and edge.edge_type != edge_type:
                    continue

                neighbor_id = edge.target_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

                    neighbor_doc = self.client._documents.get(neighbor_id)
                    if neighbor_doc:
                        neighbors.append({
                            "id": neighbor_id,
                            "text": neighbor_doc["text"],
                            "metadata": neighbor_doc.get("metadata", {}),
                            "edge_type": edge.edge_type,
                            "edge_properties": edge.properties,
                            "depth": depth + 1,
                        })

        return neighbors

    async def execute_query(self, cypher: str) -> Any:
        """
        Execute a Cypher-like query (subset of Cypher).

        Supports basic patterns:
        - MATCH (n) RETURN n
        - MATCH (n)-[r]->(m) WHERE ... RETURN ...
        - MATCH (n) WHERE n.property = value RETURN n

        Args:
            cypher: Cypher-like query string

        Returns:
            Query results
        """
        # Simple query parser for basic patterns
        cypher = cypher.strip()

        # Pattern: MATCH (n) RETURN n
        if re.match(r'MATCH\s+\((\w+)\)\s+RETURN\s+\1', cypher, re.IGNORECASE):
            # Return all nodes
            return [
                {
                    "id": node_id,
                    "properties": node.properties,
                }
                for node_id, node in self.nodes.items()
            ]

        # Pattern: MATCH (n)-[r]->(m) RETURN n, r, m
        match_pattern = re.match(
            r'MATCH\s+\((\w+)\)-\[(\w+):?(\w*)\]->\((\w+)\)\s+RETURN',
            cypher,
            re.IGNORECASE,
        )
        if match_pattern:
            results = []
            for edge in self.edges:
                source_node = self.nodes.get(edge.source_id)
                target_node = self.nodes.get(edge.target_id)

                if source_node and target_node:
                    results.append({
                        "source": {
                            "id": edge.source_id,
                            "properties": source_node.properties,
                        },
                        "edge": {
                            "type": edge.edge_type,
                            "properties": edge.properties,
                        },
                        "target": {
                            "id": edge.target_id,
                            "properties": target_node.properties,
                        },
                    })

            return results

        logger.warning(f"Unsupported Cypher query: {cypher}")
        return None

    async def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the graph.

        Returns:
            Dict with graph statistics
        """
        # Calculate degree distribution
        degrees = [len(node.edges) for node in self.nodes.values()]

        edge_types = defaultdict(int)
        for edge in self.edges:
            edge_types[edge.edge_type] += 1

        return {
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "avg_degree": sum(degrees) / len(degrees) if degrees else 0,
            "max_degree": max(degrees) if degrees else 0,
            "edge_types": dict(edge_types),
        }

    async def export_graph(self, format: str = "json") -> Any:
        """
        Export graph in various formats.

        Args:
            format: Export format ('json', 'cytoscape', 'networkx')

        Returns:
            Graph data in specified format
        """
        if format == "json":
            return {
                "nodes": [
                    {
                        "id": node_id,
                        "properties": node.properties,
                    }
                    for node_id, node in self.nodes.items()
                ],
                "edges": [
                    {
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "type": edge.edge_type,
                        "properties": edge.properties,
                    }
                    for edge in self.edges
                ],
            }
        elif format == "cytoscape":
            # Cytoscape.js format
            return {
                "nodes": [
                    {
                        "data": {
                            "id": node_id,
                            **node.properties,
                        }
                    }
                    for node_id, node in self.nodes.items()
                ],
                "edges": [
                    {
                        "data": {
                            "source": edge.source_id,
                            "target": edge.target_id,
                            "label": edge.edge_type,
                            **edge.properties,
                        }
                    }
                    for edge in self.edges
                ],
            }
        else:
            logger.warning(f"Unsupported export format: {format}")
            return None

    def __repr__(self) -> str:
        return (
            f"GraphOperations(nodes={len(self.nodes)}, edges={len(self.edges)})"
        )


async def create_graph(client: Any) -> GraphOperations:  # RuVectorClient
    """
    Factory function to create a GraphOperations instance.

    Args:
        client: Initialized RuVectorClient

    Returns:
        GraphOperations instance
    """
    graph = GraphOperations(client)
    # Optionally build graph on creation
    # await graph.build_graph_from_documents()
    return graph
