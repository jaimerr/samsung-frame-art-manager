"""
Samsung Frame Art Manager - Flask Application
A web interface to manage art on Samsung The Frame TV
"""

import os
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, jsonify, 
                   send_file, redirect, url_for, flash, session)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from image_utils import ImageProcessor, is_valid_image, get_supported_formats, convert_heic_to_jpeg, is_heic_file
from frame_tv import get_frame_manager, SAMSUNGTVWS_AVAILABLE

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'frame-art-manager-secret-key-change-me')

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
PROCESSED_FOLDER = os.path.join(os.path.dirname(__file__), 'processed')
THUMBNAILS_FOLDER = os.path.join(os.path.dirname(__file__), 'thumbnails')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

# Create necessary directories
for folder in [UPLOAD_FOLDER, PROCESSED_FOLDER, THUMBNAILS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Allowed extensions (including HEIC)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'tif', 'heic', 'heif'}

# Global state
frame_manager = None
image_processor = ImageProcessor()


def load_config() -> dict:
    """Load configuration from file"""
    default_config = {
        "tv_ip": "",
        "tv_port": 8002,
        "use_mock": not SAMSUNGTVWS_AVAILABLE,
        "default_fit_mode": "contain",
        "default_matte": "none",
        "background_color": [0, 0, 0],
        "use_blur_background": False,
        "auto_process": True
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                return {**default_config, **config}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    return default_config


def save_config(config: dict):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {e}")


def get_frame_manager_instance():
    """Get or create frame manager instance"""
    global frame_manager
    config = load_config()
    
    if frame_manager is None and config.get('tv_ip'):
        frame_manager = get_frame_manager(
            tv_ip=config['tv_ip'],
            port=config.get('tv_port', 8002),
            use_mock=config.get('use_mock', False)
        )
    
    return frame_manager


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_image_metadata(filename: str) -> dict:
    """Get metadata for an uploaded image"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    processed_path = os.path.join(PROCESSED_FOLDER, f"{Path(filename).stem}_processed.jpg")
    
    info = image_processor.get_image_info(filepath)
    if info:
        info['filename'] = filename
        info['uploaded'] = datetime.fromtimestamp(
            os.path.getmtime(filepath)
        ).isoformat()
        info['processed'] = os.path.exists(processed_path)
        info['processed_path'] = processed_path if info['processed'] else None
    
    return info


def get_all_images() -> list:
    """Get list of all uploaded images with metadata"""
    images = []
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath) and allowed_file(filename):
            metadata = get_image_metadata(filename)
            if metadata:
                images.append(metadata)
    
    # Sort by upload date, newest first
    images.sort(key=lambda x: x.get('uploaded', ''), reverse=True)
    return images


# Routes

@app.route('/')
def index():
    """Main page - Gallery view"""
    config = load_config()
    images = get_all_images()
    
    return render_template('index.html', 
                         images=images, 
                         config=config,
                         tv_connected=frame_manager is not None and frame_manager.is_connected(),
                         samsungtvws_available=SAMSUNGTVWS_AVAILABLE)


@app.route('/settings')
def settings():
    """Settings page"""
    config = load_config()
    return render_template('settings.html', 
                         config=config,
                         samsungtvws_available=SAMSUNGTVWS_AVAILABLE)


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    if request.method == 'GET':
        return jsonify(load_config())
    
    elif request.method == 'POST':
        config = load_config()
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['tv_ip', 'tv_port', 'use_mock', 'default_fit_mode',
                         'default_matte', 'background_color', 'use_blur_background',
                         'auto_process']
        
        for field in allowed_fields:
            if field in data:
                config[field] = data[field]
        
        save_config(config)
        
        # Reconnect to TV if IP changed
        global frame_manager
        if 'tv_ip' in data:
            frame_manager = None
            if data['tv_ip']:
                frame_manager = get_frame_manager(
                    tv_ip=data['tv_ip'],
                    port=config.get('tv_port', 8002),
                    use_mock=config.get('use_mock', False)
                )
        
        return jsonify({"success": True, "config": config})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle image upload"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400
    
    try:
        # Generate unique filename
        ext = Path(file.filename).suffix.lower()
        unique_id = uuid.uuid4().hex
        temp_filename = f"{unique_id}{ext}"
        temp_filepath = os.path.join(UPLOAD_FOLDER, temp_filename)
        
        # Save file temporarily
        file.save(temp_filepath)
        
        # Convert HEIC/HEIF to JPEG
        if is_heic_file(temp_filepath):
            try:
                # Convert to JPEG
                jpeg_filename = f"{unique_id}.jpg"
                jpeg_filepath = os.path.join(UPLOAD_FOLDER, jpeg_filename)
                convert_heic_to_jpeg(temp_filepath, jpeg_filepath)
                
                # Remove original HEIC file
                os.remove(temp_filepath)
                
                # Use JPEG version
                unique_filename = jpeg_filename
                filepath = jpeg_filepath
                logger.info(f"Converted HEIC to JPEG: {unique_filename}")
            except Exception as e:
                logger.error(f"HEIC conversion failed: {e}")
                os.remove(temp_filepath)
                return jsonify({"error": f"Failed to convert HEIC: {str(e)}"}), 500
        else:
            unique_filename = temp_filename
            filepath = temp_filepath
        
        # Validate image
        if not is_valid_image(filepath):
            os.remove(filepath)
            return jsonify({"error": "Invalid image file"}), 400
        
        # Get image info
        metadata = get_image_metadata(unique_filename)
        
        # Auto-process if enabled
        config = load_config()
        if config.get('auto_process', True):
            try:
                processed_path = os.path.join(
                    PROCESSED_FOLDER, 
                    f"{Path(unique_filename).stem}_processed.jpg"
                )
                image_processor.process_image(
                    filepath, 
                    processed_path,
                    fit_mode=config.get('default_fit_mode', 'contain'),
                    background_color=tuple(config.get('background_color', [0, 0, 0])),
                    background_blur=config.get('use_blur_background', False)
                )
                metadata['processed'] = True
                metadata['processed_path'] = processed_path
            except Exception as e:
                logger.error(f"Auto-process failed: {e}")
        
        # Create thumbnail
        thumb_path = os.path.join(THUMBNAILS_FOLDER, f"{Path(unique_filename).stem}_thumb.jpg")
        thumb_data = image_processor.create_thumbnail(filepath)
        if thumb_data:
            with open(thumb_path, 'wb') as f:
                f.write(thumb_data)
        
        return jsonify({
            "success": True,
            "filename": unique_filename,
            "metadata": metadata
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/images')
def api_images():
    """Get list of all images"""
    return jsonify(get_all_images())


@app.route('/api/images/<filename>')
def api_image_info(filename):
    """Get info for a specific image"""
    metadata = get_image_metadata(filename)
    if metadata:
        return jsonify(metadata)
    return jsonify({"error": "Image not found"}), 404


@app.route('/api/images/<filename>/process', methods=['POST'])
def process_image(filename):
    """Process an image with specified settings"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    
    data = request.get_json() or {}
    config = load_config()
    
    try:
        processed_path = os.path.join(
            PROCESSED_FOLDER, 
            f"{Path(filename).stem}_processed.jpg"
        )
        
        fit_mode = data.get('fit_mode', config.get('default_fit_mode', 'contain'))
        bg_color = data.get('background_color', config.get('background_color', [0, 0, 0]))
        use_blur = data.get('use_blur_background', config.get('use_blur_background', False))
        
        image_processor.process_image(
            filepath,
            processed_path,
            fit_mode=fit_mode,
            background_color=tuple(bg_color),
            background_blur=use_blur
        )
        
        return jsonify({
            "success": True,
            "processed_path": processed_path
        })
        
    except Exception as e:
        logger.error(f"Process error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/images/<filename>/crop-preview')
def crop_preview(filename):
    """Get crop preview data for an image"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    
    portrait = request.args.get('portrait', 'true').lower() == 'true'
    
    try:
        preview_data = image_processor.get_crop_preview(filepath, portrait=portrait)
        if preview_data:
            return jsonify(preview_data)
        return jsonify({"error": "Could not generate preview"}), 500
    except Exception as e:
        logger.error(f"Crop preview error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/images/<filename>/crop', methods=['POST'])
def crop_image(filename):
    """Crop an image for The Frame display - saves as a new image in gallery"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    
    data = request.get_json() or {}
    portrait = data.get('portrait', True)
    crop_box = data.get('crop_box')  # [left, top, right, bottom] as percentages
    
    try:
        # Create a new file in uploads folder so it appears in gallery
        suffix = "_portrait" if portrait else "_landscape"
        new_filename = f"{Path(filename).stem}{suffix}.jpg"
        cropped_path = os.path.join(UPLOAD_FOLDER, new_filename)
        
        # If file exists, add unique suffix
        if os.path.exists(cropped_path):
            new_filename = f"{Path(filename).stem}{suffix}_{uuid.uuid4().hex[:6]}.jpg"
            cropped_path = os.path.join(UPLOAD_FOLDER, new_filename)
        
        image_processor.crop_to_frame(
            filepath,
            cropped_path,
            crop_box=tuple(crop_box) if crop_box else None,
            portrait=portrait
        )
        
        # Create thumbnail for the cropped version
        thumb_name = f"{Path(new_filename).stem}_thumb.jpg"
        thumb_path = os.path.join(THUMBNAILS_FOLDER, thumb_name)
        thumb_data = image_processor.create_thumbnail(cropped_path)
        if thumb_data:
            with open(thumb_path, 'wb') as f:
                f.write(thumb_data)
        
        # Get metadata for the new cropped image
        metadata = get_image_metadata(new_filename)
        
        return jsonify({
            "success": True,
            "filename": new_filename,
            "cropped_path": cropped_path,
            "metadata": metadata,
            "dimensions": {
                "width": 2160 if portrait else 3840,
                "height": 3840 if portrait else 2160
            }
        })
        
    except Exception as e:
        logger.error(f"Crop error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/images/<filename>/delete', methods=['DELETE'])
def delete_image(filename):
    """Delete an image and its processed version"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    
    try:
        # Delete original
        os.remove(filepath)
        
        # Delete processed version if exists
        processed_path = os.path.join(PROCESSED_FOLDER, 
                                      f"{Path(filename).stem}_processed.jpg")
        if os.path.exists(processed_path):
            os.remove(processed_path)
        
        # Delete thumbnail if exists
        thumb_path = os.path.join(THUMBNAILS_FOLDER, 
                                  f"{Path(filename).stem}_thumb.jpg")
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded image"""
    return send_file(os.path.join(UPLOAD_FOLDER, filename))


@app.route('/processed/<filename>')
def serve_processed(filename):
    """Serve processed image"""
    return send_file(os.path.join(PROCESSED_FOLDER, filename))


@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """Serve thumbnail image"""
    thumb_path = os.path.join(THUMBNAILS_FOLDER, filename)
    if os.path.exists(thumb_path):
        return send_file(thumb_path)
    # Fall back to original if thumbnail doesn't exist
    original = filename.replace('_thumb', '').replace('.jpg', '')
    for ext in ALLOWED_EXTENSIONS:
        original_path = os.path.join(UPLOAD_FOLDER, f"{original}.{ext}")
        if os.path.exists(original_path):
            return send_file(original_path)
    return jsonify({"error": "Not found"}), 404


# Frame TV API Routes

@app.route('/api/tv/connect', methods=['POST'])
def tv_connect():
    """Connect to the Samsung Frame TV"""
    global frame_manager
    config = load_config()
    
    if not config.get('tv_ip'):
        return jsonify({"error": "TV IP not configured"}), 400
    
    try:
        frame_manager = get_frame_manager(
            tv_ip=config['tv_ip'],
            port=config.get('tv_port', 8002),
            use_mock=config.get('use_mock', False)
        )
        
        success = frame_manager.connect()
        
        if success:
            return jsonify({
                "success": True,
                "status": frame_manager.get_art_mode_status()
            })
        else:
            return jsonify({"error": "Failed to connect to TV"}), 500
            
    except Exception as e:
        logger.error(f"TV connect error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tv/status')
def tv_status():
    """Get TV connection and art mode status"""
    if frame_manager is None:
        return jsonify({
            "connected": False,
            "status": "Not configured"
        })
    
    try:
        status = frame_manager.get_art_mode_status()
        return jsonify({
            "connected": frame_manager.is_connected(),
            **status
        })
    except Exception as e:
        return jsonify({
            "connected": False,
            "error": str(e)
        })


@app.route('/api/tv/art-mode', methods=['POST'])
def set_art_mode():
    """Enable or disable art mode"""
    if frame_manager is None or not frame_manager.is_connected():
        return jsonify({"error": "TV not connected"}), 400
    
    data = request.get_json()
    enabled = data.get('enabled', True)
    
    success = frame_manager.set_art_mode(enabled)
    
    if success:
        return jsonify({"success": True, "art_mode": enabled})
    return jsonify({"error": "Failed to set art mode"}), 500


@app.route('/api/tv/upload', methods=['POST'])
def upload_to_tv():
    """Upload a processed image to the TV"""
    if frame_manager is None or not frame_manager.is_connected():
        return jsonify({"error": "TV not connected"}), 400
    
    data = request.get_json()
    filename = data.get('filename')
    matte = data.get('matte', 'none')
    
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    
    # Use processed version if available
    processed_path = os.path.join(PROCESSED_FOLDER, 
                                  f"{Path(filename).stem}_processed.jpg")
    if os.path.exists(processed_path):
        image_path = processed_path
    else:
        image_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(image_path):
        return jsonify({"error": "Image not found"}), 404
    
    result = frame_manager.upload_image(image_path, matte=matte)
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@app.route('/api/tv/art-list')
def get_tv_art_list():
    """Get list of art on the TV"""
    if frame_manager is None or not frame_manager.is_connected():
        return jsonify({"error": "TV not connected"}), 400
    
    try:
        art_list = frame_manager.get_art_list()
        return jsonify({"success": True, "art": art_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tv/select', methods=['POST'])
def select_tv_art():
    """Select an image to display on the TV"""
    if frame_manager is None or not frame_manager.is_connected():
        return jsonify({"error": "TV not connected"}), 400
    
    data = request.get_json()
    content_id = data.get('content_id')
    
    if not content_id:
        return jsonify({"error": "No content_id provided"}), 400
    
    success = frame_manager.select_image(content_id)
    
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to select image"}), 500


@app.route('/api/tv/delete', methods=['DELETE'])
def delete_tv_art():
    """Delete an image from the TV"""
    if frame_manager is None or not frame_manager.is_connected():
        return jsonify({"error": "TV not connected"}), 400
    
    data = request.get_json()
    content_id = data.get('content_id')
    
    if not content_id:
        return jsonify({"error": "No content_id provided"}), 400
    
    success = frame_manager.delete_image(content_id)
    
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to delete image"}), 500


@app.route('/api/tv/mattes')
def get_mattes():
    """Get available matte styles"""
    if frame_manager:
        return jsonify(frame_manager.get_matte_list())
    
    # Return defaults if not connected
    return jsonify([
        {"id": "none", "name": "No Matte"},
        {"id": "flexible", "name": "Flexible"},
        {"id": "modernthin", "name": "Modern Thin"},
        {"id": "modern", "name": "Modern"},
        {"id": "modernwide", "name": "Modern Wide"},
        {"id": "shadowbox", "name": "Shadow Box"},
        {"id": "classic", "name": "Classic"},
    ])


# Error handlers

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 50MB."}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Initialize frame manager if configured
    config = load_config()
    if config.get('tv_ip'):
        frame_manager = get_frame_manager(
            tv_ip=config['tv_ip'],
            port=config.get('tv_port', 8002),
            use_mock=config.get('use_mock', False)
        )
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080)),
        debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    )

