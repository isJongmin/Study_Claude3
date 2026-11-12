"""백엔드가 stdio MCP 클라이언트로 날씨 MCP 서버를 호출한다. 10분 캐시, 실패하면 샘플값(state=sample)."""
import asyncio
import json
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .. import config

REGIONS = ("울산", "거제", "목포")
SAMPLE = {
    "울산": {"tempC": 17.6, "condition": "맑음", "humidity": 52, "windMs": 3.2},
    "거제": {"tempC": 18.9, "condition": "구름조금", "humidity": 61, "windMs": 4.1},
    "목포": {"tempC": 16.2, "condition": "흐림", "humidity": 70, "windMs": 5.0},
}
SERVER = config.ROOT / "backend" / "mcp_servers" / "weather_server.py"
_cache: dict[str, tuple[float, dict]] = {}


async def _call_mcp(region: str) -> dict:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        res = await s.call_tool("get_weather", {"region": region})
        if res.isError:
            raise RuntimeError("weather tool error")
        return res.structuredContent or json.loads(res.content[0].text)


async def get_weather(region: str) -> dict:
    hit = _cache.get(region)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    try:
        data = {**await asyncio.wait_for(_call_mcp(region), 12), "state": "live"}
        _cache[region] = (time.time(), data)
    except Exception:  # 네트워크·MCP 실패는 모두 샘플로 대체 (화면은 '샘플' 배지)
        data = {"region": region, "obsDt": f"{config.TODAY}T09:00", **SAMPLE[region], "state": "sample"}
    return data
