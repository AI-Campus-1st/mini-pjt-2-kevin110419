"""subwayStationMaster: 서울시 지하철역 마스터(역명 + 위경도)."""
from ..client import fetch_all


def fetch_station_master():
    """1행 = 1호선 x 1역. BLDN_NM(역명), ROUTE(호선), LAT/LOT(위경도).

    역명 표기가 CardSubwayTime의 STTN과 동일하다('역' 접미사 없음)므로 그대로 조인된다.
    """
    return fetch_all("subwayStationMaster")
