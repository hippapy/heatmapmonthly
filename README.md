# 섹터 로테이션 히트맵 (GICS 근사 19개 세부업종 월별 수익률)

국내 상장 종목을 19개 세부업종(GICS Sub-Industry 근사 커버리지)으로 나누어 월별 수익률을
히트맵으로 시각화하는 대시보드. 원본 요구사항은 PRD(요청 메시지) 참고.

## 파일 구성

| 경로 | 설명 |
|---|---|
| `sector_heatmap.html` | 단일 파일 대시보드 (외부 의존성 없음, 오프라인 열람 가능) |
| `data/sector_monthly_returns.json` | 대시보드가 읽는 데이터. 현재는 **샘플(합성) 데이터**임 |
| `scripts/sector_index_mapping.py` | 19개 세부업종 ↔ KRX 지수/종목 바스켓 매핑 설정 |
| `scripts/fetch_sector_data.py` | pykrx로 실데이터를 수집해 위 JSON을 생성하는 배치 스크립트 |

## ⚠ 현재 상태: 실데이터 미연동 (샘플 데이터로 동작)

이 작업이 실행된 샌드박스 환경은 아웃바운드 네트워크가 허용 목록(GitHub, PyPI, npm 등) 기반으로
제한되어 있고, `data.krx.co.kr`은 그 목록에 없어 직접 접근이 차단된다
(`curl data.krx.co.kr` → 프록시에서 403 / connect_rejected). pykrx는 내부적으로 KRX 정보데이터시스템을
스크래핑하므로 이 환경에서는 설치는 되어도 실제 데이터 수집이 불가능하다.

그래서 `data/sector_monthly_returns.json`은 **19개 섹터 × 30개월 형태와 스키마는 실데이터와 동일하지만
값 자체는 랜덤 시드로 생성한 합성 데이터**이며, 대시보드 상단에 "샘플 데이터" 배너로 항상 표시된다
(`meta.is_sample: true`). 섹터 로테이션 내러티브(반도체 강세 → 방산 강세 → 2차전지 강세 구간)를
일부러 흉내 내어 히트맵 기능이 어떻게 보이는지 확인할 수 있게 했을 뿐, 실제 시장 수익률이 아니다.

### 실데이터로 교체하는 방법 (택1)

**A. KRX 접근이 가능한 환경(로컬 PC, 사내 서버 등)에서 pykrx 자동 수집**

```bash
pip install pykrx pandas
python scripts/fetch_sector_data.py --start 2024-01-01 --end 2026-06-30 \
    --out data/sector_monthly_returns.json
```

**B. 토스증권 Open API로 자동 수집 (권장 — IP 화이트리스트가 걸린 로컬 환경에서 실행)**

토스증권 Open API의 공식 스펙(`/api/v1/candles`, Market Data 그룹)을 확인해 스크립트로 만들어 뒀다.
이 엔드포인트는 계좌 연동이 필요 없는 읽기 전용 API지만, 발급받은 클라이언트(API Key/Secret Key)에
IP 화이트리스트가 걸려 있으므로 **그 IP가 등록된 로컬 환경에서 실행해야 한다** (이 리포지토리를
다루는 샌드박스에서는 실행 불가).

```bash
pip install requests
export TOSS_CLIENT_ID=발급받은_API_Key       # 절대 코드/커밋에 넣지 말 것
export TOSS_CLIENT_SECRET=발급받은_Secret_Key
python scripts/fetch_toss_data.py --since 2023-12-01 --out data/sector_monthly_returns.json
```

- `/api/v1/candles`는 월봉을 지원하지 않아(`interval`이 `1m`/`1d`만 가능) 일봉을 받아 각 월의
  마지막 거래일 종가를 직접 뽑아 월간 수익률을 계산한다. 한 번에 최대 200개 봉만 오므로
  종목당 여러 번 페이지네이션(`before` 파라미터)한다.
- `scripts/sector_index_mapping.py`의 `SECTOR_TOSS_SYMBOL`에 4개 세부업종(반도체·2차전지·
  방위산업·은행)만 티커가 채워져 있다. 나머지 15개는 `None`이라 건너뛰고 `null`로 남는다 —
  같은 파일의 `TOSS_SEARCH_HINTS` 키워드로 토스 앱에서 검색해 티커를 채워 넣으면 그 섹터도
  수집된다.
- **경고**: 이 API의 `/api/v1/orders` 등 Order 그룹은 실제 매매를 실행하는 엔드포인트다.
  `fetch_toss_data.py`는 Market Data(조회)만 호출하며 주문 관련 코드는 전혀 포함하지 않는다.

**C. 토스증권 앱/API에서 사람이 직접 값을 가져와 입력 (자동화 없이 수동으로)**

