"""
Samsung Frame TV Integration Module
Based on Samsung Frame Art Mode++ functionality
"""

import os
import time
import base64
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import samsungtvws - will fail gracefully if not installed
try:
    from samsungtvws import SamsungTVWS
    from samsungtvws.art import SamsungTVArt
    SAMSUNGTVWS_AVAILABLE = True
except ImportError:
    SAMSUNGTVWS_AVAILABLE = False
    logger.warning("samsungtvws not installed. Run: pip install 'git+https://github.com/xchwarze/samsung-tv-ws-api.git#egg=samsungtvws[async,encrypted]'")


class FrameTVManager:
    """Manager class for Samsung The Frame TV operations"""
    
    def __init__(self, tv_ip: str, port: int = 8002, token_file: str = None):
        self.tv_ip = tv_ip
        self.port = port
        self.token_file = token_file or os.path.join(os.path.dirname(__file__), '.tv_token')
        self.tv = None
        self.art = None
        self._connected = False
        
    def connect(self) -> bool:
        """Establish connection to the TV"""
        if not SAMSUNGTVWS_AVAILABLE:
            logger.error("samsungtvws library not available")
            return False
            
        try:
            self.tv = SamsungTVWS(
                host=self.tv_ip,
                port=self.port,
                token_file=self.token_file,
                timeout=15,
                name="FrameArtManager"
            )
            # Initialize art mode
            self.art = self.tv.art()
            self._connected = True
            logger.info(f"Connected to Samsung Frame TV at {self.tv_ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to TV: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if TV is connected"""
        return self._connected and self.tv is not None
    
    def get_art_mode_status(self) -> dict:
        """Get current art mode status"""
        if not self.is_connected():
            return {"status": "disconnected", "art_mode": False}
        
        try:
            supported = self.art.supported()
            if supported:
                status = self.art.get_artmode()
                return {"status": "connected", "art_mode": status == "on", "supported": True}
            return {"status": "connected", "art_mode": False, "supported": False}
        except Exception as e:
            logger.error(f"Error getting art mode status: {e}")
            return {"status": "error", "message": str(e)}
    
    def set_art_mode(self, enabled: bool) -> bool:
        """Enable or disable art mode"""
        if not self.is_connected():
            return False
        
        try:
            if enabled:
                self.art.set_artmode("on")
            else:
                self.art.set_artmode("off")
            return True
        except Exception as e:
            logger.error(f"Error setting art mode: {e}")
            return False
    
    def get_current_art(self) -> dict:
        """Get currently displayed artwork"""
        if not self.is_connected():
            return None
        
        try:
            current = self.art.get_current()
            return current
        except Exception as e:
            logger.error(f"Error getting current art: {e}")
            return None
    
    def get_art_list(self, category: str = "MY-C0004") -> list:
        """
        Get list of artworks on the TV
        Categories:
        - MY-C0004: My Photos (uploaded images)
        - MY-C0002: Favorites
        """
        if not self.is_connected():
            return []
        
        try:
            art_list = self.art.available(category)
            return art_list if art_list else []
        except Exception as e:
            logger.error(f"Error getting art list: {e}")
            return []
    
    def upload_image(self, image_path: str, matte: str = "none", 
                     portrait_matte: str = "none") -> dict:
        """
        Upload an image to the TV
        
        Args:
            image_path: Path to the image file
            matte: Matte style for landscape images 
                   (none, flexible, modernthin, modern, modernwide)
            portrait_matte: Matte style for portrait images
        
        Returns:
            dict with upload result including content_id if successful
        """
        if not self.is_connected():
            return {"success": False, "error": "Not connected to TV"}
        
        if not os.path.exists(image_path):
            return {"success": False, "error": "Image file not found"}
        
        try:
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Determine file type
            file_ext = Path(image_path).suffix.lower()
            file_type = "JPEG"
            if file_ext == ".png":
                file_type = "PNG"
            
            # Upload to TV
            content_id = self.art.upload(
                image_data,
                file_type=file_type,
                matte=matte
            )
            
            logger.info(f"Uploaded image: {image_path} -> {content_id}")
            return {"success": True, "content_id": content_id}
            
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_image(self, content_id: str) -> bool:
        """Delete an image from the TV"""
        if not self.is_connected():
            return False
        
        try:
            self.art.delete(content_id)
            logger.info(f"Deleted image: {content_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            return False
    
    def select_image(self, content_id: str, category: str = "MY-C0004",
                     show_matte: bool = True) -> bool:
        """
        Set an image as the currently displayed artwork
        
        Args:
            content_id: The content ID of the image to display
            category: Category of the image
            show_matte: Whether to show the matte/frame
        """
        if not self.is_connected():
            return False
        
        try:
            self.art.select_image(content_id, category=category, show=show_matte)
            logger.info(f"Selected image: {content_id}")
            return True
        except Exception as e:
            logger.error(f"Error selecting image: {e}")
            return False
    
    def get_thumbnail(self, content_id: str) -> bytes:
        """Get thumbnail data for an image on the TV"""
        if not self.is_connected():
            return None
        
        try:
            thumbnail = self.art.get_thumbnail(content_id)
            return thumbnail
        except Exception as e:
            logger.error(f"Error getting thumbnail: {e}")
            return None
    
    def get_matte_list(self) -> list:
        """Get available matte styles"""
        return [
            {"id": "none", "name": "No Matte"},
            {"id": "flexible", "name": "Flexible"},
            {"id": "modernthin", "name": "Modern Thin"},
            {"id": "modern", "name": "Modern"},
            {"id": "modernwide", "name": "Modern Wide"},
            {"id": "shadowbox", "name": "Shadow Box"},
            {"id": "classic", "name": "Classic"},
        ]
    
    def disconnect(self):
        """Disconnect from the TV"""
        self._connected = False
        self.tv = None
        self.art = None


class MockFrameTVManager:
    """Mock manager for testing without a TV connection"""
    
    def __init__(self, tv_ip: str = "192.168.1.100", **kwargs):
        self.tv_ip = tv_ip
        self._connected = False
        self._art_mode = False
        self._images = []
        self._current_image = None
    
    def connect(self) -> bool:
        self._connected = True
        return True
    
    def is_connected(self) -> bool:
        return self._connected
    
    def get_art_mode_status(self) -> dict:
        return {
            "status": "connected" if self._connected else "disconnected",
            "art_mode": self._art_mode,
            "supported": True
        }
    
    def set_art_mode(self, enabled: bool) -> bool:
        self._art_mode = enabled
        return True
    
    def get_current_art(self) -> dict:
        return self._current_image
    
    def get_art_list(self, category: str = "MY-C0004") -> list:
        return self._images
    
    def upload_image(self, image_path: str, matte: str = "none", 
                     portrait_matte: str = "none") -> dict:
        content_id = f"MY_PHOTO_{len(self._images) + 1}_{int(time.time())}"
        self._images.append({
            "content_id": content_id,
            "path": image_path,
            "matte": matte
        })
        return {"success": True, "content_id": content_id}
    
    def delete_image(self, content_id: str) -> bool:
        self._images = [img for img in self._images if img.get("content_id") != content_id]
        return True
    
    def select_image(self, content_id: str, **kwargs) -> bool:
        for img in self._images:
            if img.get("content_id") == content_id:
                self._current_image = img
                return True
        return False
    
    def get_thumbnail(self, content_id: str) -> bytes:
        return None
    
    def get_matte_list(self) -> list:
        return FrameTVManager("").get_matte_list()
    
    def disconnect(self):
        self._connected = False


def get_frame_manager(tv_ip: str, use_mock: bool = False, **kwargs):
    """
    Factory function to get the appropriate Frame TV manager
    
    Args:
        tv_ip: IP address of the Samsung Frame TV
        use_mock: If True, return mock manager for testing
    """
    if use_mock or not SAMSUNGTVWS_AVAILABLE:
        logger.info("Using mock Frame TV manager")
        return MockFrameTVManager(tv_ip, **kwargs)
    return FrameTVManager(tv_ip, **kwargs)

