-- 서울 지하철 야간 이용률 x 유동인구 대시보드 스키마 (MariaDB)
-- 실행: mysql -u root -p < db/schema.sql

CREATE DATABASE IF NOT EXISTS mini_project2 DEFAULT CHARACTER SET utf8mb4;
USE mini_project2;

-- ============================================================
-- 원본 계층 (수집기가 적재, 최소 정제)
-- ============================================================

-- CardSubwayTime API: 1행 = 1역 x 1개월 x 1시간대
-- (API 원본은 호선별 wide 형태. transform.py가 long으로 펼친 뒤 환승역을 역 단위로 합산해 적재)
CREATE TABLE IF NOT EXISTS subway_hourly_raw (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    use_mm        CHAR(6)      NOT NULL,   -- 사용월 'YYYYMM'
    line_nm       VARCHAR(100) NOT NULL,   -- 호선명. 환승역은 여러 호선을 공백으로 이어붙임
    station_nm    VARCHAR(30)  NOT NULL,   -- 역명
    hour          TINYINT      NOT NULL,   -- 0~23
    get_on_cnt    INT          NOT NULL,   -- 승차인원
    get_off_cnt   INT          NOT NULL,   -- 하차인원
    job_ymd       CHAR(8),                 -- API 작업일자
    collected_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 그레인: 1행 = 1역 x 1개월 x 1시간대 (환승역은 호선 합산되므로 line_nm은 키가 아님)
    UNIQUE KEY uk_subway_hourly (use_mm, station_nm, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ppsLocalResd API: 1행 = 1기준일 x 1시간대 x 1집계구(OA_CD)
CREATE TABLE IF NOT EXISTS living_pop_raw (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    base_date     CHAR(8)      NOT NULL,   -- STDR_DE_ID, 'YYYYMMDD'
    hour          TINYINT      NOT NULL,   -- TMZON_PD_SE, 0~23
    adstrd_code   CHAR(8)      NOT NULL,   -- ADSTRD_CODE_SE, 행정동코드(8자리)
    oa_code       VARCHAR(20)  NOT NULL,   -- OA_CD, 집계구코드
    total_pop     DOUBLE       NOT NULL,   -- TOT_LVPOP_CO, 추계값이라 소수점
    collected_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_living_pop (base_date, hour, oa_code),
    -- 인덱스를 테이블 정의에 포함해야 schema.sql을 여러 번 실행해도 안전하다.
    KEY idx_living_pop_dong_date (adstrd_code, base_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 매핑 계층 (수동 관리 — CardSubwayTime에는 행정동코드가 없어 직접 채워야 함)
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_station (
    station_nm   VARCHAR(30) NOT NULL,   -- API 표기 그대로 ('역' 접미사 없음: 홍대입구, 강남)
    adstrd_code  CHAR(8)     NOT NULL,   -- 역이 속한 행정동코드(8자리)
                                        -- 행정표준코드 10자리가 아니라 그 앞 8자리다
    adstrd_nm    VARCHAR(30),           -- 행정동명 (참고용)
    PRIMARY KEY (station_nm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 마트 계층 (대시보드 조회 전용, build_mart.sql로 생성/갱신)
-- ============================================================

-- 메인: 역 x 월 야간이용률 요약 (로드맵 핵심 산출물)
CREATE TABLE IF NOT EXISTS mart_station_monthly (
    station_nm       VARCHAR(30) NOT NULL,
    use_mm           CHAR(6)     NOT NULL,
    line_nm          VARCHAR(100) NOT NULL,  -- 표시용(환승역은 공백으로 이어붙인 호선 목록)
    total_ridership  BIGINT      NOT NULL,  -- 월 전체 승하차 합
    night_ridership  BIGINT      NOT NULL,  -- 야간시간대 승하차 합 (20~04시)
    night_ratio      DOUBLE      NOT NULL,  -- night_ridership / total_ridership
    adstrd_code      CHAR(8),               -- dim_station 매핑 결과 (없으면 NULL)
    PRIMARY KEY (station_nm, use_mm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 드릴다운: 역 x 월 x 시간대 (히트맵/시간대 차트용)
CREATE TABLE IF NOT EXISTS mart_station_hourly (
    station_nm   VARCHAR(30) NOT NULL,
    use_mm       CHAR(6)     NOT NULL,
    hour         TINYINT     NOT NULL,
    line_nm      VARCHAR(100) NOT NULL,
    get_on_cnt   INT         NOT NULL,
    get_off_cnt  INT         NOT NULL,
    total_cnt    INT         NOT NULL,
    PRIMARY KEY (station_nm, use_mm, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 행정동 x 월 유동인구 요약 (역-행정동 매핑된 역의 배후 유동인구 비교용)
CREATE TABLE IF NOT EXISTS mart_dong_monthly (
    adstrd_code    CHAR(8)  NOT NULL,
    base_ym        CHAR(6)  NOT NULL,
    avg_daily_pop  DOUBLE,   -- 월 평균 유동인구 (모든 시간대 샘플 평균)
    night_avg_pop  DOUBLE,   -- 야간시간대(20~04시) 평균 유동인구
    day_avg_pop    DOUBLE,   -- 주간시간대 평균 유동인구
    night_ratio    DOUBLE,   -- night_avg_pop / avg_daily_pop
    PRIMARY KEY (adstrd_code, base_ym)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
