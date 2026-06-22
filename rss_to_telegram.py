import os
import html
import json
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://mt-news.ru/news/"
STATE_FILE = "state.json"


# =========================
# Отримання тексту статті
# =========================

def get_article_text(url):

    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    article = soup.select_one("div.text.margin-top")

    if not article:
        return ""

    parts = []

    for tag in article.find_all(["p", "blockquote"]):

        text = tag.get_text(" ", strip=True)

        if text:
            parts.append(text)

    return "\n\n".join(parts)


# =========================
# Завантаження state.json
# =========================

try:
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

except:
    state = {"last_url": ""}


# =========================
# Завантаження сторінки новин
# =========================

r = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")


# =========================
# Пошук першої новини
# =========================

news = soup.select_one("a.border.border-radius.padding")

if not news:
    raise Exception("News not found")


# =========================
# Дані новини
# =========================

link = news["href"]

print("Current link:", link)
print("Saved link:", state.get("last_url"))


# =========================
# Захист від дублювання
# =========================

if link == state.get("last_url"):

    print("No new posts")

    raise SystemExit(0)


date = news.find("span").get_text(strip=True)

title = news.find(
    "h3",
    class_="padding-top"
).get_text(strip=True)


# =========================
# Текст статті
# =========================

article_text = get_article_text(link)


# =========================
# Фото новини
# =========================

article_page = requests.get(
    link,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

article_page.raise_for_status()

article_soup = BeautifulSoup(
    article_page.text,
    "html.parser"
)

preview_photo = None

figure = article_soup.select_one(
    "div.text.margin-top figure.wp-block-image img"
)

if figure:
    preview_photo = figure.get("src")

print("Photo URL:", preview_photo)


# =========================
# Кнопка
# =========================

keyboard = {
    "inline_keyboard": [[
        {
            "text": "Читати оригінал",
            "url": link
        }
    ]]
}


# =========================
# Повідомлення з фото
# =========================

caption = (
    f"🏍 MotoGP News\n\n"
    f"<b>{title}</b>\n\n"
    f"📅 {date}"
)

if preview_photo:

    img = requests.get(
        preview_photo,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    img.raise_for_status()
    print("Downloading image...")
    print("Photo URL:", preview_photo)
    print("Image size:", len(img.content))
    print("Image content-type:", img.headers.get("content-type"))

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={
            "chat_id": CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        },
        files={
            "photo": (
                "photo.jpg",
                img.content
            )
        },
        timeout=60
    )

else:

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": caption,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        },
        timeout=30
    )

print("Status:", response.status_code)
print("Response:", response.text)

response.raise_for_status()

# =========================
# Надсилання тексту статті
# =========================

MAX_LEN = 3500
for i in range(0, len(article_text), MAX_LEN):
    # chunk = article_text[i:i + MAX_LEN]
    # chunk = html.escape(chunk)
    # requests.post(
    #     f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    #     json={
    #         "chat_id": CHAT_ID,
    #         "text": f"<blockquote>{chunk}</blockquote>",
    #         "parse_mode": "HTML"
    #     },  
    #     timeout=30
    # )
    
    article_text = html.escape(article_text)
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": f"<blockquote expandable>{article_text}</blockquote>",
            "parse_mode": "HTML"
        },
        timeout=30
    )

# =========================
# Оновлення state.json
# =========================

state["last_url"] = link

with open(
    STATE_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        state,
        f,
        ensure_ascii=False,
        indent=2
    )


print("Published:", link)
