# -*- coding: utf-8 -*-
from api.model_registry import MODEL_REGISTRY
from services.image_gen.openai_provider import OpenAiImageProvider
from services.image_gen.fal_provider import FalImageProvider
from services.image_gen.grok_provider import GrokImageProvider
from services.image_gen.hotapi_provider import HotApiProvider

class ImageGenerationManager:
    def __init__(self, api_client):
        self.api_client = api_client
        self.providers = {
            "openai": OpenAiImageProvider(api_client),
            "fal": FalImageProvider(api_client),
            "xai": GrokImageProvider(api_client),
            "hotapi": HotApiProvider(api_client)
        }

    def generate_image(self, model_id: str, prompt: str, size: str, quality: str, expert_params: str | None = None) -> tuple:
        """
        Looks up model in registry and calls appropriate provider.
        Returns: (image_bytes, actual_size, cost)
        """
        model_meta = MODEL_REGISTRY.get(model_id)
        if not model_meta:
            raise ValueError(f"Model {model_id} is not registered")
            
        provider_name = model_meta["provider"]
        endpoint = model_meta["endpoint"]
        
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"No image provider registered for '{provider_name}'")
            
        return provider.generate(endpoint, prompt, size, quality, expert_params=expert_params)

    def edit_image(self, model_id: str, image_path: str, prompt: str, size: str, quality: str = "Medium", mask_path: str | None = None, expert_params: str | None = None) -> tuple:
        """
        Looks up model in registry and calls appropriate provider for edit.
        Returns: (image_bytes, actual_size, cost)
        """
        model_meta = MODEL_REGISTRY.get(model_id)
        if not model_meta:
            raise ValueError(f"Model {model_id} is not registered")
            
        provider_name = model_meta["provider"]
        endpoint = model_meta["endpoint"]
        
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"No image provider registered for '{provider_name}'")
            
        return provider.edit(endpoint, image_path, prompt, size, quality, mask_path, expert_params=expert_params)
