#!/usr/bin/env python3
"""Forgotten Realms Wiki → ZIM Scraper

Two-phase pipeline:
  Phase 1: Scrape articles from Fandom MediaWiki API → SQLite (resumable)
  Phase 2: Pack SQLite → ZIM file using libzim

Usage:
  python scripts/scrape_fr_wiki.py scrape    # Phase 1
  python scripts/scrape_fr_wiki.py build     # Phase 2
  python scripts/scrape_fr_wiki.py all       # Both phases
  python scripts/scrape_fr_wiki.py status    # Check progress

Requires: requests, beautifulsoup4, lxml, libzim (all installed via zimscraperlib)
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fr_scraper")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIKI_API = "https://forgottenrealms.fandom.com/api.php"
WIKI_BASE = "https://forgottenrealms.fandom.com/wiki/"
USER_AGENT = "CodexFRScraper/1.0 (Pi5; offline-wiki-mirror)"

SCRIPT_DIR = Path(__file__).resolve().parent
ARTICLE_LIST = SCRIPT_DIR / "fr_wiki_articles.txt"
_KNOWLEDGE_POOL = Path(os.environ.get('KNOWLEDGE_POOL', str(Path(__file__).resolve().parent.parent / 'knowledge_pool')))
DB_PATH = _KNOWLEDGE_POOL / "fr_wiki_scrape.db"
ZIM_OUTPUT = _KNOWLEDGE_POOL / "forgotten_realms_2026-03.zim"

# Concurrency: conservative to avoid Fandom rate limits
MAX_WORKERS = 4
REQUEST_DELAY = 0.15  # seconds between requests per worker
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

def _update_workers(n: int):
    global MAX_WORKERS
    MAX_WORKERS = n

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            title TEXT PRIMARY KEY,
            html TEXT,
            clean_html TEXT,
            text_length INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error TEXT,
            scraped_at REAL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON articles(status)
    """)
    conn.commit()
    return conn


def seed_articles(conn: sqlite3.Connection, article_file: Path):
    """Load article titles into DB if not already present."""
    existing = set(
        r[0] for r in conn.execute("SELECT title FROM articles").fetchall()
    )
    titles = []
    with open(article_file, "r", encoding="utf-8") as f:
        for line in f:
            title = line.strip()
            if title and title not in existing:
                titles.append(title)

    if titles:
        conn.executemany(
            "INSERT OR IGNORE INTO articles (title) VALUES (?)",
            [(t,) for t in titles],
        )
        conn.commit()
        log.info(f"Seeded {len(titles)} new articles (total: {len(existing) + len(titles)})")
    else:
        log.info(f"All {len(existing)} articles already in DB")


# ---------------------------------------------------------------------------
# HTML Cleaning
# ---------------------------------------------------------------------------

def clean_html(raw_html: str, title: str) -> str:
    """Strip Fandom cruft, keep article content."""
    soup = BeautifulSoup(raw_html, "lxml")

    # Remove unwanted elements
    for tag in soup.find_all(["script", "style", "noscript", "link"]):
        tag.decompose()

    # Remove Fandom-specific elements
    for selector in [
        ".portable-infobox",   # Keep infoboxes actually — they have useful data
        ".navbox",             # Navigation boxes at bottom
        ".reference",          # [citation needed] etc
        ".mw-editsection",     # Edit section links
        ".toc",                # Table of contents (we disabled it but just in case)
        ".noprint",            # Print-hidden elements
        "#scroll-banner",      # Fandom scroll banner
        ".page-header",        # Page header
        ".notifications-placeholder",
        ".fandom-community-header",
        ".global-navigation",
        ".WikiaBarWrapper",
        ".wikia-bar",
    ]:
        for el in soup.select(selector):
            el.decompose()

    # Remove external Fandom links but keep text
    for a in soup.find_all("a"):
        href = a.get("href", "")
        parsed = urlparse(href) if href else None
        host = parsed.hostname if parsed else None
        # Treat root-relative links as belonging to the main wiki host
        if not host and href.startswith("/"):
            host = "forgottenrealms.fandom.com"
        is_fandom = host and (
            host == "fandom.com" or host.endswith(".fandom.com")
            or host == "wikia.com" or host.endswith(".wikia.com")
            or host == "wikia.nocookie.net" or host.endswith(".wikia.nocookie.net")
        )
        if is_fandom:
            # Convert to internal ZIM link if it's a wiki article link
            if "/wiki/" in href:
                article_name = href.split("/wiki/")[-1].split("?")[0].split("#")[0]
                article_name = unquote(article_name)
                a["href"] = f"../{quote(article_name, safe='')}"
            else:
                # Remove link but keep text
                a.unwrap()

    # Remove image elements (they'd need separate handling)
    for img in soup.find_all("img"):
        img.decompose()
    for figure in soup.find_all("figure"):
        figure.decompose()

    # Wrap in minimal HTML
    clean = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{title} - Forgotten Realms Wiki</title>
