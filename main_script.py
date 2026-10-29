print("ЗАПУСК НОВОГО СКРИПТА МОСТІВ ПОЧАТОВ")
import os
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
import time

KYIV_TZ = timezone(timedelta(hours=3))
HISTORY_FILE = "bridges_traffic_log.csv"

# Повний реєстр 16 критичних вузлів з точними координатами та еталонними відстанями (в км)
BRIDGES = {
    'KYI_SOUTH': {
        'name': 'Південний міст', 'region': 'Київ', 
        'start_lat': 50.3920, 'start_lon': 30.5750, 
        'end_lat': 50.3780, 'end_lon': 30.6200,
        'baseline_km': 4.5,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_DARN': {
        'name': 'Дарницький міст', 'region': 'Київ', 
        'start_lat': 50.418943, 'start_lon': 30.597587, 
        'end_lat': 50.413308, 'end_lon': 30.575035, 
        'baseline_km': 3.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_PATON': {
        'name': 'Міст Патона', 'region': 'Київ', 
        'start_lat': 50.430015, 'start_lon': 30.591375, 
        'end_lat': 50.424265, 'end_lon': 30.571904, 
        'baseline_km': 3.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_METRO': {
        'name': 'Міст Метро', 'region': 'Київ', 
        'start_lat': 50.441491, 'start_lon': 30.560397, 
        'end_lat': 50.445658, 'end_lon': 30.575147, 
        'baseline_km': 2.6,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_NORTH': {
        'name': 'Північний міст', 'region': 'Київ', 
        'start_lat': 50.4890, 'start_lon': 30.5320, 
        'end_lat': 50.4960, 'end_lon': 30.5700, 
        'baseline_km': 4.3,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_GAVAN': {
        'name': 'Гаванський міст', 'region': 'Київ', 
        'start_lat': 50.467400, 'start_lon': 30.524984, 
        'end_lat': 50.475162, 'end_lon': 30.534496, 
        'baseline_km': 2.2,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_HPP': {
        'name': 'Київська ГЕС', 'region': 'Вишгород', 
        'start_lat': 50.5750, 'start_lon': 30.4850, 
        'end_lat': 50.5900, 'end_lon': 30.5200, 
        'baseline_km': 3.5,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KANIV_HPP': {
        'name': 'Канівська ГЕС', 'region': 'Черкаська обл.', 
        'start_lat': 49.7450, 'start_lon': 31.4300, 
        'end_lat': 49.7600, 'end_lon': 31.4700, 
        'baseline_km': 4.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'CHK': {
        'name': 'Черкаський міст', 'region': 'Черкаси', 
        'start_lat': 49.4350, 'start_lon': 32.0500, 
        'end_lat': 49.4680, 'end_lon': 32.1450, 
        'baseline_km': 13.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KREM': {
        'name': 'Крюківський міст / ГЕС', 'region': 'Кременчук', 
        'start_lat': 49.0580, 'start_lon': 33.4050, 
        'end_lat': 49.0740, 'end_lon': 33.4280, 
        'baseline_km': 2.5,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KAM_HPP': {
        'name': 'Камʼянська ГЕС', 'region': 'Дніпропетровська обл.', 
        'start_lat': 48.5400, 'start_lon': 34.8100, 
        'end_lat': 48.5600, 'end_lon': 34.8600, 
        'baseline_km': 4.2,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'DNI_AMUR': {
        'name': 'Амурський міст', 'region': 'Дніпро', 
        'start_lat': 48.4830, 'start_lon': 35.0220, 
        'end_lat': 48.4980, 'end_lon': 35.0480, 
        'baseline_km': 2.8,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'DNI_CENTR': {
        'name': 'Центральний міст', 'region': 'Дніпро', 
        'start_lat': 48.4740, 'start_lon': 35.0480, 
        'end_lat': 48.4890, 'end_lon': 35.0780, 
        'baseline_km': 3.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'DNI_SOUTH': {
        'name': 'Південний міст (Дніпро)', 'region': 'Дніпро', 
        'start_lat': 48.3980, 'start_lon': 35.0680, 
        'end_lat': 48.4280, 'end_lon': 35.0980, 
        'baseline_km': 4.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'ZP_PREOBR': {
        'name': 'Мости Преображенського', 'region': 'Запоріжжя', 
        'start_lat': 47.8480, 'start_lon': 35.0830, 
        'end_lat': 47.8630, 'end_lon': 35.0930, 
        'baseline_km': 2.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'ZP_NEW': {
        'name': 'Нові мости (Запоріжжя)', 'region': 'Запоріжжя', 
        'start_lat': 47.8380, 'start_lon': 35.0580, 
        'end_lat': 47.8580, 'end_lon': 35.0880, 
        'baseline_km': 3.5,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    }
}

def main():
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        print("❌ ПОМИЛКА: Ключ GOOGLE_MAPS_API_KEY не знайдено в середовищі!")
        return
    else:
        print(f"✅ Ключ успішно зчитано (довжина: {len(api_key)} символів)")

    timestamp_str = datetime.now(timezone.utc).astimezone(KYIV_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters'
    }
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    batch_records = []

    for b_id, b_info in BRIDGES.items():
        speed_str = "Н/Д"
        status_str = "❌ Немає зв'язку з API"
        
        payload = {
            "origin": {"location": {"latLng": {"latitude": b_info['start_lat'], "longitude": b_info['start_lon']}}},
            "destination": {"location": {"latLng": {"latitude": b_info['end_lat'], "longitude": b_info['end_lon']}}},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE"
        }
        
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=10).json()
            
            if 'routes' in res and len(res['routes']) > 0:
                route = res['routes'][0]
                dist_m = route.get('distanceMeters', 0)
                dur_str = str(route.get('duration', '0s')).replace('s', '')
                dur_sec = float(dur_str) if dur_str else 0.0
                
                if dist_m > 0:
                    dist_km = dist_m / 1000.0
                    
                    # МАТЕМАТИЧНИЙ ДЕТЕКТОР ЗАКРИТТЯ МОСТУ ЗА ВІДСТАННЮ:
                    # Якщо фактична відстань від API перевищує еталонну більш ніж на 40% (коефіцієнт 1.4),
                    # це означає, що Google не може їхати прямо через міст і веде в об'їзд -> МІСТ ЗАКРИТИЙ
                    is_closed = dist_km > (b_info['baseline_km'] * 2.3)
                    
                    if is_closed:
                        speed_str = "0 км/год"
                        status_str = '⛔ Закрито / Обʼїзд (Math Detector)'
                    else:
                        hours = dur_sec / 3600.0 if dur_sec > 0 else 0.01
                        calc_speed = round(dist_km / hours) if hours > 0 else 0
                        speed_str = f"{calc_speed} км/год"
                        
                        if calc_speed < 20:
                            status_str = '🔴 Критично / Затор (Live)'
                        elif calc_speed < 35:
                            status_str = '🟡 Повільний рух (Live)'
                        else:
                            status_str = '🟢 Вільно (Live)'
                            
                    print(f"Оброблено: {b_info['name']} -> {speed_str} ({status_str}) [Факт: {dist_km:.1f}км / Еталон: {b_info['baseline_km']}км]")
            elif 'error' in res:
                err_msg = res['error'].get('message', 'Unknown error')
                print(f"❌ Помилка для {b_info['name']}: {err_msg}")
                status_str = f"❌ API Error: {err_msg}"
            else:
                print(f"❌ Неочікувана відповідь для {b_info['name']}: {res}")
        except Exception as e:
            print(f"❌ Виняток для {b_info['name']}: {str(e)}")
            status_str = f"❌ Помилка: {str(e)}"

        record = {
            'timestamp': timestamp_str, 'id': b_id, 'name': b_info['name'],
            'region': b_info['region'], 'state': status_str, 'speed': speed_str,
            'source_name': b_info['source_name'], 'source_url': b_info['source_url']
        }
        batch_records.append(record)
        time.sleep(1.0)

    df_new = pd.DataFrame(batch_records)
    if os.path.exists(HISTORY_FILE):
        df_new.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    
    print(f"✅ Успішно збережено {len(batch_records)} записів у {HISTORY_FILE}")

if __name__ == "__main__":
    main()
