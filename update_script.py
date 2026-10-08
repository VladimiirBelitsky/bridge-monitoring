import os
import requests
import pandas as pd
from datetime import datetime

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

def get_route_speed(start_lat, start_lon, end_lat, end_lon):
    if not API_KEY:
        return None
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"
    }
    data = {
        "origin": {"location": {"latLng": {"latitude": start_lat, "longitude": start_lon}}},
        "destination": {"location": {"latLng": {"latitude": end_lat, "longitude": end_lon}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE"
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 200:
            res_json = response.json()
            if "routes" in res_json and len(res_json["routes"]) > 0:
                route = res_json["routes"][0]
                duration_sec = int(route.get("duration", "0s").replace("s", ""))
                distance_m = route.get("distanceMeters", 0)
                if duration_sec > 0:
                    speed_kmh = (distance_m / 1000) / (duration_sec / 3600)
                    return round(speed_kmh, 1)
    except Exception as e:
        print(f"Помилка запиту: {e}")
    return None

def main():
    excel_filename = "Робоча_модель_мережі_ФІНАЛ 1.xlsx"
    if not os.path.exists(excel_filename):
        print(f"Файл {excel_filename} не знайдено!")
        return

    df_excel = pd.read_excel(excel_filename)
    print("Знайдені стовпчики в Excel:", list(df_excel.columns))
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_records = []

    for idx, row in df_excel.iterrows():
        try:
            # Використовуємо безпечне отримання за індексами або назвами
            bridge_id = str(row.iloc[0])
            name = str(row.iloc[1])
            lat1 = float(row.iloc[2])
            lon1 = float(row.iloc[3])
            lat2 = float(row.iloc[4])
            lon2 = float(row.iloc[5])

            speed = get_route_speed(lat1, lon1, lat2, lon2)
            if speed is not None:
                new_records.append({
                    "timestamp": current_time,
                    "bridge_id": bridge_id,
                    "name": name,
                    "speed": speed
                })
        except Exception as row_err:
            print(f"Помилка в рядку {idx}: {row_err}")

    if new_records:
        history_file = "bridge_history.csv"
        df_new = pd.DataFrame(new_records)
        
        if os.path.exists(history_file):
            df_history = pd.read_csv(history_file)
            df_history = pd.concat([df_history, df_new], ignore_index=True)
        else:
            df_history = df_new
            
        df_history.to_csv(history_file, index=False)
        print(f"Успішно збережено {len(new_records)} записів у {history_file}")
    else:
        print("Жодного запису не було додано.")

if __name__ == "__main__":
    main()
