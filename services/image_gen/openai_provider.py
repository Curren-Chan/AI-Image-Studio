# -*- coding: utf-8 -*-
import logging
from services.image_gen.base import BaseImageProvider
from api.image_client import ImageClient

class OpenAiImageProvider(BaseImageProvider):
    def __init__(self, api_client):
        super().__init__(api_client)
        self.image_client = ImageClient(api_client)

    def generate(self, model_endpoint: str, prompt: str, size: str, quality: str, expert_params: str | None = None) -> tuple:
        import json
        if expert_params:
            try:
                params_dict = json.loads(expert_params)
                if "quality" in params_dict and params_dict["quality"]:
                    quality = params_dict["quality"]
            except Exception as e:
                logging.error(f"[OPENAI] Failed to parse expert_params: {e}")

        # Temporarily switch model to the requested one
        old_model = self.api_client.image_model
        self.api_client.image_model = model_endpoint
        try:
            image_bytes, actual_size, cost = self.image_client.generate_image_bytes(prompt, size, quality)
            return image_bytes, actual_size, cost
        finally:
            self.api_client.image_model = old_model

    def edit(self, model_endpoint: str, image_path: str, prompt: str, size: str, quality: str = "Medium", mask_path: str | None = None, expert_params: str | None = None) -> tuple:
        import os
        from api.vision_client import VisionClient
        logging.info(f"[OPENAI EDIT] Performing Vision-guided Image Edit on source image: {image_path}")
        
        source_description = ""
        if image_path and os.path.isfile(image_path):
            try:
                vision_client = VisionClient(self.api_client)
                source_description = vision_client.describe_image(image_path)
                logging.info(f"[OPENAI EDIT] Extracted Vision context: {source_description}")
            except Exception as e:
                logging.warning(f"[OPENAI EDIT] Vision extraction skipped: {e}")

        if source_description:
            fused_prompt = f"Based on the visual elements of the original source image ('{source_description}'), create a modified variation incorporating these updates: {prompt}"
        else:
            fused_prompt = prompt

        return self.generate(model_endpoint, fused_prompt, size, quality, expert_params)
