-- raw -> mart 집계 (수집기 실행 후 매번 재실행)
-- 실행: mysql -u root -p mini_project2 < db/build_mart.sql
-- 야간시간대 정의: 20,21,22,23,0,1,2,3,4시 (collector/config.py의 NIGHT_HOURS와 동일하게 유지할 것)

USE mini_project2;

-- ① mart_station_hourly
INSERT INTO mart_station_hourly (station_nm, use_mm, hour, line_nm, get_on_cnt, get_off_cnt, total_cnt)
SELECT station_nm, use_mm, hour, line_nm, get_on_cnt, get_off_cnt, get_on_cnt + get_off_cnt
FROM subway_hourly_raw
ON DUPLICATE KEY UPDATE
    line_nm     = VALUES(line_nm),
    get_on_cnt  = VALUES(get_on_cnt),
    get_off_cnt = VALUES(get_off_cnt),
    total_cnt   = VALUES(total_cnt);

-- ② mart_station_monthly (야간이용률 = 로드맵 핵심 지표)
INSERT INTO mart_station_monthly (station_nm, use_mm, line_nm, total_ridership, night_ridership, night_ratio, adstrd_code)
SELECT
    r.station_nm,
    r.use_mm,
    MAX(r.line_nm) AS line_nm,
    SUM(r.get_on_cnt + r.get_off_cnt) AS total_ridership,
    SUM(CASE WHEN r.hour IN (20,21,22,23,0,1,2,3,4) THEN r.get_on_cnt + r.get_off_cnt ELSE 0 END) AS night_ridership,
    SUM(CASE WHEN r.hour IN (20,21,22,23,0,1,2,3,4) THEN r.get_on_cnt + r.get_off_cnt ELSE 0 END)
        / NULLIF(SUM(r.get_on_cnt + r.get_off_cnt), 0) AS night_ratio,
    d.adstrd_code
FROM subway_hourly_raw r
LEFT JOIN dim_station d
    ON d.station_nm = r.station_nm
GROUP BY r.station_nm, r.use_mm, d.adstrd_code
ON DUPLICATE KEY UPDATE
    line_nm         = VALUES(line_nm),
    total_ridership = VALUES(total_ridership),
    night_ridership = VALUES(night_ridership),
    night_ratio     = VALUES(night_ratio),
    adstrd_code     = VALUES(adstrd_code);

-- ③ mart_dong_monthly (living_pop_raw는 집계구 단위 -> 행정동으로 합산 후 월 평균)
INSERT INTO mart_dong_monthly (adstrd_code, base_ym, avg_daily_pop, night_avg_pop, day_avg_pop, night_ratio)
SELECT
    adstrd_code,
    LEFT(base_date, 6) AS base_ym,
    AVG(dong_pop) AS avg_daily_pop,
    AVG(CASE WHEN hour IN (20,21,22,23,0,1,2,3,4) THEN dong_pop END) AS night_avg_pop,
    AVG(CASE WHEN hour NOT IN (20,21,22,23,0,1,2,3,4) THEN dong_pop END) AS day_avg_pop,
    AVG(CASE WHEN hour IN (20,21,22,23,0,1,2,3,4) THEN dong_pop END) / NULLIF(AVG(dong_pop), 0) AS night_ratio
FROM (
    SELECT adstrd_code, base_date, hour, SUM(total_pop) AS dong_pop
    FROM living_pop_raw
    GROUP BY adstrd_code, base_date, hour
) hourly_dong
GROUP BY adstrd_code, LEFT(base_date, 6)
ON DUPLICATE KEY UPDATE
    avg_daily_pop = VALUES(avg_daily_pop),
    night_avg_pop = VALUES(night_avg_pop),
    day_avg_pop   = VALUES(day_avg_pop),
    night_ratio   = VALUES(night_ratio);
