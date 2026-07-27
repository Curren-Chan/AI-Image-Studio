# -*- coding: utf-8 -*-
import os
import logging
import requests
from typing import Any
from pathlib import Path
from services.image_gen.base import BaseImageProvider
from api.image_client import ImageClient

class FalImageProvider(BaseImageProvider):
    _MULTI_IMAGE_EDIT_ENDPOINTS = {
        "fal-ai/qwen-image-2/edit",
        "fal-ai/qwen-image-2/pro/edit",
        "fal-ai/gpt-image-2",
        "openai/gpt-image-2",
        "xai/grok-imagine-image/edit",
        "xai/grok-imagine-image/quality/edit",
        "bytedance/seedream/v5/pro/edit",
    }

    def __init__(self, api_client):
        super().__init__(api_client)
        self.mock_client = ImageClient(api_client)

    def _setup_auth(self):
        fal_key = getattr(self.api_client, "fal_key", None)
        if fal_key:
            os.environ["FAL_KEY"] = fal_key
            return True
        os.environ.pop("FAL_KEY", None)
        return False

    @classmethod
    def _add_edit_source(cls, arguments: dict[str, Any], endpoint: str, image_url: str):
        if endpoint in cls._MULTI_IMAGE_EDIT_ENDPOINTS:
            arguments["image_urls"] = [image_url]
        else:
            arguments["image_url"] = image_url

    def generate(self, model_endpoint: str, prompt: str, size: str, quality: str, expert_params: str | None = None) -> tuple:
        # Check mock mode
        has_auth = self._setup_auth()
        is_mock = self.api_client.mock_mode or not has_auth
        
        cost = 0.02 # default fallback cost
        # Find cost in registry if possible
        from api.model_registry import MODEL_REGISTRY
        for key, val in MODEL_REGISTRY.items():
            if val["endpoint"] == model_endpoint:
                cost = val["estimated_cost"] if isinstance(val["estimated_cost"], (int, float)) else 0.05
                break

        if is_mock:
            logging.info(f"[FAL MOCK] Generating image for model {model_endpoint}")
            # Map size to pixels for mock generator
            pixel_size = self._map_preset_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality)
            return mock_bytes, pixel_size, cost

        try:
            import fal_client
            logging.info(f"[FAL] Running text2img: {model_endpoint} with prompt: {prompt}")
            
            # Map size
            # fal.ai accepts landscape_16_9, square_hd, etc.
            # If the size is already in that format (e.g. landscape_16_9), pass it.
            # If it's a pixel size (e.g. 1024x1024), try to map it.
            fal_size = size
            if "x" in size:
                fal_size = self._map_pixel_to_preset(size)

            arguments: dict[str, Any] = {
                "prompt": prompt,
                "image_size": fal_size,
                "num_images": 1
            }
            
            # Quality handling is moved to expert_params for safety_checker if needed.

            # Get default expert params from model registry to avoid API default value bugs
            from api.model_registry import MODEL_REGISTRY
            model_meta = None
            for key, meta in MODEL_REGISTRY.items():
                if meta.get("endpoint") == model_endpoint:
                    model_meta = meta
                    break
            
            # 1. Fill defaults
            registry_params = model_meta.get("expert_params", []) if model_meta else []
            if isinstance(registry_params, list):
                for param in registry_params:
                    if not isinstance(param, dict):
                        continue
                    k = param["name"]
                    def_val = param.get("default")
                    if def_val is not None:
                        try:
                            if k in ["safety_tolerance", "num_inference_steps", "seed", "num_images"]:
                                arguments[k] = int(def_val)
                            elif k == "guidance_scale":
                                arguments[k] = float(def_val)
                            elif k == "enable_safety_checker":
                                arguments[k] = (str(def_val).lower() == "true")
                            else:
                                arguments[k] = def_val
                        except Exception:
                            pass

            # 2. Merge expert_params if provided (overriding defaults)
            if expert_params:
                try:
                    import json
                    expert_dict = json.loads(expert_params)
                    for k, v in expert_dict.items():
                        # Skip if empty or None
                        if v is None or str(v).strip() == "":
                            continue
                        
                        # Convert values to correct types based on expected types
                        try:
                            if k in ["safety_tolerance", "num_inference_steps", "seed", "num_images"]:
                                arguments[k] = int(v)
                            elif k == "guidance_scale":
                                arguments[k] = float(v)
                            elif k == "enable_safety_checker":
                                arguments[k] = (str(v).lower() == "true")
                            else:
                                arguments[k] = v
                        except ValueError as ve:
                            logging.warning(f"[FAL] Skipping invalid param {k}={v}: {ve}")
                except Exception as ex:
                    logging.warning(f"[FAL] Failed to parse expert_params: {ex}")

            result = fal_client.subscribe(
                model_endpoint,
                arguments=arguments,
                with_logs=False
            )
            
            if "images" in result and len(result["images"]) > 0:
                image_url = result["images"][0]["url"]
                width = result["images"][0].get("width", 1024)
                height = result["images"][0].get("height", 1024)
                actual_size = f"{width}x{height}"
                
                # Download image
                response = requests.get(image_url, timeout=20)
                response.raise_for_status()
                return response.content, actual_size, cost
            else:
                raise Exception("No image returned in fal.ai response.")
                
        except Exception as e:
            logging.error(f"FalImageProvider generation error: {e}. Falling back to Mock.")
            pixel_size = self._map_preset_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality, error_msg=str(e))
            return mock_bytes, pixel_size, cost

    def edit(self, model_endpoint: str, image_path: str, prompt: str, size: str, quality: str = "Medium", mask_path: str | None = None, expert_params: str | None = None) -> tuple:
        has_auth = self._setup_auth()
        is_mock = self.api_client.mock_mode or not has_auth
        
        cost = 0.02
        from api.model_registry import MODEL_REGISTRY
        for key, val in MODEL_REGISTRY.items():
            if val["endpoint"] == model_endpoint:
                cost = val["estimated_cost"] if isinstance(val["estimated_cost"], (int, float)) else 0.05
                break

        if is_mock:
            logging.info(f"[FAL MOCK] Editing image for model {model_endpoint}")
            pixel_size = self._map_preset_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality)
            return mock_bytes, pixel_size, cost

        try:
            import fal_client
            logging.info(f"[FAL] Uploading source image: {image_path}")
            image_url = fal_client.upload_file(Path(image_path))
            
            arguments: dict[str, Any] = {"prompt": prompt}
            self._add_edit_source(arguments, model_endpoint, image_url)
            
            # Handle inpainting if mask is provided
            if mask_path and os.path.exists(mask_path):
                logging.info(f"[FAL] Uploading mask image: {mask_path}")
                mask_url = fal_client.upload_file(Path(mask_path))
                arguments["mask_url"] = mask_url
                
            # Get default expert params from model registry to avoid API default value bugs
            from api.model_registry import MODEL_REGISTRY
            model_meta = None
            for key, meta in MODEL_REGISTRY.items():
                if meta.get("endpoint") == model_endpoint:
                    model_meta = meta
                    break
            
            # 1. Fill defaults
            registry_params = model_meta.get("expert_params", []) if model_meta else []
            if isinstance(registry_params, list):
                for param in registry_params:
                    if not isinstance(param, dict):
                        continue
                    k = param["name"]
                    def_val = param.get("default")
                    if def_val is not None:
                        try:
                            if k in ["safety_tolerance", "num_inference_steps", "seed", "num_images"]:
                                arguments[k] = int(def_val)
                            elif k == "guidance_scale":
                                arguments[k] = float(def_val)
                            elif k == "enable_safety_checker":
                                arguments[k] = (str(def_val).lower() == "true")
                            else:
                                arguments[k] = def_val
                        except Exception:
                            pass

            # 2. Merge expert_params if provided (overriding defaults)
            if expert_params:
                try:
                    import json
                    expert_dict = json.loads(expert_params)
                    for k, v in expert_dict.items():
                        if v is None or str(v).strip() == "":
                            continue
                        
                        if k in ["safety_tolerance", "num_inference_steps", "seed", "num_images"]:
                            arguments[k] = int(v)
                        elif k == "guidance_scale":
                            arguments[k] = float(v)
                        elif k == "enable_safety_checker":
                            arguments[k] = (str(v).lower() == "true")
                        else:
                            arguments[k] = v
                except Exception as ex:
                    logging.warning(f"[FAL] Failed to parse expert_params in edit: {ex}")
                
            result = fal_client.subscribe(
                model_endpoint,
                arguments=arguments,
                with_logs=False
            )
            
            if "images" in result and len(result["images"]) > 0:
                out_url = result["images"][0]["url"]
                width = result["images"][0].get("width", 1024)
                height = result["images"][0].get("height", 1024)
                actual_size = f"{width}x{height}"
                
                response = requests.get(out_url, timeout=20)
                response.raise_for_status()
                return response.content, actual_size, cost
            else:
                raise Exception("No image returned in fal.ai edit response.")
                
        except Exception as e:
            logging.error(f"FalImageProvider edit error: {e}. Falling back to Mock.")
            pixel_size = self._map_preset_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality, error_msg=str(e))
            return mock_bytes, pixel_size, cost

    def _map_preset_to_pixel(self, preset: str) -> str:
        mapping = {
            "square_hd": "1024x1024",
            "square": "1024x1024",
            "landscape_16_9": "1280x720",
            "landscape_4_3": "1024x768",
            "portrait_16_9": "720x1280",
            "portrait_4_3": "768x1024",
            "auto": "1024x1024"
        }
        return mapping.get(preset, "1024x1024" if "x" not in preset else preset)

    def _map_pixel_to_preset(self, pixel_size: str) -> str:
        mapping = {
            "1024x1024": "square_hd",
            "1280x720": "landscape_16_9",
            "1024x768": "landscape_4_3",
            "720x1280": "portrait_16_9",
            "768x1024": "portrait_4_3"
        }
        return mapping.get(pixel_size, "square_hd")