1. `scripts/toss_data_template.csv`를 연다. 19개 세부업종 행이 있고, `ticker`/`instrument_name`
   컬럼에 이미 확인된 4개 섹터(반도체·2차전지·방위산업·은행)의 대표 ETF가 채워져 있다.
   나머지 15개는 `scripts/sector_index_mapping.py`의 `TOSS_SEARCH_HINTS`에 있는 키워드로
   토스증권 앱에서 검색해 가장 순자산(AUM)이 큰 섹터 ETF를 골라 `ticker`/`instrument_name`을 채운다.
   (적당한 ETF가 없는 섹터는 비워두면 해당 섹터만 `null`로 남고 나머지는 정상 렌더링된다.)
2. 각 행의 `data_type`을 고른다:
   - `return`: 토스에서 월간 수익률(%)을 바로 확인할 수 있으면 2024-01~2026-06 30칸에 그 값을 입력.
   - `price`: 월말 종가/기준가만 확인 가능하면 `baseline_2023-12_price`(2023-12월말 값)와
     2024-01~2026-06 각 월말 값을 채운다. 등락률은 스크립트가 자동 계산한다.
3. 저장 후 실행:
   ```bash
   python scripts/import_toss_data.py --in scripts/toss_data_template.csv \
       --out data/sector_monthly_returns.json
   ```

두 방법 모두 실행되면 `meta.is_sample`이 `false`가 되고(B는 비어있는 섹터가 있으면 `true`로 남아
일부 데이터만 채워졌음을 표시), 대시보드를 새로고침하면 샘플 배너가 사라지며 실데이터로
렌더링된다. HTML은 수정할 필요 없다.

## 데이터 수집 전략 (Track A / Track B)

PRD 4.4에서 정리한 3-트랙 전략 중 비용이 들지 않는 A/B 두 트랙을 구현했다.

- **Track A (공식 지수)**: `pykrx.stock.get_index_ticker_list()`로 KRX/KOSPI/KOSDAQ/테마 지수 전체 목록을
  가져와 세부업종 키워드와 매칭 (반도체, 2차전지, 은행, 증권, 철강, 에너지화학, 자동차, 건설/기계장비 등).
  지수 자체가 시총가중으로 이미 산출되어 있으므로 월말 종가만 받아 전월 대비 수익률을 계산.
- **Track B (자체 시총가중 지수)**: Track A에 대응 지수가 없는 업종(반도체장비/소재, 전력기기, 화장품,
  방위산업, 조선, 제약, 바이오텍, 인터넷/포털, 게임, 통신서비스, 전력유틸리티)은 대표종목 바스켓을
  `scripts/sector_index_mapping.py`에 curated 리스트로 정의해 두고, 종목별 일별 시가총액을 합산한
  합성 지수로 근사.
- Track C(FnGuide/WISEfn 유료 구독을 통한 정밀 GICS 매핑)는 예산 결정 사항이라 구현하지 않음.

**주의**: Track B 바스켓 티커는 초기 프로토타이핑용으로 사람이 curated한 리스트이며 실거래 데이터로
검증되지 않았다. 운영에 투입하기 전 KRX "업종분류현황" 공식 다운로드로 종목 구성을 재검증할 것
(`scripts/sector_index_mapping.py` 상단 주석 참고). 또한 PRD 리스크 항목대로 KOSDAQ 쪽 일부 세부지수가
2024-07-01부로 산출 중단된 이력이 있어 Track A 매칭이 비거나 부정확할 수 있으니, 스크립트 실행 로그의
"Track A 매칭: ..." 출력을 반드시 확인해 실제 어떤 지수가 붙었는지 확인해야 한다.

## 시도했던 우회 경로: ETF 프록시 + 웹서치 (2026-07-03)

KRX 직접 접근(pykrx)과 Agent Store `capital-markets` 서브서비스가 모두 막힌 상태라, 사용자 요청으로
"ETF 섹터분석" 등 KRX를 거치지 않는 보조 경로를 시도했다. 결과:

- `WebSearch`는 정상 동작해서 실제 섹터 ETF 상품/티커 일부를 확인할 수 있었다 (예: KODEX 반도체
  091160, TIGER 반도체 091230, TIGER Fn반도체TOP10 396500, KODEX 2차전지산업 305720,
  SOL K방산 490480 — `scripts/sector_index_mapping.py`의 `TRACK_D_ETF_PROXY`에 반영).
- 그러나 `WebFetch`로 실제 가격 데이터가 있는 페이지에 접근하는 것은 전부 실패했다 — Naver Finance
  (자체 차단), Yahoo Finance(403), 삼성자산운용 KODEX 상품 페이지(403), Investing.com(403),
  WiseReport(403), Stooq(403). 즉 티커는 찾을 수 있어도 실제 30개월 가격 시계열을 이 세션에서
  가져올 방법은 없었다.

결론적으로 이 세션에서 시도 가능했던 3개 경로(① pykrx 직접 접근, ② Agent Store capital-markets,
③ WebFetch를 통한 ETF 가격 스크래핑) 모두 막혀 있어, **실데이터 수집은 이 세션 환경의 한계로
완료하지 못했다.** `TRACK_D_ETF_PROXY`에 확인된 티커는 4개 세부업종(반도체·2차전지·방위산업·은행)
뿐이며, 나머지 15개는 상품이 존재할 가능성은 높지만 이번 세션에서 코드를 확인하지 못했다.

