# Samsung Frame Art Manager

A beautiful web interface to manage artwork on your Samsung The Frame TV. Upload your photos, have them automatically formatted for the display, and send them directly to your TV.

![Frame Art Manager](https://img.shields.io/badge/Samsung-The%20Frame-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![Flask](https://img.shields.io/badge/Flask-3.0-orange)

## Features

✨ **Beautiful Gallery Interface** - Modern, responsive web UI to manage your art collection

📤 **Easy Upload** - Drag and drop multiple images at once

🖼️ **Smart Image Processing** - Automatically resize and format images for optimal display on The Frame (4K resolution)

📺 **Direct TV Control** - Send images to your Samsung Frame TV with one click

🎨 **Matte Selection** - Choose from various matte/frame styles for your artwork

⚙️ **Flexible Settings** - Configure fit modes, background colors, and more

## Screenshots

The interface features:
- A gallery view showing all your uploaded artwork
- Image upload with drag-and-drop support
- Settings page for TV connection and image processing
- Send-to-TV modal with matte style selection

## Requirements

- Python 3.8 or higher
- Samsung The Frame TV (2020-2021 models work best)
- Both devices on the same local network

## Installation

### 1. Clone or Download the Project

```bash
cd "The Frame"
```

### 2. Create a Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Samsung TV WebSocket API

This library is required for TV communication:

```bash
pip install "git+https://github.com/xchwarze/samsung-tv-ws-api.git#egg=samsungtvws[async,encrypted]"
```

## Usage

### Start the Application

```bash
python app.py
```

The web interface will be available at: **http://localhost:5000**

### First-Time Setup

1. Open the web interface in your browser
2. Go to **Settings**
3. Enter your Samsung Frame TV's IP address
4. Click **Connect**
5. On your TV, accept the connection request when prompted (first time only)

### Finding Your TV's IP Address

1. On your Samsung TV, go to **Settings**
2. Navigate to **General → Network → Network Status**
3. Select **IP Settings** to see the IP address

💡 **Tip:** Set a static IP for your TV in your router settings for consistent connectivity.

### Uploading Images

1. Go to the **Gallery** page
2. Drag and drop images onto the upload zone, or click to select files
3. Images are automatically processed for optimal display

### Sending to TV

1. Hover over an image in the gallery
2. Click **Send** button
3. Select your preferred matte style
4. Click **Send to TV**

## Configuration Options

### Image Processing

| Option | Description |
|--------|-------------|
| **Contain** | Fit entire image within screen, may add letterbox/pillarbox |
| **Cover** | Fill screen completely, may crop edges |
| **Smart** | Automatically choose best method based on aspect ratio |
| **Stretch** | Fill screen exactly (may distort image) |

### Matte Styles

Choose from various frame styles:
- None
- Flexible
- Modern Thin
- Modern
- Modern Wide
- Shadow Box
- Classic

### Background Options

- **Solid Color** - Choose any RGB color for letterbox areas
- **Blurred Background** - Use a blurred version of the image itself

## Technical Details

### Supported Image Formats

- JPEG/JPG
- PNG
- WebP
- BMP
- TIFF

### Image Processing

Images are automatically:
- Resized to 4K resolution (3840×2160)
- Converted to RGB color space
- EXIF orientation corrected
- Saved as high-quality JPEG (95% quality)

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload an image |
| `/api/images` | GET | List all images |
| `/api/images/<filename>` | GET | Get image info |
| `/api/images/<filename>/delete` | DELETE | Delete an image |
| `/api/tv/connect` | POST | Connect to TV |
| `/api/tv/status` | GET | Get TV status |
| `/api/tv/upload` | POST | Upload image to TV |
| `/api/tv/select` | POST | Select image on TV |
| `/api/config` | GET/POST | Get/update configuration |

## Troubleshooting

### "samsungtvws not installed"

Install the Samsung TV library:
```bash
pip install "git+https://github.com/xchwarze/samsung-tv-ws-api.git#egg=samsungtvws[async,encrypted]"
```

### Can't Connect to TV

1. Verify TV and computer are on the same network
2. Check the IP address is correct
3. Ensure the TV is powered on
4. Try enabling "Developer Mode" on the TV (Settings → Support → Developer Mode)

### Connection Timeout

The first connection requires approval on the TV. Look for a popup on your TV screen asking to allow the connection.

### Images Not Displaying Correctly

- Try different fit modes (contain vs cover)
- Ensure images are in a supported format
- Check that images aren't corrupted

## Compatibility

### Tested Models
- Samsung The Frame 2020 (LS03T)
- Samsung The Frame 2021 (LS03A)

### Known Limitations
- 2022+ models may have limited API support due to Samsung removing Art Mode components from the API
- Some features may not work with all TV firmware versions

## Credits

This project builds upon:
- [Samsung Frame Art Mode++](https://github.com/ow/samsung-frame-art) - Original Python script for Frame TV control
- [samsung-tv-ws-api](https://github.com/xchwarze/samsung-tv-ws-api) - Samsung TV WebSocket API library

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

