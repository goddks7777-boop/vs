from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "업비트_원화마켓_시각화_보고서_2026-08-11.html",
    "업비트_1시간_모니터링.html",
    "코인_1주일_가상투자.html",
    "업비트_지표_백과.html",
    "코인_AI스윙_학습검증.html",
    "코인_싸이클_분석.html",
    "코인_유동.html",
    "코인_매집포착.html",
]
anchors = [
    ("코인_AI스윙_학습검증.html", '<a href="코인_AI스윙_학습검증.html" data-page="코인_AI스윙_학습검증.html" class=""><span class="gn-icon">◆</span><span>AI 스윙</span><small>현재 위치</small></a>'),
    ("코인_싸이클_분석.html", '<a href="코인_싸이클_분석.html" data-page="코인_싸이클_분석.html" class=""><span class="gn-icon">◉</span><span>BTC 싸이클</span><small>현재 위치</small></a>'),
    ("코인_유동.html", '<a href="코인_유동.html" data-page="코인_유동.html" class=""><span class="gn-icon">≋</span><span>코인 유동</span><small>현재 위치</small></a>'),
    ("코인_매집포착.html", '<a href="코인_매집포착.html" data-page="코인_매집포착.html" class=""><span class="gn-icon">⌁</span><span>매집포착</span><small>현재 위치</small></a>'),
]
needle = '<a href="업비트_지표_백과.html"'
updated = 0
for name in TARGETS:
    path = ROOT / name
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        continue
    before = text
    for marker, anchor in anchors:
        if marker not in text:
            text = text.replace(needle, anchor + needle, 1)
    if text != before:
        path.write_text(text, encoding="utf-8", newline="\n")
        updated += 1
home = ROOT / "업비트_분석_홈.html"
if home.exists():
    text = home.read_text(encoding="utf-8")
    home_anchor = '<a href="코인_유동.html">코인 유동·펀딩비</a>'
    cycle_anchor = '<a href="코인_싸이클_분석.html">BTC 장기 싸이클</a>'
    home_needle = '<a href="업비트_지표_백과.html">코인 지표 백과</a>'
    before = text
    if "코인_유동.html" not in text and home_needle in text:
        text = text.replace(home_needle, home_anchor + home_needle, 1)
    if "코인_싸이클_분석.html" not in text and home_needle in text:
        text = text.replace(home_needle, cycle_anchor + home_needle, 1)
    if text != before:
        home.write_text(text, encoding="utf-8", newline="\n")
        updated += 1
print(f"updated={updated}")

