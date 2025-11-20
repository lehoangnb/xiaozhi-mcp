#!/usr/bin/env python3
# coding: utf-8
"""
SJC Gold Prices MCP tool (fetch from sjc.com.vn)
- Fetch gold prices from https://sjc.com.vn/
- Return structured data suitable for AI consumption:
    {"data": [ {product, region, price_buy, price_sell, unit, updated_at, source}, ... ], "schema_version": "1.0"}
"""

from fastmcp import FastMCP
import requests
import re
import logging
import sys
import datetime
import json
import os
from typing import Dict, Any, List

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

# Initialise FastMCP server and logger for SJC Gold
mcp = FastMCP("SJC Gold Prices")
logger = logging.getLogger("SJC_Gold")
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s")


def _clean_number_str(s: str) -> str:
    """Return representative display string for a numeric token like '76.050.000' or '76,050,000'. Keeps separators."""
    if not s:
        return ""
    s = str(s).strip()
    s = s.replace("\xa0", " ").strip()
    # Keep the original formatting including . or ,
    # Extract numeric-like pattern: 76.050.000 or 76,050,000 or 76050000
    m = re.search(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+", s)
    return m.group(0) if m else s


def _get_cache_file_path() -> str:
    """Get the path for the cache file."""
    return os.path.join(os.path.dirname(__file__), "sjc_gold_cache.json")


def _read_cache() -> tuple:
    """Read data from cache file if it exists and is less than 1 hour old."""
    cache_file = _get_cache_file_path()
    if not os.path.exists(cache_file):
        return None, None

    try:
        # Get file modification time
        mod_time = os.path.getmtime(cache_file)
        current_time = datetime.datetime.now().timestamp()
        # Check if cache is less than 1 hour old (3600 seconds)
        if current_time - mod_time > 3600:
            logger.debug("Cache file is older than 1 hour, need to fetch new data")
            return None, None

        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        logger.debug("Successfully read data from cache file")
        return cache_data.get("prices", {}), cache_data.get("timestamp", "")
    except Exception as e:
        logger.error("Error reading cache file: %s", e)
        return None, None


def _write_cache(prices: Dict[str, Dict[str, str]], timestamp: str) -> None:
    """Write data to cache file."""
    cache_file = _get_cache_file_path()
    try:
        cache_data = {
            "prices": prices,
            "timestamp": timestamp,
            "last_updated": datetime.datetime.now().isoformat()
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        logger.debug("Successfully wrote data to cache file")
    except Exception as e:
        logger.error("Error writing cache file: %s", e)


def fetch_gold_prices_from_sjc() -> Dict[str, Dict[str, str]]:
    """
    Fetch the SJC gold price table from SJC API and return a raw mapping:
      { "Vàng SJC 1L": {"Mua vào": "76.500.000", "Bán ra": "7.100.000"}, ... }
    If error returns {"error": "..."}
    """
    # Check if we have valid cache data first
    cached_prices, cached_timestamp = _read_cache()
    if cached_prices is not None:
        logger.debug("Using cached data for SJC gold prices")
        return cached_prices

    # If no valid cache, fetch from API
    url = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx"
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    try:
        logger.debug("Fetching SJC gold prices from API: %s", url)
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        json_data = resp.json()
        logger.debug("Successfully fetched SJC gold prices from API")
        
        if not json_data.get("success"):
            logger.error("API returned success=false")
            return {"error": "API returned success=false"}
        
        prices: Dict[str, Dict[str, str]] = {}
        
        # Process the data from the API
        data_list = json_data.get("data", [])
        for item in data_list:
            type_name = item.get("TypeName", "")
            branch_name = item.get("BranchName", "")
            buy_price = item.get("Buy", "")  # Price in thousands VND
            sell_price = item.get("Sell", "")  # Price in thousands VND
            
            # Only add if we have actual price values
            if type_name and branch_name and buy_price and sell_price:
                # The API already includes thousands separators, so we just need to format properly
                # Example: "148,300" means 148,300,000 VND per lượng
                formatted_buy = buy_price
                formatted_sell = sell_price
                
                product_name = f"{type_name} - {branch_name}"
                prices[product_name] = {"Mua vào": formatted_buy, "Bán ra": formatted_sell}
                logger.debug("Found gold price: %s - Mua: %s, Bán: %s", product_name, formatted_buy, formatted_sell)
        
        if prices:
            logger.debug("Parsed %d entries from SJC API.", len(prices))
            # Write to cache for future requests
            latest_date = json_data.get("latestDate", "")
            _write_cache(prices, latest_date)
            return prices
        else:
            logger.warning("No gold prices found in SJC API response.")
            return {"error": "No gold prices found in SJC API response."}

    except requests.exceptions.RequestException as e:
        logger.error("Request error when fetching SJC API: %s", e)
        # If API request fails but we have cache data, return the cached data
        if cached_prices is not None:
            logger.info("API request failed, using cached data")
            return cached_prices
        return {"error": f"Request error when fetching SJC API: {e}"}
    except ValueError as e:  # JSON decode error
        logger.error("Error parsing JSON response from SJC API: %s", e)
        # If API request fails but we have cache data, return the cached data
        if cached_prices is not None:
            logger.info("API request failed, using cached data")
            return cached_prices
        return {"error": f"Error parsing JSON response from SJC API: {e}"}
    except Exception as e:
        logger.exception("Error fetching SJC API")
        # If API request fails but we have cache data, return the cached data
        if cached_prices is not None:
            logger.info("API request failed, using cached data")
            return cached_prices
        return {"error": f"Error fetching SJC API: {e}"}


def normalize_prices_for_ai(raw_prices: Dict[str, Dict[str, str]], source_url: str) -> List[Dict[str, Any]]:
    """
    Convert raw mapping to a structured list of records for AI / machine consumption.
    raw_prices: {"Product": {"Mua vào": "76.500.000", "Bán ra": "77.100.000"}}
    Returns list of records with price_buy, price_sell, unit, updated_at, source.
    """
    out: List[Dict[str, Any]] = []
    ts = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    for product, prices in raw_prices.items():
        # skip errors
        if product == "error":
            continue
        # Extract region from product name (format: "TypeName - BranchName")
        region = "Miền Bắc"  # Default
        product_parts = product.split(" - ")
        if len(product_parts) >= 2:
            region = product_parts[-1]  # BranchName is the last part
        
        record = {
            "product": product,
            "region": region,
            "price_buy": prices.get("Mua vào", ""),
            "price_sell": prices.get("Bán ra", ""),
            "unit": "nghìn đồng một lượng",
            "updated_at": ts,
            "source": source_url
        }
        out.append(record)
    return out


# MCP tool that returns structured data suitable for AI
@mcp.tool()
def get_gold_prices() -> dict:
    """
    MCP tool entrypoint to get SJC gold prices.
    Returns:
      {"data": [ {product, region, price_buy, price_sell, unit, updated_at, source}, ... ],
       "schema_version": "1.0" }
    On failure returns {"error": "..."}
    """
    raw = fetch_gold_prices_from_sjc()
    structured = normalize_prices_for_ai(raw, "https://sjc.com.vn/")
    return {"data": structured, "schema_version": "1.0"}


# Additional tool to get specifically northern region prices
@mcp.tool()
def get_northern_gold_prices() -> dict:
    """
    MCP tool entrypoint to get SJC gold prices specifically for Northern region.
    Returns:
      {"data": [ {product, region, price_buy, price_sell, unit, updated_at, source}, ... ],
       "schema_version": "1.0" }
    On failure returns {"error": "..."}
    """
    raw = fetch_gold_prices_from_sjc()
    structured = normalize_prices_for_ai(raw, "https://sjc.com.vn/")
    # Filter for Northern region (in this implementation, we're already targeting northern region)
    northern_prices = [item for item in structured if "Miền Bắc" in item.get("region", "")]
    return {"data": northern_prices, "schema_version": "1.0"}


if __name__ == "__main__":
    logger.info("Running debug fetch for SJC gold prices (sjc.com.vn source)")
    raw = fetch_gold_prices_from_sjc()
    result = normalize_prices_for_ai(raw, "https://sjc.com.vn/")
    logger.info("Result: %s", {"data": result, "schema_version": "1.0"})
    try:
        # Start MCP server (stdio transport)
        mcp.run(transport="stdio")
    except Exception as e:
        logger.exception("Failed to run MCP server: %s", e)
