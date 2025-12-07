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

Token is auto-created on first run and saved to `~/.telegraph_token`.

## Features

- **Deduplication**: Same content won't be uploaded twice (cache in `~/.telepress_cache.json`)
- **Auto-pagination**: Large content split into multiple linked pages
- **Paragraph preservation**: Plain text line breaks become paragraphs

## Limits

- **Note**: Telegraph's image upload API is currently unavailable. Images must be hosted externally and URLs pasted into articles.

Supported: `.txt` `.md` `.markdown` `.rst`

Not supported: Direct image upload, PDF, DOCX

## Project structure

```
telepress/
├── core.py       # TelegraphPublisher
├── auth.py       # token management
├── converter.py  # markdown to telegraph nodes
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
