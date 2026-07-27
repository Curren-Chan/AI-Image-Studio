# -*- coding: utf-8 -*-

class BaseTranslator:
    def __init__(self, api_client):
        self.api_client = api_client

    def translate_prompt(self, prompt_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        """
        Translates Japanese prompt to English with negative prompt and quality considerations.
        Returns: (expanded_prompt_en, cost)
        """
        raise NotImplementedError

    def translate_modified_prompt(self, prev_jp: str, prev_en: str, new_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        """
        Modifies an existing English prompt with new modifications.
        Returns: (expanded_prompt_en, cost)
        """
        raise NotImplementedError
