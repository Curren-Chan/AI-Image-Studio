# -*- coding: utf-8 -*-
import logging
import base64
import requests
from services.image_gen.base import BaseImageProvider
from api.image_client import ImageClient

class GrokImageProvider(BaseImageProvider):
    def __init__(self, api_client):
        super().__init__(api_client)
        self.mock_client = ImageClient(api_client)

    def _get_api_key(self):
        return getattr(self.api_client, "xai_key", None)

    def generate(self, model_endpoint: str, prompt: str, size: str, quality: str, expert_params: str | None = None) -> tuple:
        xai_key = self._get_api_key()
        is_mock = self.api_client.mock_mode or not xai_key
        
        cost = 0.05
        from api.model_registry import MODEL_REGISTRY
        for key, val in MODEL_REGISTRY.items():
            if val["endpoint"] == model_endpoint:
                cost = val["estimated_cost"] if isinstance(val["estimated_cost"], (int, float)) else 0.05
                break

        if is_mock:
            logging.info(f"[GROK MOCK] Generating image for model {model_endpoint}")
            # Map ratio to pixel dimensions for mock
            pixel_size = self._map_ratio_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality)
            return mock_bytes, pixel_size, cost

        try:
            logging.info(f"[GROK] Generating image using xAI API. model: {model_endpoint}, prompt: {prompt}")
            
            # Grok Imagine accepts aspect ratios: "1:1", "16:9", etc.
            # If the format passed is "1024x1024", map it to "1:1"
            ratio = size
            if "x" in size:
                ratio = self._map_pixel_to_ratio(size)

            # We can use requests to call the Grok Imagine endpoint directly
            # to ensure correct parameter passing (e.g. aspect_ratio)
            headers = {
                "Authorization": f"Bearer {xai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_endpoint,
                "prompt": prompt,
                "aspect_ratio": ratio,
                "n": 1,
                "response_format": "b64_json"
            }
            
            if expert_params:
                try:
                    import json
                    expert_dict = json.loads(expert_params)
                    if "upsample_prompt" in expert_dict:
                        payload["upsample_prompt"] = expert_dict["upsample_prompt"] == "true"
                except Exception as ex:
                    logging.warning(f"[GROK] Failed to parse expert_params: {ex}")

            response = requests.post(
                "https://api.x.ai/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            res_data = response.json()
            
            if "data" in res_data and len(res_data["data"]) > 0:
                img_data = res_data["data"][0]
                if "b64_json" in img_data:
                    image_bytes = base64.b64decode(img_data["b64_json"])
                else:
                    image_url = img_data["url"]
                    img_res = requests.get(image_url, timeout=20)
                    img_res.raise_for_status()
                    image_bytes = img_res.content
                
                # Retrieve actual dimensions or guess based on ratio
                actual_size = self._map_ratio_to_pixel(ratio)
                return image_bytes, actual_size, cost
            else:
                raise Exception(f"Invalid API response: {res_data}")

        except Exception as e:
            logging.error(f"GrokImageProvider generation error: {e}. Falling back to Mock.")
            pixel_size = self._map_ratio_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality, error_msg=str(e))
            return mock_bytes, pixel_size, cost

    def edit(self, model_endpoint: str, image_path: str, prompt: str, size: str, quality: str = "Medium", mask_path: str | None = None, expert_params: str | None = None) -> tuple:
        xai_key = self._get_api_key()
        is_mock = self.api_client.mock_mode or not xai_key
        
        cost = 0.05
        from api.model_registry import MODEL_REGISTRY
        for key, val in MODEL_REGISTRY.items():
            if val["endpoint"] == model_endpoint:
                cost = val["estimated_cost"] if isinstance(val["estimated_cost"], (int, float)) else 0.05
                break

        if is_mock:
            logging.info(f"[GROK MOCK] Editing image for model {model_endpoint}")
            pixel_size = self._map_ratio_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality)
            return mock_bytes, pixel_size, cost

        try:
            logging.info(f"[GROK] Editing image using xAI API. model: {model_endpoint}")
            
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                
            headers = {
                "Authorization": f"Bearer {xai_key}",
                "Content-Type": "application/json"
            }
            
            # Map aspect ratio
            ratio = size
            if "x" in size:
                ratio = self._map_pixel_to_ratio(size)

            payload = {
                "model": model_endpoint,
                "prompt": prompt,
                "image": f"data:image/png;base64,{img_b64}",
                "aspect_ratio": ratio,
                "response_format": "b64_json"
            }
            
            if expert_params:
                try:
                    import json
                    expert_dict = json.loads(expert_params)
                    if "upsample_prompt" in expert_dict:
                        payload["upsample_prompt"] = expert_dict["upsample_prompt"] == "true"
                except Exception as ex:
                    logging.warning(f"[GROK] Failed to parse expert_params in edit: {ex}")
            
            # If mask is available
            if mask_path:
                with open(mask_path, "rb") as f:
                    mask_b64 = base64.b64encode(f.read()).decode("utf-8")
                payload["mask"] = f"data:image/png;base64,{mask_b64}"

            response = requests.post(
                "https://api.x.ai/v1/images/edits",
                headers=headers,
                json=payload,
                timeout=40
            )
            response.raise_for_status()
            res_data = response.json()
            
            if "data" in res_data and len(res_data["data"]) > 0:
                img_data = res_data["data"][0]
                if "b64_json" in img_data:
                    image_bytes = base64.b64decode(img_data["b64_json"])
                else:
                    image_url = img_data["url"]
                    img_res = requests.get(image_url, timeout=20)
                    img_res.raise_for_status()
                    image_bytes = img_res.content
                    
                actual_size = self._map_ratio_to_pixel(ratio)
                return image_bytes, actual_size, cost
            else:
                raise Exception(f"Invalid API response: {res_data}")

        except Exception as e:
            logging.error(f"GrokImageProvider edit error: {e}. Falling back to Mock.")
            pixel_size = self._map_ratio_to_pixel(size)
            mock_bytes = self.mock_client._mock_generate_image_bytes(prompt, pixel_size, quality, error_msg=str(e))
            return mock_bytes, pixel_size, cost

    def _map_pixel_to_ratio(self, pixel_size: str) -> str:
        mapping = {
            "1024x1024": "1:1",
            "1280x720": "16:9",
            "720x1280": "9:16",
            "768x1024": "3:4",
            "1024x768": "4:3"
        }
        return mapping.get(pixel_size, "1:1")

    def _map_ratio_to_pixel(self, ratio: str) -> str:
        mapping = {
            "1:1": "1024x1024",
            "16:9": "1280x720",
            "9:16": "720x1280",
            "4:3": "1024x768",
            "3:4": "768x1024",
            "3:2": "1024x682",
            "2:3": "682x1024",
            "21:9": "1280x548",
            "auto": "1024x1024"
        }
        return mapping.get(ratio, "1024x1024" if "x" not in ratio else ratio)
