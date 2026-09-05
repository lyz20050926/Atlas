from __future__ import annotations

import sys

import httpx

from src.config import get_settings
from src.tools.google_books import GoogleBooksClient


def main() -> int:
    settings = get_settings()
    if not settings.google_books_api_key:
        print("[FAIL] GOOGLE_BOOKS_API_KEY is empty in .env.")
        print("Create a restricted Google Books API key, add it to .env, then rerun this check.")
        return 1

    client = GoogleBooksClient(
        settings.google_books_api_key,
        settings.http_timeout_seconds,
        settings.http_max_retries,
    )
    try:
        checks = (
            ("English", "embodied cognition", "en"),
            ("Chinese", "具身认知", "zh"),
        )
        for label, query, language in checks:
            books = client.search(query, max_results=3, language=language)
            print(f"[OK] {label}: Google Books returned {len(books)} normalized records.")
    except httpx.HTTPStatusError as exc:
        message = ""
        try:
            message = (exc.response.json().get("error") or {}).get("message") or ""
        except ValueError:
            pass
        print(f"[FAIL] Google Books returned HTTP {exc.response.status_code}: {message}")
        return 1
    except httpx.HTTPError as exc:
        print(f"[FAIL] Google Books connection failed: {type(exc).__name__}")
        return 1
    finally:
        client.close()

    print("Google Books API is ready for live English and Chinese catalogue searches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
