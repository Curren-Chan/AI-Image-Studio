import os
import json
import logging
from services.base import BaseService
from api.vision_client import VisionClient

class VisionService(BaseService):
    def __init__(self, vision_client: VisionClient, db_service=None):
        super().__init__(db_service)
        self.vision_client = vision_client
        
    def load_dropped_image_context(self, image_path: str) -> dict:
        base_name, _ = os.path.splitext(image_path)
        metadata_path = f"{base_name}.json"
        
        # Check if adjacent JSON file exists (app-generated image)
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                metadata["external"] = False
                metadata["success"] = True
                return metadata
            except Exception as e:
                logging.error(f"Failed to read adjacent metadata file: {e}")
                
        # If no JSON exists, treat as external image and run Vision description
        try:
            description = self.vision_client.describe_image(image_path)
            return {
                "success": True,
                "external": True,
                "prompt_jp": f"[Dropped Image: {os.path.basename(image_path)}]",
                "prompt_en": description,
                "style": "プリセット無し",
                "size": "1024x1024",
                "negative_prompt": "",
                "quality": "Medium"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to analyze image: {str(e)}"
            }
