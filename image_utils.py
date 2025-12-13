"""
Image Processing Utilities for Samsung The Frame
Handles resizing, cropping, and formatting images for optimal display
"""

import os
import io
import logging
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ExifTags

# Register HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

logger = logging.getLogger(__name__)

# Samsung Frame TV Display Resolutions
FRAME_RESOLUTIONS = {
    "4K_landscape": (3840, 2160),  # Landscape mode
    "4K_portrait": (2160, 3840),   # Portrait mode
    "1080p_landscape": (1920, 1080),
    "1080p_portrait": (1080, 1920),
}

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.heic', '.heif'}


def convert_heic_to_jpeg(input_path: str, output_path: str = None, quality: int = 100) -> str:
    """
    Convert HEIC/HEIF file to JPEG
    
    Args:
        input_path: Path to HEIC file
        output_path: Output path (if None, replaces extension with .jpg)
        quality: JPEG quality (1-100)
    
    Returns:
        Path to converted JPEG file
    """
    if output_path is None:
        output_path = str(Path(input_path).with_suffix('.jpg'))
    
    try:
        with Image.open(input_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Fix orientation from EXIF
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                exif = img._getexif()
                if exif is not None:
                    exif_orientation = exif.get(orientation)
                    if exif_orientation == 2:
                        img = img.transpose(Image.FLIP_LEFT_RIGHT)
                    elif exif_orientation == 3:
                        img = img.rotate(180)
                    elif exif_orientation == 4:
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)
                    elif exif_orientation == 5:
                        img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                    elif exif_orientation == 6:
                        img = img.rotate(-90, expand=True)
                    elif exif_orientation == 7:
                        img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                    elif exif_orientation == 8:
                        img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError, TypeError):
                pass
            
            # Save as high-quality JPEG
            img.save(output_path, "JPEG", quality=quality, optimize=True, progressive=True)
            logger.info(f"Converted HEIC to JPEG: {output_path}")
            return output_path
            
    except Exception as e:
        logger.error(f"Error converting HEIC: {e}")
        raise


def is_heic_file(filepath: str) -> bool:
    """Check if file is HEIC/HEIF format"""
    return Path(filepath).suffix.lower() in {'.heic', '.heif'}


