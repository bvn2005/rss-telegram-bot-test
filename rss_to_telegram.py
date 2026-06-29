import time
# Робота з змінними середовища (BOT_TOKEN, CHAT_ID)
import os
# Парсер HTML
import html
# Робота з файлом state.json
import json
# HTTP-запити до сайту та Telegram API
import requests
from bs4 import BeautifulSoup


# Токен Telegram-бота із GitHub Secrets
BOT_TOKEN = os.environ["BOT_TOKEN"]
# ID каналу або чату із GitHub Secrets
CHAT_ID = os.environ["CHAT_ID"]


# Сторінка зі списком новин
URL = "https://mt-news.ru/news/"
# Файл для запам'ятовування останньої опублікованої новини
STATE_FILE = "state.json"

# ======================================================
# Функція створення сторінки Telegraph (тільки source)
# ======================================================
def create_source_telegraph(source_name, source_url):
    response = requests.post(
        "https://api.telegra.ph/createPage",
        json={
            "access_token": "33ad462e4a40ef3e201d080257c97cce622050da97d0f5e79bbb4548c0ec",
            "title": "Источник",
            "author_name": "Moto News",
            "content": [
                {
                    "tag": "p",
                    "children": [f"Источник: {source_name} ({source_url})"]
                }
            ],
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()["result"]["url"]
    

# ===============================================================
# 👉 Функція для відправки повідомлень у Telegram через Bot API
# 👉 з автоматичним повтором при помилках (особливо 429)
# ===============================================================
def tg_post(method, payload=None, files=None):
    for attempt in range(3):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
        if files:
            response = requests.post(url, data=payload, files=files, timeout=60)
        else:
            response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response
        if response.status_code == 429:
            retry_after = response.json()["parameters"]["retry_after"]
            print(f"Rate limit! Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue
        response.raise_for_status()
    raise Exception("Failed after retries")


# =================================
# Функція отримання тексту статті
# =================================
def get_article_text(url):
    r = requests.get(
        url,
        # Імітуємо звичайний браузер
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    
    # Якщо сайт повернув помилку (404, 500 тощо)
    r.raise_for_status()
    
    # Розбір HTML
    soup = BeautifulSoup(r.text, "html.parser")
    article = soup.select_one("div.text.margin-top")
    if not article:
        return ""
    parts = []

    for tag in article.find_all(["p", "blockquote"]):
        # ❗ пропускаємо p всередині blockquote
        if tag.name == "p" and tag.find_parent("blockquote"):
            continue     
        text = tag.get_text(" ", strip=True)
        if text:
            parts.append(text)
    return "\n\n".join(parts)


# =========================
# Функція пошуку тегів
# =========================
def get_tags(soup):
    tags_block = soup.select_one("p.tags")   
    if not tags_block:
        return []
    tags = []
    
    for a in tags_block.find_all("a"):
        tag = a.get_text(strip=True)
    
        if tag:
            # робимо hashtag
            tag = "#" + tag.replace(" ", "")
            tags.append(tag)
    return tags


# =========================
# Функція пошуку джерела
# =========================
def get_source(soup):
    source_block = soup.select_one("p.source a")
    if not source_block:
        return ""
    source_text = source_block.get_text(strip=True)
    source_url = source_block.get("href")
    return f"Источник: <a href='{source_url}'>{source_text}</a>"


# =========================
# Завантаження state.json
# =========================
try:
    # Якщо файл існує — читаємо його
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
except:
    # Якщо файл відсутній — створюємо порожній стан
    state = {"last_url": ""}


# =============================
# Завантаження сторінки новин
# =============================
r = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")


# =========================
# Пошук новин
# =========================
news_list = soup.select("a.border.border-radius.padding")
if not news_list:
    raise Exception("News not found")


# =========================
# Пошук нових новин
# =========================
new_posts = []
for news in news_list:
    # Посилання на новину
    link = news["href"]

    # Захист від дублювання
    # Якщо ця новина вже публікувалася
    if link == state.get("last_url"):
        break
    new_posts.append(news)

print("New posts found:", len(new_posts))
if not new_posts:
    print("No new posts")
    # Завершуємо роботу без помилки
    raise SystemExit(0)
    

# ==================
# Публікація новин
# ==================
for news in reversed(new_posts):
    link = news["href"]

    print("=" * 50)
    print("Publishing:", link)
    # Отримання дати новини
    date = news.find("span").get_text(strip=True)
    # Отримання заголовка
    title = news.find(
        "h3",
        class_="padding-top"
    ).get_text(strip=True)

    # ==============
    # Текст статті
    # ==============
    article_text = get_article_text(link)
    print("LEN:", len(article_text))
    # виводить шматок тексту в лог
    # print(article_text[:1000])
    
    for line in article_text.split("\n\n"):
        if article_text.count(line) > 1:
            print("DUPLICATE:", line[:80])

    # =============
    # Фото новини
    # ============= 
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
    tags = get_tags(article_soup)
    tags_text = " ".join(tags)
    source_text = get_source(article_soup)

    # ====================================================================
    # Функція створення сторінки Telegraph (тільки source)
    source_block = article_soup.select_one("p.source a")
    telegraph_url = None
    if source_block:
        source_name = source_block.get_text(strip=True)
        source_url = source_block.get("href")
        telegraph_url = create_source_telegraph(source_name, source_url)
    # ====================================================================
        
    preview_photo = None
    figure = article_soup.select_one(
        "div.text.margin-top figure.wp-block-image img"
    )
    if figure:
        preview_photo = figure.get("src")
    print("Photo URL:", preview_photo)
    
    # ========
    # Кнопка
    # ========
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "Читати оригінал",
                "url": link
            }
        ]]
    }

    # =====================
    # Повідомлення з фото
    # =====================
    caption = (
        f"🏍 MotoGP News\n\n"
        f"<b>{title}</b>\n\n"
        f"📅 {date}\n\n"
        f"{tags_text}\n\n"
        f"{source_text}\n\n"
        f"Источник: {telegraph_url}" if telegraph_url else source_text
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
    
        tg_post(
            "sendPhoto",
            payload={
                "chat_id": CHAT_ID,
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(keyboard)
            },
            files={
                "photo": ("photo.jpg", img.content)
            }
        )
    else:
        tg_post(
            "sendMessage",
            {
                "chat_id": CHAT_ID,
                "text": caption,
                "parse_mode": "HTML",
                "reply_markup": keyboard
            }
        )
    print("Preview sent")
    time.sleep(2)
    
    # ==========================
    # Надсилання тексту статті
    # ==========================    
    MAX_LEN = 3500
    print("Article length:", len(article_text))
    
    for i in range(0, len(article_text), MAX_LEN):
        chunk = html.escape(article_text[i:i + MAX_LEN])
        tg_post(
            "sendMessage",
            {
                "chat_id": CHAT_ID,
                "text": f"<blockquote expandable>{chunk}</blockquote>",
                "parse_mode": "HTML"
            }
        )
    
        if len(article_text) > MAX_LEN:
            time.sleep(1)
        print("Chunk sent:", i // MAX_LEN + 1)


# ======================
# Оновлення state.json
# ======================
if new_posts:
    # Запам'ятати новину
    state["last_url"] = new_posts[0]["href"]
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
    print("New last_url:", state["last_url"])
