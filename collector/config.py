import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SEOUL_API_KEY = os.getenv("SEOUL_API_KEY", "")
SEOUL_API_BASE_URL = "http://openapi.seoul.go.kr:8088"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "mini_project2")

# 야간시간대 정의 (20시~04시) — db/build_mart.sql의 CASE 조건과 반드시 동일하게 유지할 것
NIGHT_HOURS = {20, 21, 22, 23, 0, 1, 2, 3, 4}


def recent_months(n=3, lag_months=2):
    """오늘 기준 최근 n개월치 'YYYYMM' 목록. CardSubwayTime은 매월 5일 전월 데이터가
    올라오므로 기본 lag_months=2로 아직 갱신 안 된 최신 월을 피한다."""
    year, month = date.today().year, date.today().month
    month -= lag_months
    while month <= 0:
        month += 12
        year -= 1
    months = []
    for _ in range(n):
        months.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(months))


# 지하철 승하차 데이터 수집 대상 월. 필요에 맞게 직접 수정하세요.
TARGET_USE_MM = recent_months(n=3)

# 생활인구(ppsLocalResd) 수집 설정.
# 이 API는 날짜·지역 필터를 받지 않는다. 경로에 날짜를 붙이면 INFO-200('해당하는 데이터가 없습니다')이
# 돌아오고, 파라미터 없이 호출하면 "가장 최근 1일치" 서울 전체 집계구 스냅샷만 내려온다.
# (2026-09 확인 기준 약 458,000행 = 집계구 19,096개 x 24시간, 페이지당 1,000행이라 약 459회 요청)
COLLECT_LIVING_POP = True

# 시험 삼아 일부만 받아볼 때 페이지 수 제한 (1페이지 = 1,000행). None이면 전체 수집.
# 열린데이터광장 인증키는 일일 호출 한도가 있으므로 전체 수집 전에 작은 값으로 먼저 확인할 것.
LIVING_POP_MAX_PAGES = None

# 역 좌표 -> 행정동코드 매핑용 행정동 경계 데이터. 최초 1회만 받아 data/raw에 캐시한다.
ADM_BOUNDARY_URL = (
    "https://raw.githubusercontent.com/vuski/admdongkor/master/"
    "ver20250401/HangJeongDong_ver20250401.geojson"
)
ADM_BOUNDARY_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "HangJeongDong.geojson"

# python -m collector 실행 시 dim_station(역-행정동 매핑)도 함께 갱신할지 여부
BUILD_DIM_STATION = True
