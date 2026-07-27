import io
import time
import requests
from PIL import Image, ImageDraw, ImageFont
import os
import logging
from typing import Any
from api.client import ApiClient

class ImageClient:
    def __init__(self, api_client: ApiClient):
        self.api_client = api_client
        
    def calculate_image_cost(self, size: str, quality: str = "Medium") -> float:
        try:
            w, h = map(int, size.split("x"))
            pixels = w * h
            base_cost = 0.04
            if pixels <= 256 * 256:
                base_cost = 0.016
            elif pixels <= 512 * 512:
                base_cost = 0.02
                
            if quality in ("High", "hd", "high"):
                return base_cost * 2.0
            elif quality == "Low":
                return base_cost * 0.5
            return base_cost
        except Exception:
            if quality in ("High", "hd", "high"):
                return 0.08
            elif quality == "Low":
                return 0.02
            return 0.04

    def generate_image_bytes(self, prompt: str, size: str, quality: str = "Medium") -> tuple:
        api_size = size
        # Check size scaling for gpt-image model
        if "gpt-image" in self.api_client.image_model.lower():
            try:
                w, h = map(int, size.split("x"))
                if w * h < 655360:
                    w = min(2048, w * 2)
                    h = min(2048, h * 2)
                    api_size = f"{w}x{h}"
            except Exception:
                pass

        img_cost = self.calculate_image_cost(api_size, quality)
        
        if self.api_client.mock_mode:
            return self._mock_generate_image_bytes(prompt, api_size, quality), api_size, img_cost
            
        try:
            params = {
                "model": self.api_client.image_model,
                "prompt": prompt,
                "n": 1,
                "size": api_size
            }
            if "gpt-image" not in self.api_client.image_model.lower():
                params["response_format"] = "b64_json"

            model_lower = self.api_client.image_model.lower()
            if "dall-e-3" in model_lower:
                if quality in ("High", "hd", "high"):
                    params["quality"] = "hd"
                else:
                    params["quality"] = "standard"
            elif "gpt-image" in model_lower:
                if quality in ("High", "hd", "high"):
                    params["quality"] = "high"
                else:
                    params["quality"] = "medium"

            response = self.api_client.client.images.generate(**params)
            
            if hasattr(response.data[0], "b64_json") and response.data[0].b64_json:
                import base64
                image_bytes = base64.b64decode(response.data[0].b64_json)
            else:
                image_url = response.data[0].url
                download_response = requests.get(image_url, timeout=15)
                download_response.raise_for_status()
                image_bytes = download_response.content
                
            return image_bytes, api_size, img_cost
            
        except Exception as e:
            logging.error(f"API Error in ImageClient: {e}. Falling back to mock.")
            return self._mock_generate_image_bytes(prompt, api_size, quality, error_msg=str(e)), api_size, img_cost

    def _mock_generate_image_bytes(self, prompt: str, size: str, quality: str, error_msg: str | None = None) -> bytes:
        try:
            width, height = map(int, size.split("x"))
        except (AttributeError, TypeError, ValueError):
            width, height = 512, 512
        if (
            width < 64
            or height < 64
            or width > 4096
            or height > 4096
            or width * height > 16_777_216
        ):
            raise ValueError("Mock image dimensions exceed the safe allocation limit")
            
        time.sleep(1.2)
        
        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        
        for y in range(height):
            factor = y / height
            r = int(15 + factor * 35)
            g = int(25 + factor * 25)
            b = int(45 + factor * 75)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
            
        center_x, center_y = width // 2, height // 2
        radius = min(width, height) // 3
        
        for r_offset in range(radius, 0, -12):
            alpha = int((1 - r_offset / radius) * 110)
            glow_color = (0, 191, 255, alpha)
            draw.ellipse(
                [center_x - r_offset, center_y - r_offset, center_x + r_offset, center_y + r_offset],
                fill=glow_color
            )
            
        draw.ellipse([center_x - 12, center_y - 12, center_x + 12, center_y + 12], fill=(255, 20, 147, 220))
        
        font_large: Any = None
        font_medium: Any = None
        font_small: Any = None
        font_paths = [
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\msgothic.ttc"
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_large = ImageFont.truetype(font_path, max(18, int(width * 0.05)))
                    font_medium = ImageFont.truetype(font_path, max(12, int(width * 0.035)))
                    font_small = ImageFont.truetype(font_path, max(10, int(width * 0.026)))
                    break
                except Exception:
                    pass
                    
        if font_large is None:
            font_large = font_medium = font_small = ImageFont.load_default()
            
        draw.text((20, 20), "GPT IMAGE STUDIO", fill=(0, 255, 200, 255), font=font_large)
        img_cost = self.calculate_image_cost(size, quality)
        draw.text((20, 20 + max(25, int(width * 0.06))), f"SIMULATED IMAGE COST: ${img_cost:.3f}", fill=(255, 215, 0, 255), font=font_medium)
        
        if error_msg:
            draw.text((20, 20 + max(50, int(width * 0.12))), "API ERROR FALLBACK", fill=(255, 69, 0, 255), font=font_medium)
            draw.text((20, height - 120), f"Detail: {error_msg}"[:80], fill=(255, 99, 71, 255), font=font_small)
        else:
            draw.text((20, 20 + max(50, int(width * 0.12))), "GPT-IMAGE-2 GENERATION", fill=(220, 220, 220, 255), font=font_medium)
            
        draw.text((20, height - 160), f"QUALITY: {quality.upper()}", fill=(255, 255, 255, 200), font=font_small)

        # Wrap prompt
        wrapped_lines = []
        words = prompt.split(" ")
        current_line: list[str] = []
        max_chars = max(30, int(width / 7.5))
        for word in words:
            test_line = " ".join(current_line + [word])
            if len(test_line) > max_chars:
                wrapped_lines.append(" ".join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        if current_line:
            wrapped_lines.append(" ".join(current_line))
            
        wrapped_lines = wrapped_lines[:4]
        y_offset = height - 130
        draw.text((20, y_offset - 20), "ENHANCED ENGLISH PROMPT:", fill=(255, 255, 255, 180), font=font_small)
        for line in wrapped_lines:
            draw.text((20, y_offset), line, fill=(255, 255, 255, 255), font=font_small)
            y_offset += max(12, int(width * 0.03))
            
        img_byte_arr = io.BytesIO()
        image.convert("RGB").save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()
