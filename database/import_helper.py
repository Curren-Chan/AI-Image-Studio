import json
import logging
import os
from datetime import datetime


import re

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".img")


def normalize_path(path: str) -> str:
    if not path:
        return ""
    norm = os.path.normpath(path)
    if len(norm) >= 2 and norm[1] == ":":
        return norm[0].lower() + norm[1:]
    return norm


def import_legacy_history(conn, output_dir):
    """Import any metadata/image pair not already represented in SQLite.

    This runs incrementally so an output whose DB insert failed can be recovered
    on the next launch instead of remaining permanently invisible.
    Files are scanned outside DB transactions to prevent holding long SQLite locks.
    """
    if not os.path.isdir(output_dir):
        return

    # 1. Fetch default project ID and existing records in a short read block
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO projects (name, description) VALUES (?, ?);",
        ("Default Project", "Default workspace for imported images"),
    )
    conn.commit()

    row = cursor.execute(
        "SELECT id FROM projects WHERE name = ?;", ("Default Project",)
    ).fetchone()
    if not row:
        return
    project_id = int(row[0])

    existing_rows = cursor.execute("SELECT filename, lower(image_path) FROM images;").fetchall()
    existing_filenames = {r[0] for r in existing_rows if r[0]}
    existing_norm_paths = {r[1] for r in existing_rows if r[1]}

    # 2. Disk I/O & JSON parsing completely outside DB transactions
    to_insert = []
    try:
        filenames = os.listdir(output_dir)
    except OSError as exc:
        logging.warning("Could not list directory %s: %s", output_dir, exc)
        return

    for filename in filenames:
        if not filename.lower().endswith(".json"):
            continue
        metadata_path = os.path.join(output_dir, filename)
        stem = os.path.splitext(metadata_path)[0]
        image_path = next(
            (stem + extension for extension in IMAGE_EXTENSIONS if os.path.exists(stem + extension)),
            None,
        )
        if image_path is None:
            continue

        norm_image_path = normalize_path(image_path)
        base_img_name = os.path.basename(image_path)

        if base_img_name in existing_filenames or norm_image_path.lower() in existing_norm_paths:
            continue

        try:
            with open(metadata_path, "r", encoding="utf-8") as handle:
                meta = json.load(handle)
            if not isinstance(meta, dict):
                raise TypeError("metadata JSON root must be an object")

            try:
                cost = float(meta.get("cost", 0.0))
            except (TypeError, ValueError):
                cost = 0.0

            # Try parsing timestamp from filename first (IMG_YYYYMMDD_HHMMSS)
            match_fn = re.search(r"IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", base_img_name)
            if match_fn:
                created_at_str = f"{match_fn.group(1)}-{match_fn.group(2)}-{match_fn.group(3)} {match_fn.group(4)}:{match_fn.group(5)}:{match_fn.group(6)}"
            else:
                raw_time = meta.get("timestamp", "")
                try:
                    created_at = datetime.strptime(str(raw_time), "%Y-%m-%d %H:%M:%S")
                    created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    created_at_str = datetime.fromtimestamp(os.path.getmtime(image_path)).strftime("%Y-%m-%d %H:%M:%S")

            to_insert.append((
                project_id,
                base_img_name,
                image_path,
                str(meta.get("prompt_jp", "") or ""),
                str(meta.get("prompt_en", "") or ""),
                str(meta.get("negative_prompt", "") or ""),
                str(meta.get("size", "1024x1024") or "1024x1024"),
                str(meta.get("style", "プリセット無し") or "プリセット無し"),
                str(meta.get("quality", "standard") or "standard"),
                cost,
                1 if meta.get("favorite", False) else 0,
                created_at_str,
                meta.get("model_id"),
                meta.get("model_name"),
                meta.get("provider"),
                meta.get("style_preset"),
                meta.get("expert_params"),
            ))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logging.warning("Skipped invalid metadata file %s: %s", filename, exc)
        except Exception as exc:
            logging.error("Failed to import metadata file %s: %s", filename, exc)

    # 3. Batch DB insert in a short transaction
    if not to_insert:
        return

    imported_count = 0
    try:
        cursor.executemany(
            """
            INSERT INTO images (
                project_id, filename, image_path, prompt_jp, prompt_en,
                negative_prompt, size, style, quality, cost, favorite,
                created_at, model_id, model_name, provider, style_preset,
                expert_params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            to_insert,
        )
        conn.commit()
        imported_count = len(to_insert)
        logging.info("Recovered %s output record(s) into SQLite.", imported_count)
    except Exception as exc:
        logging.error("Failed to batch insert legacy history records: %s", exc)
