# TelePress

[中文文档](README_CN.md)

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

Zip files are treated as image galleries. Images are sorted naturally (1, 2, 10 not 1, 10, 2) and paginated at 100 per page.

Token is auto-created on first run and saved to `~/.telegraph_token`.

## Features

- **Auto compression**: Images over 5MB are automatically compressed (JPEG/WebP)
- **Batch upload**: Multi-threaded concurrent uploads with progress callback
- **Retry & resume**: Exponential backoff retry, resume failed uploads
- **Deduplication**: Same content won't be uploaded twice (cache in `~/.telepress_cache.json`)
- **Paragraph preservation**: Plain text line breaks become paragraphs

## Limits

- 5MB per image (auto-compressed if larger)
- 100 images per page (for browser performance)

Supported: `.txt` `.md` `.markdown` `.rst` `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.tiff` `.zip`

Not supported: PDF, DOCX (convert first)

## Batch Upload

```python
from telepress import ImageUploader

uploader = ImageUploader(max_workers=4)

# Upload with progress
def on_progress(done, total, result):
    status = "OK" if result.success else result.error
    print(f"[{done}/{total}] {result.path}: {status}")

results = uploader.upload_batch(
    image_paths,
    auto_compress=True,
    progress_callback=on_progress
)
print(f"Success: {results.success_rate:.0%}")

# Retry failed uploads
if results.failed > 0:
    retry_results = uploader.retry_failed(results)
```

## Image Compression

```python
from telepress import compress_image_to_size, MAX_IMAGE_SIZE

# Compress to under 5MB
compressed_path, was_compressed = compress_image_to_size(
    "large_photo.png",
    max_size=MAX_IMAGE_SIZE,  # 5MB
    prefer_webp=False  # output JPEG (or True for WebP)
)
```

Supported formats: JPEG, PNG, WebP, BMP, TIFF (GIF excluded due to animation)

## Project structure

```
telepress/
├── core.py       # TelegraphPublisher
├── auth.py       # token management
├── converter.py  # markdown to telegraph nodes
├── uploader.py   # ImageUploader with batch & retry
├── utils.py      # compression, validation
├── server.py     # FastAPI service
└── cli.py        # command line
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
