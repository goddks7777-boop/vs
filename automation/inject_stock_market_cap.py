from pathlib import Path


root = Path(__file__).resolve().parents[1]
page = root / "주식_종합분석.html"
html = page.read_text(encoding="utf-8")
tag = '<script src="automation/stock-market-cap-live.js"></script>'
if tag not in html:
    page.write_text(html.replace("</body>", tag + "</body>"), encoding="utf-8")
print("stock market-cap UI ready")

