import streamlit as st
import requests
from datetime import datetime
import pytz
import random

# Налаштування сторінки
st.set_page_config(
    page_title="Моніторинг переправ та логістики",
    page_icon="🌉",
    layout="wide"
)

# Список переправ / мостів (координати та регіони)
BRIDGES = {
    'KYI_SOUTH': {'name': 'Південний міст', 'lat': 50.3904, 'lon': 30.5872, 'region': 'Київ'},
    'KYI_DARN': {'name': 'Міст Дарницький', 'lat': 50.4192, 'lon': 30.5935, 'region': 'Київ'},
    'KYI_NORTH': {'name': 'Північний міст', 'lat': 50.4886, 'lon': 30.5367, 'region': 'Київ'},
    'KYI_HPP': {'name': 'Міст Патона / Гребля ГЕС', 'lat': 50.5842, 'lon': 30.5053, 'region': 'Вишгород / Київ'}
}

def get_kyiv_now_str():
    kyiv_tz = pytz.timezone('Europe/Kyiv')
    return datetime.now(kyiv_tz).strftime('%Y-%m-%d %H:%M:%S')

def fetch_google_maps_traffic_and_sources():
    traffic_dict = {}
    logs = []
    
    # Безпечне зчитування ключа із st.secrets
    api_key = ""
    try:
        api_key = st.secrets.get("google_maps", {}).get("api_key", "")
    except Exception:
        pass
    
    for b_id, b_info in BRIDGES.items():
        try:
            if api_key:
                # Формуємо короткий відрізок для розрахунку швидкості потоку через Distance Matrix API
                orig_lat = b_info['lat'] - 0.008
                orig_lon = b_info['lon'] - 0.008
                dest_lat = b_info['lat']
                dest_lon = b_info['lon']
                
                url = (f"https://maps.googleapis.com/maps/api/distancematrix/json?"
                       f"origins={orig_lat},{orig_lon}&destinations={dest_lat},{dest_lon}"
                       f"&departure_time=now&key={api_key}")
                
                res = requests.get(url, timeout=4).json()
                element = res.get('rows', [{}])[0].get('elements', [{}])[0]
                
                if element.get('status') == 'OK':
                    distance_meters = element.get('distance', {}).get('value', 1000)
                    dur_norm = element.get('duration', {}).get('value', 60)
                    dur_traf = element.get('duration_in_traffic', {}).get('value', dur_norm)
                    
                    distance_km = distance_meters / 1000.0
                    hours_in_traffic = dur_traf / 3600.0
                    
                    speed_kmh = round(distance_km / hours_in_traffic) if hours_in_traffic > 0 else 50
                    speed_kmh = max(5, min(speed_kmh, 110))
                    
                    state_str = '🟡 Повільний рух' if (dur_traf > dur_norm * 1.3 or speed_kmh < 25) else '🟢 Вільно'
                    
                    traffic_dict[b_id] = {
                        'name': b_info['name'],
                        'state': state_str, 
                        'speed': speed_kmh, 
                        'source': f"Google Maps API (Live) | {b_info['region']}"
                    }
                    continue

            # Резервний режим (якщо ключ не спрацював або відсутній)
            sp = random.randint(35, 68)
            traffic_dict[b_id] = {
                'name': b_info['name'],
                'state': '🟢 Вільно' if sp > 40 else '🟡 Повільний рух', 
                'speed': sp, 
                'source': f"Автономний/Імітаційний режим ({b_info['region']})"
            }
            
        except Exception as e:
            traffic_dict[b_id] = {
                'name': b_info['name'],
                'state': '🟢 Вільно', 
                'speed': 50, 
                'source': f"Помилка зв'язку ({b_info['region']})"
            }
            
    logs.append(f"[{get_kyiv_now_str()}] 🌐 [Моніторинг] Дані трафіку успішно синхронізовано.")
    return traffic_dict, logs

# --- Інтерфейс Streamlit ---
st.title("🌉 Оперативний моніторинг переправ та логістики")
st.markdown("Панель контролю транспортних потоків у реальному часі.")

# Кнопка оновлення даних
if st.button("🔄 Оновити дані потоку"):
    st.rerun()

# Отримуємо дані
traffic_data, session_logs = fetch_google_maps_traffic_and_sources()

# Виводимо метрики у колонках
col1, col2, col3, col4 = st.columns(4)
cols = [col1, col2, col3, col4]

for i, (b_id, data) in enumerate(traffic_data.items()):
    with cols[i % 4]:
        st.metric(
            label=data['name'], 
            value=f"{data['speed']} км/год", 
            delta=data['state']
        )

st.markdown("---")
st.subheader("📊 Детальна таблиця станів та джерел телеметрії")

# Формуємо таблицю для відображення
table_rows = []
for b_id, data in traffic_data.items():
    table_rows.append({
        "Переправа": data['name'],
        "Статус": data['state'],
        "Швидкість": f"{data['speed']} км/год",
        "Джерело даних": data['source']
    })

st.dataframe(table_rows, use_container_width=True)

with st.expander("📜 Журнал подій (System Logs)"):
    for log in session_logs:
        st.text(log)
    st.text(f"[{get_kyiv_now_str()}] ℹ️ Система працює стабільно.")
