"""Streamlit 진입점: streamlit run app/main.py"""
import streamlit as st

import charts
import components
import repository

st.set_page_config(page_title="야간 관리가 강화되어야 할 지하철역", layout="wide")

st.title("야간 관리가 강화되어야 할 지하철역")
st.markdown(
    "**야간(20~04시) 이용률이 높으면서 배후 유동인구까지 많은 역은 야간 운영과 안전 관리를 "
    "특별히 강화해야 합니다.** 아래는 그 우선순위 후보입니다."
)

filters = components.render_sidebar()
if filters is None:
    st.stop()

use_mm, top_n = filters["use_mm"], filters["top_n"]
ranking_df = repository.load_station_ranking(
    use_mm, top_n=top_n, min_ridership=filters["min_ridership"]
)

if ranking_df.empty:
    st.warning(f"{use_mm} 기준으로 조회된 데이터가 없습니다.")
    st.stop()

night_threshold, candidate_count, rankable_count = repository.load_night_threshold(
    use_mm, min_ridership=filters["min_ridership"]
)

components.render_kpis(ranking_df)

tab_summary, tab1, tab2, tab3 = st.tabs(["요약", "역 랭킹", "시간대 히트맵", "월별 추이"])

with tab_summary:
    st.subheader("특별 관리가 필요한 상위 10개 역")
    summary_df = repository.load_station_ranking(
        use_mm, top_n=10, min_ridership=filters["min_ridership"]
    )
    components.render_summary_cards(summary_df)
    if night_threshold is not None:
        st.caption(
            f"야간(20~04시) 이용률 상위 10%({night_threshold:.1%} 이상)에 드는 {candidate_count}개 역 중, "
            f"배후 행정동 유동인구를 확인할 수 있는 {rankable_count}개 역을 유동인구가 많은 순으로 세운 결과입니다."
        )

with tab1:
    st.plotly_chart(charts.ranking_bar(ranking_df), use_container_width=True)
    st.caption(
        "위에서부터 우선순위 순(유동인구 많은 순)이며, 막대 길이는 야간(20~04시) 승하차 인원 비율입니다."
    )

    display_df = ranking_df[["station_nm", "line_nm", "use_mm", "night_ratio"]].rename(
        columns={
            "station_nm": "역",
            "line_nm": "호선",
            "use_mm": "기준월",
            "night_ratio": "야간이용률",
        }
    )
    display_df["야간이용률"] = display_df["야간이용률"] * 100
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "야간이용률": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.download_button(
        "CSV로 다운로드",
        display_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"station_ranking_{use_mm}.csv",
    )

with tab2:
    hourly_df = repository.load_hourly_for_month(use_mm)
    top_stations = set(ranking_df["station_nm"])
    if hourly_df.empty:
        st.info("표시할 시간대 데이터가 없습니다.")
    else:
        hourly_df = hourly_df[hourly_df["station_nm"].isin(top_stations)]
        st.plotly_chart(charts.station_hour_heatmap(hourly_df), use_container_width=True)

with tab3:
    station_list = repository.load_station_list()
    if station_list.empty:
        st.info("표시할 역이 없습니다.")
    else:
        labels = dict(zip(station_list["station_nm"], station_list["line_nm"]))
        choice = st.selectbox(
            "역 선택", station_list["station_nm"].tolist(),
            format_func=lambda s: f"{s} ({labels.get(s, '')})",
        )
        trend_df = repository.load_station_trend(choice)
        if len(trend_df) < 2:
            st.info("추이를 그리려면 2개월 이상의 데이터가 필요합니다.")
        else:
            st.plotly_chart(charts.trend_line(trend_df), use_container_width=True)

        hourly_one = repository.load_station_hourly(choice, use_mm)
        if not hourly_one.empty:
            st.plotly_chart(charts.hourly_line(hourly_one), use_container_width=True)
