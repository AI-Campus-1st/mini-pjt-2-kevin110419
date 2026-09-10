"""역 좌표 -> 행정동코드 매핑으로 dim_station을 자동 생성한다.

CardSubwayTime에는 행정동코드가 없고 생활인구(ppsLocalResd)는 행정동 단위라, 둘을 잇는
다리가 필요하다. subwayStationMaster의 역 위경도를 행정동 경계(GeoJSON)와
point-in-polygon으로 대조해서 채운다.

실행: python -m collector.dim_station
"""
import json
import logging
import urllib.request

from . import config
from .loader import load_dim_station
from .sources.station_master import fetch_station_master

logger = logging.getLogger(__name__)


def ensure_boundary_file():
    path = config.ADM_BOUNDARY_PATH
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("행정동 경계 파일 내려받는 중(약 34MB): %s", config.ADM_BOUNDARY_URL)
    urllib.request.urlretrieve(config.ADM_BOUNDARY_URL, path)
    return path


def load_seoul_dongs():
    """[(adstrd_code, adstrd_nm, bbox, polygons)] 반환.

    주의: 생활인구의 ADSTRD_CODE_SE와 맞는 값은 GeoJSON의 adm_cd(통계청 8자리)가 아니라
    adm_cd2(행정표준코드 10자리)의 앞 8자리다. adm_cd를 쓰면 424개 중 32개만 매칭된다.
    """
    with open(ensure_boundary_file(), encoding="utf-8") as f:
        geojson = json.load(f)

    dongs = []
    for feature in geojson["features"]:
        props = feature["properties"]
        if props.get("sido") != "11":  # 서울시만
            continue
        geom = feature["geometry"]
        polygons = (
            geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        )
        xs, ys = [], []
        for polygon in polygons:
            for x, y in polygon[0]:
                xs.append(x)
                ys.append(y)
        adstrd_nm = f"{props.get('sggnm', '')} {props['adm_nm'].split()[-1]}".strip()
        dongs.append(
            (props["adm_cd2"][:8], adstrd_nm, (min(xs), min(ys), max(xs), max(ys)), polygons)
        )
    logger.info("행정동 경계 로드: 서울 %d개 동", len(dongs))
    return dongs


def _point_in_ring(x, y, ring) -> bool:
    """ray casting."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y):
            if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def _point_in_polygon(x, y, polygon) -> bool:
    if not _point_in_ring(x, y, polygon[0]):
        return False
    return not any(_point_in_ring(x, y, hole) for hole in polygon[1:])  # 구멍(내부 경계) 제외


def find_dong(lon: float, lat: float, dongs):
    for code, name, (min_x, min_y, max_x, max_y), polygons in dongs:
        if not (min_x <= lon <= max_x and min_y <= lat <= max_y):
            continue
        if any(_point_in_polygon(lon, lat, polygon) for polygon in polygons):
            return code, name
    return None


def build_records():
    dongs = load_seoul_dongs()
    stations = fetch_station_master()

    mapped, outside = {}, []
    for station in stations:
        name = station["BLDN_NM"]
        if name in mapped:
            continue  # 환승역은 호선 수만큼 중복 등장 (좌표는 사실상 동일)
        try:
            lat, lon = float(station["LAT"]), float(station["LOT"])
        except (TypeError, ValueError):
            continue
        hit = find_dong(lon, lat, dongs)
        if hit is None:
            outside.append(name)  # 서울 밖 역(7호선 인천 구간 등)은 생활인구 데이터가 없다
            continue
        mapped[name] = {"station_nm": name, "adstrd_code": hit[0], "adstrd_nm": hit[1]}

    logger.info("역-행정동 매핑 완료: %d개 매핑, %d개 서울 외 제외", len(mapped), len(outside))
    return list(mapped.values())


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    records = build_records()
    load_dim_station(records)
    logger.info("dim_station 적재 완료: %d건", len(records))


if __name__ == "__main__":
    main()
