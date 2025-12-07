# TelePress

TelePress 是一个用于将本地内容发布到 [Telegraph](https://telegra.ph) 的 Python 工具和库。它支持 Markdown、图片和 Zip 压缩包，主要解决长文分卷和图集分页的问题。

## 功能

*   **Markdown 支持**: 将 Markdown 转换为 Telegraph 格式。自动处理 H1/H2 标题降级。
*   **自动分卷**: 
    *   **长文本**: 超过一定长度（约 4万字）的文本会自动拆分成多页。
    *   **图集**: 包含大量图片的 Zip 包会自动拆分成多页（每页 100 张）。
    *   **导航**: 自动生成“上一页/下一页”和页码索引。
*   **图片处理**: 支持将 Zip 包直接转为图集，按文件名自然排序（1, 2, 10...）。
*   **接口**: 提供 CLI 命令行工具、Python 库和 REST API。

## 安装

```bash
git clone <repository-url>
cd txt2gh
pip install -e .
```

如果需要运行 REST API：
```bash
pip install fastapi uvicorn python-multipart
```

## 安装方式

```bash
# 基础安装
pip install telepress

# 包含 REST API 支持
pip install telepress[api]

# 开发环境
pip install telepress[dev]
```

## 使用

### 一行代码发布

```python
from telepress import publish, publish_text

# 发布文件
url = publish("article.md", title="我的文章")

# 直接发布文本内容
url = publish_text("# 标题\n\n这是内容", title="测试")
```

### Python SDK

```python
from telepress import TelegraphPublisher

publisher = TelegraphPublisher()

# 发布文件（自动识别类型）
url = publisher.publish("article.md", title="文章标题")

# 直接发布文本
url = publisher.publish_text("# Hello\n\nWorld!", title="测试")

# 发布图集
url = publisher.publish("photos.zip", title="我的相册")
```

### 命令行 (CLI)

```bash
# 发布 Markdown
telepress novel.md --title "我的小说"

# 发布 Zip 图集
telepress comics.zip --title "漫画第一卷"

# 发布单张图片
telepress image.jpg
```

### REST API

启动服务：
```bash
# 方式 1: 命令行
telepress-server --host 0.0.0.0 --port 8000

# 方式 2: Python
python -c "from telepress.server import start_server; start_server()"
```

调用示例：
```bash
# 发布文件
curl -X POST "http://localhost:8000/publish/file" \
  -F "file=@doc.zip" \
  -F "title=文档"

# 发布文本
curl -X POST "http://localhost:8000/publish/text" \
  -H "Content-Type: application/json" \
  -d '{"content": "# 标题\n\n内容", "title": "测试"}'
```

**API 文档**: 启动后访问 `http://localhost:8000/docs`

### 集成到其他项目

```python
# Flask 示例
from flask import Flask, request
from telepress import publish_text, TelePressError

app = Flask(__name__)

@app.route('/publish', methods=['POST'])
def api_publish():
    try:
        data = request.json
        url = publish_text(data['content'], title=data['title'])
        return {'url': url}
    except TelePressError as e:
        return {'error': str(e)}, 400
```

```python
# Django 示例
from django.http import JsonResponse
from telepress import publish_text

def publish_view(request):
    content = request.POST.get('content')
    title = request.POST.get('title')
    url = publish_text(content, title=title)
    return JsonResponse({'url': url})
```

## 说明

*   **Token**: 首次运行会自动注册账号，Token 保存在 `~/.telegraph_token`。

## 限制

| 类型 | 限制 |
|------|------|
| 文件大小 | 最大 100MB |
| 文本长度 | 最多 100 页（约 400 万字） |
| 图集大小 | 最多 5000 张图片 |
| 每页图片 | 100 张 |
| 每页文字 | 约 40KB |

## 支持格式

*   **文本**: `.txt`, `.md`, `.markdown`, `.rst`, `.text`
*   **图片**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`
*   **压缩包**: `.zip`

> ⚠️ 不支持 PDF、DOCX 等二进制文档格式。如需转换，请先转为纯文本或图片。

## License

MIT
