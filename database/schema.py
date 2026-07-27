# -*- coding: utf-8 -*-
import json
import logging
import os

CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    filename TEXT NOT NULL,
    image_path TEXT NOT NULL,
    prompt_jp TEXT,
    prompt_en TEXT,
    negative_prompt TEXT,
    size TEXT,
    style TEXT,
    quality TEXT,
    cost REAL,
    favorite BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_name TEXT,
    provider TEXT,
    model_id TEXT,
    style_preset TEXT,
    expert_params TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    prompt_jp TEXT,
    prompt_en TEXT,
    model TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL, -- 'positive', 'negative', 'style'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    status TEXT NOT NULL, -- 'Pending', 'Running', 'Completed', 'Failed', 'Paused'
    prompt_jp TEXT,
    prompt_en TEXT,
    style TEXT,
    size TEXT,
    negative_prompt TEXT,
    quality TEXT,
    batch_count INTEGER,
    completed_count INTEGER NOT NULL DEFAULT 0,
    model_id TEXT,
    provider TEXT,
    mode TEXT DEFAULT 'generate',
    image_path TEXT,
    mask_path TEXT,
    style_preset TEXT,
    expert_params TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    image_path TEXT,
    prompt_fragment TEXT NOT NULL,
    tags TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    brand TEXT,
    image_path TEXT,
    prompt_fragment TEXT NOT NULL,
    tags TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_images_project ON images(project_id);
CREATE INDEX IF NOT EXISTS idx_images_favorite ON images(favorite);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_templates_type ON templates(type);
"""

def setup_schema(conn):
    """Executes the DDL schema setup and index creation scripts."""
    logging.info("Setting up database schema...")
    cursor = conn.cursor()
    cursor.executescript(CREATE_SCHEMA_SQL)
    cursor.executescript(CREATE_INDEXES_SQL)
    conn.commit()
    
    # Run explicit, idempotent migrations.  Inspecting the schema avoids
    # mistaking lock/disk errors for an already-existing column.
    image_columns = {
        "model_name": "TEXT",
        "provider": "TEXT",
        "model_id": "TEXT",
        "style_preset": "TEXT",
        "expert_params": "TEXT",
    }
    job_columns = {
        "model_id": "TEXT",
        "provider": "TEXT",
        "mode": "TEXT DEFAULT 'generate'",
        "image_path": "TEXT",
        "mask_path": "TEXT",
        "style_preset": "TEXT",
        "expert_params": "TEXT",
        "completed_count": "INTEGER NOT NULL DEFAULT 0",
    }
    _ensure_columns(cursor, "images", image_columns)
    _ensure_columns(cursor, "jobs", job_columns)

    # Restore model IDs for existing records from their adjacent metadata JSON.
    backfilled_count = 0
    cursor.execute(
        "SELECT id, image_path FROM images "
        "WHERE model_id IS NULL OR TRIM(model_id) = '';"
    )
    for image_id, image_path in cursor.fetchall():
        if not image_path:
            continue
        metadata_path = f"{os.path.splitext(image_path)[0]}.json"
        if not os.path.exists(metadata_path):
            continue
        try:
            with open(metadata_path, "r", encoding="utf-8") as metadata_file:
                metadata = json.load(metadata_file)
            if not isinstance(metadata, dict):
                raise TypeError("metadata JSON root must be an object")
            model_id = metadata.get("model_id")
            if model_id:
                cursor.execute(
                    "UPDATE images SET model_id = ? WHERE id = ?;",
                    (str(model_id), image_id),
                )
                backfilled_count += 1
        except (OSError, ValueError, TypeError) as e:
            logging.warning(
                "Could not backfill model_id for image record %s: %s",
                image_id,
                e,
            )

    conn.commit()
    if backfilled_count:
        logging.info(
            "Backfilled model_id for %s existing image record(s).",
            backfilled_count,
        )
    logging.info("Database schema migration and setup completed.")


def _ensure_columns(cursor, table_name: str, columns: dict[str, str]):
    existing = {
        row[1] for row in cursor.execute(f"PRAGMA table_info({table_name});").fetchall()
    }
    for column_name, declaration in columns.items():
        if column_name in existing:
            continue
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {declaration};"
        )
