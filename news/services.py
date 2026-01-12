from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import socket
import urllib.request

import feedparser
from django.conf import settings
from django.core.cache import cache


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    link: str
    published_at: datetime | None


def _parse_datetime(entry: dict[str, Any]) -> datetime | None:
    # feedparser provides either `published_parsed` or `updated_parsed` as time.struct_time
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct_time:
        return None
    return datetime(*struct_time[:6], tzinfo=timezone.utc)


def _fetch_url_bytes(url: str, timeout_seconds: int = 8) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "uzwire/1.0 (+https://uzwire.uz)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        return resp.read()


def fetch_news(limit: int = 40, cache_seconds: int = 300) -> list[NewsItem]:
    cache_key = f"news:v1:limit={limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    items: list[NewsItem] = []

    for src in getattr(settings, "NEWS_FEEDS", []):
        name = src.get("name")
        url = src.get("url")
        if not name or not url:
            continue

        try:
            # Ensure we never hang on slow sources.
            socket.setdefaulttimeout(8)
            raw = _fetch_url_bytes(url, timeout_seconds=8)
            parsed = feedparser.parse(raw)
        except Exception:
            continue
        for entry in parsed.entries[:200]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue

            items.append(
                NewsItem(
                    source=str(name),
                    title=title,
                    link=link,
                    published_at=_parse_datetime(entry),
                )
            )

    def sort_key(item: NewsItem):
        # Put undated items last
        return item.published_at or datetime.min.replace(tzinfo=timezone.utc)

    items.sort(key=sort_key, reverse=True)
    items = items[:limit]

    cache.set(cache_key, items, timeout=cache_seconds)
    return items
