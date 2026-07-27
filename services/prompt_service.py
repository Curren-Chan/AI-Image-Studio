# -*- coding: utf-8 -*-
import logging
from api.client import ApiClient
from services.base import BaseService
from services.translation.manager import TranslationManager

class PromptService(BaseService):
    def __init__(self, api_client: ApiClient | None, db_service=None):
        super().__init__(db_service)
        self._api_client = api_client
        self.translation_manager = TranslationManager(api_client)
        self.settings_service = None

    @property
    def api_client(self):
        return self._api_client

    @api_client.setter
    def api_client(self, value):
        self._api_client = value
        self.translation_manager.api_client = value
        if hasattr(self.translation_manager, 'translators'):
            for translator in self.translation_manager.translators.values():
                translator.api_client = value

    def set_settings_service(self, settings_service):
        self.settings_service = settings_service

    def generate_prompt(self, prompt_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        provider = "openai"
        if self.settings_service:
            provider = self.settings_service.get_setting("translation_provider", "openai")
        
        logging.info(f"Generating prompt using translation provider: {provider}")
        return self.translation_manager.translate_prompt(
            provider=provider,
            prompt_jp=prompt_jp,
            translation_rule=translation_rule,
            negative_prompt=negative_prompt,
            quality=quality
        )

    def generate_modified_prompt(self, prev_jp: str, prev_en: str, new_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        provider = "openai"
        if self.settings_service:
            provider = self.settings_service.get_setting("translation_provider", "openai")
            
        logging.info(f"Generating modified prompt using translation provider: {provider}")
        return self.translation_manager.translate_modified_prompt(
            provider=provider,
            prev_jp=prev_jp,
            prev_en=prev_en,
            new_jp=new_jp,
            translation_rule=translation_rule,
            negative_prompt=negative_prompt,
            quality=quality
        )
