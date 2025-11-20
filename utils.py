"""
Shared utilities for MCP tools.
"""

import datetime
from typing import Dict, Any, List


def normalize_prices_for_ai(raw_prices: Dict[str, Dict[str, str]], source_url: str, schema_type: str = "general") -> List[Dict[str, Any]]:
    """
    Convert raw price mapping to a structured list for AI consumption.

    Args:
        raw_prices: Dict mapping product names to price data
        source_url: URL of the data source
        schema_type: "fuel" for fuel prices, "gold" for gold prices, etc.

    Returns:
        List of structured records suitable for AI consumption
    """
    out: List[Dict[str, Any]] = []
    ts = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    for product, data in raw_prices.items():
        # Skip errors
        if product == "error":
            continue

        if schema_type == "fuel":
            # Fuel price schema with regions
            for region_name, display_val in data.items():
                record = {
                    "product": product,
                    "region": region_name,
                    "price_display": display_val,
                    "unit": "nghìn đồng",
                    "updated_at": ts,
                    "source": source_url
                }
                out.append(record)
        elif schema_type == "gold":
            # Gold price schema with buy/sell prices
            # Extract region from product name (format: "TypeName - BranchName")
            region = "Miền Bắc"  # Default
            product_parts = product.split(" - ")
            if len(product_parts) >= 2:
                region = product_parts[-1]  # BranchName is the last part

            record = {
                "product": product,
                "region": region,
                "price_buy": data.get("Mua vào", ""),
                "price_sell": data.get("Bán ra", ""),
                "unit": "Triệu đồng một lượng",
                "updated_at": ts,
                "source": source_url
            }
            out.append(record)
        else:
            # General schema
            record = {
                "product": product,
                "data": data,
                "updated_at": ts,
                "source": source_url
            }
            out.append(record)

    return out


def clean_number_string(s: str) -> str:
    """
    Clean and standardize number strings by removing extra spaces and handling separators.

    Args:
        s: Input string containing numbers

    Returns:
        Cleaned number string
    """
    if not s:
        return ""
    s = str(s).strip()
    s = s.replace("\xa0", " ").strip()
    # Keep the original formatting including . or ,
    # Extract numeric-like pattern: 21.050 or 1.234 or 21050 or 21,05
    import re
    m = re.search(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+", s)
    return m.group(0) if m else s
