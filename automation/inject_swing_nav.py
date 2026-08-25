from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "업비트_원화마켓_시각화_보고서_2026-08-11.html",
    "업비트_1시간_모니터링.html",
    "코인_1주일_가상투자.html",
    "업비트_지표_백과.html",
]
anchor = '<a href="코인_AI스윙_학습검증.html" data-page="코인_AI스윙_학습검증.html" class=""><span class="gn-icon">◆</span><span>AI 스윙</span><small>현재 위치</small></a>'
needle = '<a href="업비트_지표_백과.html"'
updated = 0
for name in TARGETS:
    path = ROOT / name
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    if "코인_AI스윙_학습검증.html" in text or needle not in text:
        continue
    text = text.replace(needle, anchor + needle, 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    updated += 1
print(f"updated={updated}")
