#!/usr/bin/env python3
# news_report.py
import os
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparser
from bs4 import BeautifulSoup
from jinja2 import Template
import smtplib
from email.mime.text import MIMEText

# ---------- CONFIG (kan sättas som env vars i GitHub Actions/secrets) ----------
RSS_FEEDS = os.getenv("RSS_FEEDS",
    "https://news.google.com/rss/search?q=solar+park+Sweden&hl=en-SE&gl=SE&ceid=SE:en,"
    "https://news.google.com/rss/search?q=solar+park+EU&hl=en&gl=EU&ceid=EU:en,"
    "https://news.google.com/rss/search?q=solar+park&hl=en&gl=US&ceid=US:en"
).split(",")

KEYWORDS = os.getenv("KEYWORDS", "solar,solcells,energigemenskap,energy community,solar park,PV,battery,storage,Gotland").split(",")
DAYS_BACK = int(os.getenv("DAYS_BACK", "2"))  # how far back to include
MAX_ITEMS = int(os.getenv("MAX_ITEMS", "30"))

# Email settings (optional)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO = os.getenv("EMAIL_TO")  # comma separated

# Slack webhook (optional)
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

# Report meta
REPORT_TITLE = os.getenv("REPORT_TITLE", "WISE Gotland — Daily Solar News Brief")
TZ_OFFSET = int(os.getenv("TZ_OFFSET", "0"))  # hours offset from UTC if needed

# ---------- helpers ----------
def html_excerpt(text, maxlen=300):
    soup = BeautifulSoup(text or "", "html.parser")
    txt = soup.get_text()
    return (txt[:maxlen] + "...") if len(txt) > maxlen else txt

def fetch_feed(url):
    try:
        return feedparser.parse(url)
    except Exception as e:
        print("Feed error:", url, e)
        return None

def matches_keywords(entry, keywords):
    hay = " ".join([
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("description", "")
    ]).lower()
    return any(kw.lower().strip() for kw in keywords if kw.lower().strip() in hay)

def normalize_date(entry):
    for k in ("published", "updated", "pubDate"):
        if entry.get(k):
            try:
                return dtparser.parse(entry.get(k))
            except:
                pass
    return datetime.now(timezone.utc)

# ---------- Main ----------
def build_report():
    now = datetime.now(timezone.utc) + timedelta(hours=TZ_OFFSET)
    cutoff = now - timedelta(days=DAYS_BACK)
    items = []

    for feed_url in RSS_FEEDS:
        feed = fetch_feed(feed_url)
        if not feed or not feed.entries:
            continue
        for entry in feed.entries:
            dt = normalize_date(entry)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < cutoff:
                continue
            if matches_keywords(entry, KEYWORDS):
                items.append({
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "summary": html_excerpt(entry.get("summary") or entry.get("description") or ""),
                    "published": dt.astimezone().isoformat()
                })

    # dedupe by link/title
    seen = set()
    unique = []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        key = (it["link"] or it["title"]).strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)
        if len(unique) >= MAX_ITEMS:
            break

    # render HTML using Jinja
    template = Template("""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
body{font-family: Arial, Helvetica, sans-serif; color:#222; background:#fff; padding:20px}
.header{background:#0b5e76;color:#fff;padding:20px;border-radius:6px}
.item{border-bottom:1px solid #eee;padding:12px 0}
.item h3{margin:0 0 6px}
.meta{color:#777;font-size:0.9em}
</style>
</head>
<body>
<div class="header">
  <h1>{{ title }}</h1>
  <p>Report generated: {{ now }}</p>
  <p>Keywords: {{ keywords|join(', ') }}</p>
</div>
<div>
{% if items %}
  {% for it in items %}
    <div class="item">
      <h3><a href="{{ it.link }}" target="_blank">{{ it.title }}</a></h3>
      <div class="meta">Published: {{ it.published }}</div>
      <p>{{ it.summary }}</p>
    </div>
  {% endfor %}
{% else %}
  <p>No relevant items found.</p>
{% endif %}
</div>
</body>
</html>
""")
    html = template.render(title=REPORT_TITLE, now=now.isoformat(), items=unique, keywords=KEYWORDS)
    return html, unique

def send_email(html):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS or not EMAIL_TO:
        print("Email settings missing, skipping email.")
        return False
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = REPORT_TITLE
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    try:
        s = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO.split(","), msg.as_string())
        s.quit()
        print("Email sent to", EMAIL_TO)
        return True
    except Exception as e:
        print("Email error:", e)
        return False

def post_slack(html_text):
    if not SLACK_WEBHOOK:
        print("No Slack webhook configured, skipping Slack post.")
        return False
    # Slack prefers short text; we send a summary then link to full report if hosted.
    try:
        payload = {"text": f"{REPORT_TITLE}\n\n{html_text}"}
        resp = requests.post(SLACK_WEBHOOK, json=payload, timeout=15)
        print("Slack response", resp.status_code)
        return resp.status_code == 200
    except Exception as e:
        print("Slack error", e)
        return False

if __name__ == "__main__":
    html, items = build_report()
    # write file for archive / GitHub Pages
    out_file = os.getenv("OUT_FILE", "report.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {len(items)} items to {out_file}")

    # send
    send_email(html)
    # optionally post a short text to Slack (first 5 titles)
    if items:
        short = "\n".join([f"- {i['title']} ({i['link']})" for i in items[:5]])
        post_slack(short)
