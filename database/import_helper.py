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
    """
    cursor = conn.cursor()
    if not os.path.isdir(output_dir):
        return

    cursor.execute(
        "INSERT OR IGNORE INTO projects (name, description) VALUES (?, ?);",
        ("Default Project", "Default workspace for imported images"),
    )
    row = cursor.execute(
        "SELECT id FROM projects WHERE name = ?;", ("Default Project",)
    ).fetchone()
    if not row:
        return
    project_id = int(row[0])

    imported_count = 0
    for filename in os.listdir(output_dir):
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

        if cursor.execute(
            "SELECT 1 FROM images WHERE filename = ? OR lower(image_path) = ? LIMIT 1;", 
            (base_img_name, norm_image_path.lower())
        ).fetchone():
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

            cursor.execute(
                """
                INSERT INTO images (
                    project_id, filename, image_path, prompt_jp, prompt_en,
                    negative_prompt, size, style, quality, cost, favorite,
                    created_at, model_id, model_name, provider, style_preset,
                    expert_params
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
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
                ),
            )
            imported_count += 1
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logging.warning("Skipped invalid metadata file %s: %s", filename, exc)
        except Exception as exc:
            logging.error("Failed to import metadata file %s: %s", filename, exc)

    conn.commit()
    if imported_count:
        logging.info("Recovered %s output record(s) into SQLite.", imported_count)