<style>
body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 1em; }}
h1,h2,h3 {{ color: #2c3e50; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
td,th {{ border: 1px solid #ccc; padding: 4px 8px; }}
a {{ color: #2980b9; }}
</style>
</head>
<body>
<h1>{title}</h1>
{str(soup)}
</body>
</html>"""
    return clean


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def fetch_article(title: str, session: requests.Session) -> tuple[str, str | None, str | None]:
    """Fetch and clean a single article. Returns (title, clean_html, error)."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(
                WIKI_API,
                params={
                    "action": "parse",
                    "page": title,
                    "prop": "text",
                    "disabletoc": "true",
                    "disableeditsection": "true",
                    "format": "json",
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                code = data["error"].get("code", "unknown")
                if code == "missingtitle":
                    return (title, None, "missing")
                return (title, None, data["error"].get("info", code))

            raw_html = data["parse"]["text"]["*"]

            # Skip if it's a redirect/disambiguation page with no real content
            if len(raw_html) < 100:
                return (title, None, "too_short")

            cleaned = clean_html(raw_html, title)
            time.sleep(REQUEST_DELAY)
            return (title, cleaned, None)

        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return (title, None, "timeout")
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return (title, None, str(e)[:200])
        except Exception as e:
            return (title, None, f"parse_error: {str(e)[:200]}")

    return (title, None, "max_retries")


def scrape_phase(db_path: Path, article_file: Path):
    """Phase 1: Scrape articles from Fandom API into SQLite."""
    conn = init_db(db_path)
    seed_articles(conn, article_file)

    # Get pending articles
    pending = [
        r[0] for r in conn.execute(
            "SELECT title FROM articles WHERE status = 'pending' ORDER BY title"
        ).fetchall()
    ]

    if not pending:
        log.info("No pending articles to scrape!")
        show_status(db_path)
        return

    log.info(f"Scraping {len(pending)} articles with {MAX_WORKERS} workers...")

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    done = 0
    errors = 0
    start = time.time()
    batch_size = 50  # Commit every N articles

    batch_results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(fetch_article, title, session): title
            for title in pending
        }

        for future in as_completed(futures):
            title, html, error = future.result()
            done += 1

            if error:
                errors += 1
                batch_results.append((title, None, None, 0, "error", error))
            else:
                text_len = len(html) if html else 0
                batch_results.append((title, html, html, text_len, "done", None))

            # Commit in batches
            if len(batch_results) >= batch_size:
                _commit_batch(conn, batch_results)
                batch_results.clear()

                elapsed = time.time() - start
                rate = done / elapsed if elapsed > 0 else 0
                eta = (len(pending) - done) / rate if rate > 0 else 0
                log.info(
                    f"Progress: {done}/{len(pending)} "
                    f"({100*done/len(pending):.1f}%) | "
                    f"Errors: {errors} | "
                    f"Rate: {rate:.1f}/s | "
                    f"ETA: {eta/60:.0f}m"
                )

    # Final commit
    if batch_results:
        _commit_batch(conn, batch_results)

    elapsed = time.time() - start
    log.info(f"Scrape complete: {done} articles in {elapsed/60:.1f}m ({errors} errors)")
    conn.close()
    show_status(db_path)


def _commit_batch(conn: sqlite3.Connection, results: list):
    for title, html, clean, text_len, status, error in results:
        conn.execute(
            """UPDATE articles
               SET html=?, clean_html=?, text_length=?, status=?, error=?, scraped_at=?
               WHERE title=?""",
            (html, clean, text_len, status, error, time.time(), title),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# ZIM Building
# ---------------------------------------------------------------------------

def build_phase(db_path: Path, zim_path: Path):
    """Phase 2: Pack SQLite articles into ZIM file."""
    from libzim.writer import Creator, Item, StringProvider, Hint

    conn = sqlite3.connect(str(db_path))
    articles = conn.execute(
        "SELECT title, clean_html, text_length FROM articles WHERE status='done' AND clean_html IS NOT NULL ORDER BY title"
    ).fetchall()
    conn.close()

    if not articles:
        log.error("No articles to build! Run 'scrape' first.")
        return

    log.info(f"Building ZIM from {len(articles)} articles → {zim_path}")

    class WikiItem(Item):
        def __init__(self, path, title, content):
            super().__init__()
            self._path = path
            self._title = title
            self._content = content

        def get_path(self):
            return self._path

        def get_title(self):
            return self._title

        def get_mimetype(self):
            return "text/html"

        def get_contentprovider(self):
            return StringProvider(self._content)

        def get_hints(self):
            return {Hint.FRONT_ARTICLE: True}

    # Build main page with alphabetical index
    letters = {}
    for title, _, _ in articles:
        first = title[0].upper() if title else "?"
        if not first.isalpha():
            first = "#"
        letters.setdefault(first, []).append(title)

    index_links = []
    for letter in sorted(letters.keys()):
        count = len(letters[letter])
        index_links.append(f'<a href="../index_{letter}">{letter}</a> ({count})')

    main_page_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Forgotten Realms Wiki</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 1em; background: #1a1a2e; color: #e0e0e0; }}
h1 {{ color: #c9a959; text-align: center; }}
h2 {{ color: #8b7355; }}
.index {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 2em 0; }}
.index a {{ padding: 8px 16px; background: #2d2d44; color: #c9a959; text-decoration: none; border-radius: 4px; }}
.index a:hover {{ background: #3d3d55; }}
p {{ text-align: center; color: #888; }}
</style>
</head>
<body>
<h1>Forgotten Realms Wiki</h1>
<p>Offline mirror — {len(articles)} articles</p>
<div class="index">
{''.join(index_links)}
</div>
<p>Scraped from forgottenrealms.fandom.com for offline use with Project Codex.</p>
</body>
</html>"""

    # Remove existing ZIM if present
    if zim_path.exists():
        zim_path.unlink()
        log.info("Removed existing ZIM")

    with Creator(zim_path).config_indexing(True, "en").config_nbworkers(2) as creator:
        creator.set_mainpath("Main_Page")

        # ZIM metadata for kiwix-serve identification
        import datetime
        creator.add_metadata("Name", "forgotten_realms")
        creator.add_metadata("Title", "Forgotten Realms Wiki")
        creator.add_metadata("Description", "Offline mirror of the Forgotten Realms Wiki (Fandom)")
        creator.add_metadata("Language", "eng")
        creator.add_metadata("Creator", "forgottenrealms.fandom.com")
        creator.add_metadata("Publisher", "Project Codex (self-scraped)")
        creator.add_metadata("Date", datetime.date.today().isoformat())
        creator.add_metadata("Tags", "_category:other;_ftindex:yes;_pictures:no")

        # Add main page
        creator.add_item(WikiItem("Main_Page", "Forgotten Realms Wiki", main_page_html))

        # Add letter index pages
        for letter in sorted(letters.keys()):
            items_html = "\n".join(
                f'<li><a href="../{quote(t, safe="")}">{t}</a></li>'
                for t in sorted(letters[letter])
            )
            page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Index: {letter}</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:0 auto;padding:1em;}}a{{color:#2980b9;}}</style>
</head><body>
<h1>Articles: {letter}</h1>
<p><a href="../Main_Page">← Back to index</a></p>
<ul>{items_html}</ul>
</body></html>"""
            creator.add_item(WikiItem(f"index_{letter}", f"Index: {letter}", page))

        # Add articles
        added = 0
        for title, html, text_len in articles:
            path = quote(title, safe="")
            try:
                creator.add_item(WikiItem(path, title, html))
                added += 1
                if added % 1000 == 0:
                    log.info(f"  Added {added}/{len(articles)} articles...")
            except Exception as e:
                log.warning(f"  Skip '{title}': {e}")

    final_size = zim_path.stat().st_size
    log.info(f"ZIM created: {zim_path} ({final_size / 1024 / 1024:.1f} MB, {added} articles)")


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def show_status(db_path: Path):
    if not db_path.exists():
        print("No database found. Run 'scrape' first.")
        return

    conn = sqlite3.connect(str(db_path))
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM articles WHERE status='done'").fetchone()[0]
    errors = conn.execute("SELECT COUNT(*) FROM articles WHERE status='error'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM articles WHERE status='pending'").fetchone()[0]
    missing = conn.execute("SELECT COUNT(*) FROM articles WHERE error='missing'").fetchone()[0]
    total_size = conn.execute("SELECT COALESCE(SUM(text_length), 0) FROM articles WHERE status='done'").fetchone()[0]

    print(f"\n  FR Wiki Scrape Status")
    print(f"  {'─' * 35}")
    print(f"  Total articles:  {total:,}")
    print(f"  Scraped (done):  {done:,}")
    print(f"  Pending:         {pending:,}")
    print(f"  Errors:          {errors:,}")
    print(f"  Missing pages:   {missing:,}")
    print(f"  Total HTML size: {total_size / 1024 / 1024:.1f} MB")
    print(f"  Progress:        {100 * done / total:.1f}%" if total else "  Progress: 0%")

    if errors > 0:
        print(f"\n  Top errors:")
        for row in conn.execute(
            "SELECT error, COUNT(*) as c FROM articles WHERE status='error' GROUP BY error ORDER BY c DESC LIMIT 5"
        ).fetchall():
            print(f"    {row[0]}: {row[1]}")

    conn.close()
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="FR Wiki → ZIM Scraper")
    parser.add_argument(
        "command",
        choices=["scrape", "build", "all", "status", "retry"],
        help="scrape=fetch articles, build=create ZIM, all=both, status=show progress, retry=re-scrape errors",
    )
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path")
    parser.add_argument("--articles", type=Path, default=ARTICLE_LIST, help="Article list file")
    parser.add_argument("--output", type=Path, default=ZIM_OUTPUT, help="Output ZIM path")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Concurrent workers")
    args = parser.parse_args()

    # Update module-level workers count
    _update_workers(args.workers)

    if args.command == "status":
        show_status(args.db)
    elif args.command == "scrape":
        scrape_phase(args.db, args.articles)
    elif args.command == "build":
        build_phase(args.db, args.output)
    elif args.command == "retry":
        # Reset errors to pending for retry
        conn = init_db(args.db)
        reset = conn.execute(
            "UPDATE articles SET status='pending', error=NULL WHERE status='error' AND error != 'missing'"
        ).rowcount
        conn.commit()
        conn.close()
        log.info(f"Reset {reset} failed articles to pending")
        scrape_phase(args.db, args.articles)
    elif args.command == "all":
        scrape_phase(args.db, args.articles)
        build_phase(args.db, args.output)


if __name__ == "__main__":
    main()
