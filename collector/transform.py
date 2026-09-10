"""API 원본 응답 -> DB 적재용 레코드(dict list) 변환."""
import logging

import pandas as pd

logger = logging.getLogger(__name__)

HOURS = list(range(24))


def transform_subway_rows(raw_rows: list[dict]) -> list[dict]:
    """CardSubwayTime의 wide(시간대 48컬럼) 응답을 long 레코드로 펼친 뒤 역 단위로 합친다.

    - 환승역은 호선별로 따로 내려온다(예: 홍대입구 = 2호선 / 경의선 / 공항철도 1호선).
      역 단위 야간이용률이 목적이므로 승하차를 합산하고 line_nm은 공백으로 이어붙인다.
    - 일부 월은 원본이 같은 행을 두 번 내려주므로(예: 202607) 합치기 전에 중복을 제거한다.
    """
    records = []
    for row in raw_rows:
        use_mm = row["USE_MM"]
        line_nm = row["SBWY_ROUT_LN_NM"]
        station_nm = row["STTN"]
        job_ymd = row.get("JOB_YMD")
        for hour in HOURS:
            get_on = row.get(f"HR_{hour}_GET_ON_NOPE")
            get_off = row.get(f"HR_{hour}_GET_OFF_NOPE")
            if get_on is None or get_off is None:
                continue
            records.append(
                {
                    "use_mm": use_mm,
                    "line_nm": line_nm,
                    "station_nm": station_nm,
                    "hour": hour,
                    "get_on_cnt": int(float(get_on)),
                    "get_off_cnt": int(float(get_off)),
                    "job_ymd": job_ymd,
                }
            )
    if not records:
        return []

    df = pd.DataFrame(records)

    before = len(df)
    df = df.drop_duplicates(subset=["use_mm", "line_nm", "station_nm", "hour"])
    if len(df) < before:
        logger.warning(
            "원본 중복 %d건 제거 (API가 같은 역/시간대를 중복 제공)", before - len(df)
        )

    merged = (
        df.sort_values(["use_mm", "station_nm", "hour", "line_nm"])
        .groupby(["use_mm", "station_nm", "hour"], as_index=False)
        .agg(
            # dict.fromkeys: 순서 유지하면서 중복 호선명 제거
            line_nm=("line_nm", lambda s: " ".join(dict.fromkeys(s))),
            get_on_cnt=("get_on_cnt", "sum"),
            get_off_cnt=("get_off_cnt", "sum"),
            job_ymd=("job_ymd", "max"),
        )
    )

    # pymysql이 numpy 정수형을 처리하지 못하므로 파이썬 int로 변환
    for col in ("hour", "get_on_cnt", "get_off_cnt"):
        merged[col] = merged[col].astype("int64").map(int)
    merged = merged.astype(object).where(pd.notna(merged), None)

    return merged.to_dict("records")


def transform_living_pop_rows(raw_rows: list[dict]) -> list[dict]:
    """ppsLocalResd 응답을 (base_date, hour, adstrd_code, oa_code, total_pop) 레코드로 변환."""
    records = []
    for row in raw_rows:
        records.append(
            {
                "base_date": row["STDR_DE_ID"],
                "hour": int(row["TMZON_PD_SE"]),
                "adstrd_code": row["ADSTRD_CODE_SE"],
                "oa_code": row["OA_CD"],
                "total_pop": float(row["TOT_LVPOP_CO"]),
            }
        )
    return records
