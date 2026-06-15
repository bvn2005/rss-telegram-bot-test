# Робота з змінними середовища (BOT_TOKEN, CHAT_ID)
import os

# Робота з файлом state.json
import json

# HTTP-запити до сайту та Telegram API
import requests

# Парсер HTML
from bs4 import BeautifulSoup


# Токен Telegram-бота із GitHub Secrets
BOT_TOKEN = os.environ["BOT_TOKEN"]

# ID каналу або чату із GitHub Secrets
CHAT_ID = os.environ["CHAT_ID"]

# Сторінка зі списком новин
URL = "https://mt-news.ru/news/"

# Файл для запам'ятовування останньої опублікованої новини
STATE_FILE = "state.json"


# =========================
# Завантаження state.json
# =========================

try:
    # Якщо файл існує — читаємо його
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

except:
    # Якщо файл відсутній — створюємо порожній стан
    state = {
        "last_url": ""
    }


# =========================
# Завантаження сторінки новин
# =========================

r = requests.get(
    URL,
    headers={
        # Імітуємо звичайний браузер
        "User-Agent": "Mozilla/5.0"
    },
    timeout=30
)

# Якщо сайт повернув помилку (404, 500 тощо)
r.raise_for_status()


# =========================
# Розбір HTML
# =========================

soup = BeautifulSoup(r.text, "html.parser")


# =========================
# Пошук першої новини
# =========================

news = soup.select_one(
    "a.border.border-radius.padding"
)

if not news:
    raise Exception("News not found")


# =========================
# Посилання на новину
# =========================

link = news["href"]


# =========================
# Захист від дублювання
# =========================
print("Current link:", link)
print("Saved link:", state.get("last_url"))

# Якщо ця новина вже публікувалася
if link == state.get("last_url"):

    print("No new posts")

    # Завершуємо роботу без помилки
    raise SystemExit(0)


# =========================
# Отримання дати новини
# =========================

date = news.find("span").get_text(strip=True)


# =========================
# Отримання заголовка
# =========================

title = news.find(
    "h3",
    class_="padding-top"
).get_text(strip=True)


# =========================
# Формування тексту повідомлення
# =========================

text = (
    f"🏍 MotoGP News\n\n"
    f"{title}\n\n"
    f"📅 {date}"
)


# =========================
# Кнопка "Читати"
# =========================

keyboard = {
    "inline_keyboard": [
        [
            {
                "text": "Читати",
                "url": link
            }
        ]
    ]
}


# =========================
# Відправка повідомлення
# =========================

response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,

        # Текст повідомлення
        "text": text,

        # Кнопка під повідомленням
        "reply_markup": keyboard,

        # Показувати прев'ю сторінки
        "disable_web_page_preview": False
    },
    timeout=30
)


# =========================
# Логування відповіді Telegram
# =========================

print(response.status_code)
print(response.text)


# Якщо Telegram повернув помилку
response.raise_for_status()


# =========================
# Запам'ятати новину
# =========================

state["last_url"] = link


# =========================
# Зберегти state.json
# =========================

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


# =========================
# Лог успішної публікації
# =========================

print("Published:", link)
