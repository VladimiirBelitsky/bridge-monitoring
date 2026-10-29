from bs4 import BeautifulSoup
import requests

channel = "patrolpolice_kyiv"
url = f"https://t.me/s/{channel}"
headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
}

print(f"🔍 Запит до каналу: {url}...")
res = requests.get(url, headers=headers)

if res.status_code == 200:
  soup = BeautifulSoup(res.text, 'html.parser')

  # 1. Перевіряємо закріплені / виділені повідомлення
  print("\n--- СМД / ТЕКСТИ З КАНАЛУ ---")
  posts = soup.find_all('div', class_='tgme_widget_message_text')

  for i, post in enumerate(posts[-5:], 1):  # Останні 5 постів
    text = post.get_text()
    print(f"\n[Пост #{i}]:\n{text[:200]}...")

    # Перевірка на наявність згадок про мости
    if any(
        kw in text.lower()
        for kw in ['міст', 'південн', 'патон', 'обмежен', 'перекрит']
    ):
      print("   👉 [ЗНАЙДЕНО КЛЮЧОВЕ СЛОВО ПРО МОСТИ/ПЕРЕКРИТТЯ!]")
else:
  print(f"❌ Помилка доступу до каналу: Статус {res.status_code}")
