# -*- coding: utf-8 -*-
import os
import time
import json
import logging
import requests
from typing import Any
from pathlib import Path
from services.image_gen.base import BaseImageProvider
from api.image_client import ImageClient

class HotApiProvider(BaseImageProvider):
    BASE_URL = "https://api.hotapi.ai"

    def __init__(self, api_client):
        super().__init__(api_client)
        self.mock_client = ImageClient(api_client)

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
        return mapping.get(preset, preset if "x" in str(preset) else "1024x1024")

    def _setup_auth(self) -> tuple[str | None, bool]:
        hotapi_key = getattr(self.api_client, "hotapi_key", None) or os.getenv("HOTAPI_KEY")
        if hotapi_key:
            return hotapi_key, True
        return None, False

    def upload_file(self, file_path: str, hotapi_key: str) -> str:
        """Uploads a local image file to HotAPI (POST /v1/uploads/) and returns its temporary CDN URL."""
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"Upload file path does not exist: {file_path}")

        headers = {
            "Authorization": f"Bearer {hotapi_key}"
        }
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        mime_type = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"

        logging.info(f"[HotAPI] Uploading local file '{filename}' to /v1/uploads/...")
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            response = requests.post(f"{self.BASE_URL}/v1/uploads/", headers=headers, files=files, timeout=60)

        if response.status_code not in (200, 201):
            err_msg = response.text
            try:
                err_json = response.json()
                err_msg = err_json.get("error", {}).get("message", response.text)
            except Exception:
                pass
            raise RuntimeError(f"HotAPI file upload failed ({response.status_code}): {err_msg}")

        uploaded_url = response.json().get("url")
        if not uploaded_url:
            raise RuntimeError("HotAPI file upload response did not return a valid URL.")

        logging.info(f"[HotAPI] File uploaded successfully: {uploaded_url}")
        return uploaded_url

    def _poll_task(self, task_id: str, hotapi_key: str, poll_interval: float = 2.0, timeout: float = 120.0) -> dict:
        """Polls GET /v1/tasks/{task_id} until status reaches a terminal state."""
        headers = {
            "Authorization": f"Bearer {hotapi_key}"
        }
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            res = requests.get(f"{self.BASE_URL}/v1/tasks/{task_id}", headers=headers, timeout=30)
            if res.status_code != 200:
                logging.warning(f"[HotAPI] Task polling HTTP {res.status_code}: {res.text}")
                time.sleep(poll_interval)
                continue

            task = res.json()
            status = task.get("status")
            logging.info(f"[HotAPI] Polling task {task_id}: status={status}")

            if status == "succeeded":
                return task
            elif status in ("failed", "cancelled", "expired"):
                err_info = task.get("error", {})
                msg = err_info.get("message") or f"Task ended with status '{status}'"
                raise RuntimeError(f"HotAPI task error ({status}): {msg}")

            time.sleep(poll_interval)

        raise TimeoutError(f"HotAPI task {task_id} timed out after {timeout} seconds.")

    def generate(self, model_endpoint: str, prompt: str, size: str, quality: str, expert_params: str | None = None) -> tuple:
        hotapi_key, has_auth = self._setup_auth()
        is_mock = self.api_client.mock_mode or not has_auth

        cost = 0.03
        from api.model_registry import MODEL_REGISTRY
        for key, val in MODEL_REGISTRY.items():
            if val.get("endpoint") == model_endpoint:
                cost = float(val.get("estimated_cost", 0.03))
                break

        pixel_size = self._map_preset_to_pixel(size)

        if is_mock:
            logging.info(f"[HOTAPI MOCK] Generating image for model {model_endpoint}")
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality)
            return mock_bytes, pixel_size, cost

        try:
            payload: dict[str, Any] = {
                "prompt": prompt
            }

            # Map width & height from size string (e.g. 1024x1024)
            if "x" in pixel_size:
                try:
                    w, h = pixel_size.split("x")
                    payload["width"] = int(w)
                    payload["height"] = int(h)
                except Exception:
                    pass

            # Merge expert_params if specified
            if expert_params:
                try:
                    expert_dict = json.loads(expert_params)
                    if isinstance(expert_dict, dict):
                        for k, v in expert_dict.items():
                            if v is not None and str(v).strip() != "":
                                payload[k] = v
                except Exception as ex:
                    logging.warning(f"[HotAPI] Failed to parse expert_params: {ex}")

            headers = {
                "Authorization": f"Bearer {hotapi_key}",
                "Content-Type": "application/json"
            }

            endpoint_url = f"{self.BASE_URL}/v1/{model_endpoint}"
            logging.info(f"[HotAPI] Submitting text2img task to {endpoint_url}...")
            res = requests.post(endpoint_url, headers=headers, json=payload, timeout=30)

            if res.status_code not in (200, 201, 202):
                err_msg = res.text
                try:
                    err_msg = res.json().get("error", {}).get("message", res.text)
                except Exception:
                    pass
                raise RuntimeError(f"HotAPI task submission failed ({res.status_code}): {err_msg}")

            task_data = res.json()
            task_id = task_data.get("id")
            if not task_id:
                raise RuntimeError("HotAPI did not return a valid task_id.")

            # Poll task until completion
            completed_task = self.poll_task_safe(task_id, hotapi_key)

            # Extract image URL
            output = completed_task.get("output", {})
            img_url = None
            if "images" in output and len(output["images"]) > 0:
                img_url = output["images"][0].get("url")
            elif "assets" in output and len(output["assets"]) > 0:
                img_url = output["assets"][0].get("url")
            elif "url" in output:
                img_url = output["url"]

            if not img_url:
                raise RuntimeError("HotAPI task succeeded but no output image URL was found.")

            # Download image bytes
            img_res = requests.get(img_url, timeout=30)
            if img_res.status_code != 200:
                raise RuntimeError(f"Failed to download generated image from {img_url}")

            # Deduct balance if settings_service is available
            try:
                main_win = getattr(self.api_client, "settings_service", None)
                if hasattr(self.api_client, "coordinator") and self.api_client.coordinator:
                    self.api_client.coordinator.settings_service.deduct_balance("balance_hotapi", cost)
            except Exception as e:
                logging.warning(f"[HotAPI] Could not deduct balance: {e}")

            return img_res.content, pixel_size, cost

        except Exception as e:
            logging.error(f"[HotAPI] Generation failed for {model_endpoint}: {e}")
            raise e

    def poll_task_safe(self, task_id: str, hotapi_key: str) -> dict:
        return self._poll_task(task_id, hotapi_key)

    def edit(self, model_endpoint: str, image_path: str, prompt: str, size: str, quality: str = "Medium", mask_path: str | None = None, expert_params: str | None = None) -> tuple:
        hotapi_key, has_auth = self._setup_auth()
        is_mock = self.api_client.mock_mode or not has_auth

        cost = 0.035
        from api.model_registry import MODEL_REGISTRY
        for key, val in MODEL_REGISTRY.items():
            if val.get("endpoint") == model_endpoint:
                cost = float(val.get("estimated_cost", 0.035))
                break

        pixel_size = self._map_preset_to_pixel(size)

        if is_mock:
            logging.info(f"[HOTAPI MOCK] Editing image for model {model_endpoint}")
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality)
            return mock_bytes, pixel_size, cost

        try:
            # Upload main target image
            target_url = self.upload_file(image_path, hotapi_key)

            payload: dict[str, Any] = {
                "prompt": prompt,
                "image": target_url
            }

            # Parse expert_params
            expert_dict = {}
            if expert_params:
                try:
                    parsed = json.loads(expert_params)
                    if isinstance(parsed, dict):
                        expert_dict = parsed
                except Exception as ex:
                    logging.warning(f"[HotAPI] Failed to parse expert_params in edit: {ex}")

            # Merge non-empty expert params
            for k, v in expert_dict.items():
                if v is not None and str(v).strip() != "":
                    payload[k] = v

            # Handle Face Swap specific face_image param
            if model_endpoint == "face-swap-spicy":
                face_img_path = expert_dict.get("face_image")
                if face_img_path and os.path.exists(face_img_path):
                    source_face_url = self.upload_file(face_img_path, hotapi_key)
                    payload["face_image"] = source_face_url
                elif not payload.get("face_image"):
                    # If face_image is missing, fall back to target_url
                    payload["face_image"] = target_url

            headers = {
                "Authorization": f"Bearer {hotapi_key}",
                "Content-Type": "application/json"
            }

            endpoint_url = f"{self.BASE_URL}/v1/{model_endpoint}"
            logging.info(f"[HotAPI] Submitting edit task to {endpoint_url}...")
            res = requests.post(endpoint_url, headers=headers, json=payload, timeout=30)

            if res.status_code not in (200, 201, 202):
                err_msg = res.text
                try:
                    err_msg = res.json().get("error", {}).get("message", res.text)
                except Exception:
                    pass
                raise RuntimeError(f"HotAPI edit task submission failed ({res.status_code}): {err_msg}")

            task_data = res.json()
            task_id = task_data.get("id")
            if not task_id:
                raise RuntimeError("HotAPI did not return a valid task_id for edit.")

            completed_task = self.poll_task_safe(task_id, hotapi_key)

            output = completed_task.get("output", {})
            img_url = None
            if "images" in output and len(output["images"]) > 0:
                img_url = output["images"][0].get("url")
            elif "assets" in output and len(output["assets"]) > 0:
                img_url = output["assets"][0].get("url")
            elif "url" in output:
                img_url = output["url"]

            if not img_url:
                raise RuntimeError("HotAPI edit task succeeded but no output image URL was found.")

            img_res = requests.get(img_url, timeout=30)
            if img_res.status_code != 200:
                raise RuntimeError(f"Failed to download edited image from {img_url}")

            return img_res.content, pixel_size, cost

        except Exception as e:
            logging.error(f"[HotAPI] Edit failed for {model_endpoint}: {e}")
            raise e
