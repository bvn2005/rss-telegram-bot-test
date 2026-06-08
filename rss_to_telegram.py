import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://mt-news.ru/news/"

r = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

news = soup.select_one("a.border.border-radius.padding")

if not news:
    raise Exception("News not found")

link = news["href"]

date = news.find("span").get_text(strip=True)

title = news.find(
    "h3",
    class_="padding-top"
).get_text(strip=True)

text = (
    f"🏍 MotoGP News\n\n"
    f"{title}\n\n"
    f"📅 {date}"
)

keyboard = {
    "inline_keyboard": [[
        {
            "text": "Читати",
            "url": link
        }
    ]]
}

response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": text,
        "reply_markup": keyboard,
        "disable_web_page_preview": False
    },
    timeout=30
)

print(response.status_code)
print(response.text)

response.raise_for_status()
