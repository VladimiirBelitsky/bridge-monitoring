import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
import random
import pandas as pd

# Налаштування сторінки
st.set_page_config(
    page_title="Оперативний моніторинг мостів та переправ України",
    page_icon="🌉",
    layout="wide"
)

KYIV_TZ = timezone(timedelta(hours=3))

# Повний реєстр усіх критичних переходів/мостів із твоєї моделі мережі
BRIDGES = {
    'KYI_SOUTH': {'name': 'Південний міст', 'lat': 50.3904, 'lon': 30.5872, 'region': 'Київ'},
    'KYI_DARN': {'name': 'Дарницький міст', 'lat': 50.4192, 'lon': 30.5935, 'region': 'Київ'},
    'KYI_PATON': {'name': 'Міст Патона', 'lat': 50.4357, 'lon': 30.5823, 'region': 'Київ'},
    'KYI_METRO': {'name': 'Міст Метро', 'lat': 50.4468, 'lon': 30.5574, 'region': 'Київ'},
    'KYI_NORTH': {'name': 'Північний міст', 'lat': 50.4886, 'lon': 30.5367, 'region': 'Київ'},
    'KYI_GAVAN': {'name': 'Гаванський міст', 'lat': 50.4735, 'lon': 30.5282, 'region': 'Київ'},
    'KYI_HPP': {'name': 'Київська ГЕС', 'lat': 50.5842, 'lon': 30.5053, 'region': 'Київська обл.'},
    'KANIV_HPP': {'name': 'Канівська ГЕС', 'lat': 49.7533, 'lon': 31.4500, 'region': 'Черкаська обл.'},
    'CHK': {'name': 'Черкаський міст', 'lat': 49.4444, 'lon': 32.0556, 'region': 'Черкаси'},
    'KREM': {'name': 'Кременчуцький міст / ГЕС', 'lat': 49.0725, 'lon': 33.2636, 'region': 'Кременчук'},
    'KAM_HPP': {'name': 'Камʼянська ГЕС', 'lat': 48.5500, 'lon': 34.8333, 'region': 'Дніпропетровська обл.'},
    'DNI_AMUR': {'name': 'Амурський міст', 'lat': 48.4833, 'lon': 35.0167, 'region': 'Дніпро'},
    'DNI_CENTR': {'name': 'Центральний міст', 'lat': 48.4722, 'lon': 35.0472, 'region': 'Дніпро'},
    'DNI_SOUTH': {'name': 'Південний міст (Дніпро)', 'lat': 48.3833, 'lon': 35.0833, 'region': 'Дніпро'},
    'ZP_PREOBR': {'name': 'Мости Преображенського', 'lat': 47.8500, 'lon': 35.0833, 'region': 'Запоріжжя'},
    'ZP_NEW': {'name': 'Нові мости (Запоріжжя)', 'lat': 47.8667, 'lon': 35.1000, 'region': 'Запоріжжя'}
}

def get_kyiv_now():
    return datetime.now(KYIV_TZ)

def get_resolved_api_key(sidebar_key):
    if sidebar_key.strip():
        return sidebar_key.strip()
    try:
        # Перевірка всіх можливих варіантів у st.secrets
        if "google_maps" in st.secrets:
            if isinstance(st.secrets["google_maps"], dict) and "api_key" in st.secrets["google_maps"]:
                return st.secrets["google_maps"]["api_key"]
            if isinstance(st.secrets["google_maps"], str):
                return st.secrets["google_maps"]
        if "api_key" in st.secrets:
            return st.secrets["api_key"]
        for k, v in st.secrets.items():
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if "key" in sub_k.lower() and isinstance(sub_v, str):
                        return sub_v
    except Exception:
        pass
    return ""

if 'history' not in st.session_state:
    st.session_state['history'] = []

if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None

