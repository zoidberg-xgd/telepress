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

- **去重**: 相同内容不会重复上传（缓存在 `~/.telepress_cache.json`）
- **自动重试**: 自动处理 Telegraph 限流
- **保留段落**: 纯文本的换行会变成段落

## 限制

- 单文件最大 100MB
- 最多 100 页（约 100 万字，或 5000 张图）
- 单张图片 5MB（Telegraph 限制）

支持: `.txt` `.md` `.markdown` `.rst` `.jpg` `.png` `.gif` `.webp` `.zip`

不支持: PDF、DOCX（先转成文本或图片）

## 项目结构

```
telepress/
├── core.py       # TelegraphPublisher 主类
├── auth.py       # token 管理
├── converter.py  # markdown 转 telegraph 节点
├── uploader.py   # 图片上传，带重试
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
