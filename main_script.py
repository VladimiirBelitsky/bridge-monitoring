import os
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
import time

KYIV_TZ = timezone(timedelta(hours=3))
HISTORY_FILE = "traffic_history.csv"

# Повний реєстр 16 критичних вузлів
BRIDGES = {
    'KYI_SOUTH': {'name': 'Південний міст', 'region': 'Київ', 'start_lat': 50.3850, 'start_lon': 30.5750, 'end_lat': 50.3950, 'end_lon': 30.5950, 'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'},
    'KYI_DARN': {'name': 'Дарницький міст', 'region': 'Київ', 'start_lat': 50.4120, 'start_lon': 30.5850, 'end_lat': 50.4250, 'end_lon': 30.6000, 'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'},
    'KYI_PATON': {'name': 'Міст Патона', 'region': 'Київ', 'start_lat': 50.4320, 'start_lon': 30.5700, 'end_lat': 50.4400, 'end_lon': 30.5900, 'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'},
    'KYI_METRO': {'name': 'Міст Метро', 'region': 'Київ', 'start_lat': 50.4430, 'start_lon': 30.5480, 'end_lat': 50.4500, 'end_lon': 30.5650, 'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'},
    'KYI_NORTH': {'name': 'Північний міст', 'region': 'Київ', 'start_lat': 50.4820, 'start_lon': 30.5300, 'end_lat': 50.4940, 'end_lon': 30.5420, 'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'},
    'KYI_GAVAN': {'name': 'Гаванський міст', 'region': 'Київ', 'start_lat': 50.4680, 'start_lon': 30.5220, 'end_lat': 50.4780, 'end_lon': 30.5340, 'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'},
    'KYI_HPP': {'name': 'Київська ГЕС', 'region': 'Вишгород', 'start_lat': 50.5750, 'start_lon': 30.4950, 'end_lat': 50.5900, 'end_lon': 30.5150, 'source_name': 'Вишгородська міськрада', 'source_url': 'https://t.me/vyshgorod_rada'},
    'KANIV_HPP': {'name': 'Канівська ГЕС', 'region': 'Черкаська обл.', 'start_lat': 49.7450, 'start_lon': 31.4400, 'end_lat': 49.7600, 'end_lon': 31.4650, 'source_name': 'Черкаська ОВА', 'source_url': 'https://t.me/cherkaskaODA'},
    'CHK': {'name': 'Черкаський міст', 'region': 'Черкаси', 'start_lat': 49.4350, 'start_lon': 32.0400, 'end_lat': 49.4550, 'end_lon': 32.0700, 'source_name': 'Патрульна поліція Черкащини', 'source_url': 'https://t.me/patrolpolice_cherkasy'},
    'KREM': {'name': 'Кременчуцький міст / ГЕС', 'region': 'Кременчук', 'start_lat': 49.0650, 'start_lon': 33.2500, 'end_lat': 49.0800, 'end_lon': 33.2800, 'source_name': 'Полтавська ОВА', 'source_url': 'https://t.me/poltavaoda'},
    'KAM_HPP': {'name': 'Камʼянська ГЕС', 'region': 'Дніпропетровська обл.', 'start_lat': 48.5400, 'start_lon': 34.8200, 'end_lat': 48.5600, 'end_lon': 34.8500, 'source_name': 'Дніпропетровська ОВА', 'source_url': 'https://t.me/adm_dp'},
    'DNI_AMUR': {'name': 'Амурський міст', 'region': 'Дніпро', 'start_lat': 48.4750, 'start_lon': 35.0050, 'end_lat': 48.4900, 'end_lon': 35.0300, 'source_name': 'Патрульна поліція Дніпра', 'source_url': 'https://t.me/patrolpolice_dp'},
    'DNI_CENTR': {'name': 'Центральний міст', 'region': 'Дніпро', 'start_lat': 48.4650, 'start_lon': 35.0350, 'end_lat': 48.4800, 'end_lon': 35.0600, 'source_name': 'Дніпровська міськрада', 'source_url': 'https://t.me/borys_filatov'},
    'DNI_SOUTH': {'name': 'Південний міст (Дніпро)', 'region': 'Дніпро', 'start_lat': 48.3750, 'start_lon': 35.0700, 'end_lat': 48.3900, 'end_lon': 35.1000, 'source_name': 'Патрульна поліція Дніпра', 'source_url': 'https://t.me/patrolpolice_dp'},
    'ZP_PREOBR': {'name': 'Мости Преображенського', 'region': 'Запоріжжя', 'start_lat': 47.8400, 'start_lon': 35.0700, 'end_lat': 47.8600, 'end_lon': 35.1000, 'source_name': 'Запорізька ОВА', 'source_url': 'https://t.me/zoda_gov_ua'},
    'ZP_NEW': {'name': 'Нові мости (Запоріжжя)', 'region': 'Запоріжжя', 'start_lat': 47.8550, 'start_lon': 35.0850, 'end_lat': 47.8750, 'end_lon': 35.1150, 'source_name': 'Запорізька ОВА', 'source_url': 'https://t.me/zoda_gov_ua'}
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
                
                if dist_m > 0 and dur_sec > 0:
                    dist_km = dist_m / 1000.0
                    hours = dur_sec / 3600.0
                    calc_speed = round(dist_km / hours)
                    
                    speed_str = f"{calc_speed} км/год"
                    if calc_speed < 20:
                        status_str = '🔴 Критично / Затор (Live)'
                    elif calc_speed < 35:
                        status_str = '🟡 Повільний рух (Live)'
                    else:
                        status_str = '🟢 Вільно (Live)'
                print(f"Оброблено: {b_info['name']} -> {speed_str} ({status_str})")
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
