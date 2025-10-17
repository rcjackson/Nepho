from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from PIL import Image
import base64
import io

class BaseModel(ABC):
    """Abstract base class for all chatbot models."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
    
    @abstractmethod
    async def chat(self, prompt: str, images: Optional[List[str]] = None) -> str:
        """Generate a response based on the prompt and optional images."""
        pass
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string for API calls."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Error encoding image {image_path}: {e}")
    
    def validate_image(self, image_path: str) -> bool:
        """Validate if image exists and is in supported format."""
        import os
        from config import config
        
        if not os.path.exists(image_path):
            return False
        
        # Check file extension
        file_ext = os.path.splitext(image_path)[1].lower().lstrip('.')
        if file_ext not in config.SUPPORTED_IMAGE_FORMATS:
            return False
        
        # Check file size
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        if file_size_mb > config.MAX_IMAGE_SIZE_MB:
            return False
        
        # Try to open with PIL to validate it's a valid image
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.model_name})"
