from fastmcp import FastMCP
import urllib.request
import urllib.parse
import re
import logging
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

# Initialise FastMCP server and logger
mcp = FastMCP("Dantri News")
logger = logging.getLogger("DantriNews")
logging.basicConfig(level=logging.INFO)


def fetch_dantri_news(url: str) -> list[str]:
    """Fetch up to 5 latest news headlines from the given Dantri URL."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode("utf-8")
        matches = re.findall(r"<h3 class=\"article-title\">.*?<a[^>]*>(.*?)</a>", html_content, re.DOTALL)
        titles: list[str] = []
        for match in matches:
            clean_title = re.sub(r"<.*?>", "", match).strip()
            clean_title = (
                clean_title.replace("\u0026quot;", '"')
                .replace("\u0026apos;", "'")
                .replace("\u0026amp;", "&")
                .replace("\u0026lt;", "<")
                .replace("\u0026gt;", ">")
            )
            if clean_title and clean_title not in titles:
                titles.append(clean_title)
            if len(titles) >= 5:
                break
        return titles
    except Exception as e:
        logger.error(f"Error fetching news from {url}: {e}")
        return [f"Error fetching news: {str(e)}"]


def fetch_article_summary(url: str) -> str:
    """Fetch the article page and return a ~200‑word plain‑text summary."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
        clean_paras = [re.sub(r"<.*?>", "", p).strip() for p in paragraphs]
        full_text = " ".join(clean_paras)
        words = full_text.split()
        summary_words = words[:200]
        return " ".join(summary_words) + ("..." if len(words) > 200 else "")
    except Exception as e:
        logger.error(f"Error summarizing article {url}: {e}")
        return f"Error summarizing article: {str(e)}"


def search_dantri(query: str) -> list[str]:
    """Search Dantri with the given query string and return up to 5 titles.
    Uses the search page https://dantri.com.vn/tim-kiem/<query>.htm.
    """
    try:
        search_url = f"https://dantri.com.vn/tim-kiem/{urllib.parse.quote_plus(query)}.htm"
        logger.debug(f"Searching Dantri for '{query}': {search_url}")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")
        matches = re.findall(r"<h3 class=\"article-title\">.*?<a[^>]*>(.*?)</a>", html, re.DOTALL)
        titles: list[str] = []
        for match in matches:
            clean = re.sub(r"<.*?>", "", match).strip()
            clean = (
                clean.replace("\u0026quot;", '"')
                .replace("\u0026apos;", "'")
                .replace("\u0026amp;", "&")
                .replace("\u0026lt;", "<")
                .replace("\u0026gt;", ">")
            )
            if clean and clean not in titles:
                titles.append(clean)
            if len(titles) >= 5:
                break
        return titles
    except Exception as e:
        logger.error(f"Error searching Dantri for '{query}': {e}")
        return []


def fetch_news_with_fallback(url: str, fallback_query: str) -> list[str]:
    """Try to fetch headlines from a category URL; if none found, search.
    Returns up to 5 titles.
    """
    titles = fetch_dantri_news(url)
    if titles and not titles[0].lower().startswith("error"):
        return titles
    logger.info(f"No headlines found for {url}, falling back to search with query '{fallback_query}'.")
    return search_dantri(fallback_query)

# MCP tools ---------------------------------------------------------------
@mcp.tool()
def get_world_news() -> list[str]:
    """Return the latest 5 world‑news headlines (the‑gioi)."""
    return fetch_news_with_fallback("https://dantri.com.vn/the-gioi.htm", "the gioi")

@mcp.tool()
def get_vietnam_news() -> list[str]:
    """Return the latest 5 Vietnam‑news headlines (thoi‑su)."""
    return fetch_news_with_fallback("https://dantri.com.vn/thoi-su.htm", "thoi su")

@mcp.tool()
def get_sports_news() -> list[str]:
    """Return the latest 5 sports headlines (the‑thao)."""
    return fetch_news_with_fallback("https://dantri.com.vn/the-thao.htm", "the thao")

@mcp.tool()
def get_auto_news() -> list[str]:
    """Return the latest 5 auto (oto, xe máy) headlines."""
    return fetch_news_with_fallback("https://dantri.com.vn/o-to-xe-may.htm", "oto xe may")

@mcp.tool()
def get_news_summary(url: str) -> str:
    """Return a ~200‑word summary for the given Dantri article URL."""
    return fetch_article_summary(url)

@mcp.tool()
def search_news(query: str) -> list[str]:
    """Search Dantri for the given query and return up to 5 headlines."""
    return search_dantri(query)

if __name__ == "__main__":
    mcp.run(transport="stdio")
