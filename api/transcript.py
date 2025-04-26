# api/transcript.py (token-free test mode)
"""
FastAPI micro-service that turns any public YouTube video into a static, bot-friendly
HTML transcript page—without any signed-URL logic. Useful for local/staging
testing where security is not a concern.

Production tip: re-add the HMAC guard or an allow-list before going public.
"""

import os, pathlib, json, textwrap
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

CACHE_DIR = pathlib.Path("/tmp/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="YouTube Transcript Proxy – Dev")

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def html_template(title: str, transcript: List[dict], video_id: str) -> str:
    """Return a bare-bones HTML page with <pre> transcript."""
    body = "\n".join(f"{s['start']:06.1f}  {s['text']}" for s in transcript)
    return textwrap.dedent(
        f"""
        <!doctype html>
        <html lang=\"en\">  
        <meta charset=\"utf-8\">  
        <title>Transcript – {title}</title>  
        <link rel=\"canonical\" href=\"https://youtube.com/watch?v={video_id}\">  
        <style>body{{font:16px/1.5 system-ui}} pre{{white-space:pre-wrap}}</style>  
        <h1>{title}</h1>  
        <pre id=transcript>{body}</pre>  
        </html>  
        """
    )

# ---------------------------------------------------------------------------
# Main route – no token required
# ---------------------------------------------------------------------------

@app.get("/v/{video_id}.html", response_class=HTMLResponse)
async def serve_transcript(video_id: str):
    """Return cached transcript page or build it on first request."""
    print(f"[serve_transcript] video_id={video_id}")
    try:
        cached_page = CACHE_DIR / f"{video_id}.html"
        if cached_page.exists():
            try:
                return FileResponse(str(cached_page), media_type="text/html")
            except Exception as e:
                print(f"Error reading cache: {str(e)}")
                # Continue to fetch transcript if cache read fails
        
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        title = f"YouTube Video {video_id}"
        html = html_template(title, transcript, video_id)
        
        try:
            cached_page.write_text(html, encoding="utf-8")
        except Exception as e:
            print(f"Error writing to cache: {str(e)}")
            # Continue even if caching fails
            
        return HTMLResponse(html)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise HTTPException(status_code=404, detail=f"No transcript found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ---------------------------------------------------------------------------
# Local dev runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn, argparse

    parser = argparse.ArgumentParser(description="Run dev server")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("api.transcript:app", host="0.0.0.0", port=args.port, reload=True)
