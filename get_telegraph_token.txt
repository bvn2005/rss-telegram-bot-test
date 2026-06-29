# отримати TELEGRAPH_TOKEN
import requests

response = requests.post(
    "https://api.telegra.ph/createAccount",
    json={"short_name": "bot"}
)

print(response.json())
