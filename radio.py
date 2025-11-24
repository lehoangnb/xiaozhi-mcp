# coding: utf-8
"""
Radio Stations and Music MCP tool
- Provides a list of Vietnamese radio stations (VOV) and their streaming URLs.
- Allows searching for a radio station by name or ID.
- Provides music search functionality using MP3 proxy service.
- Supports streaming music with metadata and lyrics.
"""

from fastmcp import FastMCP
import logging
import sys
from typing import List, Dict, Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

mcp = FastMCP("Vietnam Radio Stations")
logger = logging.getLogger("Radio")
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s")

# MP3 Proxy configuration
# Use service name in Docker, fallback to localhost for local development
import os
MP3_PROXY_URL = os.getenv("MP3_PROXY_URL", "http://mp3-proxy:5005")

# Define the radio stations data
# Structure: Key (ID) -> {name, url, description, genre}
RADIO_STATIONS = {
    "VOV1": {
        "name": "VOV 1 - Đài Tiếng nói Việt Nam",
        "url": "https://stream.vovmedia.vn/vov-1",
        "description": "Kênh thông tin tổng hợp",
        "genre": "News/Talk"
    },
    "VOV2": {
        "name": "VOV 2 - Âm thanh Việt Nam",
        "url": "https://stream.vovmedia.vn/vov-2",
        "description": "Kênh văn hóa - văn nghệ",
        "genre": "Culture/Music"
    },
    "VOV3": {
        "name": "VOV 3 - Tiếng nói Việt Nam",
        "url": "https://stream.vovmedia.vn/vov-3",
        "description": "Kênh thông tin - giải trí",
        "genre": "Entertainment"
    },
    "VOV5": {
        "name": "VOV 5 - Tiếng nói người Việt",
        "url": "https://stream.vovmedia.vn/vov5",
        "description": "Kênh dành cho người Việt ở nước ngoài",
        "genre": "Overseas Vietnamese"
    },
    "VOVGT": {
        "name": "VOV Giao thông Hà Nội",
        "url": "https://stream.vovmedia.vn/vovgt-hn",
        "description": "Thông tin giao thông Hà Nội",
        "genre": "Traffic"
    },
    "VOVGT_HCM": {
        "name": "VOV Giao thông Hồ Chí Minh",
        "url": "https://stream.vovmedia.vn/vovgt-hcm",
        "description": "Thông tin giao thông TP. Hồ Chí Minh",
        "genre": "Traffic"
    },
    "VOV_ENGLISH": {
        "name": "VOV English Tiếng Anh",
        "url": "https://stream.vovmedia.vn/vov247",
        "description": "VOV English Service",
        "genre": "International"
    },
    "VOV_MEKONG": {
        "name": "VOV Mê Kông",
        "url": "https://stream.vovmedia.vn/vovmekong",
        "description": "Kênh vùng Đồng bằng sông Cửu Long",
        "genre": "Regional"
    },
    "VOV_MIENTRUNG": {
        "name": "VOV Miền Trung",
        "url": "https://stream.vovmedia.vn/vov4mt",
        "description": "Kênh vùng miền Trung",
        "genre": "Regional"
    },
    "VOV_TAYBAC": {
        "name": "VOV Tây Bắc",
        "url": "https://stream.vovmedia.vn/vov4tb",
        "description": "Kênh vùng Tây Bắc",
        "genre": "Regional"
    },
    "VOV_DONGBAC": {
        "name": "VOV Đông Bắc",
        "url": "https://stream.vovmedia.vn/vov4db",
        "description": "Kênh vùng Đông Bắc",
        "genre": "Regional"
    },
    "VOV_TAYNGUYEN": {
        "name": "VOV Tây Nguyên",
        "url": "https://stream.vovmedia.vn/vov4tn",
        "description": "Kênh vùng Tây Nguyên",
        "genre": "Regional"
    },
    "ZING_RADIO": {
        "name": "Zing radio",
        "url": f"{MP3_PROXY_URL}/proxy_audio?stream=zing_mp3",
        "description": "Zing radio",
        "genre": "Music"
    }
}

