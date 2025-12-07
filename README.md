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

```python
from telepress import publish, publish_text

url = publish("article.md")
url = publish_text("# Hello\n\nWorld!", title="Test")
```

CLI:
```bash
telepress article.md --title "My Post"
telepress photos.zip --title "Album"
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

- **External image hosting**: Upload to imgbb, imgur, or sm.ms (configurable)
- **Auto compression**: Images over 5MB automatically compressed
- **Batch upload**: Multi-threaded concurrent uploads with progress callback
- **Deduplication**: Same content won't be uploaded twice
- **Auto-pagination**: Large content split into multiple linked pages

## Limits

- Telegraph's direct image upload is unavailable, using external image hosts instead
- 5MB per image (auto-compressed if larger)

Supported: `.txt` `.md` `.markdown` `.rst` `.jpg` `.png` `.gif` `.webp` `.zip`

## Image Upload

Supported hosts: **imgbb**, **imgur**, **sm.ms**, **Cloudflare R2**, **Custom API**

### Configuration File

Create `~/.telepress.json`:

```json
{
    "image_host": {
        "type": "r2",
        "account_id": "your_account_id",
        "access_key_id": "your_access_key",
        "secret_access_key": "your_secret_key",
        "bucket": "your_bucket",
        "public_url": "https://pub-xxx.r2.dev"
    }
}
```

Or use environment variables:
```bash
export TELEPRESS_IMAGE_HOST_TYPE=r2
export TELEPRESS_IMAGE_HOST_ACCESS_KEY_ID=xxx
export TELEPRESS_IMAGE_HOST_SECRET_ACCESS_KEY=xxx
export TELEPRESS_IMAGE_HOST_BUCKET=my-bucket
export TELEPRESS_IMAGE_HOST_PUBLIC_URL=https://pub-xxx.r2.dev
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
