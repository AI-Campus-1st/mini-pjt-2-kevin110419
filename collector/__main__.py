"""수집기 진입점: python -m collector"""
import json
import logging
from datetime import datetime
from pathlib import Path

from . import config
from .dim_station import build_records as build_dim_station_records
from .loader import load_dim_station, load_living_pop, load_subway_hourly
from .sources.living_pop import iter_living_pop_pages
from .sources.subway import fetch_subway_hourly
from .transform import transform_living_pop_rows, transform_subway_rows

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"collect_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


def raw_path(name: str) -> Path:
    day_dir = RAW_DIR / datetime.now().strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    return day_dir / name


def save_raw(name: str, payload) -> None:
    with open(raw_path(f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def collect_subway() -> None:
    logger = logging.getLogger("collector.subway")
    if not config.TARGET_USE_MM:
        logger.warning("TARGET_USE_MM이 비어있어 지하철 데이터 수집을 건너뜁니다.")
        return
    for use_mm in config.TARGET_USE_MM:
        logger.info("지하철 승하차 데이터 수집 시작: use_mm=%s", use_mm)
        try:
            api_rows = fetch_subway_hourly(use_mm)
        except Exception:
            logger.exception("지하철 데이터 수집 실패: use_mm=%s", use_mm)
            continue
        save_raw(f"subway_{use_mm}", api_rows)

        records = transform_subway_rows(api_rows)
        unique = len({(r["line_nm"], r["station_nm"], r["hour"]) for r in records})
        # API가 같은 역을 여러 번 내려주는 달이 있다(예: 202607). UNIQUE 제약 덕에 DB에는
        # 고유 건수만 남지만, 원본에 중복이 있었다는 사실은 로그로 드러나야 한다.
        if unique != len(records):
            logger.warning(
                "원본 중복 감지: use_mm=%s, API %d행 -> 레코드 %d건이지만 고유 키는 %d건 (중복은 UPSERT로 덮어씀)",
                use_mm, len(api_rows), len(records), unique,
            )
        load_subway_hourly(records)
        logger.info(
            "지하철 데이터 적재 완료: use_mm=%s, API %d행 -> 고유 %d건 적재",
            use_mm, len(api_rows), unique,
        )


def collect_living_pop() -> None:
    logger = logging.getLogger("collector.living_pop")
    if not config.COLLECT_LIVING_POP:
        logger.info("COLLECT_LIVING_POP=False 이므로 생활인구 수집을 건너뜁니다.")
        return

    logger.info("생활인구 데이터 수집 시작 (최신 1일치 전체 스냅샷)")
    loaded = 0
    base_dates = set()
    out_file = raw_path("living_pop.jsonl")
    try:
        # 수십만 행이라 페이지 단위로 즉시 적재한다(메모리에 전부 쌓지 않음).
        with open(out_file, "w", encoding="utf-8") as raw_file:
            for page_rows, total in iter_living_pop_pages(config.LIVING_POP_MAX_PAGES):
                for row in page_rows:
                    raw_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                records = transform_living_pop_rows(page_rows)
                loaded += load_living_pop(records)
                base_dates.update(r["base_date"] for r in records)
                if loaded % 50_000 < len(records):
                    logger.info("생활인구 진행률: %d / %d행", loaded, total)
    except Exception:
        logger.exception("생활인구 데이터 수집 실패 (여기까지 %d행 적재됨)", loaded)
        return
    logger.info("생활인구 데이터 적재 완료: rows=%d, 기준일=%s", loaded, sorted(base_dates))


def build_dim_station() -> None:
    """역 좌표를 행정동 경계와 대조해 dim_station을 채운다 (지하철 <-> 생활인구 조인 키)."""
    logger = logging.getLogger("collector.dim_station")
    if not config.BUILD_DIM_STATION:
        logger.info("BUILD_DIM_STATION=False 이므로 역-행정동 매핑을 건너뜁니다.")
        return
    try:
        records = build_dim_station_records()
    except Exception:
        logger.exception("역-행정동 매핑 실패")
        return
    logger.info("dim_station 적재 완료: %d건", load_dim_station(records))


def main() -> None:
    setup_logging()
    if not config.SEOUL_API_KEY:
        raise SystemExit(".env의 SEOUL_API_KEY가 비어있습니다. 먼저 인증키를 채워주세요.")
    build_dim_station()
    collect_subway()
    collect_living_pop()


if __name__ == "__main__":
    main()
