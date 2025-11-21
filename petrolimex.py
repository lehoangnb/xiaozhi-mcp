#!/usr/bin/env python3
# coding: utf-8
"""
Petrolimex Fuel Prices MCP tool (fetch from webgia)
- Fetch table from https://webgia.com/gia-xang-dau/petrolimex/
- Return structured data suitable for AI consumption:
    {"data": [ {product, region, price_display, unit, updated_at, source}, ... ], "schema_version": "1.0"}
"""

from fastmcp import FastMCP
import requests
import re
import logging
import sys
from typing import Dict, Any, List
from utils import normalize_prices_for_ai, clean_number_string

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

# Initialise FastMCP server and logger for Petrolimex
mcp = FastMCP("Petrolimex Fuel Prices")
logger = logging.getLogger("Petrolimex")
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s")


def _clean_number_str(s: str) -> str:
    """Return representative display string for a numeric token like '21.050' or '21,050'. Keeps separators."""
    if not s:
        return ""
    s = str(s).strip()
    s = s.replace("\xa0", " ").strip()
    # Keep the original formatting including . or ,
    # Extract numeric-like pattern: 21.050 or 1.234 or 21050 or 21,05
    m = re.search(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+", s)
    return m.group(0) if m else s


def fetch_fuel_prices_from_webgia() -> Dict[str, Dict[str, str]]:
    """
    Fetch the Petrolimex price table from webgia and return a raw mapping:
      { "Xăng RON 95-V": {"Vùng 1": "21.050", "Vùng 2": "21.470"}, ... }
    If error returns {"error": "..."}
    """
    url = "https://webgia.com/gia-xang-dau/petrolimex/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    try:
        logger.debug("Fetching webgia Petrolimex page: %s", url)
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.exception("Failed to fetch webgia page")
        return {"error": f"Failed to fetch webgia page: {e}"}

    # Try BeautifulSoup for robust parsing
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("BeautifulSoup not installed. Please pip install beautifulsoup4")
        return {"error": "BeautifulSoup required. Please pip install beautifulsoup4"}

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Find table(s) that contain both 'Sản phẩm' and 'Vùng 1'
        candidate_tables = []
        for t in soup.find_all("table"):
            txt = t.get_text(" ", strip=True)
            if "Sản phẩm" in txt and "Vùng 1" in txt:
                candidate_tables.append(t)

        # fallback: any table whose text contains 'Vùng 1' and some 'Xăng'
        if not candidate_tables:
            for t in soup.find_all("table"):
                txt = t.get_text(" ", strip=True)
                if "Vùng 1" in txt and ("Xăng" in txt or "DO" in txt or "Dầu" in txt):
                    candidate_tables.append(t)

        prices: Dict[str, Dict[str, str]] = {}

        def clean_num_token(s: str) -> str:
            return _clean_number_str(s)

        for table in candidate_tables:
            # parse rows
            for tr in table.find_all("tr"):
                tds = tr.find_all(["td", "th"])
                if not tds:
                    continue
                first_text = tds[0].get_text(" ", strip=True)
                # skip header row
                header_lower = first_text.lower()
                if "sản phẩm" in header_lower or "vùng 1" in header_lower:
                    continue
                product = first_text
                v1 = tds[1].get_text(" ", strip=True) if len(tds) > 1 else ""
                v2 = tds[2].get_text(" ", strip=True) if len(tds) > 2 else ""
                v1c = clean_num_token(v1)
                v2c = clean_num_token(v2)
                if product:
                    prices[product] = {"Vùng 1": v1c, "Vùng 2": v2c}
            if prices:
                logger.debug("Parsed %d entries from webgia table.", len(prices))
                return prices

        # Final fallback: parse text lines for pattern: PRODUCT 21.050 21.470
        text = soup.get_text("\n")
        line_re = re.compile(
            r"(?P<prod>[A-Za-zÀ-ỹ0-9\-\s\/\(\)\.]{3,80}?)\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)"
        )
        for line in text.splitlines():
            m = line_re.search(line)
            if m:
                prod = m.group("prod").strip()
                if "đơn vị" in prod.lower():
                    logger.debug("Skipping non-product line from fallback: %s", prod)
                    continue
                v1 = m.group(2)
                v2 = m.group(3)
                if prod and ("Xăng" in prod or "DO" in prod or "Dầu" in prod):
                    prices[prod] = {"Vùng 1": _clean_number_str(v1), "Vùng 2": _clean_number_str(v2)}

        if prices:
            logger.debug("Parsed %d entries from webgia fallback text.", len(prices))
            return prices

        logger.warning("No price table found on webgia page.")
        return {"error": "No prices found on webgia page (structure may have changed)."}

    except Exception as e:
        logger.exception("Error parsing webgia HTML")
        return {"error": str(e)}




# MCP tool that returns structured data suitable for AI
@mcp.tool()
def get_fuel_prices() -> dict:
    """
    MCP tool entrypoint.
    Returns:
      {"data": [ {product, region, price_display, unit, updated_at, source}, ... ],
       "schema_version": "1.0" }
    On failure returns {"error": "..."}
    """
    raw = fetch_fuel_prices_from_webgia()
    structured = normalize_prices_for_ai(raw, "https://webgia.com/gia-xang-dau/petrolimex/", "fuel")
    return {"data": structured, "schema_version": "1.0"}


if __name__ == "__main__":
    logger.info("Running debug fetch for Petrolimex fuel prices (webgia source)")
    raw = fetch_fuel_prices_from_webgia()
    result = normalize_prices_for_ai(raw, "https://webgia.com/gia-xang-dau/petrolimex/", "fuel")
    logger.info("Result: %s", {"data": result, "schema_version": "1.0"})
    try:
        # Start MCP server (stdio transport)
        mcp.run(transport="stdio")
    except Exception as e:
        logger.exception("Failed to run MCP server: %s", e)
