from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
import shutil
import tempfile
from .core import TelegraphPublisher
from .exceptions import TelePressError

app = FastAPI(
    title="TelePress API",
    description="REST API to convert text, markdown, images, and zips to Telegraph pages.",
    version="0.1.0"
)

# Request Models
class TextPublishRequest(BaseModel):
    content: str
    title: str
    token: Optional[str] = None

class PublishResponse(BaseModel):
    url: str
    status: str = "success"

def get_publisher(token: Optional[str] = None):
    try:
        return TelegraphPublisher(token=token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "ok", "service": "telepress"}

@app.post("/publish/text", response_model=PublishResponse)
async def publish_text(request: TextPublishRequest):
    """
    Publish raw Markdown/Text content directly.
    """
    try:
        # We need to save to a temp file because our core logic expects files
        # Alternatively, we could refactor core to accept string, but file is safer for large content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp:
            tmp.write(request.content)
            tmp_path = tmp.name
        
        publisher = get_publisher(request.token)
        url = publisher.publish(tmp_path, title=request.title)
        
        os.unlink(tmp_path)
        return PublishResponse(url=url)
        
    except TelePressError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publish/file", response_model=PublishResponse)
async def publish_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    token: Optional[str] = Form(None)
):
    """
    Upload a file (md, txt, zip, image) to be processed and published.
    """
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        publisher = get_publisher(token)
        
        # If no title provided, use filename from upload
        pub_title = title if title else file.filename
        
        url = publisher.publish(tmp_path, title=pub_title)
        
        os.unlink(tmp_path)
        return PublishResponse(url=url)
        
    except TelePressError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Clean up if exists
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))

def start_server(host="0.0.0.0", port=8000):
    """Start the TelePress API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


def main():
    """
    CLI entry point for telepress-server command.
    
    Usage:
        telepress-server
        telepress-server --host 127.0.0.1 --port 9000
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Start the TelePress REST API server."
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to listen on (default: 8000)"
    )
    
    args = parser.parse_args()
    
    print(f"Starting TelePress API server at http://{args.host}:{args.port}")
    print("API docs available at: http://localhost:{}/docs".format(args.port))
    
    start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
