
from pathlib import Path


root = Path(__file__).resolve().parents[1]
tag = '<script src="automation/ichimoku-correct.js"></script>'
updated = 0
for name in ("업비트_지표_백과.html", "주식_지표_백과.html"):
    path = root / name
    html = path.read_text(encoding="utf-8")
    if tag not in html:
        path.write_text(html.replace("</body>", tag + "</body>"), encoding="utf-8")
        updated += 1
print(f"ichimoku pages updated={updated}")

