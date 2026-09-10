# DB 스키마 문서

`collector/`와 `app/`이 공유하는 유일한 접점입니다. 컬럼을 바꾸기 전에 양쪽 다 확인하세요.

## 원본 계층

### subway_hourly_raw
- **출처**: 서울 열린데이터광장 `CardSubwayTime`
- **그레인**: 1행 = 1역 x 1개월(`use_mm`) x 1시간대(`hour`, 0~23)
- **비고**: API 원본은 호선별로 1행씩, 시간대 48개 컬럼이 wide로 붙어있음. `collector/transform.py`가 long으로 펼친 뒤 **환승역을 역 단위로 합산**한다(승하차는 더하고 `line_nm`은 공백으로 이어붙임: `2호선 경의선 공항철도 1호선`).
- 일부 월(예: 202607)은 원본이 같은 행을 2번 내려주므로 정제 단계에서 중복을 제거한다.
- **갱신 주기**: API 자체가 매월 5일 전월 데이터 갱신. 수집기는 필요한 `use_mm` 목록을 돌며 매번 UPSERT.
- **행정동코드 없음** — 역명/호선명만 존재. 지역 조인은 `dim_station`을 거쳐야 함.

### living_pop_raw
- **출처**: 서울 열린데이터광장 `ppsLocalResd` (집계구 단위 생활인구, 내국인)
- **그레인**: 1행 = 1기준일(`base_date`) x 1시간대(`hour`) x 1집계구(`oa_code`)
- **비고**: 집계구(`oa_code`)는 행정동(`adstrd_code`)보다 세밀한 단위. 같은 행정동에 여러 집계구가 속함 -> 마트 생성 시 행정동 단위로 `SUM`.
- **주의**: 응답에 포함된 성별x15개 연령대 컬럼은 이번 프로젝트 범위(야간 이용률 우선순위)에서는 사용하지 않아 `total_pop`(총생활인구수)만 저장. 연령대 분석이 필요해지면 컬럼 추가.

## 매핑 계층

### dim_station (자동 생성)
- **목적**: `subway_hourly_raw`(역명 기준)와 `living_pop_raw`(행정동 기준)를 연결하는 유일한 다리.
- **`collector/dim_station.py`가 자동으로 채운다** (`python -m collector` 시 함께 실행, 또는 `python -m collector.dim_station` 단독 실행).
  1. `subwayStationMaster` API에서 역별 위경도(LAT/LOT)를 받는다. 역명 표기가 `CardSubwayTime`과 동일해 그대로 조인된다.
  2. 행정동 경계 GeoJSON(`config.ADM_BOUNDARY_URL`, 최초 1회 `data/raw/`에 캐시)과 point-in-polygon으로 대조한다.
  3. 서울 밖 역(7호선 인천 구간, 1호선 경기 구간 등)은 생활인구 데이터가 없으므로 매핑에서 빠진다.

#### 행정동코드 체계 (중요)
`living_pop_raw.adstrd_code`는 **8자리**(`11110515`)다. 10자리 행정표준코드를 넣으면 조인이 조용히 실패한다.
GeoJSON에서 맞는 필드는 `adm_cd`(통계청 코드, 424개 중 32개만 일치)가 **아니라** `adm_cd2`(행정표준코드 10자리)의 **앞 8자리**다(416/424 일치).

## 마트 계층 (대시보드 전용, `build_mart.sql`로 생성)

| 테이블 | 그레인 | 용도 |
|---|---|---|
| `mart_station_monthly` | 역 x 월 | 역 랭킹 탭 — 야간이용률(`night_ratio`) 기준 정렬의 메인 소스 |
| `mart_station_hourly` | 역 x 월 x 시간대 | 시간대 히트맵 탭 |
| `mart_dong_monthly` | 행정동 x 월 | 매핑된 역의 배후 유동인구와 야간이용률 비교 |

- **야간시간대 정의**: 20시~04시 (20, 21, 22, 23, 0, 1, 2, 3, 4시). `db/build_mart.sql`과 `collector/config.py`의 `NIGHT_HOURS`가 항상 같아야 함.
- **기준시점**: `use_mm`/`base_ym`은 데이터가 가리키는 연월이며 수집(적재) 시점이 아님.
- **갱신 방법**: `mart_*` 테이블은 항상 `raw` 테이블에서 재계산되는 파생 데이터. 원본이 갱신되면 `build_mart.sql`을 다시 실행하면 됨 (직접 UPDATE 금지).

## 실행 순서

```
mysql -u root -p < db/schema.sql          # DB/테이블 생성 (최초 1회)
python -m collector                       # 실 데이터 수집/적재
mysql -u root -p mini_project2 < db/build_mart.sql   # 마트 재생성 (수집 후 매번)
```