class ImageProcessor:
    """Process images for Samsung The Frame TV display"""
    
    def __init__(self, target_resolution: tuple = (3840, 2160), 
                 quality: int = 100, portrait_mode: bool = False):
        """
        Initialize the image processor
        
        Args:
            target_resolution: Target (width, height) for the TV
            quality: JPEG quality for output (1-100)
            portrait_mode: If True, use portrait orientation (2160x3840)
        """
        if portrait_mode:
            self.target_width, self.target_height = (2160, 3840)
        else:
            self.target_width, self.target_height = target_resolution
        self.target_aspect = self.target_width / self.target_height
        self.quality = 100  # Maximum quality for The Frame
        self.portrait_mode = portrait_mode
    
    def set_orientation(self, portrait: bool):
        """Switch between portrait and landscape mode"""
        if portrait:
            self.target_width, self.target_height = (2160, 3840)
        else:
            self.target_width, self.target_height = (3840, 2160)
        self.target_aspect = self.target_width / self.target_height
        self.portrait_mode = portrait
    
    def fix_orientation(self, image: Image.Image) -> Image.Image:
        """Fix image orientation based on EXIF data"""
        try:
            # Get EXIF orientation tag
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            
            exif = image._getexif()
            if exif is not None:
                exif_orientation = exif.get(orientation)
                
                if exif_orientation == 2:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                elif exif_orientation == 3:
                    image = image.rotate(180)
                elif exif_orientation == 4:
                    image = image.transpose(Image.FLIP_TOP_BOTTOM)
                elif exif_orientation == 5:
                    image = image.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                elif exif_orientation == 6:
                    image = image.rotate(-90, expand=True)
                elif exif_orientation == 7:
                    image = image.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                elif exif_orientation == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError, TypeError):
            # No EXIF data or orientation tag
            pass
        
        return image
    
    def get_image_info(self, image_path: str) -> dict:
        """Get information about an image"""
        try:
            with Image.open(image_path) as img:
                img = self.fix_orientation(img)
                width, height = img.size
                aspect = width / height
                orientation = "landscape" if width >= height else "portrait"
                
                return {
                    "width": width,
                    "height": height,
                    "aspect_ratio": round(aspect, 2),
                    "orientation": orientation,
                    "format": img.format,
                    "mode": img.mode,
                    "file_size": os.path.getsize(image_path),
                    "needs_resize": width != self.target_width or height != self.target_height
                }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return None
    
    def process_image(self, input_path: str, output_path: str = None,
                      fit_mode: str = "contain", 
                      background_color: tuple = (0, 0, 0),
                      background_blur: bool = False) -> str:
        """
        Process an image for The Frame display
        
        Args:
            input_path: Path to input image
            output_path: Path for output (if None, creates _processed suffix)
            fit_mode: How to fit image to display:
                - "contain": Fit entire image, add letterbox/pillarbox
                - "cover": Fill display, crop excess
                - "stretch": Stretch to fill (may distort)
                - "smart": Automatically choose best method
            background_color: RGB tuple for letterbox/pillarbox areas
            background_blur: Use blurred image as background instead of solid color
        
        Returns:
            Path to processed image
        """
        if output_path is None:
            path = Path(input_path)
            output_path = str(path.parent / f"{path.stem}_processed.jpg")
        
        try:
            with Image.open(input_path) as img:
                # Fix orientation first
                img = self.fix_orientation(img)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, background_color)
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get current dimensions
                orig_width, orig_height = img.size
                orig_aspect = orig_width / orig_height
                
                # Determine fit mode if smart
                if fit_mode == "smart":
                    aspect_diff = abs(orig_aspect - self.target_aspect)
                    if aspect_diff < 0.1:  # Very close aspect ratios
                        fit_mode = "cover"
                    else:
                        fit_mode = "contain"
                
                # Process based on fit mode
                if fit_mode == "contain":
                    processed = self._fit_contain(img, background_color, background_blur)
                elif fit_mode == "cover":
                    processed = self._fit_cover(img)
                elif fit_mode == "stretch":
                    processed = img.resize((self.target_width, self.target_height), 
                                          Image.Resampling.LANCZOS)
                else:
                    processed = self._fit_contain(img, background_color, background_blur)
                
                # Save processed image
                processed.save(output_path, "JPEG", quality=self.quality, 
                              optimize=True, progressive=True)
                
                logger.info(f"Processed image saved to: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    def _fit_contain(self, img: Image.Image, background_color: tuple,
                     background_blur: bool = False) -> Image.Image:
        """
        Fit image within target dimensions, preserving aspect ratio
        Adds letterbox or pillarbox as needed
        """
        orig_width, orig_height = img.size
        orig_aspect = orig_width / orig_height
        
        # Calculate new dimensions to fit within target
        if orig_aspect > self.target_aspect:
            # Image is wider - fit to width
            new_width = self.target_width
            new_height = int(new_width / orig_aspect)
        else:
            # Image is taller - fit to height
            new_height = self.target_height
            new_width = int(new_height * orig_aspect)
        
        # Resize image
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create background
        if background_blur:
            # Use blurred version of original image as background
            background = img.resize((self.target_width, self.target_height), 
                                   Image.Resampling.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(radius=50))
            # Darken the blurred background
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(background)
            background = enhancer.enhance(0.3)
        else:
            background = Image.new('RGB', (self.target_width, self.target_height), 
                                  background_color)
        
        # Calculate position to center image
        x = (self.target_width - new_width) // 2
        y = (self.target_height - new_height) // 2
        
        # Paste resized image onto background
        background.paste(resized, (x, y))
        
        return background
    
    def _fit_cover(self, img: Image.Image) -> Image.Image:
        """
        Fill target dimensions, cropping excess while preserving aspect ratio
        Uses center crop
        """
        orig_width, orig_height = img.size
        orig_aspect = orig_width / orig_height
        
        # Calculate dimensions to cover target
        if orig_aspect > self.target_aspect:
            # Image is wider - fit to height and crop width
            new_height = self.target_height
            new_width = int(new_height * orig_aspect)
        else:
            # Image is taller - fit to width and crop height
            new_width = self.target_width
            new_height = int(new_width / orig_aspect)
        
        # Resize image
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center crop
        x = (new_width - self.target_width) // 2
        y = (new_height - self.target_height) // 2
        
        cropped = resized.crop((x, y, x + self.target_width, y + self.target_height))
        
        return cropped
    
    def create_thumbnail(self, image_path: str, size: tuple = (400, 225)) -> bytes:
        """Create a thumbnail for web display"""
        try:
            with Image.open(image_path) as img:
                img = self.fix_orientation(img)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save to bytes
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                return buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return None
    
    def batch_process(self, input_dir: str, output_dir: str, 
                      fit_mode: str = "contain", **kwargs) -> list:
        """
        Process all images in a directory
        
        Returns:
            List of tuples (input_path, output_path, success)
        """
        results = []
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for file_path in input_path.iterdir():
            if file_path.suffix.lower() in SUPPORTED_FORMATS:
                try:
                    out_file = output_path / f"{file_path.stem}_processed.jpg"
                    self.process_image(str(file_path), str(out_file), 
                                      fit_mode=fit_mode, **kwargs)
                    results.append((str(file_path), str(out_file), True))
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    results.append((str(file_path), None, False))
        
        return results
    
    def crop_to_frame(self, input_path: str, output_path: str = None,
                      crop_box: tuple = None, portrait: bool = True) -> str:
        """
        Crop and resize image to exact Frame dimensions
        Supports extended crop areas beyond image bounds (filled with black)
        
        Args:
            input_path: Path to input image
            output_path: Path for output (if None, creates _cropped suffix)
            crop_box: Optional (left, top, right, bottom) crop coordinates as percentages
                      Can be negative or >100 to extend beyond image (black fill)
                      If None, uses center crop
            portrait: If True, crop to portrait 2160x3840, else landscape 3840x2160
        
        Returns:
            Path to cropped image
        """
        if output_path is None:
            path = Path(input_path)
            suffix = "_portrait" if portrait else "_landscape"
            output_path = str(path.parent / f"{path.stem}{suffix}.jpg")
        
        # Set target dimensions
        if portrait:
            target_w, target_h = 2160, 3840
        else:
            target_w, target_h = 3840, 2160
        
        try:
            with Image.open(input_path) as img:
                # Fix orientation first
                img = self.fix_orientation(img)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (0, 0, 0))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                orig_width, orig_height = img.size
                
                if crop_box:
                    # Use provided crop box (percentages - can be negative or >100)
                    left_pct, top_pct, right_pct, bottom_pct = crop_box
                    
                    # Calculate pixel coordinates (can be negative or beyond image)
                    crop_left = orig_width * left_pct / 100
                    crop_top = orig_height * top_pct / 100
                    crop_right = orig_width * right_pct / 100
                    crop_bottom = orig_height * bottom_pct / 100
                    
                    crop_width = crop_right - crop_left
                    crop_height = crop_bottom - crop_top
                    
                    # Create a new black canvas for the crop area
                    canvas = Image.new('RGB', (int(crop_width), int(crop_height)), (0, 0, 0))
                    
                    # Calculate where to paste the original image on the canvas
                    paste_x = int(-crop_left) if crop_left < 0 else 0
                    paste_y = int(-crop_top) if crop_top < 0 else 0
                    
                    # Calculate what portion of the original image to use
                    src_left = int(max(0, crop_left))
                    src_top = int(max(0, crop_top))
                    src_right = int(min(orig_width, crop_right))
                    src_bottom = int(min(orig_height, crop_bottom))
                    
                    # Only paste if there's overlap with the original image
                    if src_right > src_left and src_bottom > src_top:
                        # Crop the portion of original image that's within bounds
                        img_portion = img.crop((src_left, src_top, src_right, src_bottom))
                        
                        # Adjust paste position if crop started within image
                        if crop_left > 0:
                            paste_x = 0
                        if crop_top > 0:
                            paste_y = 0
                        
                        canvas.paste(img_portion, (paste_x, paste_y))
                    
                    # Resize to target dimensions
                    final = canvas.resize((target_w, target_h), Image.Resampling.LANCZOS)
                else:
                    # No crop box - use center crop to target aspect ratio
                    target_aspect = target_w / target_h
                    orig_aspect = orig_width / orig_height
                    
                    if orig_aspect > target_aspect:
                        # Image is wider - crop width
                        new_width = int(orig_height * target_aspect)
                        new_height = orig_height
                        left = (orig_width - new_width) // 2
                        top = 0
                    else:
                        # Image is taller - crop height
                        new_width = orig_width
                        new_height = int(orig_width / target_aspect)
                        left = 0
                        top = (orig_height - new_height) // 2
                    
                    cropped = img.crop((left, top, left + new_width, top + new_height))
                    final = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                # Save
                final.save(output_path, "JPEG", quality=self.quality, 
                          optimize=True, progressive=True)
                
                logger.info(f"Cropped image saved to: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error cropping image: {e}")
            raise
    
    def get_crop_preview(self, input_path: str, portrait: bool = True) -> dict:
        """
        Get crop preview information for an image
        
        Returns:
            dict with original dimensions, suggested crop box, and preview dimensions
        """
        try:
            with Image.open(input_path) as img:
                img = self.fix_orientation(img)
                orig_width, orig_height = img.size
                
                # Target aspect ratio
                if portrait:
                    target_aspect = 2160 / 3840  # 0.5625 (9:16)
                else:
                    target_aspect = 3840 / 2160  # 1.778 (16:9)
                
                orig_aspect = orig_width / orig_height
                
                # Calculate suggested crop area
                if orig_aspect > target_aspect:
                    # Image is wider - suggest cropping width
                    new_width = int(orig_height * target_aspect)
                    new_height = orig_height
                    left = (orig_width - new_width) // 2
                    top = 0
                else:
                    # Image is taller - suggest cropping height
                    new_width = orig_width
                    new_height = int(orig_width / target_aspect)
                    left = 0
                    top = (orig_height - new_height) // 2
                
                # Return as percentages for easier UI handling
                return {
                    "original_width": orig_width,
                    "original_height": orig_height,
                    "original_aspect": round(orig_aspect, 3),
                    "target_aspect": round(target_aspect, 3),
                    "suggested_crop": {
                        "left": round(left / orig_width * 100, 2),
                        "top": round(top / orig_height * 100, 2),
                        "right": round((left + new_width) / orig_width * 100, 2),
                        "bottom": round((top + new_height) / orig_height * 100, 2),
                        "width": new_width,
                        "height": new_height
                    },
                    "output_dimensions": {
                        "width": 2160 if portrait else 3840,
                        "height": 3840 if portrait else 2160
                    }
                }
        except Exception as e:
            logger.error(f"Error getting crop preview: {e}")
            return None


def is_valid_image(file_path: str) -> bool:
    """Check if a file is a valid image"""
    try:
        ext = Path(file_path).suffix.lower()
        if ext not in SUPPORTED_FORMATS:
            return False
        
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def get_supported_formats() -> set:
    """Get set of supported image format extensions"""
    return SUPPORTED_FORMATS.copy()

