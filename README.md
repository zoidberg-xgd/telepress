# TelePress

[中文文档](https://github.com/zoidberg-xgd/telepress/blob/master/README_CN.md)

Publish Markdown, images and zip archives to [Telegraph](https://telegra.ph). Handles large files by auto-splitting into multiple linked pages.

## Install

```bash
pip install telepress

# with REST API
pip install telepress[api]

# from source
git clone https://github.com/zoidberg-xgd/telepress
cd telepress && pip install -e .
```

## Usage

CLI Configuration Wizard:
```bash
telepress configure
```

Check configuration:
```bash
telepress check
```

Publishing:
```bash
telepress article.md --title "My Post"
telepress photos.zip --title "Album"

# Set image size limit to 10MB
telepress article.md --image-size-limit 10

# Disable compression
telepress article.md --no-compress
```

REST API:
```bash
telepress-server --port 8000

curl -X POST localhost:8000/publish/text \
  -H "Content-Type: application/json" \
  -d '{"content": "# Title\n\nBody", "title": "Test"}'
```

## How it works

Text files are converted to Telegraph format (Markdown supported). Plain text files preserve line breaks as paragraphs. Large content is split at ~10KB boundaries into multiple pages with prev/next navigation.

Token is auto-created on first run and saved to `~/.telegraph_token`.

## Features

- **External image hosting**: Upload to imgbb, imgur, sm.ms, S3/R2/OSS, or Rclone (configurable)
- **Rclone Integration**: High-performance batch uploads using Rclone (requires [manual installation](https://rclone.org/downloads/))
- **Smart Text Optimization**: Automatically formats novels/articles with chapter detection and layout cleanup
- **Auto compression**: Images over 5MB automatically compressed (configurable)
- **Batch upload**: Multi-threaded concurrent uploads with progress callback
- **Deduplication**: Same content won't be uploaded twice
- **Auto-pagination**: Large content split into multiple linked pages

## Limits

- Telegraph's direct image upload is unavailable, using external image hosts instead
- 5MB per image (auto-compressed if larger, configurable via `--image-size-limit` or `--no-compress`)

Supported: `.txt` `.md` `.markdown` `.rst` `.jpg` `.png` `.gif` `.webp` `.zip`

## Image Upload

Supported hosts: **imgbb**, **imgur**, **sm.ms**, **S3/R2/OSS**, **Rclone**, **Custom API**

### Configuration

Use the wizard:
```bash
telepress configure
```

Install Rclone (if needed):
```bash
telepress install-rclone
```

Or create `~/.telepress.json` manually:

```json
{
    "image_host": {
        "type": "rclone",
        "remote_path": "myremote:bucket/path",
        "public_url": "https://pub.r2.dev/path",
        "rclone_flags": ["--transfers=32", "--checkers=32"]
    }
}
```

Or use S3/R2:

```json
{
    "image_host": {
        "type": "s3",
        "access_key_id": "your_access_key",
        "secret_access_key": "your_secret_key",
        "bucket": "your_bucket",
        "public_url": "https://your-bucket.s3.amazonaws.com",
        "endpoint_url": "https://s3.us-west-1.amazonaws.com",
        "region_name": "us-west-1"
    }
}
```

Or use environment variables:
```bash
export TELEPRESS_IMAGE_HOST_TYPE=rclone
export TELEPRESS_IMAGE_HOST_REMOTE_PATH=myremote:bucket/path
export TELEPRESS_IMAGE_HOST_PUBLIC_URL=https://pub.r2.dev/path
```

### Usage

```python
from telepress import ImageUploader

# Load from config file or env vars
uploader = ImageUploader()  # Auto-loads from ~/.telepress.json

# Or specify explicitly
uploader = ImageUploader('imgbb', api_key='your_key')
uploader = ImageUploader('r2', access_key_id='...', secret_access_key='...', bucket='...', public_url='...')

# Custom API endpoint
uploader = ImageUploader('custom',
    upload_url='https://your-api.com/upload',
    headers={'Authorization': 'Bearer xxx'},
    response_url_path='data.url'  # JSON path to URL in response
)

# Upload
url = uploader.upload('photo.jpg')

# Batch upload
results = uploader.upload_batch(image_paths)
print(f"Success: {results.success_rate:.0%}")
```

## Image Compression

```python
from telepress import compress_image_to_size, MAX_IMAGE_SIZE

# Compress to under 5MB
compressed_path, was_compressed = compress_image_to_size(
    "large_photo.png",
    max_size=MAX_IMAGE_SIZE,
    prefer_webp=False  # True for WebP output
)
```

## Project structure

```
telepress/
├── core.py       # TelegraphPublisher
├── image_host.py # External image hosting (imgbb, imgur, smms)
├── uploader.py   # ImageUploader with batch support
├── utils.py      # Compression utilities
├── server.py     # FastAPI service
└── cli.py        # Command line
```

## Error handling

```python
from telepress import publish, ValidationError, TelePressError

try:
    url = publish("file.md")
except ValidationError as e:
    # bad input: wrong format, too large, etc
    print(e)
except TelePressError as e:
    # other errors: upload failed, auth failed, etc
    print(e)
```

## Integration

```python
# Flask
@app.route('/publish', methods=['POST'])
def api_publish():
    url = publish_text(request.json['content'], title=request.json['title'])
    return {'url': url}

# async
async def async_publish(content, title):
    return await asyncio.to_thread(publish_text, content, title)
```

## Dev

```bash
git clone https://github.com/zoidberg-xgd/telepress
cd telepress && pip install -e .[dev]
pytest tests/ -v
```

## License

MIT
