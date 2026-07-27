import json
import logging
import os
import tempfile

from services.base import BaseService


class TemplateService(BaseService):
    def __init__(self, db_service=None, project_root: str | None = None):
        super().__init__(db_service)
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.presets_path = os.path.join(project_root, "presets.json")
        self.prompt_templates_path = os.path.join(project_root, "prompt_templates.json")
        self.negative_templates_path = os.path.join(project_root, "negative_templates.json")
        self.style_presets_path = os.path.join(project_root, "style_presets.json")

    @staticmethod
    def _normalise_templates(value: object) -> dict[str, str] | None:
        if not isinstance(value, dict):
            return None
        return {
            str(name): str(content)
            for name, content in value.items()
            if str(name).strip() and isinstance(content, str)
        }

    def _load_json_templates(self, path: str) -> dict[str, str] | None:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                templates = self._normalise_templates(json.load(handle))
            if templates is None:
                raise TypeError("template JSON root must be an object")
            return templates
        except Exception as exc:
            logging.error("Failed to load template file %s: %s", path, exc)
            return None

    def _load_db_templates(self, template_type: str) -> dict[str, str] | None:
        try:
            with self.connection() as conn:
                rows = conn.execute(
                    "SELECT name, content FROM templates WHERE type = ?;",
                    (template_type,),
                ).fetchall()
            return {str(row[0]): str(row[1]) for row in rows} if rows else None
        except Exception as exc:
            logging.error("Failed to load %s templates from database: %s", template_type, exc)
            return None

    def _save_json_templates(self, path: str, templates: dict[str, str]) -> bool:
        temp_path: str | None = None
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            descriptor, temp_path = tempfile.mkstemp(
                prefix=f".{os.path.basename(path)}.",
                suffix=".tmp",
                dir=os.path.dirname(path),
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(templates, handle, ensure_ascii=False, indent=4)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            return True
        except Exception as exc:
            logging.error("Failed to write template file %s: %s", path, exc)
            return False
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _save_templates(
        self,
        templates: dict,
        template_type: str,
        json_path: str,
    ) -> bool:
        clean_templates = self._normalise_templates(templates)
        if clean_templates is None:
            logging.error("Refusing to save non-object template data for %s", template_type)
            return False

        db_saved = False
        try:
            with self.connection() as conn:
                conn.execute("DELETE FROM templates WHERE type = ?;", (template_type,))
                conn.executemany(
                    "INSERT INTO templates (name, content, type) VALUES (?, ?, ?);",
                    [
                        (name, content, template_type)
                        for name, content in clean_templates.items()
                    ],
                )
                conn.commit()
            db_saved = True
        except Exception as exc:
            logging.error("Failed to save %s templates to database: %s", template_type, exc)

        file_saved = self._save_json_templates(json_path, clean_templates)
        return db_saved or file_saved

    def _get_templates(
        self,
        template_type: str,
        json_path: str,
        defaults: dict[str, str],
    ) -> dict[str, str]:
        db_templates = self._load_db_templates(template_type)
        if db_templates is not None:
            return db_templates

        file_templates = self._load_json_templates(json_path)
        if file_templates is not None:
            self._save_templates(file_templates, template_type, json_path)
            return file_templates

        self._save_templates(defaults, template_type, json_path)
        return defaults.copy()

    def get_prompt_templates(self) -> dict[str, str]:
        defaults = {
            "水彩画風の風景": "水彩画風の美しい中世ヨーロッパの街並み、夕暮れ、優しい色合い",
            "サイバーパンク都市": "サイバーパンクなネオンが輝く大都市、雨の降る夜、路地裏の光、未来的な乗り物",
            "アニメ調": "cel-shaded, high quality anime illustration, vibrant colors, detailed line art, masterpiece",
            "実写風": "photorealistic, cinematic lighting, shot on 35mm lens, 8k resolution, highly detailed, realistic textures",
            "3D CG": "3D render, Unreal Engine 5 style, octane render, volumetric lighting, ray tracing, sharp focus",
            "水彩画風": "watercolor painting, soft textures, delicate color washes, artistic brush strokes, pastel colors",
            "墨絵風": "traditional sumi-e style, ink wash painting, bold black ink brush strokes, minimalist, textured paper",
            "色鉛筆風": "colored pencil sketch, hand-drawn texture, fine crosshatching, soft gradients, sketch paper",
            "商品ページ画像": "studio lighting, product shot, shot on 50mm lens, clean white background, highly detailed, soft shadows, professional commercial photography",
        }

        migrated = self._load_json_templates(self.presets_path) or {}
        migrated.pop("プリセット無し", None)
        templates = self._get_templates("positive", self.prompt_templates_path, defaults)
        changed = False
        for name, content in migrated.items():
            if name not in templates and content:
                templates[name] = content
                changed = True

        if migrated and (not changed or self.save_prompt_templates(templates)):
            try:
                os.remove(self.presets_path)
                logging.info("Migrated presets.json to prompt templates.")
            except OSError as exc:
                logging.warning("Could not remove migrated presets file: %s", exc)
        return templates

    def save_prompt_templates(self, templates: dict) -> bool:
        return self._save_templates(templates, "positive", self.prompt_templates_path)

    def get_negative_templates(self) -> dict[str, str]:
        defaults = {
            "低画質・不自然さ排除": "low quality, worst quality, distorted anatomy, extra limbs, bad proportions, bad hands, blurry",
            "文字・ロゴ・署名排除": "text, watermark, logo, signature, copyright, writing, letters, branding",
        }
        return self._get_templates("negative", self.negative_templates_path, defaults)

    def save_negative_templates(self, templates: dict) -> bool:
        return self._save_templates(templates, "negative", self.negative_templates_path)

    def get_style_presets(self) -> dict[str, str]:
        return self._get_templates("style_preset", self.style_presets_path, {})

    def save_style_presets(self, presets: dict) -> bool:
        return self._save_templates(presets, "style_preset", self.style_presets_path)
