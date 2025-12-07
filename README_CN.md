# TelePress

[English](README.md)

把 Markdown、图片、Zip 压缩包发布到 [Telegraph](https://telegra.ph)。大文件会自动分页并生成导航链接。

## 安装

```bash
pip install telepress

# 需要 REST API
pip install telepress[api]

# 从源码安装
git clone https://github.com/zoidberg-xgd/telepress
cd telepress && pip install -e .
```

## 用法

```python
from telepress import publish, publish_text

url = publish("article.md")
url = publish_text("# 标题\n\n正文", title="测试")
```

命令行:
```bash
telepress article.md --title "我的文章"
telepress photos.zip --title "相册"
```

REST API:
```bash
telepress-server --port 8000

curl -X POST localhost:8000/publish/text \
  -H "Content-Type: application/json" \
  -d '{"content": "# 标题\n\n正文", "title": "测试"}'
```

## 原理

文本文件转成 Telegraph 格式（支持 Markdown）。纯文本的换行会保留为段落。内容太长的话按 ~10KB 切分成多页，自动加上下一页链接。

Zip 文件当图集处理。图片按文件名自然排序（1, 2, 10 而不是 1, 10, 2），每 100 张一页。

首次运行会自动创建 Telegraph 账号，token 存在 `~/.telegraph_token`。

## 特性

- **自动压缩**: 超过 5MB 的图片自动压缩（JPEG/WebP）
- **批量上传**: 多线程并发上传，带进度回调
- **断点续传**: 指数退避重试，可恢复失败的上传
- **去重**: 相同内容不会重复上传（缓存在 `~/.telepress_cache.json`）
- **保留段落**: 纯文本的换行会变成段落

## 限制

- 单张图片 5MB（超过自动压缩）
- 每页 100 张图（浏览器性能考虑）

支持: `.txt` `.md` `.markdown` `.rst` `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.tiff` `.zip`

不支持: PDF、DOCX（先转成文本或图片）

## 批量上传

```python
from telepress import ImageUploader

uploader = ImageUploader(max_workers=4)

# 带进度回调的上传
def on_progress(done, total, result):
    status = "成功" if result.success else result.error
    print(f"[{done}/{total}] {result.path}: {status}")

results = uploader.upload_batch(
    image_paths,
    auto_compress=True,
    progress_callback=on_progress
)
print(f"成功率: {results.success_rate:.0%}")

# 重试失败的上传
if results.failed > 0:
    retry_results = uploader.retry_failed(results)
```

## 图片压缩

```python
from telepress import compress_image_to_size, MAX_IMAGE_SIZE

# 压缩到 5MB 以下
compressed_path, was_compressed = compress_image_to_size(
    "large_photo.png",
    max_size=MAX_IMAGE_SIZE,  # 5MB
    prefer_webp=False  # 输出 JPEG（True 则输出 WebP）
)
```

支持格式: JPEG, PNG, WebP, BMP, TIFF（GIF 因动画复杂暂不支持压缩）

## 项目结构

```
telepress/
├── core.py       # TelegraphPublisher 主类
├── auth.py       # token 管理
├── converter.py  # markdown 转 telegraph 节点
├── uploader.py   # ImageUploader 批量上传 & 重试
├── utils.py      # 压缩、校验工具
├── server.py     # FastAPI 服务
└── cli.py        # 命令行
```

## 错误处理

```python
from telepress import publish, ValidationError, TelePressError

try:
    url = publish("file.md")
except ValidationError as e:
    # 输入有问题：格式不对、文件太大等
    print(e)
except TelePressError as e:
    # 其他错误：上传失败、认证失败等
    print(e)
```

## 集成到其他项目

```python
# Flask
@app.route('/publish', methods=['POST'])
def api_publish():
    url = publish_text(request.json['content'], title=request.json['title'])
    return {'url': url}

# 异步
async def async_publish(content, title):
    return await asyncio.to_thread(publish_text, content, title)
```

## 开发

```bash
git clone https://github.com/zoidberg-xgd/telepress
cd telepress && pip install -e .[dev]
pytest tests/ -v
```

## License

MIT
