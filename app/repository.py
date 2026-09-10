"""DB 조회 전용 (SELECT only). collector/는 절대 import하지 않는다."""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "mini_project2")


@st.cache_resource
def get_engine():
    url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=3600)
def load_available_months() -> list:
    engine = get_engine()
    df = pd.read_sql(text("SELECT DISTINCT use_mm FROM mart_station_monthly ORDER BY use_mm"), engine)
    return df["use_mm"].tolist()


# 방향성: "야간 이용률이 높은 역 중 유동인구까지 많은 역"을 특별 관리 대상으로 고른다.
# 야간이용률 상위 (1 - NIGHT_QUANTILE) 구간만 후보로 남기고, 그 안에서 유동인구 순으로 세운다.
NIGHT_QUANTILE = 0.90


@st.cache_data(ttl=3600)
def load_station_ranking(
    use_mm: str, top_n: int = 15, min_ridership: int = 0, night_quantile: float = NIGHT_QUANTILE
) -> pd.DataFrame:
    """우선순위 순(유동인구 많은 순)으로 정렬된 후보 역을 반환.

    1) 월 승하차가 min_ridership 미만인 역은 비율이 튀므로 제외
    2) 남은 역 중 야간이용률 상위 구간만 후보로 추림
    3) 배후 행정동 유동인구가 많은 순으로 정렬 (유동인구가 없는 역은 순위에서 제외)
    """
    query = text(
        """
        SELECT m.station_nm, m.line_nm, m.use_mm, m.total_ridership, m.night_ridership,
               m.night_ratio, m.adstrd_code, d.avg_daily_pop AS dong_avg_pop
        FROM mart_station_monthly m
        LEFT JOIN mart_dong_monthly d
               ON d.adstrd_code = m.adstrd_code AND d.base_ym = m.use_mm
        WHERE m.use_mm = :use_mm
          AND m.total_ridership >= :min_ridership
        """
    )
    df = pd.read_sql(
        query, get_engine(), params={"use_mm": use_mm, "min_ridership": min_ridership}
    )
    if df.empty:
        return df

    threshold = df["night_ratio"].quantile(night_quantile)
    candidates = df[df["night_ratio"] >= threshold]
    ranked = candidates.dropna(subset=["dong_avg_pop"]).sort_values(
        "dong_avg_pop", ascending=False
    )
    return ranked.head(top_n).reset_index(drop=True)


@st.cache_data(ttl=3600)
def load_night_threshold(use_mm: str, min_ridership: int = 0, night_quantile: float = NIGHT_QUANTILE):
    """(야간이용률 하한, 후보 역 수, 유동인구까지 있어 실제 순위에 오를 수 있는 역 수).

    유동인구가 연결되지 않은 역(서울 밖 구간 등)은 후보에는 들어가도 순위에는 오르지 못하므로
    화면 설명에서 두 숫자를 구분해서 보여준다.
    """
    query = text(
        """
        SELECT m.night_ratio, d.avg_daily_pop
        FROM mart_station_monthly m
        LEFT JOIN mart_dong_monthly d
               ON d.adstrd_code = m.adstrd_code AND d.base_ym = m.use_mm
        WHERE m.use_mm = :use_mm AND m.total_ridership >= :min_ridership
        """
    )
    df = pd.read_sql(
        query, get_engine(), params={"use_mm": use_mm, "min_ridership": min_ridership}
    )
    if df.empty:
        return None, 0, 0
    threshold = df["night_ratio"].quantile(night_quantile)
    candidates = df[df["night_ratio"] >= threshold]
    return threshold, len(candidates), int(candidates["avg_daily_pop"].notna().sum())


@st.cache_data(ttl=3600)
def load_hourly_for_month(use_mm: str) -> pd.DataFrame:
    query = text(
        """
        SELECT line_nm, station_nm, hour, get_on_cnt, get_off_cnt, total_cnt
        FROM mart_station_hourly
        WHERE use_mm = :use_mm
        ORDER BY line_nm, station_nm, hour
        """
    )
    return pd.read_sql(query, get_engine(), params={"use_mm": use_mm})


@st.cache_data(ttl=3600)
def load_station_hourly(station_nm: str, use_mm: str) -> pd.DataFrame:
    query = text(
        """
        SELECT hour, get_on_cnt, get_off_cnt, total_cnt
        FROM mart_station_hourly
        WHERE station_nm = :station_nm AND use_mm = :use_mm
        ORDER BY hour
        """
    )
    return pd.read_sql(query, get_engine(), params={"station_nm": station_nm, "use_mm": use_mm})


@st.cache_data(ttl=3600)
def load_station_trend(station_nm: str) -> pd.DataFrame:
    query = text(
        """
        SELECT use_mm, total_ridership, night_ridership, night_ratio
        FROM mart_station_monthly
        WHERE station_nm = :station_nm
        ORDER BY use_mm
        """
    )
    return pd.read_sql(query, get_engine(), params={"station_nm": station_nm})


@st.cache_data(ttl=3600)
def load_station_list() -> pd.DataFrame:
    query = text(
        "SELECT station_nm, MAX(line_nm) AS line_nm FROM mart_station_monthly "
        "GROUP BY station_nm ORDER BY station_nm"
    )
    return pd.read_sql(query, get_engine())
