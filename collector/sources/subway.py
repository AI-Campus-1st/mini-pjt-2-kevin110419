"""CardSubwayTime: 지하철호선별 역별 시간대별 승하차인원 정보."""
from ..client import fetch_all


def fetch_subway_hourly(use_mm: str):
    """1행 = 1호선 x 1역 x 1개월(use_mm), 시간대 48개 컬럼이 wide로 붙어서 온다."""
    return fetch_all("CardSubwayTime", use_mm)
