"""
19개 세부업종 <-> KRX 데이터 소스 매핑 설정.

PRD 4.4의 3-트랙 전략 중 Track A(공식 지수)/Track B(자체 시총가중 지수) 배정표.
공식 GICS Sub-Industry 1:1 매핑이 아닌 실무 커버리지 기준 근사치이므로,
운영 전 KRX "업종분류현황" 다운로드로 최신 종목 구성을 검증/갱신할 것.

SECTORS 순서/ id는 sector_heatmap.html의 SECTORS와 반드시 동일하게 유지한다
(달라지면 필터/정렬 로직이 깨짐).
"""

SECTORS = [
    {"id": "semis", "name_kr": "반도체", "hue": 0},
    {"id": "semi_equip", "name_kr": "반도체장비/소재", "hue": 19},
    {"id": "battery", "name_kr": "2차전지/배터리", "hue": 38},
    {"id": "power_equip", "name_kr": "전력기기", "hue": 57},
    {"id": "cosmetics", "name_kr": "화장품", "hue": 76},
    {"id": "defense", "name_kr": "방위산업", "hue": 95},
    {"id": "shipbuilding", "name_kr": "조선", "hue": 114},
    {"id": "auto_parts", "name_kr": "자동차부품", "hue": 133},
    {"id": "steel", "name_kr": "철강", "hue": 152},
    {"id": "chemicals", "name_kr": "화학소재", "hue": 171},
    {"id": "banks", "name_kr": "은행", "hue": 189},
    {"id": "securities", "name_kr": "증권", "hue": 208},
    {"id": "pharma", "name_kr": "제약", "hue": 227},
    {"id": "biotech", "name_kr": "바이오텍", "hue": 246},
    {"id": "internet", "name_kr": "인터넷/포털", "hue": 265},
    {"id": "gaming", "name_kr": "게임", "hue": 284},
    {"id": "telecom", "name_kr": "통신서비스", "hue": 303},
    {"id": "power_utility", "name_kr": "전력유틸리티", "hue": 322},
    {"id": "construction_machinery", "name_kr": "건설/기계", "hue": 341},
]

# Track A: KRX/KOSPI/KOSDAQ/테마 공식 지수 이름에서 찾을 키워드.
# pykrx.stock.get_index_ticker_list(date, market)로 얻은 (ticker, name) 목록을
# 아래 키워드로 substring 매칭한다. 여러 개 매칭되면 첫 번째(가장 대표적인 것)를 사용.
# 값이 list인 경우 여러 지수를 시총가중 평균해 근사치로 합성한다(운영 전 검증 필요).
TRACK_A_KEYWORDS = {
    "semis": ["반도체"],
    "battery": ["2차전지"],
    "banks": ["은행"],
    "securities": ["증권"],
    "steel": ["철강"],
    "chemicals": ["에너지화학"],  # 근사치: 화학소재보다 넓은 범위(에너지 포함)
    "auto_parts": ["자동차"],  # 근사치: 완성차+부품 통합
    "construction_machinery": ["건설", "기계장비"],  # 두 지수 평균으로 근사
}

# Track B: Track A에 대응 지수가 없거나 근사 오차가 커서 개별종목 시총가중
# 자체지수로 계산하는 세부업종의 대표종목 바스켓 (KRX 6자리 코드).
# ** 주의: 아래 티커는 초기 프로토타이핑용 curated 리스트이며 실거래 검증 전임.
#    운영 투입 전 KRX "업종분류현황" 공식 다운로드로 재검증할 것. **
TRACK_B_BASKETS = {
    "semi_equip": ["042700", "240810", "036930", "095340", "131290"],
    "power_equip": ["267260", "010120", "034020", "052690", "001440"],
    "cosmetics": ["090430", "051900", "161890", "192820", "237880"],
    "defense": ["012450", "047810", "079550", "064350"],
    "shipbuilding": ["009540", "010140", "042660", "097230"],
    "pharma": ["000100", "185750", "128940", "069620", "006280"],
    "biotech": ["207940", "068270", "196170", "141080", "298380"],
    "internet": ["035420", "035720"],
    "gaming": ["036570", "251270", "293490", "112040", "263750"],
    "telecom": ["017670", "030200", "032640"],
    "power_utility": ["015760", "018670", "016710"],
}

# 산출 방식 검증: 19개 섹터가 Track A 아니면 Track B 둘 중 하나에 반드시 있어야 함
_covered = set(TRACK_A_KEYWORDS) | set(TRACK_B_BASKETS)
_all_ids = {s["id"] for s in SECTORS}
assert _covered == _all_ids, f"매핑 누락: {_all_ids - _covered}"
