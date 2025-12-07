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

CLI 配置向导:
```bash
telepress configure
```

发布内容:
```bash
telepress article.md --title "我的文章"

# 调整图片大小限制为 10MB
telepress article.md --image-size-limit 10

# 关闭自动压缩
telepress article.md --no-compress
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

首次运行会自动创建 Telegraph 账号，token 存在 `~/.telegraph_token`。

## 特性

- **外部图床**: 支持 imgbb、imgur、sm.ms、Cloudflare R2
- **自动压缩**: 超过 5MB 的图片自动压缩（可配置）
- **批量上传**: 多线程并发上传，带进度回调
- **去重**: 相同内容不会重复上传
- **自动分页**: 大内容自动分割成多个链接页面

## 限制

- Telegraph 直接上传不可用，改用外部图床
- 单张图片默认 5MB（超过自动压缩，可通过 `--image-size-limit` 调整或 `--no-compress` 关闭）

支持: `.txt` `.md` `.markdown` `.rst` `.jpg` `.png` `.gif` `.webp` `.zip`

## 图片上传

支持图床: **imgbb**, **imgur**, **sm.ms**, **S3/R2/OSS**, **自定义 API**

### 配置

使用配置向导:
```bash
telepress configure
```

或者手动创建 `~/.telepress.json`:

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

或者使用环境变量:
```bash
export TELEPRESS_IMAGE_HOST_TYPE=r2
export TELEPRESS_IMAGE_HOST_ACCESS_KEY_ID=xxx
export TELEPRESS_IMAGE_HOST_SECRET_ACCESS_KEY=xxx
export TELEPRESS_IMAGE_HOST_BUCKET=my-bucket
export TELEPRESS_IMAGE_HOST_PUBLIC_URL=https://pub-xxx.r2.dev
```

### 使用

```python
from telepress import ImageUploader

# 从配置文件加载
uploader = ImageUploader()  # 自动读取 ~/.telepress.json

# 或者显式指定
uploader = ImageUploader('imgbb', api_key='your_key')
uploader = ImageUploader('r2', access_key_id='...', secret_access_key='...', bucket='...', public_url='...')

# 自定义 API
uploader = ImageUploader('custom',
    upload_url='https://your-api.com/upload',
    headers={'Authorization': 'Bearer xxx'},
    response_url_path='data.url'  # 响应中 URL 的 JSON 路径
)

# 上传
url = uploader.upload('photo.jpg')

# 批量上传
results = uploader.upload_batch(image_paths)
print(f"成功率: {results.success_rate:.0%}")
```

## 图片压缩

```python
from telepress import compress_image_to_size, MAX_IMAGE_SIZE

# 压缩到 5MB 以下
compressed_path, was_compressed = compress_image_to_size(
    "large_photo.png",
    max_size=MAX_IMAGE_SIZE,
    prefer_webp=False  # True 输出 WebP
)
```

## 项目结构

```
telepress/
├── core.py       # TelegraphPublisher 主类
├── image_host.py # 外部图床 (imgbb, imgur, smms)
├── uploader.py   # ImageUploader 批量上传
├── utils.py      # 压缩工具
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
