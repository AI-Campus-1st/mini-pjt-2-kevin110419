"""MariaDB 적재 (UPSERT). DB 쓰기는 이 모듈만 담당한다."""
import pymysql

from . import config


def get_connection():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        autocommit=False,
    )


def load_subway_hourly(records: list[dict]) -> int:
    if not records:
        return 0
    sql = """
        INSERT INTO subway_hourly_raw (use_mm, line_nm, station_nm, hour, get_on_cnt, get_off_cnt, job_ymd)
        VALUES (%(use_mm)s, %(line_nm)s, %(station_nm)s, %(hour)s, %(get_on_cnt)s, %(get_off_cnt)s, %(job_ymd)s)
        ON DUPLICATE KEY UPDATE
            line_nm = VALUES(line_nm),
            get_on_cnt = VALUES(get_on_cnt),
            get_off_cnt = VALUES(get_off_cnt),
            job_ymd = VALUES(job_ymd)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        return len(records)
    finally:
        conn.close()


def load_living_pop(records: list[dict]) -> int:
    if not records:
        return 0
    sql = """
        INSERT INTO living_pop_raw (base_date, hour, adstrd_code, oa_code, total_pop)
        VALUES (%(base_date)s, %(hour)s, %(adstrd_code)s, %(oa_code)s, %(total_pop)s)
        ON DUPLICATE KEY UPDATE
            total_pop = VALUES(total_pop)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        return len(records)
    finally:
        conn.close()


def load_dim_station(records: list[dict]) -> int:
    if not records:
        return 0
    sql = """
        INSERT INTO dim_station (station_nm, adstrd_code, adstrd_nm)
        VALUES (%(station_nm)s, %(adstrd_code)s, %(adstrd_nm)s)
        ON DUPLICATE KEY UPDATE
            adstrd_code = VALUES(adstrd_code),
            adstrd_nm = VALUES(adstrd_nm)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        return len(records)
    finally:
        conn.close()