@mcp.tool()
def get_radio_stations() -> List[Dict[str, str]]:
    """
    Get a list of all available radio stations.
    Returns a list of dictionaries containing station details (id, name, description, genre).
    Does NOT return the URL to keep the context small; use get_radio_station_url for that.
    """
    stations = []
    for station_id, data in RADIO_STATIONS.items():
        stations.append({
            "id": station_id,
            "name": data["name"],
            "description": data["description"],
            "genre": data["genre"]
        })
    return stations

@mcp.tool()
def get_radio_station_url(station_id_or_name: str) -> Dict[str, str]:
    """
    Get the streaming URL for a specific radio station.
    Args:
        station_id_or_name: The ID (e.g., "VOV1") or name (e.g., "VOV 1") of the station.
    Returns:
        A dictionary with "url" and "name" if found, or an error message.
    """
    query = station_id_or_name.lower().strip()

    # Direct ID match
    if station_id_or_name in RADIO_STATIONS:
        data = RADIO_STATIONS[station_id_or_name]
        return {"url": data["url"], "name": data["name"]}

    # Case-insensitive ID match
    for sid, data in RADIO_STATIONS.items():
        if sid.lower() == query:
            return {"url": data["url"], "name": data["name"]}

    # Name match (partial)
    for sid, data in RADIO_STATIONS.items():
        if query in data["name"].lower():
            return {"url": data["url"], "name": data["name"]}

    return {"error": f"Station '{station_id_or_name}' not found."}

def _search_music_internal(song: str, artist: str = "") -> Dict[str, any]:
    """
    Internal function to search for music using the MP3 proxy service.
    """
    import requests

    try:
        # Construct search URL
        search_url = f"{MP3_PROXY_URL}/stream_pcm?song={requests.utils.quote(song)}"
        if artist:
            search_url += f"&artist={requests.utils.quote(artist)}"

        # Make request to mp3-proxy
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Check for error
        if "error" in data:
            return {"error": data["error"]}

        # Convert relative URLs to absolute URLs
        audio_url = data.get("audio_url", "")
        lyric_url = data.get("lyric_url", "")

        if audio_url.startswith("/"):
            audio_url = MP3_PROXY_URL + audio_url
        if lyric_url.startswith("/"):
            lyric_url = MP3_PROXY_URL + lyric_url

        return {
            "title": data.get("title", song),
            "artist": data.get("artist", artist or "Unknown"),
            "audio_url": audio_url,
            "lyric_url": lyric_url,
            "thumbnail": data.get("thumbnail", ""),
            "duration": data.get("duration", 0),
            "language": data.get("language", "unknown")
        }

    except requests.RequestException as e:
        return {"error": f"Failed to search music: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@mcp.tool()
def search_music(song: str, artist: str = "") -> Dict[str, any]:
    """
    Search for a song using the MP3 proxy service.
    Args:
        song: The name of the song to search for.
        artist: The artist name (optional, improves search accuracy).
    Returns:
        A dictionary with song metadata including stream URL, or an error message.
    """
    return _search_music_internal(song, artist)

@mcp.tool()
def get_music_stream(song: str, artist: str = "") -> Dict[str, any]:
    """
    Get a music stream URL for playback. This is a convenience function that searches
    and returns only the essential information needed for playback.
    Args:
        song: The name of the song to search for.
        artist: The artist name (optional).
    Returns:
        A dictionary with stream URL and metadata for playback.
    """
    result = _search_music_internal(song, artist)

    if "error" in result:
        return result

    return {
        "url": result["audio_url"],
        "title": result["title"],
        "artist": result["artist"],
        "lyric_url": result["lyric_url"]
    }

if __name__ == "__main__":
    logger.info("Starting Radio MCP Server")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.exception("Failed to run MCP server: %s", e)
