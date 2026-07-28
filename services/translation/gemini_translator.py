# -*- coding: utf-8 -*-
import logging
from services.translation.base import BaseTranslator
from services.translation.translation_rules import load_translation_rule

class GeminiTranslator(BaseTranslator):
    def __init__(self, api_client):
        super().__init__(api_client)

    def _get_api_key(self):
        return getattr(self.api_client, "gemini_key", None)

    def calculate_cost(self, prompt_in: str, prompt_out: str) -> float:
        # Cost estimate for gemini-3.1-flash-lite
        # Input: $0.075 / 1M tokens, Output: $0.30 / 1M tokens
        input_tokens = len(prompt_in) / 4.0
        output_tokens = len(prompt_out) / 4.0
        cost = (input_tokens * 0.075 / 1000000.0) + (output_tokens * 0.30 / 1000000.0)
        return cost

    def _get_instructions(self, negative_prompt: str, quality: str) -> tuple:
        quality_instruction = ""
        if quality in ("High", "hd", "high"):
            quality_instruction = "Ensure the output is described with rich details, artistic rendering, and high-quality descriptors (e.g. masterpiece, high resolution, stunning detail, ultra-detailed)."
        elif quality in ("Low", "low"):
            quality_instruction = "Optimize for a fast draft or low detail, using simplified descriptions and sketch-like terminology."

        negative_instruction = ""
        if negative_prompt.strip():
            negative_instruction = (
                f"4. Negative Prompt Constraints:\n"
                f"   The user wishes to exclude the following elements from the image: '{negative_prompt}'.\n"
                f"   Translate this to English if necessary, and explicitly describe these exclusions in the output prompt\n"
                f"   (e.g., 'Do not include [elements]', 'avoid [elements]', 'smooth background without [elements]').\n"
                f"   Instruct the image generator in English what to omit.\n"
            )

        return quality_instruction, negative_instruction

    def translate_prompt(self, prompt_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        if translation_rule == "Raw - Direct":
            return prompt_jp, 0.0

        gemini_key = self._get_api_key()
        is_mock = self.api_client.mock_mode or not gemini_key

        if is_mock:
            # Fallback to simple mock generation
            from services.translation.openai_translator import OpenAiTranslator
            fallback = OpenAiTranslator(self.api_client)
            return fallback._mock_generate_prompt(prompt_jp, negative_prompt, quality), 0.0

        quality_instruction, negative_instruction = self._get_instructions(
            negative_prompt, quality
        )

        base_prompt = load_translation_rule(translation_rule)
        
        # Replace placeholders if present
        if "{quality_instruction}" in base_prompt:
            base_prompt = base_prompt.replace("{quality_instruction}", quality_instruction)

        if negative_instruction:
            system_prompt = base_prompt + "\n\n" + negative_instruction
        else:
            system_prompt = base_prompt
        
        user_prompt = f"Japanese description: {prompt_jp}"
        
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    max_output_tokens=300
                )
            )
            text_val = response.text
            expanded_prompt = text_val.strip() if text_val else ""
            if not expanded_prompt or not expanded_prompt.strip():
                logging.warning("Gemini returned empty prompt. Falling back to input Japanese prompt.")
                expanded_prompt = prompt_jp
            cost = self.calculate_cost(system_prompt + user_prompt, expanded_prompt)
            return expanded_prompt, cost
        except Exception as e:
            logging.error(f"API Error in GeminiTranslator: {e}. Falling back to mock.")
            from services.translation.openai_translator import OpenAiTranslator
            fallback = OpenAiTranslator(self.api_client)
            return fallback._mock_generate_prompt(prompt_jp, negative_prompt, quality, error_msg=str(e)), 0.0

    def translate_modified_prompt(self, prev_jp: str, prev_en: str, new_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        if translation_rule == "Raw - Direct":
            return new_jp, 0.0

        gemini_key = self._get_api_key()
        is_mock = self.api_client.mock_mode or not gemini_key

        if is_mock:
            from services.translation.openai_translator import OpenAiTranslator
            fallback = OpenAiTranslator(self.api_client)
            return fallback._mock_generate_modified_prompt(prev_jp, prev_en, new_jp, negative_prompt, quality), 0.0
            
        quality_instruction = ""
        if quality in ("High", "hd", "high"):
            quality_instruction = "Make sure the modified prompt uses detailed and high-quality descriptions."
        elif quality in ("Low", "low"):
            quality_instruction = "Make sure the modified prompt uses simplified, lower detail descriptions."

        negative_instruction = ""
        if negative_prompt.strip():
            negative_instruction = (
                f"Negative Prompt Constraints (Exclude these elements): '{negative_prompt}'.\n"
                f"Formulate instructions in the prompt to omit these elements."
            )
            
        base_prompt = load_translation_rule(translation_rule)
        if "{quality_instruction}" in base_prompt:
            base_prompt = base_prompt.replace("{quality_instruction}", quality_instruction)
        
        system_prompt = (
            f"{base_prompt}\n\n"
            "--- MODIFICATION INSTRUCTIONS ---\n"
            "Here is the context of the previous generation:\n"
            f"- Previous Japanese description: {prev_jp}\n"
            f"- Previous English prompt: {prev_en}\n\n"
            f"The user wants to modify this image. Their modification request is (in Japanese): {new_jp}\n\n"
            "Your task is to generate a new, updated English DALL-E prompt that incorporates the requested change "
            "while maintaining visual consistency with the previous English prompt. Do not start from scratch; "
            "modify the previous prompt selectively.\n"
            f"{quality_instruction}\n"
            f"{negative_instruction}\n"
            "Output ONLY the final updated English prompt. No preamble, no quotes."
        )
        
        user_prompt = f"Modification request: {new_jp}"
        
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    max_output_tokens=300
                )
            )
            text_val = response.text
            expanded_prompt = text_val.strip() if text_val else ""
            if not expanded_prompt or not expanded_prompt.strip():
                logging.warning("Gemini returned empty modified prompt. Falling back to previous prompt or new request.")
                expanded_prompt = f"{prev_en}, {new_jp}" if prev_en else new_jp
            cost = self.calculate_cost(system_prompt + user_prompt, expanded_prompt)
            return expanded_prompt, cost
        except Exception as e:
            logging.error(f"API Error in Gemini modified prompt generation: {e}. Falling back to mock.")
            from services.translation.openai_translator import OpenAiTranslator
            fallback = OpenAiTranslator(self.api_client)
            return fallback._mock_generate_modified_prompt(prev_jp, prev_en, new_jp, negative_prompt, quality, error_msg=str(e)), 0.0
