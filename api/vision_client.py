import base64
import os
import logging
from api.client import ApiClient

class VisionClient:
    def __init__(self, api_client: ApiClient):
        self.api_client = api_client
        
    def describe_image(self, image_path: str) -> str:
        """Uses gpt-4o-mini Vision API to describe an image for prompt context."""
        if self.api_client.mock_mode:
            return f"A detailed offline mock description of the image: {os.path.basename(image_path)}"
            
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
                
            # Determine mime type
            mime_type = "image/png"
            if image_path.lower().endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
                
            response = self.api_client.client.chat.completions.create(
                model=self.api_client.text_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image in detail for a DALL-E image generation prompt. Provide only the description, no introductory text."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"API Vision Error in VisionClient: {e}")
            return f"A detailed representation of the visual contents of {os.path.basename(image_path)}"
