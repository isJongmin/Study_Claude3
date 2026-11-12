"""MCP 날씨 서버(stdio). 도구 get_weather(region) 하나. Open-Meteo 현재값을 반환한다."""
import json
import urllib.request

from mcp.server.fastmcp import FastMCP

REGIONS = {"울산": (35.54, 129.31), "거제": (34.88, 128.62), "목포": (34.81, 126.39)}
mcp = FastMCP("shipyard-weather")


def condition(code: int) -> str:
    if code == 0:
        return "맑음"
    if code in (1, 2):
        return "구름조금"
    if code == 3:
        return "흐림"
    if code in (45, 48):
        return "안개"
    if code in (71, 73, 75, 77, 85, 86):
        return "눈"
    if code in (95, 96, 99):
        return "뇌우"
    if code in (80, 81, 82):
        return "소나기"
    return "비" if code >= 51 else "구름조금"


@mcp.tool()
def get_weather(region: str) -> dict:
    """조선소 지역(울산·거제·목포)의 현재 기온(℃)·습도(%)·풍속(m/s)·날씨를 조회한다."""
    if region not in REGIONS:
        raise ValueError(f"지원하지 않는 지역입니다: {region} (울산·거제·목포)")
    lat, lon = REGIONS[region]
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&wind_speed_unit=ms&timezone=Asia%2FSeoul")
    with urllib.request.urlopen(url, timeout=6) as r:  # noqa: S310 (고정된 https 주소)
        cur = json.load(r)["current"]
    return {"region": region, "obsDt": cur["time"], "tempC": cur["temperature_2m"], "condition": condition(cur["weather_code"]),
            "humidity": cur["relative_humidity_2m"], "windMs": cur["wind_speed_10m"]}


if __name__ == "__main__":
    mcp.run()
