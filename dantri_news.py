from fastmcp import FastMCP
import urllib.request
import re
import logging
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

# Initialize FastMCP server and logger
mcp = FastMCP("Dantri News")
logger = logging.getLogger("DantriNews")
logging.basicConfig(level=logging.INFO)

def fetch_dantri_news(url: str) -> list[str]:
    """Fetch up to 5 latest news headlines from the given Dantri URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode("utf-8")
        # Dantri article titles are typically inside <h3 class="article-title"><a ...>Title</a></h3>
        matches = re.findall(r"<h3 class=\"article-title\">.*?<a[^>]*>(.*?)</a>", html_content, re.DOTALL)
        titles = []
        for match in matches:
            # Strip any remaining HTML tags and whitespace
            clean_title = re.sub(r"<.*?>", "", match).strip()
            # Basic HTML entity unescaping
            clean_title = (
                clean_title.replace("&quot;", '"')
                .replace("&apos;", "'")
                .replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
            )
            if clean_title and clean_title not in titles:
                titles.append(clean_title)
            if len(titles) >= 5:
                break
        return titles
    except Exception as e:
        logger.error(f"Error fetching news from {url}: {e}")
        return [f"Error fetching news: {str(e)}"]

# MCP tools for each category
@mcp.tool()
def get_world_news() -> list[str]:
    """Return the latest 5 world news headlines (the-gioi)."""
    return fetch_dantri_news("https://dantri.com.vn/the-gioi.htm")

@mcp.tool()
def get_vietnam_news() -> list[str]:
    """Return the latest 5 Vietnam news headlines (thoi-su)."""
    return fetch_dantri_news("https://dantri.com.vn/thoi-su.htm")

if __name__ == "__main__":
    mcp.run(transport="stdio")
