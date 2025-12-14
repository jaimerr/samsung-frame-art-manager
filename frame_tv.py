"""
Samsung Frame TV Integration Module
Based on Samsung Frame Art Mode++ functionality
"""

import os
import time
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import samsungtvws - will fail gracefully if not installed
SAMSUNGTVWS_AVAILABLE = False
SamsungTVWS = None
SamsungTVArt = None

try:
    from samsungtvws import SamsungTVWS
    from samsungtvws.art import SamsungTVArt
    SAMSUNGTVWS_AVAILABLE = True
    logger.info("samsungtvws library loaded successfully")
except ImportError as e:
    logger.warning(f"samsungtvws not installed: {e}")
    logger.warning("Run: pip install 'git+https://github.com/xchwarze/samsung-tv-ws-api.git#egg=samsungtvws[async,encrypted]'")


class FrameTVManager:
    """Manager class for Samsung The Frame TV operations"""
    
    def __init__(self, tv_ip: str, port: int = 8002, token_file: str = None):
        self.tv_ip = tv_ip
        self.port = port
        self.token_file = token_file or os.path.join(os.path.dirname(__file__), 'tv_token.txt')
        self.tv = None
        self._art = None
        self._connected = False
        self._last_error = None
        
    def connect(self) -> bool:
        """Establish connection to the TV"""
        if not SAMSUNGTVWS_AVAILABLE:
            self._last_error = "samsungtvws library not available"
            logger.error(self._last_error)
            return False
        
        try:
            logger.info(f"Connecting to TV at {self.tv_ip}:{self.port}")
            logger.info(f"Token file: {self.token_file}")
            
            # Create TV connection with longer timeout
            self.tv = SamsungTVWS(
                host=self.tv_ip,
                port=self.port,
                token_file=self.token_file,
                timeout=60,  # Longer timeout for initial connection
                name="FrameArtManager"
            )
            
            # Open connection
            self.tv.open()
            logger.info("WebSocket connection opened")
            
            # Try to get art interface
            try:
                self._art = self.tv.art()
                # Test if art mode is supported
                supported = self._art.supported()
                logger.info(f"Art mode supported: {supported}")
            except Exception as art_err:
                logger.warning(f"Art mode check failed (may still work): {art_err}")
            
            self._connected = True
            self._last_error = None
            
            logger.info(f"Successfully connected to Samsung Frame TV at {self.tv_ip}")
            
            # Check if token was saved
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_content = f.read().strip()
                    if token_content:
                        logger.info(f"Token saved and valid")
                    else:
                        logger.warning("Token file exists but is empty")
            
            return True
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Failed to connect to TV: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._connected = False
            return False
    
    def _ensure_connection(self) -> bool:
        """Ensure we have an active connection"""
        if self.tv is None:
            return self.connect()
        
        # Try a simple operation to verify connection is still alive
        try:
            if self._art is None:
                self._art = self.tv.art()
            return self._connected
        except Exception as e:
            logger.warning(f"Connection check failed, reconnecting: {e}")
            self._connected = False
            return self.connect()
    
    def is_connected(self) -> bool:
        """Check if TV is connected"""
        return self._connected and self.tv is not None
    
    def get_last_error(self) -> str:
        """Get the last error message"""
        return self._last_error
    
    def get_art_mode_status(self) -> dict:
        """Get current art mode status"""
        if not self._ensure_connection():
            return {"status": "disconnected", "art_mode": False, "error": self._last_error}
        
        try:
            if self._art is None:
                self._art = self.tv.art()
            
            supported = self._art.supported()
            
            if supported:
                try:
                    status = self._art.get_artmode()
                    return {
                        "status": "connected", 
                        "art_mode": status == "on", 
                        "supported": True,
                        "tv_ip": self.tv_ip
                    }
                except Exception as mode_err:
                    logger.warning(f"Could not get art mode state: {mode_err}")
                    return {
                        "status": "connected", 
                        "art_mode": False, 
                        "supported": True,
                        "tv_ip": self.tv_ip
                    }
            return {"status": "connected", "art_mode": False, "supported": False, "tv_ip": self.tv_ip}
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error getting art mode status: {e}")
            # Don't mark as disconnected for transient errors
            return {"status": "connected", "art_mode": False, "error": str(e), "tv_ip": self.tv_ip}
    
    def set_art_mode(self, enabled: bool) -> bool:
        """Enable or disable art mode"""
        if not self._ensure_connection():
            return False
        
        try:
            if self._art is None:
                self._art = self.tv.art()
            
            if enabled:
                self._art.set_artmode("on")
                logger.info("Art mode enabled")
            else:
                self._art.set_artmode("off")
                logger.info("Art mode disabled")
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error setting art mode: {e}")
            return False
    
    def get_current_art(self) -> dict:
        """Get currently displayed artwork"""
        if not self._ensure_connection():
            return None
        
        try:
            if self._art is None:
                self._art = self.tv.art()
            current = self._art.get_current()
            return current
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error getting current art: {e}")
            return None
    
    def get_art_list(self, category: str = "MY-C0004") -> list:
        """
        Get list of artworks on the TV
        Categories:
        - MY-C0004: My Photos (uploaded images)
        - MY-C0002: Favorites
        """
        if not self._ensure_connection():
            return []
        
        try:
            if self._art is None:
                self._art = self.tv.art()
            
            logger.info(f"Getting art list for category: {category}")
            art_list = self._art.available(category)
            logger.info(f"Found {len(art_list) if art_list else 0} items")
            return art_list if art_list else []
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error getting art list: {e}")
            return []
    
    def upload_image(self, image_path: str, matte: str = "none", 
                     portrait_matte: str = "none") -> dict:
        """
        Upload an image to the TV
        
        Args:
            image_path: Path to the image file
            matte: Matte style (none, flexible, modernthin, modern, modernwide, shadowbox, classic)
        
        Returns:
            dict with upload result including content_id if successful
        """
        if not self._ensure_connection():
            return {"success": False, "error": self._last_error or "Not connected to TV"}
        
        if not os.path.exists(image_path):
            return {"success": False, "error": "Image file not found"}
        
        try:
            logger.info(f"Uploading image: {image_path}")
            
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            file_size_mb = len(image_data) / (1024 * 1024)
            logger.info(f"Image size: {file_size_mb:.2f} MB")
            
            # Determine file type
            file_ext = Path(image_path).suffix.lower()
            file_type = "JPEG"
            if file_ext == ".png":
                file_type = "PNG"
            
            logger.info(f"File type: {file_type}, Matte: {matte}")
            
            # Get art interface
            if self._art is None:
                self._art = self.tv.art()
            
            # Upload to TV
            logger.info("Starting upload to TV...")
            content_id = self._art.upload(
                image_data,
                file_type=file_type,
                matte=matte
            )
            
            logger.info(f"Upload successful! Content ID: {content_id}")
            
            # Optionally set as current image
            try:
                self._art.select_image(content_id, show=True)
                logger.info(f"Image selected as current art")
            except Exception as select_err:
                logger.warning(f"Could not auto-select image: {select_err}")
            
            return {"success": True, "content_id": content_id}
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error uploading image: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    def delete_image(self, content_id: str) -> bool:
        """Delete an image from the TV"""
        if not self._ensure_connection():
            return False
        
        try:
            if self._art is None:
                self._art = self.tv.art()
            self._art.delete(content_id)
            logger.info(f"Deleted image: {content_id}")
            return True
        except Exception as e:
            self._last_error = str(e)
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
        if not self._ensure_connection():
            return False
        
        try:
            if self._art is None:
                self._art = self.tv.art()
            self._art.select_image(content_id, category=category, show=show_matte)
            logger.info(f"Selected image: {content_id}")
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error selecting image: {e}")
            return False
    
    def get_thumbnail(self, content_id: str) -> bytes:
        """Get thumbnail data for an image on the TV"""
        if not self._ensure_connection():
            return None
        
        try:
            if self._art is None:
                self._art = self.tv.art()
            thumbnail = self._art.get_thumbnail(content_id)
            return thumbnail
        except Exception as e:
            self._last_error = str(e)
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
        try:
            if self.tv:
                self.tv.close()
        except:
            pass
        self._connected = False
        self.tv = None


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
    
    def get_last_error(self) -> str:
        return None
    
    def get_art_mode_status(self) -> dict:
        return {
            "status": "connected" if self._connected else "disconnected",
            "art_mode": self._art_mode,
            "supported": True,
            "tv_ip": self.tv_ip
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
    if use_mock:
        logger.info("Using mock Frame TV manager (mock mode enabled)")
        return MockFrameTVManager(tv_ip, **kwargs)
    
    if not SAMSUNGTVWS_AVAILABLE:
        logger.info("Using mock Frame TV manager (library not available)")
        return MockFrameTVManager(tv_ip, **kwargs)
    
    return FrameTVManager(tv_ip, **kwargs)
