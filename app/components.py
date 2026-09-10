"""KPI 카드, 사이드바 필터 등 재사용 UI 조각."""
import html

import streamlit as st

import repository


def render_sidebar():
    st.sidebar.header("필터")
    months = repository.load_available_months()
    if not months:
        st.sidebar.info(
            "mart_station_monthly에 데이터가 없습니다.\n\n"
            "먼저 `db/seed_dummy.sql`을 적재하거나 `python -m collector` 후 "
            "`db/build_mart.sql`을 실행하세요."
        )
        return None
    use_mm = st.sidebar.selectbox("기준월", months, index=len(months) - 1)
    top_n = st.sidebar.slider("표시할 역 수", min_value=5, max_value=30, value=10, step=1)
    # 승하차가 극소량인 역은 비율만 튀어서 순위를 왜곡한다(월 3명인 역이 33%로 1위가 되는 식).
    min_ridership = st.sidebar.number_input(
        "최소 월 승하차 인원", min_value=0, value=10_000, step=10_000,
        help="이 값 미만인 역은 랭킹에서 제외합니다. 0으로 두면 전체를 봅니다.",
    )
    return {"use_mm": use_mm, "top_n": top_n, "min_ridership": int(min_ridership)}


def render_kpis(df) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("분석 대상 역 수", f"{len(df):,}")
    if len(df):
        c2.metric("평균 야간이용률", f"{df['night_ratio'].mean():.1%}")
        top = df.iloc[0]  # 정렬 기준이 유동인구이므로 1행 = 1순위 역
        c3.metric("1순위 역", top["station_nm"], f"야간 {top['night_ratio']:.1%}")
        c4.metric("기준월", str(df.iloc[0]["use_mm"]))
    else:
        c2.metric("평균 야간이용률", "-")
        c3.metric("1순위 역", "-")
        c4.metric("기준월", "-")
SUMMARY_CARD_CSS = """
<style>
.summary-card {
    border: 1px solid rgba(128, 128, 128, 0.25);
    border-radius: 10px;
    padding: 16px 10px 14px 10px;
    margin-bottom: 12px;
    text-align: center;
    background: rgba(76, 110, 245, 0.06);
    /* 역명 길이가 제각각이라 고정 높이 + 세로 가운데 정렬로 카드 줄을 맞춘다 */
    min-height: 132px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.summary-card .rank {
    font-size: 0.75rem;
    font-weight: 700;
    color: #4C6EF5;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}
.summary-card .station {
    font-size: 1.55rem;
    font-weight: 700;
    line-height: 1.25;
    color: inherit;
    word-break: keep-all;
}
.summary-card .station.long {
    font-size: 1.12rem;
}
.summary-card .line {
    font-size: 0.78rem;
    opacity: 0.65;
    margin-top: 8px;
    line-height: 1.3;
    word-break: keep-all;
}
</style>
"""


def render_summary_cards(df, per_row: int = 5) -> None:
    """역 이름(크게) + 노선명(작게)만 카드로 보여준다. 수치는 의도적으로 싣지 않는다."""
    st.markdown(SUMMARY_CARD_CSS, unsafe_allow_html=True)
    rows = list(df.itertuples(index=False))
    for start in range(0, len(rows), per_row):
        cols = st.columns(per_row)
        for col, (offset, row) in zip(cols, enumerate(rows[start : start + per_row])):
            raw_name = str(row.station_nm)
            # '올림픽공원(한국체대)'처럼 긴 역명은 줄바꿈이 지저분해져 한 단계 작게 쓴다
            size_class = " long" if len(raw_name) > 6 else ""
            col.markdown(
                f'<div class="summary-card">'
                f'<div class="rank">{start + offset + 1}위</div>'
                f'<div class="station{size_class}">{html.escape(raw_name)}</div>'
                f'<div class="line">{html.escape(str(row.line_nm))}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
