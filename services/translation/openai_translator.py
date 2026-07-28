# -*- coding: utf-8 -*-
import logging
from services.translation.base import BaseTranslator
from services.translation.translation_rules import load_translation_rule

class OpenAiTranslator(BaseTranslator):
    def __init__(self, api_client):
        super().__init__(api_client)

    def calculate_cost(self, prompt_in: str, prompt_out: str) -> float:
        """Estimates the API cost of the text LLM call (gpt-4o-mini)."""
        input_tokens = len(prompt_in) / 4.0
        output_tokens = len(prompt_out) / 4.0
        cost = (input_tokens * 0.15 / 1000000.0) + (output_tokens * 0.60 / 1000000.0)
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
                f"   DALL-E does not support a native negative prompt parameter, so you must explicitly instruct it in English what to omit.\n"
            )

        return quality_instruction, negative_instruction

    def translate_prompt(self, prompt_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        if translation_rule == "Raw - Direct":
            return prompt_jp, 0.0

        if self.api_client.mock_mode:
            return self._mock_generate_prompt(prompt_jp, negative_prompt, quality), 0.0

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
            response = self.api_client.client.chat.completions.create(
                model=self.api_client.text_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            expanded_prompt = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            if not expanded_prompt or not expanded_prompt.strip():
                logging.warning("OpenAI returned empty prompt. Falling back to input Japanese prompt.")
                expanded_prompt = prompt_jp
            cost = self.calculate_cost(system_prompt + user_prompt, expanded_prompt)
            return expanded_prompt, cost
        except Exception as e:
            logging.error(f"API Error in OpenAiTranslator: {e}. Falling back to mock.")
            return self._mock_generate_prompt(prompt_jp, negative_prompt, quality, error_msg=str(e)), 0.0

    def translate_modified_prompt(self, prev_jp: str, prev_en: str, new_jp: str, translation_rule: str = "Standard", negative_prompt: str = "", quality: str = "Medium") -> tuple:
        if translation_rule == "Raw - Direct":
            # For Raw-Direct, since we skip translation, modification just passes the new raw input.
            return new_jp, 0.0

        if self.api_client.mock_mode:
            return self._mock_generate_modified_prompt(prev_jp, prev_en, new_jp, negative_prompt, quality), 0.0
            
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
            response = self.api_client.client.chat.completions.create(
                model=self.api_client.text_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            expanded_prompt = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            if not expanded_prompt or not expanded_prompt.strip():
                logging.warning("OpenAI returned empty modified prompt. Falling back to previous prompt or new request.")
                expanded_prompt = f"{prev_en}, {new_jp}" if prev_en else new_jp
            cost = self.calculate_cost(system_prompt + user_prompt, expanded_prompt)
            return expanded_prompt, cost
        except Exception as e:
            logging.error(f"API Error in OpenAI modified prompt generation: {e}. Falling back to mock.")
            return self._mock_generate_modified_prompt(prev_jp, prev_en, new_jp, negative_prompt, quality, error_msg=str(e)), 0.0

    def _mock_generate_prompt(self, prompt_jp: str, negative_prompt: str = "", quality: str = "Medium", error_msg: str | None = None) -> str:
        replacements = {
            "セクシー": "elegant body lines, subtle contrast of light and shadow",
            "エロ": "elegant body lines, artistic drapery",
            "露出": "artistic drapery, unbuttoned naturally",
            "下着": "delicate clothing drapery",
            "水着": "artistic swimwear",
            "乱れ": "draped casually"
        }
        
        cleaned_jp = prompt_jp
        safety_notice = ""
        for key, val in replacements.items():
            if key in cleaned_jp:
                cleaned_jp = cleaned_jp.replace(key, f"[{val}]")
                safety_notice = " (Safety Bypassed)"
                
        mock_translation = f"An artistic representation of '{cleaned_jp}'"
        if safety_notice:
            mock_translation += f" with {safety_notice}"
            
        if quality in ("High", "hd", "high"):
            mock_translation += " (High Quality Masterpiece)"
        elif quality in ("Low", "low"):
            mock_translation += " (Low Detail Draft Sketch)"
            
        full_prompt = mock_translation
            
        if negative_prompt.strip():
            full_prompt = f"{full_prompt} (Negative constraint: avoid '{negative_prompt}')"
            
        if error_msg:
            full_prompt = f"[API Error Fallback] {full_prompt} (Error: {error_msg})"
            
        return full_prompt

    def _mock_generate_modified_prompt(self, prev_jp: str, prev_en: str, new_jp: str, negative_prompt: str = "", quality: str = "Medium", error_msg: str | None = None) -> str:
        base = prev_en
        
        replacements = {
            "セクシー": "elegant body lines",
            "エロ": "elegant body lines, artistic drapery",
            "露出": "artistic drapery, unbuttoned naturally"
        }
        cleaned_new_jp = new_jp
        for key, val in replacements.items():
            if key in cleaned_new_jp:
                cleaned_new_jp = cleaned_new_jp.replace(key, f"[{val}]")
                
        modified_base = f"{base} (Modified: {cleaned_new_jp})"
        if quality in ("High", "hd", "high"):
            modified_base += " (High Quality)"
        elif quality in ("Low", "low"):
            modified_base += " (Low Detail)"
            
        if negative_prompt.strip():
            modified_base = f"{modified_base} (Negative constraint: avoid '{negative_prompt}')"
            
        if error_msg:
            modified_base = f"[API Error Fallback] {modified_base} (Error: {error_msg})"
            
        return modified_base
