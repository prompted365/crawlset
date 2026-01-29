import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS websets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    search_query TEXT,
    search_criteria TEXT,
    entity_type TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS webset_items (
    id TEXT PRIMARY KEY,
    webset_id TEXT,
    url TEXT NOT NULL,
    title TEXT,
    content TEXT,
    content_hash TEXT,
    metadata TEXT,
    enrichments TEXT,
    ruvector_doc_id TEXT,
    last_crawled_at TEXT,
    created_at TEXT,
    FOREIGN KEY (webset_id) REFERENCES websets(id)
);

CREATE TABLE IF NOT EXISTS monitors (
    id TEXT PRIMARY KEY,
    webset_id TEXT,
    cron_expression TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    behavior_type TEXT,
    behavior_config TEXT,
    status TEXT DEFAULT 'enabled',
    last_run_at TEXT,
    FOREIGN KEY (webset_id) REFERENCES websets(id)
);

CREATE TABLE IF NOT EXISTS monitor_runs (
    id TEXT PRIMARY KEY,
    monitor_id TEXT,
    status TEXT,
    items_added INTEGER,
    items_updated INTEGER,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    FOREIGN KEY (monitor_id) REFERENCES monitors(id)
);

CREATE TABLE IF NOT EXISTS extraction_jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT,
    result TEXT,
    error TEXT,
    created_at TEXT,
    completed_at TEXT
);
"""


def ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        # Gentle migrations: add columns if missing
        cur = conn.execute("PRAGMA table_info(webset_items)")
        cols = {r[1] for r in cur.fetchall()}
        if "content" not in cols:
            conn.execute("ALTER TABLE webset_items ADD COLUMN content TEXT")
        if "last_crawled_at" not in cols:
            conn.execute("ALTER TABLE webset_items ADD COLUMN last_crawled_at TEXT")
        conn.commit()
