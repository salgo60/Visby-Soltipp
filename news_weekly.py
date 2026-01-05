import feedparser
from datetime import datetime, timedelta
from jinja2 import Template

FEEDS = [
  "https://news.google.com/rss/search?q=solceller+Gotland&hl=sv&gl=SE&ceid=SE:sv",
  "https://news.google.com/rss/search?q=energi+Gotland&hl=sv&gl=SE&ceid=SE:sv"
]

DAYS_BACK = 7

items = []
cutoff = datetime.utcnow() - timedelta(days=DAYS_BACK)

for url in FEEDS:
    feed = feedparser.parse(url)
    for e in feed.entries:
        published = datetime(*e.published_parsed[:6])
        if published > cutoff:
            items.append({
                "title": e.title,
                "link": e.link,
                "date": published.strftime("%Y-%m-%d")
            })

items = list({i["link"]: i for i in items}.values())

html = Template("""
<h1>Veckonytt – Solceller på Gotland</h1>
<p>Uppdaterad: {{ now }}</p>
<ul>
{% for i in items %}
  <li><a href="{{ i.link }}">{{ i.title }}</a> ({{ i.date }})</li>
{% endfor %}
</ul>
""").render(
    items=items,
    now=datetime.utcnow().strftime("%Y-%m-%d")
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
