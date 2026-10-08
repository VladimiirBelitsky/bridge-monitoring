import os
from datetime import datetime
import pandas as pd
import requests

# Отримуємо API-ключ з середовища GitHub Secrets
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Словник мостів/маршрутів для моніторингу
BRIDGES = {
    "North Bridge": {
        "origin": "50.4900,30.5300",
        "destination": "50.5100,30.5500",
    },
    "Paton Bridge": {
        "origin": "50.4280,30.5720",
        "destination": "50.4350,30.5850",
    },
}

CSV_FILE = "traffic_history.csv"


def get_traffic_data(origin, destination):
  if not API_KEY:
    print("ПОМИЛКА: Не встановлено ключ GOOGLE_MAPS_API_KEY у секретах!")
    return None, None

  url = "https://maps.googleapis.com/maps/api/distancematrix/json"
  params = {
      "origins": origin,
      "destinations": destination,
      "departure_time": "now",
      "key": API_KEY,
  }

  try:
    response = requests.get(url, params=params)
    data = response.json()
    print(f"Відповідь від Google API для {origin} -> {destination}: {data}")

    if data.get("status") == "OK":
      element = data["rows"][0]["elements"][0]
      if element.get("status") == "OK":
        duration = element["duration"]["value"]  # у секундах
        duration_in_traffic = element.get("duration_in_traffic", {}).get(
            "value", duration
        )
        distance = element["distance"]["text"]
        return (
            round(duration / 60, 1),
            round(duration_in_traffic / 60, 1),
        )  # у хвилинах
      else:
        print(f"Помилка елемента маршруту: {element.get('status')}")
    else:
      print(f"Помилка API Status: {data.get('status')}")
  except Exception as e:
    print(f"Виняток при запиті до API: {e}")

  return None, None


def main():
  if not API_KEY:
    print("Зупинка: GOOGLE_MAPS_API_KEY відсутній.")
    return

  now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  new_rows = []

  print(
      f"Початок перевірки трафіку о {now}. Кількість мостів:"
      f" {len(BRIDGES)}"
  )

  for bridge_name, coords in BRIDGES.items():
    print(f"Опитування мосту: {bridge_name}...")
    duration, duration_in_traffic = get_traffic_data(
        coords["origin"], coords["destination"]
    )

    if duration is not None:
      new_rows.append({
          "timestamp": now,
          "bridge_name": bridge_name,
          "duration_min": duration,
          "duration_in_traffic_min": duration_in_traffic,
      })
      print(
          f"Успішно отримано дані для {bridge_name}: звичайний час —"
          f" {duration} хв, з трафіком — {duration_in_traffic} хв."
      )
    else:
      print(f"Не вдалося отримати дані для {bridge_name}.")

  if new_rows:
    df_new = pd.DataFrame(new_rows)

    if os.path.exists(CSV_FILE):
      df_existing = pd.read_csv(CSV_FILE)
      df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
      df_final = df_new

    df_final.to_csv(CSV_FILE, index=False)
    print(
        f"Збережено {len(new_rows)} нових записів у файл {CSV_FILE}. Готово!"
    )
  else:
    print("УВАГА: Жодного успішного запису не додано за цей цикл.")


if __name__ == "__main__":
  main()