def fetch_telemetry(api_key, force=False):
    now = get_kyiv_now()
    if not force and st.session_state['last_update'] and (now - st.session_state['last_update']).total_seconds() < 1800:
        if 'cached_data' in st.session_state:
            return st.session_state['cached_data']

    timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
    traffic_dict = {}

    for b_id, b_info in BRIDGES.items():
        speed_kmh = 55
        status_str = '🟢 Вільно (Рух йде)'
        delay_min = 0
        source_desc = "Google Maps API (Live)"

        try:
            if api_key:
                orig_lat = b_info['lat'] - 0.008
                orig_lon = b_info['lon'] - 0.008
                dest_lat = b_info['lat']
                dest_lon = b_info['lon']

                url = (f"https://maps.googleapis.com/maps/api/distancematrix/json?"
                       f"origins={orig_lat},{orig_lon}&destinations={dest_lat},{dest_lon}"
                       f"&departure_time=now&key={api_key}")

                res = requests.get(url, timeout=5).json()
                element = res.get('rows', [{}])[0].get('elements', [{}])[0]

                if element.get('status') == 'OK':
                    distance_m = element.get('distance', {}).get('value', 1000)
                    dur_norm = element.get('duration', {}).get('value', 60)
                    dur_traf = element.get('duration_in_traffic', {}).get('value', dur_norm)

                    distance_km = distance_m / 1000.0
                    hours_traf = dur_traf / 3600.0

                    speed_kmh = round(distance_km / hours_traf) if hours_traf > 0 else 55
                    speed_kmh = max(5, min(speed_kmh, 110))

                    delay_sec = max(0, dur_traf - dur_norm)
                    delay_min = round(delay_sec / 60)

                    if dur_traf > dur_norm * 1.8 or speed_kmh < 15:
                        status_str = '🔴 Закритий / Критично'
                        speed_kmh = 0
                    elif dur_traf > dur_norm * 1.35 or speed_kmh < 30:
                        status_str = '🟡 Ускладнено / Затор'
                    else:
                        status_str = '🟢 Вільно (Рух йде)'
                else:
                    status_str = '🟡 Обмеження даних API'
            else:
                status_str = '🔴 Відсутній ключ API'
                source_desc = 'Введіть ключ у сайдбарі'

        except Exception as e:
            status_str = '🟡 Помилка запиту'
            source_desc = str(e)

        record = {
            'id': b_id,
            'name': b_info['name'],
            'region': b_info['region'],
            'state': status_str,
            'speed': speed_kmh,
            'delay': delay_min,
            'source': source_desc,
            'timestamp': timestamp_str
        }
        traffic_dict[b_id] = record
        st.session_state['history'].append(record)

    st.session_state['cached_data'] = traffic_dict
    st.session_state['last_update'] = now
    return traffic_dict

# --- Інтерфейс Streamlit ---
st.title("🌉 Оперативний моніторинг мостів та переправ України")
st.markdown("Моніторинг у реальному часі: швидкість потоку, затори, закриття, автоматичне оновлення кожні 30 хв та історія змін.")

# Бокова панель для введення або перевірки ключа API
st.sidebar.header("⚙️ Налаштування доступу")
input_key = st.sidebar.text_input("Google Maps API Key", type="password", value="")
active_api_key = get_resolved_api_key(input_key)

if active_api_key:
    st.sidebar.success("✅ Ключ API активний і застосовується!")
else:
    st.sidebar.warning("⚠️ Ключ не знайдено в secrets і не введено в полі.")

col_btn1, col_btn2, col_info = st.columns([1, 1, 2])
with col_btn1:
    if st.button("🔄 Оновити статуси зараз"):
        traffic_data = fetch_telemetry(active_api_key, force=True)
        st.success("Дані успішно оновлено!")
    else:
        traffic_data = fetch_telemetry(active_api_key, force=False)

with col_info:
    last_up = st.session_state.get('last_update')
    if last_up:
        st.info(f"Останнє опитування системи: {last_up.strftime('%Y-%m-%d %H:%M:%S')} (Автооновлення кожні 30 хв)")

# Відображення карток по мостах
st.markdown("### 📊 Поточний стан переправ мережі")
batch_items = list(traffic_data.items())
for i in range(0, len(batch_items), 4):
    cols = st.columns(4)
    for j, (b_id, data) in enumerate(batch_items[i:i+4]):
        with cols[j]:
            st.metric(
                label=f"{data['name']} ({data['region']})",
                value=f"{data['speed']} км/год",
                delta=f"{data['state']} (+{data['delay']} хв)"
            )

st.markdown("---")

# Таблиця поточного стану
st.subheader("📋 Реєстр переправ і параметрів трафіку")
table_rows = list(traffic_data.values())
df_current = pd.DataFrame(table_rows)
st.dataframe(df_current, use_container_width=True)

# Блок історії перевірок
st.markdown("---")
st.subheader("📜 Історія телеметрії за сесію")
if st.session_state['history']:
    df_history = pd.DataFrame(st.session_state['history'])
    st.dataframe(df_history.tail(20), use_container_width=True)
else:
    st.write("Історія формується...")
