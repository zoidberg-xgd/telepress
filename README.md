# TelePress

TelePress is a Python tool and library for publishing local content to [Telegraph](https://telegra.ph). It supports Markdown, images, and Zip archives, handling pagination for long texts and large image sets automatically.

## Features

*   **Markdown**: Converts Markdown to Telegraph format. Handles header downgrading (H1->H3) automatically.
*   **Auto Pagination**:
    *   **Long Text**: Splits text exceeding ~40k characters into multiple linked pages.
    *   **Galleries**: Splits large Zip archives into pages of 100 images each.
    *   **Navigation**: Auto-generates "Previous/Next" links and page index.
*   **Images**: Direct Zip-to-Gallery support with natural sorting (1, 2, 10...).
*   **Interfaces**: CLI, Python SDK, and REST API.

## Installation

```bash
git clone <repository-url>
cd txt2gh
pip install -e .
```

For REST API support:
```bash
pip install fastapi uvicorn python-multipart
```

## Usage

### CLI

The main command is `telepress`.

**Publish Markdown**
```bash
telepress novel.md --title "My Novel"
```

**Publish Zip Gallery**
```bash
telepress comics.zip --title "Comic Vol. 1"
```

**Publish Image**
```bash
telepress image.jpg
```

### Python Library

```python
from telepress import TelegraphPublisher

publisher = TelegraphPublisher()

# Publish file (auto-detect type)
url = publisher.publish("article.md", title="Article Title")
print(url)
```

### REST API

Start server:
```bash
python3 -c "from telepress.server import start_server; start_server()"
```

Example request:
```bash
curl -X POST "http://localhost:8000/publish/file" \
  -F "file=@doc.zip" \
  -F "title=My Doc"
```

## Notes

*   **Token**: Created on first run and stored in `~/.telegraph_token`.

## Limits

| Type | Limit |
|------|-------|
| File size | Max 100MB |
| Text length | Max 100 pages (~4 million chars) |
| Gallery size | Max 5000 images |
| Images per page | 100 |
| Text per page | ~40KB |

## Supported Formats

*   **Text**: `.txt`, `.md`, `.markdown`, `.rst`, `.text`
*   **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`
*   **Archives**: `.zip`

> ⚠️ PDF, DOCX and other binary document formats are not supported. Convert to plain text or images first.

## License

MIT
