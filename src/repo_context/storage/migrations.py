"""Database schema initialization."""

import sqlite3


def initialize_database(conn: sqlite3.Connection) -> None:
    """Initialize the database schema.
    
    Creates all tables and indexes required for the application.
    
    Args:
        conn: SQLite connection.
    """
    conn.executescript(_get_schema_sql())
    conn.commit()


def _get_schema_sql() -> str:
    """Return the complete schema SQL."""
    return """
-- Repos table
CREATE TABLE IF NOT EXISTS repos (
    id TEXT PRIMARY KEY,
    root_path TEXT NOT NULL,
    name TEXT NOT NULL,
    default_language TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_indexed_at TEXT
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uri TEXT NOT NULL,
    module_path TEXT NOT NULL,
    language TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    last_modified_at TEXT NOT NULL,
    last_indexed_at TEXT
);

-- Nodes table
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    language TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    uri TEXT NOT NULL,
    range_json TEXT,
    selection_range_json TEXT,
    parent_id TEXT,
    visibility_hint TEXT,
    doc_summary TEXT,
    content_hash TEXT NOT NULL,
    semantic_hash TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    payload_json TEXT NOT NULL,
    last_indexed_at TEXT
);

-- Edges table
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence_file_id TEXT,
    evidence_uri TEXT,
    evidence_range_json TEXT,
    payload_json TEXT NOT NULL,
    last_indexed_at TEXT
);

-- Index runs table
CREATE TABLE IF NOT EXISTS index_runs (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    files_scanned INTEGER DEFAULT 0,
    nodes_extracted INTEGER DEFAULT 0,
    edges_extracted INTEGER DEFAULT 0,
    error_message TEXT
);

-- Indexes for nodes table
CREATE INDEX IF NOT EXISTS idx_nodes_repo_id ON nodes(repo_id);
CREATE INDEX IF NOT EXISTS idx_nodes_file_id ON nodes(file_id);
CREATE INDEX IF NOT EXISTS idx_nodes_qualified_name ON nodes(qualified_name);
CREATE INDEX IF NOT EXISTS idx_nodes_parent_id ON nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);

-- Indexes for edges table
CREATE INDEX IF NOT EXISTS idx_edges_repo_id ON edges(repo_id);
CREATE INDEX IF NOT EXISTS idx_edges_from_id ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to_id ON edges(to_id);
CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);
CREATE INDEX IF NOT EXISTS idx_edges_evidence_file_id ON edges(evidence_file_id);

-- Indexes for files table
CREATE INDEX IF NOT EXISTS idx_files_repo_id ON files(repo_id);

-- Indexes for index_runs table
CREATE INDEX IF NOT EXISTS idx_index_runs_repo_id ON index_runs(repo_id);
CREATE INDEX IF NOT EXISTS idx_index_runs_status ON index_runs(status);
"""
