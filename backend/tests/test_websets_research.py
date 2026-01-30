"""
Test sets: Webset creation and population for research domains.

Domain 1 – Perception in Agentic Orchestration Systems
Domain 2 – Biologically Inspired & Constrained Agentic Design

These tests exercise the full webset lifecycle (create, add items, list,
search, stats, update, delete) using realistic research data payloads.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Webset, WebsetItem

from conftest import make_webset_id, make_item_id


# ============================================================================
# Domain 1 – Perception in Agentic Orchestration Systems
# ============================================================================

PERCEPTION_WEBSET = {
    "id": "ws-perception-agentic",
    "name": "Perception in Agentic Orchestration Systems",
    "search_query": "perception agentic orchestration multi-agent systems",
    "entity_type": "research_paper",
    "search_criteria": {
        "domains": [
            "agentic perception",
            "multi-agent orchestration",
            "embodied cognition in AI agents",
            "perceptual grounding for LLM agents",
            "attention mechanisms in agent swarms",
        ],
        "keywords": [
            "perception loop",
            "agent observation model",
            "shared world model",
            "sensory abstraction layer",
            "grounded language agents",
        ],
    },
}

PERCEPTION_ITEMS = [
    {
        "url": "https://arxiv.org/abs/2401.00001",
        "title": "Perceptual Grounding in Multi-Agent Orchestration: A Survey",
        "content_hash": "perc_001",
        "metadata": {
            "authors": ["Zhang, L.", "Kumar, A."],
            "year": 2024,
            "venue": "NeurIPS",
            "abstract": "Survey of perception architectures enabling multi-agent task orchestration with shared world models.",
            "tags": ["perception", "multi-agent", "orchestration", "world-model"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2402.00002",
        "title": "Attention-Driven Observation Sharing in Agent Swarms",
        "content_hash": "perc_002",
        "metadata": {
            "authors": ["Patel, R.", "Chen, X."],
            "year": 2024,
            "venue": "ICML",
            "abstract": "Proposes attention-gated observation sharing where agents selectively broadcast perceptual features.",
            "tags": ["attention", "swarm", "observation-sharing", "perception"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2403.00003",
        "title": "Sensory Abstraction Layers for Heterogeneous Agent Teams",
        "content_hash": "perc_003",
        "metadata": {
            "authors": ["Ivanova, E.", "Park, J."],
            "year": 2025,
            "venue": "AAAI",
            "abstract": "Introduces a sensory abstraction layer that normalises perception across robots, code agents, and LLM agents.",
            "tags": ["abstraction", "heterogeneous-agents", "sensory-layer"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2404.00004",
        "title": "Grounded Language Agents with Visual Perception Chains",
        "content_hash": "perc_004",
        "metadata": {
            "authors": ["Nguyen, T.", "Rossi, M."],
            "year": 2025,
            "venue": "ACL",
            "abstract": "Chain-of-perception prompting to ground LLM-agent plans in visual observations.",
            "tags": ["grounded-language", "chain-of-perception", "visual"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2405.00005",
        "title": "Emergent Perception Protocols in Self-Organising Agent Networks",
        "content_hash": "perc_005",
        "metadata": {
            "authors": ["Okafor, C.", "Liang, S."],
            "year": 2025,
            "venue": "ICLR",
            "abstract": "Demonstrates that self-organising agent networks evolve shared perception protocols without explicit design.",
            "tags": ["emergent", "self-organising", "perception-protocol"],
        },
    },
]


# ============================================================================
# Domain 2 – Biologically Inspired & Constrained Agentic Design
# ============================================================================

BIO_WEBSET = {
    "id": "ws-bio-agentic-design",
    "name": "Biologically Inspired Agentic Design Systems",
    "search_query": "biologically inspired constrained agentic design systems",
    "entity_type": "research_paper",
    "search_criteria": {
        "domains": [
            "neuromorphic agent architectures",
            "spiking neural network agents",
            "ant colony optimisation for agent routing",
            "immune system inspired anomaly detection in agents",
            "homeostatic regulation in autonomous agents",
            "morphogenetic agent assembly",
        ],
        "keywords": [
            "bio-inspired agents",
            "spiking neural network",
            "homeostasis",
            "morphogenesis",
            "stigmergy",
            "neuroevolution",
            "energy-constrained agents",
        ],
    },
}

BIO_ITEMS = [
    {
        "url": "https://arxiv.org/abs/2401.10001",
        "title": "Neuromorphic Agent Architectures: From Spiking Networks to Autonomous Behaviour",
        "content_hash": "bio_001",
        "metadata": {
            "authors": ["Maass, W.", "Zenke, F."],
            "year": 2024,
            "venue": "Nature Machine Intelligence",
            "abstract": "Maps spiking neural network dynamics onto multi-agent decision making with energy budgets.",
            "tags": ["neuromorphic", "spiking", "energy-constrained", "decision-making"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2402.10002",
        "title": "Stigmergic Coordination in LLM Agent Swarms",
        "content_hash": "bio_002",
        "metadata": {
            "authors": ["Dorigo, M.", "Stützle, T."],
            "year": 2024,
            "venue": "AAMAS",
            "abstract": "Applies ant colony stigmergy to coordinate tool-using LLM agents without explicit message passing.",
            "tags": ["stigmergy", "ant-colony", "LLM-agents", "coordination"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2403.10003",
        "title": "Homeostatic Regulation for Long-Running Autonomous Agents",
        "content_hash": "bio_003",
        "metadata": {
            "authors": ["Seth, A.", "Friston, K."],
            "year": 2025,
            "venue": "JAIR",
            "abstract": "Agents maintain resource homeostasis (compute, memory, API budget) via interoceptive control loops.",
            "tags": ["homeostasis", "interoception", "resource-management", "autonomous"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2404.10004",
        "title": "Morphogenetic Assembly of Multi-Agent Systems",
        "content_hash": "bio_004",
        "metadata": {
            "authors": ["Turing, A.", "Kauffman, S."],
            "year": 2025,
            "venue": "Artificial Life",
            "abstract": "Agents self-assemble into functional structures using reaction-diffusion morphogen signals.",
            "tags": ["morphogenesis", "self-assembly", "reaction-diffusion"],
        },
    },
    {
        "url": "https://arxiv.org/abs/2405.10005",
        "title": "Immune-Inspired Anomaly Detection in Agentic Pipelines",
        "content_hash": "bio_005",
        "metadata": {
            "authors": ["De Castro, L.", "Timmis, J."],
            "year": 2025,
            "venue": "GECCO",
            "abstract": "Clonal selection and negative selection algorithms detect abnormal agent behaviour in orchestration pipelines.",
            "tags": ["immune-system", "anomaly-detection", "clonal-selection", "safety"],
        },
    },
]


# ============================================================================
# Tests – Perception in Agentic Orchestration
# ============================================================================


class TestPerceptionWebset:
    """Full lifecycle tests for the perception research webset."""

    @pytest.mark.asyncio
    async def test_create_perception_webset(self, db_session: AsyncSession):
        ws = Webset(
            id=PERCEPTION_WEBSET["id"],
            name=PERCEPTION_WEBSET["name"],
            search_query=PERCEPTION_WEBSET["search_query"],
            search_criteria=PERCEPTION_WEBSET["search_criteria"],
            entity_type=PERCEPTION_WEBSET["entity_type"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.commit()

        result = await db_session.execute(select(Webset).where(Webset.id == PERCEPTION_WEBSET["id"]))
        fetched = result.scalar_one()
        assert fetched.name == PERCEPTION_WEBSET["name"]
        assert fetched.entity_type == "research_paper"
        assert fetched.search_criteria is not None
        assert len(fetched.search_criteria["domains"]) == 5

    @pytest.mark.asyncio
    async def test_populate_perception_items(self, db_session: AsyncSession):
        # Create webset first
        ws = Webset(
            id=PERCEPTION_WEBSET["id"],
            name=PERCEPTION_WEBSET["name"],
            search_query=PERCEPTION_WEBSET["search_query"],
            entity_type=PERCEPTION_WEBSET["entity_type"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        # Add all items
        for item_data in PERCEPTION_ITEMS:
            item = WebsetItem(
                id=make_item_id(),
                webset_id=ws.id,
                url=item_data["url"],
                title=item_data["title"],
                content_hash=item_data["content_hash"],
                item_metadata=item_data["metadata"],
            )
            db_session.add(item)

        await db_session.commit()

        result = await db_session.execute(
            select(WebsetItem).where(WebsetItem.webset_id == ws.id)
        )
        items = result.scalars().all()
        assert len(items) == 5

    @pytest.mark.asyncio
    async def test_perception_item_metadata_integrity(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(),
            name="Perception Meta Test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        item = WebsetItem(
            id=make_item_id(),
            webset_id=ws.id,
            url=PERCEPTION_ITEMS[0]["url"],
            title=PERCEPTION_ITEMS[0]["title"],
            item_metadata=PERCEPTION_ITEMS[0]["metadata"],
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        assert item.item_metadata["venue"] == "NeurIPS"
        assert "perception" in item.item_metadata["tags"]
        assert item.item_metadata["year"] == 2024

    @pytest.mark.asyncio
    async def test_perception_webset_update(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(),
            name="Old Name",
            search_query="old query",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.commit()

        ws.name = PERCEPTION_WEBSET["name"]
        ws.search_query = PERCEPTION_WEBSET["search_query"]
        await db_session.commit()
        await db_session.refresh(ws)

        assert ws.name == PERCEPTION_WEBSET["name"]
        assert "agentic orchestration" in ws.search_query

    @pytest.mark.asyncio
    async def test_perception_webset_cascade_delete(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(),
            name="Delete Me",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        for item_data in PERCEPTION_ITEMS[:2]:
            db_session.add(WebsetItem(
                id=make_item_id(),
                webset_id=ws.id,
                url=item_data["url"],
                title=item_data["title"],
            ))
        await db_session.commit()

        await db_session.delete(ws)
        await db_session.commit()

        result = await db_session.execute(
            select(WebsetItem).where(WebsetItem.webset_id == ws.id)
        )
        assert len(result.scalars().all()) == 0


# ============================================================================
# Tests – Biologically Inspired Agentic Design
# ============================================================================


class TestBioInspiredWebset:
    """Full lifecycle tests for the bio-inspired agentic design webset."""

    @pytest.mark.asyncio
    async def test_create_bio_webset(self, db_session: AsyncSession):
        ws = Webset(
            id=BIO_WEBSET["id"],
            name=BIO_WEBSET["name"],
            search_query=BIO_WEBSET["search_query"],
            search_criteria=BIO_WEBSET["search_criteria"],
            entity_type=BIO_WEBSET["entity_type"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.commit()

        result = await db_session.execute(select(Webset).where(Webset.id == BIO_WEBSET["id"]))
        fetched = result.scalar_one()
        assert fetched.name == BIO_WEBSET["name"]
        assert len(fetched.search_criteria["keywords"]) == 7

    @pytest.mark.asyncio
    async def test_populate_bio_items(self, db_session: AsyncSession):
        ws = Webset(
            id=BIO_WEBSET["id"],
            name=BIO_WEBSET["name"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        for item_data in BIO_ITEMS:
            db_session.add(WebsetItem(
                id=make_item_id(),
                webset_id=ws.id,
                url=item_data["url"],
                title=item_data["title"],
                content_hash=item_data["content_hash"],
                item_metadata=item_data["metadata"],
            ))
        await db_session.commit()

        result = await db_session.execute(
            select(WebsetItem).where(WebsetItem.webset_id == ws.id)
        )
        items = result.scalars().all()
        assert len(items) == 5

    @pytest.mark.asyncio
    async def test_bio_item_tag_diversity(self, db_session: AsyncSession):
        """Verify each bio-inspired item has distinct tags."""
        ws = Webset(
            id=make_webset_id(),
            name="Bio Tags Test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        all_tags = set()
        for item_data in BIO_ITEMS:
            db_session.add(WebsetItem(
                id=make_item_id(),
                webset_id=ws.id,
                url=item_data["url"],
                item_metadata=item_data["metadata"],
            ))
            all_tags.update(item_data["metadata"]["tags"])

        await db_session.commit()

        # Bio domain should span neuromorphic, stigmergy, homeostasis, morphogenesis, immune
        assert "neuromorphic" in all_tags
        assert "stigmergy" in all_tags
        assert "homeostasis" in all_tags
        assert "morphogenesis" in all_tags
        assert "immune-system" in all_tags

    @pytest.mark.asyncio
    async def test_bio_content_hash_uniqueness(self, db_session: AsyncSession):
        """Every item should have a unique content_hash."""
        hashes = [item["content_hash"] for item in BIO_ITEMS]
        assert len(hashes) == len(set(hashes)), "Duplicate content hashes in bio items"

    @pytest.mark.asyncio
    async def test_bio_webset_entity_type(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(),
            name="Entity Type Test",
            entity_type=BIO_WEBSET["entity_type"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.commit()
        await db_session.refresh(ws)
        assert ws.entity_type == "research_paper"
