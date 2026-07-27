# -*- coding: utf-8 -*-

class BaseImageProvider:
    def __init__(self, api_client):
        self.api_client = api_client

    def generate(self, model_endpoint: str, prompt: str, size: str, quality: str, expert_params: str | None = None) -> tuple:
        """
        Generates an image from a text prompt.
        Returns: (image_bytes, actual_size, cost)
        """
        raise NotImplementedError

    def edit(self, model_endpoint: str, image_path: str, prompt: str, size: str, quality: str = "Medium", mask_path: str | None = None, expert_params: str | None = None) -> tuple:
        """
        Edits an existing image based on a prompt.
        Returns: (image_bytes, actual_size, cost)
        """
        raise NotImplementedError
