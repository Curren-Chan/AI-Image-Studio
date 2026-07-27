import os
import base64

def encode_image_base64(image_path: str) -> str:
    """Encodes a local image file to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_mime_type(image_path: str) -> str:
    """Returns the mime-type of an image based on its extension."""
    ext = os.path.splitext(image_path)[1].lower()
    if ext in ('.jpg', '.jpeg'):
        return "image/jpeg"
    return "image/png"