## 원클릭 자동화 (CMD 없이 더블클릭 → 수집 → 자동 게시)

매번 명령어를 치지 않도록 `run_and_publish.bat` 하나로 **데이터 수집 → git 커밋/푸시 →
GitHub Pages 공개 대시보드 자동 갱신**까지 끝나게 구성했다.

### 최초 1회 설정
1. **저장소 clone** (자동 push를 위해 반드시 git 저장소 안에서 실행해야 함)
   ```bash
   git clone https://github.com/hippapy/heatmapmonthly.git
   cd heatmapmonthly
   ```
2. **GitHub Pages 켜기**: GitHub 저장소 → Settings → Pages → Build and deployment →
   Source를 **GitHub Actions**로 선택. (`.github/workflows/pages.yml`이 자동 배포함)
3. **git 로그인**: 처음 `git push` 시 브라우저로 GitHub 로그인 1회 (이후 캐시됨).

### 매번 (더블클릭 한 번)
- `run_and_publish.bat` 더블클릭
  - 처음 실행 시 토스 API Key/Secret을 한 번 물어보고 `toss_secret.txt`에 저장
    (이 파일은 `.gitignore`로 커밋 제외 — 절대 저장소에 올라가지 않음)
  - 데이터 수집 → `data/sector_monthly_returns.json` 갱신 → 변경분만 자동 커밋/푸시
  - 1~2분 뒤 **https://hippapy.github.io/heatmapmonthly/** 가 자동 갱신됨 (로그인 불필요, 공개)

> IP 화이트리스트가 걸린 PC에서 실행해야 하며, 자동 실행(매월 말)을 원하면 이 배치파일을
> Windows 작업 스케줄러에 등록하면 된다 (PC가 켜져 있어야 함).

## 데이터 스키마

```json
{
  "meta": {
    "period": {"start": "2024-01", "end": "2026-06"},
    "return_definition": "월말 종가 기준 전월 대비 수익률",
    "source": "...",
    "as_of": "YYYY-MM-DD",
    "is_sample": true
  },
  "sectors": [{"id": "semis", "name_kr": "반도체", "name_en": "...", "color": "hsl(0 65% 55%)"}],
  "months": ["2024-01", "...", "2026-06"],
  "returns": {"semis": {"2024-01": 3.2, "2024-02": null}}
}
```

`sectors` 배열의 `id`/순서는 `sector_heatmap.html`과 `scripts/sector_index_mapping.py` 양쪽에서
동일하게 유지해야 필터·정렬·색상 로직이 깨지지 않는다.

## 대시보드 기능 (Acceptance Criteria 대응)

- [x] 19개 세부업종이 색상환 균등 분배로 고유 색상 표시 (hue = i × 360/19)
- [x] 2024-01 ~ 2026-06 30개월 컬럼, 가로 스크롤
- [x] 정렬 기준월 드롭다운 선택 시 해당 월 수익률 내림차순 재정렬 (기본값: 전체 기간 평균)
- [x] 섹터 체크박스로 필터링, 미선택 섹터는 회색조(grayscale) 다운플레이
- [x] 각 셀에 수익률(%)과 해당월 순위(1~19위, 필터와 무관하게 시장 전체 기준) 표기
- [x] CSV 내보내기가 현재 필터/정렬 상태 반영
- [x] 데이터 출처와 기준일 화면 하단에 표시, 샘플 데이터일 경우 상단 배너로 명시
- [ ] **실데이터 연동은 미완료** — 위 "현재 상태" 섹션 참고, 네트워크 접근 가능한 환경에서
      `scripts/fetch_sector_data.py` 실행 필요

## 색상 인코딩 설계 노트

19개라는 카테고리 수는 일반적인 색맹 안전성 기준(인접 hue 쌍 분리도)을 통과하기 어려운 수준이다.
그래서 색만으로 정체성을 구분하지 않도록 (1) 모든 셀에 수익률 숫자를 항상 표기하고, (2) 순위 뱃지를
같이 표기하고, (3) 좌측 필터 패널에 범례(색상 점 + 이름)를 항상 노출하는 방식으로 색-only 인코딩을
피했다. 마이너스 수익률은 hue를 바꾸지 않고 대각선 사선 패턴으로만 구분해 "섹터 고유색 일관성"이라는
PRD 요구사항(6.2)을 지켰다.

## 마일스톤 상태

| 단계 | 상태 |
|---|---|
| M1 (매핑 테이블, pykrx 검증) | 매핑 테이블 작성 완료 / pykrx 실데이터 검증은 네트워크 제약으로 **미완료** |
| M2 (수익률 계산 로직 + JSON 스키마) | 완료 (샘플 데이터로 스키마 검증됨) |
| M3 (HTML 히트맵 실데이터 연동) | HTML 완료, **실데이터 연동은 대기 중** |
| M4 (자동 갱신 + CSV export) | CSV export 완료 / cron 자동화는 미구현 (운영 환경에서 `fetch_sector_data.py`를 월말 cron으로 등록) |
