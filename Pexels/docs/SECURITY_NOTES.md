# Security Notes

1. Store `GEMINI_API_KEY` and `PEXELS_API_KEY` only in `.env`; never commit real secrets.
2. Validate Gemini output with Pydantic before using it.
3. Use `subprocess.run([...])` argument lists for FFmpeg and never shell strings.
4. Limit external download size with `MAX_DOWNLOAD_MB`.
5. Do not log full user input text or API keys.
6. Review Pexels license terms before commercial use.
7. Confirm that generated videos comply with the source platform and music licensing rules.
8. Treat external URLs as untrusted.
9. Keep runtime storage folders out of git.
