import os
from openai import OpenAI

class ApiClient:
    def __init__(self, api_key=None, text_model="gpt-4o-mini", image_model="gpt-image-2", fal_key=None, gemini_key=None, xai_key=None, hotapi_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.text_model = text_model or os.getenv("OPENAI_MODEL_TEXT", "gpt-4o-mini")
        self.image_model = image_model or os.getenv("OPENAI_MODEL_IMAGE", "gpt-image-2")
        
        self.fal_key = fal_key or os.getenv("FAL_KEY")
        self.gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
        self.xai_key = xai_key or os.getenv("XAI_API_KEY")
        self.hotapi_key = hotapi_key or os.getenv("HOTAPI_KEY")
        
        # mock_mode is True if no keys are set, but for backward compatibility,
        # we check the OpenAI key. We also check other keys during client calls.
        self.mock_mode = not bool(self.api_key or self.fal_key or self.gemini_key or self.xai_key or self.hotapi_key)
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            
    def update_api_key(self, api_key: str):
        self.api_key = api_key
        self.mock_mode = not bool(self.api_key or self.fal_key or self.gemini_key or self.xai_key or self.hotapi_key)
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def update_fal_key(self, fal_key: str):
        self.fal_key = fal_key
        self.mock_mode = not bool(self.api_key or self.fal_key or self.gemini_key or self.xai_key or self.hotapi_key)

    def update_gemini_key(self, gemini_key: str):
        self.gemini_key = gemini_key
        self.mock_mode = not bool(self.api_key or self.fal_key or self.gemini_key or self.xai_key or self.hotapi_key)

    def update_xai_key(self, xai_key: str):
        self.xai_key = xai_key
        self.mock_mode = not bool(self.api_key or self.fal_key or self.gemini_key or self.xai_key or self.hotapi_key)

    def update_hotapi_key(self, hotapi_key: str):
        self.hotapi_key = hotapi_key
        self.mock_mode = not bool(self.api_key or self.fal_key or self.gemini_key or self.xai_key or self.hotapi_key)

