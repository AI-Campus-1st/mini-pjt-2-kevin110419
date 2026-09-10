"""서울 열린데이터광장 공통 Open API 호출기 (재시도 · 페이징 · 결과코드 검증)."""
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config


class SeoulOpenApiError(Exception):
    pass


class NoDataError(SeoulOpenApiError):
    """INFO-200. 조회 결과가 없을 때뿐 아니라 요청인자가 틀렸을 때도 이 코드가 온다."""


def make_session(retries=3, backoff=0.5):
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def build_url(service: str, start: int, end: int, *path_params) -> str:
    segments = [
        config.SEOUL_API_BASE_URL,
        config.SEOUL_API_KEY,
        "json",
        service,
        str(start),
        str(end),
        *[str(p) for p in path_params],
    ]
    return "/".join(segments) + "/"


def fetch_page(session, service: str, start: int, end: int, *path_params, sleep: float = 0.3):
    url = build_url(service, start, end, *path_params)
    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    # 에러 응답은 서비스명 키 없이 RESULT만 최상위로 내려온다.
    if service not in payload:
        result = payload.get("RESULT", {})
        code, message = result.get("CODE"), result.get("MESSAGE")
        if code == "INFO-200":
            raise NoDataError(f"{service}: {code} {message} (요청인자가 맞는지 확인하세요)")
        raise SeoulOpenApiError(f"{service} 요청 실패: {code} {message} / keys={list(payload.keys())}")

    body = payload[service]
    result = body.get("RESULT", {})
    code = result.get("CODE")
    if code not in (None, "INFO-000"):
        raise SeoulOpenApiError(f"{service} 요청 실패: {code} {result.get('MESSAGE')}")

    time.sleep(sleep)
    return body


def iter_pages(service: str, *path_params, page_size: int = 1000, max_pages: int = None, sleep: float = 0.3):
    """(rows, total) 을 페이지 단위로 순차 반환.

    생활인구처럼 수십만 행짜리 응답을 한 번에 메모리에 올리지 않기 위한 스트리밍 방식.
    """
    session = make_session()
    start = 1
    total = None
    page_no = 0
    while total is None or start <= total:
        body = fetch_page(session, service, start, start + page_size - 1, *path_params, sleep=sleep)
        total = int(body.get("list_total_count", 0))
        rows = body.get("row") or []
        if not rows:
            break
        page_no += 1
        yield rows, total
        if max_pages is not None and page_no >= max_pages:
            break
        start += page_size


def fetch_all(service: str, *path_params, page_size: int = 1000, sleep: float = 0.3):
    """작은 응답(지하철)용. 전체 row를 모아서 반환."""
    rows = []
    for page_rows, _ in iter_pages(service, *path_params, page_size=page_size, sleep=sleep):
        rows.extend(page_rows)
    return rows
