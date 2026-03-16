"""
codex/integrations/fr_wiki.py - Forgotten Realms Wiki Client (Kiwix)
=====================================================================

Multi-source wiki client that queries locally hosted Kiwix ZIM files
for Forgotten Realms lore. Searches dedicated FR wiki first (when a
working copy exists), falls back to Wikipedia, and degrades gracefully
if kiwix-serve is down or no ZIMs are loaded.

Integration points:
  1. ``lore <topic>`` — Player command for on-demand wiki lookup
  2. NPC dialogue enrichment — Inject wiki context into Mimir prompts
  3. Module-load context — Seed ambient lore when loading an FR module

Gate: Only activates when ``setting_id`` matches a Forgotten Realms
sub-setting (Sword Coast, Icewind Dale, Chult, etc.).

WO-V55.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

# =========================================================================
# CONSTANTS
# =========================================================================

KIWIX_URL = "http://localhost:8080"
TIMEOUT = 5  # seconds — Pi 5 safety

FR_SETTINGS = frozenset({
    "forgotten_realms", "sword_coast", "icewind_dale", "chult",
    "barovia", "waterdeep", "baldurs_gate", "neverwinter",
    "underdark", "calimshan", "amn", "cormyr",
})


# =========================================================================
# KIWIX SOURCE
# =========================================================================

@dataclass
class KiwixSource:
    """Describes a single ZIM file loaded in kiwix-serve."""
    name: str
    book_id: str
    description: str
    priority: int = 10


# Priority-ordered ZIM sources. Client tries each in order.
# Operators can add/remove sources for their deployment.
# NOTE: book_id must match the kiwix-serve URL prefix (includes date suffix).
# _probe_sources() auto-detects loaded ZIMs by <name> tag in OPDS catalog.
DEFAULT_SOURCES = [
    KiwixSource(
        name="forgotten_realms",
        book_id="forgotten_realms_2026-03",
        description="Forgotten Realms Wiki (scraped from Fandom)",
        priority=1,
    ),
    KiwixSource(
        name="wikipedia",
        book_id="wikipedia_en_all_maxi_2025-08",
        description="Wikipedia (English, full)",
        priority=2,
    ),
]


# =========================================================================
# HTML HELPERS
# =========================================================================

class _ParagraphExtractor(HTMLParser):
    """Extract text from <p> tags only."""

    def __init__(self):
        super().__init__()
        self._in_p = False
        self._depth = 0
        self.paragraphs: List[str] = []
        self._buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self._in_p = True
            self._depth += 1
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "p" and self._in_p:
            self._depth -= 1
            if self._depth <= 0:
                self._in_p = False
                self._depth = 0
                text = "".join(self._buf).strip()
                if text:
                    self.paragraphs.append(text)

    def handle_data(self, data):
        if self._in_p:
            self._buf.append(data)


class _SearchResultExtractor(HTMLParser):
    """Extract search result links from kiwix search HTML.

    Kiwix-serve search results link to /{book_id}/{Article_Name}.
    We filter for links matching the expected book_id prefix and
    skip skin/catalog/random/home URLs.
    """

    # Paths that are never article links
    _SKIP_PREFIXES = ("/skin/", "/catalog/", "/search", "/random")

    def __init__(self, book_id: str = ""):
        super().__init__()
        self.results: List[Tuple[str, str]] = []  # (title, path)
        self._in_link = False
        self._current_href = ""
        self._current_title = ""
        self._book_prefix = f"/{book_id}/" if book_id else ""

    def _is_article_link(self, href: str) -> bool:
        """Check if an href points to a ZIM article."""
        if not href or href == "/":
            return False
        for skip in self._SKIP_PREFIXES:
            if href.startswith(skip):
                return False
        # If we know the book_id, match its prefix and require content after it
        if self._book_prefix:
            if href.startswith(self._book_prefix) and len(href) > len(self._book_prefix):
                return True
            return False
        # Fallback: accept /A/ style (legacy) or any deep path
        return "/A/" in href or href.count("/") >= 2

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attr_dict = dict(attrs)
            href = attr_dict.get("href", "")
            if self._is_article_link(href):
                self._in_link = True
                self._current_href = href.lstrip("/")
                self._current_title = ""

    def handle_data(self, data):
        if self._in_link:
            self._current_title += data

    def handle_endtag(self, tag):
        if tag == "a" and self._in_link:
            self._in_link = False
            title = self._current_title.strip()
            if title and self._current_href:
                self.results.append((title, self._current_href))


# =========================================================================
# WIKI CLIENT
# =========================================================================

class FRWikiClient:
    """Multi-source Kiwix wiki client with caching and graceful degradation."""

    def __init__(self, base_url: str = KIWIX_URL,
                 sources: Optional[List[KiwixSource]] = None):
        self._base = base_url.rstrip("/")
        self._sources = sorted(sources or list(DEFAULT_SOURCES),
                                key=lambda s: s.priority)
        self._available: Optional[List[KiwixSource]] = None
        self._cache: Dict[str, str] = {}
        self._max_cache = 50

    def _probe_sources(self) -> List[KiwixSource]:
        """Return only sources whose ZIM is loaded in kiwix-serve.

        Auto-detects the actual book_id (with date suffix) from the
        catalog entry's ``<link type="text/html" href="..."/>`` so we
        don't need to hardcode date suffixes.
        """
        if self._available is not None:
            return self._available
        try:
            resp = requests.get(
                f"{self._base}/catalog/search", timeout=TIMEOUT)
            catalog = resp.text
            loaded_names = set(re.findall(r'<name>([^<]+)</name>', catalog))

            # Map name → actual book_id from catalog link hrefs
            # Pattern: <name>X</name> ... <link type="text/html" href="/X_YYYY-MM" />
            name_to_bookid: Dict[str, str] = {}
            for name in loaded_names:
                # Find the HTML link href after this name's entry
                pattern = (
                    rf'<name>{re.escape(name)}</name>'
                    r'.*?<link\s+type="text/html"\s+href="/([^"]+)"'
                )
                m = re.search(pattern, catalog, re.DOTALL)
                if m:
                    name_to_bookid[name] = m.group(1)
                else:
                    name_to_bookid[name] = name

            available = []
            for s in self._sources:
                if s.name in loaded_names:
                    # Update book_id to match what kiwix-serve actually has
                    s.book_id = name_to_bookid.get(s.name, s.book_id)
                    available.append(s)
            self._available = available
        except Exception:
            self._available = []
        return self._available

    def search(self, query: str, k: int = 5
               ) -> List[Tuple[str, str, str]]:
        """Search all available sources for a topic.

        Returns list of (title, article_path, source_name) tuples.
        First source with results wins.
        """
        for source in self._probe_sources():
            try:
                url = (
                    f"{self._base}/search"
                    f"?content={quote(source.book_id)}"
                    f"&pattern={quote(query)}"
                )
                resp = requests.get(url, timeout=TIMEOUT)
                if resp.status_code != 200:
                    continue

                parser = _SearchResultExtractor(book_id=source.book_id)
                parser.feed(resp.text)

                if parser.results:
                    results = [
                        (title, path, source.name)
                        for title, path in parser.results[:k]
                    ]
                    return results
            except Exception:
                continue
        return []

    def fetch_article(self, path: str) -> str:
        """Fetch and extract plaintext from a kiwix article.

        Args:
            path: Article path from search results (e.g. "wikipedia.../A/Waterdeep").

        Returns:
            Extracted paragraph text.
        """
        if path in self._cache:
            return self._cache[path]

        try:
            url = f"{self._base}/{path}"
            resp = requests.get(url, timeout=TIMEOUT)
            if resp.status_code != 200:
                return ""

            parser = _ParagraphExtractor()
            parser.feed(resp.text)
            text = "\n\n".join(parser.paragraphs)

            # LRU eviction
            if len(self._cache) >= self._max_cache:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[path] = text
            return text
        except Exception:
            return ""

    def get_lore_summary(self, topic: str, max_chars: int = 600
                         ) -> Optional[str]:
        """Search for a topic and return a truncated summary.

        Returns None if no results or kiwix unavailable.
        """
        try:
            results = self.search(topic, k=1)
            if not results:
                return None
            _title, path, _source = results[0]
            text = self.fetch_article(path)
            if not text:
                return None
            if len(text) > max_chars:
                # Truncate at last sentence boundary within limit
                truncated = text[:max_chars]
                last_period = truncated.rfind(".")
                if last_period > max_chars // 2:
                    truncated = truncated[:last_period + 1]
                return truncated
            return text
        except Exception:
            return None


# =========================================================================
# HELPERS
# =========================================================================

def is_fr_context(setting_id: str) -> bool:
    """Check if a setting_id belongs to the Forgotten Realms."""
    return setting_id.lower() in FR_SETTINGS if setting_id else False


# =========================================================================
# SINGLETON
# =========================================================================

_client: Optional[FRWikiClient] = None


def get_fr_wiki() -> FRWikiClient:
    """Return the global FRWikiClient singleton."""
    global _client
    if _client is None:
        _client = FRWikiClient()
    return _client
