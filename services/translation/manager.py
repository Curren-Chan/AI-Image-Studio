# -*- coding: utf-8 -*-
from services.translation.openai_translator import OpenAiTranslator
from services.translation.gemini_translator import GeminiTranslator

class TranslationManager:
    def __init__(self, api_client):
        self.api_client = api_client
        self.translators = {
            "openai": OpenAiTranslator(api_client),
            "gemini": GeminiTranslator(api_client)
        }

    def get_translator(self, provider: str):
        """
        Returns translator instance. Falls back to OpenAI if provider is invalid.
        """
        # Map models if provider string is model name
        prov = provider.lower()
        if "gemini" in prov:
            return self.translators["gemini"]
        return self.translators.get(prov, self.translators["openai"])

    def translate_prompt(self, provider: str, prompt_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        translator = self.get_translator(provider)
        return translator.translate_prompt(prompt_jp, translation_rule, negative_prompt, quality)

    def translate_modified_prompt(self, provider: str, prev_jp: str, prev_en: str, new_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        translator = self.get_translator(provider)
        return translator.translate_modified_prompt(prev_jp, prev_en, new_jp, translation_rule, negative_prompt, quality)
