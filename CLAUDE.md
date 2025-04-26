# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands
- Install dependencies: `pip install -r requirements.txt`
- Run development server: `uvicorn api.transcript:app --reload`
- Test locally: `open http://127.0.0.1:8000/v/{VIDEO_ID}.html`
- Deploy to Vercel: `vercel --prod`

## Code Style Guidelines
- Imports: Group standard library, then third-party, then local imports
- Formatting: Use docstrings for functions and modules; maintain section dividers (# -----)
- Types: Use type hints (e.g., `List[dict]`, `str`) for function parameters and return values
- Naming: Use snake_case for variables and functions; descriptive names
- Error handling: Use specific exception types; provide detailed error messages in HTTPException
- String formatting: Prefer f-strings; use textwrap.dedent for multi-line strings
- Comments: Add meaningful comments for complex logic
- Line length: Aim for ≤88 characters per line
- Indentation: 4 spaces