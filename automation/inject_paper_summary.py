
from pathlib import Path


root=Path(__file__).resolve().parents[1]
page=root/'업비트_1시간_모니터링.html'
html=page.read_text(encoding='utf-8')
tag='<script src="automation/paper-summary-live.js"></script>'
if tag not in html:
    page.write_text(html.replace('</body>',tag+'</body>'),encoding='utf-8')
print('monitoring paper summary ready')

