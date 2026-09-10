"""ppsLocalResd: 집계구 단위 서울 생활인구(내국인)."""
from ..client import iter_pages


def iter_living_pop_pages(max_pages: int = None):
    """(rows, total)을 페이지 단위로 반환. 1행 = 1기준일 x 1시간대 x 1집계구.

    이 API의 요청인자는 시작/종료 인덱스뿐이다. 경로에 날짜를 붙이면
    INFO-200('해당하는 데이터가 없습니다')이 돌아오므로, 파라미터 없이 호출해서
    "가장 최근 1일치" 서울 전체 스냅샷을 페이징으로 받아야 한다.
    """
    # 약 459회를 연속 호출하므로 요청 간 0.5초를 둬서 rate limit을 피한다.
    return iter_pages("ppsLocalResd", page_size=1000, max_pages=max_pages, sleep=0.5)
