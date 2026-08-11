from pathlib import Path


root = Path(__file__).resolve().parents[1]
page = root / "주식_1주일_모의투자.html"
html = page.read_text(encoding="utf-8")
tag = '<script src="automation/stock-paper-live.js"></script>'
if tag not in html:
    html = html.replace("</body>", tag + "</body>")
    page.write_text(html, encoding="utf-8", newline="\n")
print("stock paper UI ready")

