### Zero-to-live checklist **when you don’t yet have a repo**

| # | Command / action | What it does |
|---|------------------|--------------|
| **1** | ```bash\nmkdir yt-transcript-proxy && cd yt-transcript-proxy\n``` | Create a fresh directory. |
| **2** | Copy the **canvas file** (`main.py`) into `api/transcript.py`.  Make the folder structure:  ```bash\nmkdir -p api && cp /wherever/you/downloaded/main.py api/transcript.py\n``` |
| **3** | **requirements.txt** (caption-only, no Whisper yet)  ```txt\nfastapi\nuvicorn\nyoutube-transcript-api\n``` |
| **4** | **vercel.json**  ```json\n{\n  \"functions\": {\"api/**.py\": {\"runtime\": \"python3.11\"}},\n  \"routes\": [{\"src\": \"/v/(.*)\", \"dest\": \"api/transcript.py\"}]\n}\n``` |
| **5** | ```bash\ngit init\nprintf \".venv\\n__pycache__/\\ncache/\" > .gitignore\ngit add . && git commit -m \"Initial caption-only proxy\"\n``` | Make it a repo & first commit. |
| **6** | *Optional*: create an empty GitHub repo in the UI, then push:  ```bash\ngit remote add origin https://github.com/<user>/yt-transcript-proxy.git\ngit push -u origin main\n``` |
| **7** | **Install & test locally**  ```bash\npython -m venv .venv && source .venv/bin/activate\npip install -r requirements.txt\nuvicorn api.transcript:app --reload\n# open http://127.0.0.1:8000/v/DQOO5qy_rd8.html\n``` |
| **8** | **Vercel CLI**  ```bash\nnpm i -g vercel\nvercel login\nvercel --prod\n```  (CLI asks a few questions; accept defaults.) |
| **9** | Note the URL Vercel prints, e.g. `https://yt-transcript-proxy.vercel.app` | |
| **10** | **Test the live function**  ```bash\nopen https://yt-transcript-proxy.vercel.app/v/DQOO5qy_rd8.html\n```  Should show a plain-HTML transcript. |
| **11** | **Point your LLM** to that URL format:  `https://yt-transcript-proxy.vercel.app/v/{video_id}.html` | Now `web.run` can fetch it in a single call. |
| **12** | *(Later)* Add Whisper fallback or security if needed, push again—Vercel redeploys automatically. |

That’s it: no pre-existing repo required, and the whole flow stays under a dozen terminal commands.


main.py

# yt_transcript_proxy/main.py (token‑free test mode)
"""
FastAPI micro‑service that turns any public YouTube video into a static, bot‑friendly
HTML transcript page—**without any signed‑URL logic**.  Useful for local/staging
testing where security is not a concern.

Production tip: re‑add the HMAC guard or an allow‑list before going public.
"""

import os, pathlib, json, textwrap, tempfile, subprocess
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

CACHE_DIR = pathlib.Path("./cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="YouTube Transcript Proxy – Dev")

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def html_template(title: str, transcript: List[dict], video_id: str) -> str:
    """Return a bare‑bones HTML page with <pre> transcript."""
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
# Whisper fallback (only when captions disabled)
# ---------------------------------------------------------------------------

def whisper_fallback(video_id: str):
    """Download audio with yt‑dlp and run Whisper to generate transcript."""
    tmp_dir = tempfile.mkdtemp()
    audio_path = pathlib.Path(tmp_dir) / "audio.m4a"

    # 1. download audio only
    cmd_dl = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "m4a",
        "-o",
        str(audio_path),
        f"https://youtu.be/{video_id}",
    ]
    subprocess.run(cmd_dl, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. transcribe with whisper (base model for speed)
    cmd_whisper = [
        "whisper",
        str(audio_path),
        "--model",
        "base",
        "--output_format",
        "json",
        "--language",
        "en",
    ]
    result_json = subprocess.check_output(cmd_whisper)
    data = json.loads(result_json)
    return [{"start": seg["start"], "text": seg["text"]} for seg in data["segments"]]


# ---------------------------------------------------------------------------
# Main route – no token required
# ---------------------------------------------------------------------------

@app.get("/v/{video_id}.html", response_class=HTMLResponse)
async def serve_transcript(video_id: str):
    """Return cached transcript page or build it on first request."""
    cached_page = CACHE_DIR / f"{video_id}.html"
    if cached_page.exists():
        return FileResponse(str(cached_page), media_type="text/html")

    # Attempt official captions first
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
    except (TranscriptsDisabled, NoTranscriptFound):
        transcript = whisper_fallback(video_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    title = f"YouTube Video {video_id}"
    html = html_template(title, transcript, video_id)
    cached_page.write_text(html, encoding="utf-8")
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Local dev runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn, argparse

    parser = argparse.ArgumentParser(description="Run dev server")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=True)
