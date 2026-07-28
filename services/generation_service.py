# -*- coding: utf-8 -*-
import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any

from api.model_registry import MODEL_REGISTRY
from services.base import BaseService
from services.history_service import HistoryService
from services.image_gen.manager import ImageGenerationManager
from services.prompt_service import PromptService
from services.settings_service import SettingsService


MIN_IMAGE_DIMENSION = 64
MAX_IMAGE_DIMENSION = 4096
MAX_IMAGE_PIXELS = 16_777_216


class GenerationService(BaseService):
    def __init__(
        self,
        api_client,
        prompt_service: PromptService,
        history_service: HistoryService,
        settings_service: SettingsService,
        template_service,
        db_service=None,
        project_root: str | None = None,
    ):
        super().__init__(db_service)
        self.api_client = api_client
        self.prompt_service = prompt_service
        self.prompt_service.set_settings_service(settings_service)
        self.image_manager = ImageGenerationManager(api_client)
        self.history_service = history_service
        self.settings_service = settings_service
        self.template_service = template_service
        self.session_history: list[dict[str, Any]] = []

        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(project_root, "outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    def new_project(self):
        self.session_history = []

    def set_context(
        self,
        prompt_jp: str,
        prompt_en: str,
        size: str,
        negative_prompt: str = "",
    ):
        self.session_history = [
            {
                "prompt_jp": prompt_jp,
                "prompt_en": prompt_en,
                "style": "",
                "size": size,
                "negative_prompt": negative_prompt,
            }
        ]

    @staticmethod
    def validate_size(size: str) -> tuple[bool, str | None]:
        if not isinstance(size, str) or not size.strip():
            return False, "Image size is required."
        value = size.strip().lower()
        match = re.fullmatch(r"(\d{1,5})x(\d{1,5})", value)
        if not match:
            if "x" in value:
                return False, "Custom size must use WIDTHxHEIGHT, for example 1024x1024."
            return True, None  # Provider presets such as square_hd or auto.
        width, height = (int(match.group(1)), int(match.group(2)))
        if not (
            MIN_IMAGE_DIMENSION <= width <= MAX_IMAGE_DIMENSION
            and MIN_IMAGE_DIMENSION <= height <= MAX_IMAGE_DIMENSION
        ):
            return (
                False,
                f"Custom dimensions must be between {MIN_IMAGE_DIMENSION} and "
                f"{MAX_IMAGE_DIMENSION} pixels.",
            )
        if width * height > MAX_IMAGE_PIXELS:
            return False, "Custom dimensions exceed the 16-megapixel safety limit."
        return True, None

    def generate_single(
        self,
        project_id: int | None,
        prompt_jp: str,
        translation_rule: str = "Standard",
        size: str = "1024x1024",
        negative_prompt: str = "",
        quality: str = "standard",
        model_id: str | None = None,
        mode: str | None = None,
        image_path: str | None = None,
        mask_path: str | None = None,
        style_preset: str | None = None,
        expert_params: str | None = None,
    ) -> dict:
        if not isinstance(prompt_jp, str) or not prompt_jp.strip():
            return {"success": False, "error": "Prompt cannot be empty."}
        if not model_id:
            return {"success": False, "error": "No generation model is selected."}

        model_meta = MODEL_REGISTRY.get(model_id)
        if not model_meta:
            return {"success": False, "error": f"Model {model_id} is not registered."}

        valid_size, size_error = self.validate_size(size)
        if not valid_size:
            return {"success": False, "error": size_error}

        mode = mode or ("edit" if image_path else "generate")
        category = model_meta.get("category", "text2img")
        if mode == "edit":
            if category == "text2img":
                return {"success": False, "error": "The selected model cannot edit images."}
            if not image_path or not os.path.isfile(image_path):
                return {
                    "success": False,
                    "error": "The source image for this edit no longer exists.",
                }
            if mask_path and not os.path.isfile(mask_path):
                return {"success": False, "error": "The selected mask file no longer exists."}
        elif mode == "generate":
            if category == "img_edit":
                return {
                    "success": False,
                    "error": "The selected model requires an image-edit source.",
                }
        else:
            return {"success": False, "error": f"Unsupported generation mode: {mode}"}

        if mode == "edit" and image_path and not self.session_history:
            try:
                records = self.history_service.get_history()
                for rec in records:
                    if rec.get("image_path") == image_path or os.path.basename(rec.get("image_path", "")) == os.path.basename(image_path):
                        meta = rec.get("metadata", {})
                        self.set_context(
                            prompt_jp=meta.get("prompt_jp", ""),
                            prompt_en=meta.get("prompt_en", ""),
                            size=meta.get("size", size),
                            negative_prompt=meta.get("negative_prompt", ""),
                        )
                        break
            except Exception as e:
                logging.warning(f"Could not hydrate context from image_path: {e}")

        try:
            prompt_en, text_cost = self._translate_prompt(
                prompt_jp,
                translation_rule,
                negative_prompt,
                quality,
            )
            prompt_en_final = self._apply_style_preset(prompt_en, style_preset)
            if not prompt_en_final or not prompt_en_final.strip():
                logging.warning("Final translated prompt is empty. Falling back to prompt_jp.")
                prompt_en_final = prompt_jp

            if mode == "edit":
                assert image_path is not None
                logging.info(
                    "Performing Image Edit using model: %s on image: %s",
                    model_id,
                    image_path,
                )
                image_bytes, actual_size, image_cost = self.image_manager.edit_image(
                    model_id=model_id,
                    image_path=image_path,
                    prompt=prompt_en_final,
                    size=size,
                    quality=quality,
                    mask_path=mask_path,
                    expert_params=expert_params,
                )
            else:
                logging.info("Performing Text-to-Image using model: %s", model_id)
                image_bytes, actual_size, image_cost = self.image_manager.generate_image(
                    model_id=model_id,
                    prompt=prompt_en_final,
                    size=size,
                    quality=quality,
                    expert_params=expert_params,
                )

            if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
                raise ValueError("The image provider returned no image data.")

            total_cost = float(text_cost) + float(image_cost)
            provider_name = str(model_meta["provider"])
            balance_key = self._balance_key(provider_name)
            new_balance = self.settings_service.deduct_balance(balance_key, total_cost)

            from core.event_bus import event_bus

            event_bus.preset_updated.emit()

            extension = self._detect_image_extension(bytes(image_bytes))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"IMG_{timestamp}_{uuid.uuid4().hex[:10]}"
            image_path_out = os.path.join(self.output_dir, base_name + extension)
            metadata_path = os.path.join(self.output_dir, base_name + ".json")

            meta = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prompt_jp": prompt_jp,
                "prompt_en": prompt_en_final,
                "negative_prompt": negative_prompt,
                "size": actual_size,
                "style": translation_rule,
                "style_preset": style_preset or "プリセット無し",
                "quality": quality,
                "cost": round(total_cost, 5),
                "favorite": False,
                "filename": os.path.basename(image_path_out),
                "model_id": model_id,
                "model_name": model_meta["display_name"],
                "provider": model_meta["provider"],
            }
            if expert_params:
                meta["expert_params"] = expert_params

            try:
                with open(image_path_out, "xb") as image_file:
                    image_file.write(image_bytes)
                    image_file.flush()
                    os.fsync(image_file.fileno())
                with open(metadata_path, "x", encoding="utf-8") as metadata_file:
                    json.dump(meta, metadata_file, ensure_ascii=False, indent=4)
                    metadata_file.flush()
                    os.fsync(metadata_file.fileno())
            except Exception:
                for path in (metadata_path, image_path_out):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        logging.exception("Failed to clean partial output %s", path)
                raise

            image_id = self.history_service.add_image_record(
                project_id=project_id,
                filename=os.path.basename(image_path_out),
                image_path=image_path_out,
                prompt_jp=prompt_jp,
                prompt_en=prompt_en_final,
                negative_prompt=negative_prompt,
                size=actual_size,
                style=translation_rule,
                quality=quality,
                cost=total_cost,
                model_name=str(model_meta.get("display_name", "")),
                provider=str(model_meta.get("provider", "")),
                model_id=model_id,
                style_preset=style_preset,
                expert_params=expert_params,
            )
            if image_id <= 0:
                return {
                    "success": False,
                    "error": (
                        "The image was saved, but its history record could not be stored. "
                        "It will be recovered from the outputs folder on the next launch."
                    ),
                    "image_path": image_path_out,
                    "cost": total_cost,
                    "balance": new_balance,
                }

            self.session_history.append(
                {
                    "prompt_jp": prompt_jp,
                    "prompt_en": prompt_en_final,
                    "style": translation_rule,
                    "style_preset": style_preset,
                    "size": actual_size,
                    "negative_prompt": negative_prompt,
                }
            )

            return {
                "success": True,
                "image_path": image_path_out,
                "prompt_jp": prompt_jp,
                "prompt_en": prompt_en_final,
                "negative_prompt": negative_prompt,
                "size": actual_size,
                "style": translation_rule,
                "style_preset": style_preset,
                "quality": quality,
                "cost": total_cost,
                "balance": new_balance,
                "model_id": model_id,
                "model_name": model_meta["display_name"],
                "provider": model_meta["provider"],
            }
        except Exception as exc:
            logging.exception("Failed generation inside GenerationService")
            return {"success": False, "error": str(exc)}

    def _translate_prompt(
        self,
        prompt_jp: str,
        translation_rule: str,
        negative_prompt: str,
        quality: str,
    ) -> tuple[str, float]:
        if self.session_history:
            previous = self.session_history[-1]
            try:
                return self.prompt_service.generate_modified_prompt(
                    prev_jp=previous.get("prompt_jp", ""),
                    prev_en=previous.get("prompt_en", ""),
                    new_jp=prompt_jp,
                    translation_rule=translation_rule,
                    negative_prompt=negative_prompt,
                    quality=quality,
                )
            except Exception as exc:
                logging.warning(
                    "Failed to generate modified prompt (%s); using direct generation.",
                    exc,
                )
        return self.prompt_service.generate_prompt(
            prompt_jp=prompt_jp,
            translation_rule=translation_rule,
            negative_prompt=negative_prompt,
            quality=quality,
        )

    def _apply_style_preset(self, prompt_en: str, style_preset: str | None) -> str:
        if not style_preset or style_preset == "プリセット無し":
            return prompt_en
        presets = self.template_service.get_style_presets()
        preset_text = str(presets.get(style_preset, "")).rstrip(", ").strip()
        return f"{preset_text}, {prompt_en}" if preset_text else prompt_en

    @staticmethod
    def _balance_key(provider: str) -> str:
        if provider == "fal":
            return "balance_fal"
        if provider == "xai":
            return "balance_grok"
        return "balance_openai"

    @staticmethod
    def _detect_image_extension(image_bytes: bytes) -> str:
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            return ".webp"
        logging.warning("Unknown image signature; saving with .img extension.")
        return ".img"
