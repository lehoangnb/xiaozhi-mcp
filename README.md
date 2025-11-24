# xiaozhi-mcp: Vietnamese Data MCP Servers for Xiaozhi

A collection of MCP (Model Context Protocol) servers providing access to Vietnamese financial data, news, radio stations, and music streaming. This project integrates with AI systems to fetch real-time Vietnamese gold prices (SJC), fuel prices (Petrolimex), news from Dantri, radio stations, and music search/playback.

## Features

- 💰 **SJC Gold Prices**: Real-time gold prices from SJC (Vietnam's state precious metals trading company) across different regions
- ⛽ **Petrolimex Fuel Prices**: Current fuel prices from Petrolimex (Vietnam's state oil company) with regional variations
- 📰 **Dantri News**: Latest news headlines and article summaries from Dantri.com.vn across world, Vietnam, sports, and auto categories
- 🔄 **Auto-Reconnection**: Robust WebSocket connection with exponential backoff retry mechanism
- 📡 **Multiple Transport Types**: Support for stdio, SSE, and HTTP transports
- 🐳 **Docker Support**: Containerized deployment with Docker Compose

## Project Structure

- `mcp_pipe.py`: Main WebSocket proxy that manages MCP server processes and connections
- `utils.py`: Shared utilities for data normalization and price formatting
- `sjc_gold.py`: MCP server for SJC gold price data across Vietnamese regions
- `petrolimex.py`: MCP server for Petrolimex fuel price data
- `dantri_news.py`: MCP server for Dantri.vn news scraping
- `mcp_config.json`: Optional configuration for custom server setups
- `docker/`: Docker deployment files

## Available MCP Tools

### SJC Gold Price Tools
- `get_gold_prices()`: All SJC gold prices
- `get_northern_gold_prices()`: Northern region prices
- `get_hcm_gold_prices()`: Ho Chi Minh City prices
- `get_halong_gold_prices()`: Ha Long prices
- `get_haiphong_gold_prices()`: Hai Phong prices
- `get_central_gold_prices()`: Central region prices
- `get_hue_gold_prices()`: Hue prices
- `get_quangngai_gold_prices()`: Quang Ngai prices
- `get_nhatrang_gold_prices()`: Nha Trang prices
- `get_bienhoa_gold_prices()`: Bien Hoa prices
- `get_southern_gold_prices()`: Southern region prices

### Petrolimex Fuel Price Tools
- `get_fuel_prices()`: Current Petrolimex fuel prices across regions

### Dantri News Tools
- `get_world_news()`: Latest 5 world news headlines
- `get_vietnam_news()`: Latest 5 Vietnam news headlines
- `get_sports_news()`: Latest 5 sports news headlines
- `get_auto_news()`: Latest 5 auto news headlines
- `search_news(query)`: Search news by query
- `get_news_summary(url)`: Get article summary (200 words)

### Radio Station Tools
- `get_radio_stations()`: List all available Vietnamese radio stations (Thank to [@TienHuyIoT](https://github.com/TienHuyIoT/xiaozhi-esp32_vietnam))
- `get_radio_station_url(station_id_or_name)`: Get streaming URL for a specific radio station

### Music Search Tools
- `search_music(song, artist?)`: Search for a song and return metadata including stream URL
- `get_music_stream(song, artist?)`: Get essential stream information for playback

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export MCP_ENDPOINT=wss://your-xiaozhi-endpoint
# Windows: $env:MCP_ENDPOINT = "wss://your-xiaozhi-endpoint"
```

3. Run all servers:
```bash
python mcp_pipe.py
```

Or run individual servers for testing:
```bash
python mcp_pipe.py calculator.py
python mcp_pipe.py sjc_gold.py
python mcp_pipe.py petrolimex.py
python mcp_pipe.py dantri_news.py
python mcp_pipe.py radio.py
```

### Docker Deployment

1. Clone the repository and set environment:
```bash
git clone https://github.com/lehoangnb/xiaozhi-mcp.git
cd xiaozhi-mcp
```

2. Set your MCP endpoint in docker-compose.yaml

3. Run with Docker Compose:
```bash
docker-compose up --build
```

## Configuration

### Environment Variables
- `MCP_ENDPOINT`: WebSocket URL for the MCP connection (required)
- `MCP_CONFIG`: Path to custom config file (optional, defaults to mcp_config.json)

### Custom Configuration
Edit `mcp_config.json` to configure additional servers:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["my_server.py"],
      "disabled": false
    }
  }
}
```

## Dependencies

- `python>=3.7`
- `fastmcp>=2.13.0`
- `websockets>=15.0`
- `requests>=2`
- `beautifulsoup4>=4.12`
- `mcp>=1.20.0`
- `mcp-proxy>=0.10.0`
- `python-dotenv>=1.2.1`

## Data Sources

This project scrapes data from real websites and does not store any data locally (except SJC gold cache for 1 hour):

- **SJC Gold Prices**: https://sjc.com.vn/ (Vietnam's official gold price tracking)
- **Petrolimex Fuel Prices**: https://webgia.com/gia-xang-dau/petrolimex/
- **Dantri News**: https://dantri.com.vn/ (Major Vietnamese news website)

## API Response Format

All price tools return structured data for AI consumption:
```json
{
  "data": [
    {
      "product": "Product Name",
      "region": "Region Name",
      "price_buy": "buy_price",
      "price_sell": "sell_price",
      "price_display": "display_price",
      "unit": "Triệu đồng một lượng",
      "updated_at": "2025-01-15T10:30:00+07:00",
      "source": "https://source.url"
    }
  ],
  "schema_version": "1.0"
}
```

## Contributing

Contributions welcome! Add new Vietnamese data sources by:
1. Creating a new `tool.py` following the existing pattern
2. Check `utils.normalize_prices_for_ai()` for consistent data formatting
3. Adding appropriate error handling and logging
4. Using MCP tools with clear descriptions

## Disclaimer

This project scrapes public websites and provides data access for informational purposes. Users should verify data accuracy and comply with terms of service of respective websites. The developers are not responsible for any use of this data.
