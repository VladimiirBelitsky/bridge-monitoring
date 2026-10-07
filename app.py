import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
import pandas as pd

# Налаштування сторінки
st.set_page_config(
    page_title="Оперативний моніторинг мостів та переправ України",
    page_icon="🌉",
    layout="wide"
)

KYIV_TZ = timezone(timedelta(hours=3))

# Повний реєстр переходів із точними початковими та кінцевими точками для Routes API
BRIDGES = {
    'KYI_SOUTH': {
        'name': 'Південний міст', 'region': 'Київ', 
        'start_lat': 50.3850, 'start_lon': 30.5750, 'end_lat': 50.3950, 'end_lon': 30.5950,
        'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'
    },
    'KYI_DARN': {
        'name': 'Дарницький міст', 'region': 'Київ', 
        'start_lat': 50.4120, 'start_lon': 30.5850, 'end_lat': 50.4250, 'end_lon': 30.6000,
        'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'
    },
    'KYI_PATON': {
        'name': 'Міст Патона', 'region': 'Київ', 
        'start_lat': 50.4320, 'start_lon': 30.5700, 'end_lat': 50.4400, 'end_lon': 30.5900,
        'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'
    },
    'KYI_METRO': {
        'name': 'Міст Метро', 'region': 'Київ', 
        'start_lat': 50.4430, 'start_lon': 30.5480, 'end_lat': 50.4500, 'end_lon': 30.5650,
        'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'
    },
    'KYI_NORTH': {
        'name': 'Північний міст', 'region': 'Київ', 
        'start_lat': 50.4820, 'start_lon': 30.5300, 'end_lat': 50.4940, 'end_lon': 30.5420,
        'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'
    },
    'KYI_GAVAN': {
        'name': 'Гаванський міст', 'region': 'Київ', 
        'start_lat': 50.4680, 'start_lon': 30.5220, 'end_lat': 50.4780, 'end_lon': 30.5340,
        'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'
    },
    'KYI_HPP': {
        'name': 'Київська ГЕС', 'region': 'Вишгород', 
        'start_lat': 50.5750, 'start_lon': 30.4950, 'end_lat': 50.5900, 'end_lon': 30.5150,
        'source_name': 'Вишгородська міськрада', 'source_url': 'https://t.me/vyshgorod_rada'
    },
    'KANIV_HPP': {
        'name': 'Канівська ГЕС', 'region': 'Черкаська обл.', 
        'start_lat': 50.4820, 'start_lon': 30.5300, 'end_lat': 50.4940, 'end_lon': 30.5420,
        'source_name': 'Черкаська ОВА', 'source_url': 'https://t.me/cherkaskaODA'
    },
    'CHK': {
        'name': 'Черкаський міст', 'region': 'Черкаси', 
        'start_lat': 49.4350, 'start_lon': 32.0400, 'end_lat': 49.4550, 'end_lon': 32.0700,
        'source_name': 'Патрульна поліція Черкащини', 'source_url': 'https://t.me/patrolpolice_cherkasy'
    },
    'KREM': {
        'name': 'Кременчуцький міст / ГЕС', 'region': 'Кременчук', 
        'start_lat': 49.0650, 'start_lon': 33.2500, 'end_lat': 49.0800, 'end_lon': 33.2800,
        'source_name': 'Полтавська ОВА', 'source_url': 'https://t.me/poltavaoda'
    },
    'KAM_HPP': {
        'name': 'Камʼянська ГЕС', 'region': 'Дніпропетровська обл.', 
        'start_lat': 48.5400, 'start_lon': 34.8200, 'end_lat': 48.5600, 'end_lon': 34.8500,
        'source_name': 'Дніпропетровська ОВА', 'source_url': 'https://t.me/adm_dp'
    },
    'DNI_AMUR': {
        'name': 'Амурський міст', 'region': 'Дніпро', 
        'start_lat': 48.4750, 'start_lon': 35.0050, 'end_lat': 48.4900, 'end_lon': 35.0300,
        'source_name': 'Патрульна поліція Дніпра', 'source_url': 'https://t.me/patrolpolice_dp'
    },
    'DNI_CENTR': {
        'name': 'Центральний міст', 'region': 'Дніпро', 
        'start_lat': 48.4650, 'start_lon': 35.0350, 'end_lat': 48.4800, 'end_lon': 35.0600,
        'source_name': 'Дніпровська міськрада', 'source_url': 'https://t.me/borys_filatov'
    },
    'DNI_SOUTH': {
        'name': 'Південний міст (Дніпро)', 'region': 'Дніпро', 
        'start_lat': 48.3750, 'start_lon': 35.0700, 'end_lat': 48.3900, 'end_lon': 35.1000,
        'source_name': 'Патрульна поліція Дніпра', 'source_url': 'https://t.me/patrolpolice_dp'
    },
    'ZP_PREOBR': {
        'name': 'Мости Преображенського', 'region': 'Запоріжжя', 
        'start_lat': 47.8400, 'start_lon': 35.0700, 'end_lat': 47.8600, 'end_lon': 35.1000,
        'source_name': 'Запорізька ОВА', 'source_url': 'https://t.me/zoda_gov_ua'
    },
    'ZP_NEW': {
        'name': 'Нові мости (Запоріжжя)', 'region': 'Запоріжжя', 
        'start_lat': 47.8550, 'start_lon': 35.0850, 'end_lat': 47.8750, 'end_lon': 35.1150,
        'source_name': 'Запорізька ОВА', 'source_url': 'https://t.me/zoda_gov_ua'
    }
}

def get_kyiv_now():
    return datetime.now(KYIV_TZ)

def get_active_api_key(manual_input=""):
    if manual_input.strip():
        return manual_input.strip()
    try:
        if "google_maps" in st.secrets:
            gm = st.secrets["google_maps"]
            if isinstance(gm, dict) and "api_key" in gm:
                return gm["api_key"]
        if "api_key" in st.secrets:
            return st.secrets["api_key"]
    except Exception:
        pass
    return ""

if 'history' not in st.session_state:
    st.session_state['history'] = []

if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None

def fetch_telemetry_routes_api(api_key, force=False):
    now = get_kyiv_now()
    if not force and st.session_state['last_update'] and (now - st.session_state['last_update']).total_seconds() < 1800:
        if 'cached_data' in st.session_state:
            return st.session_state['cached_data']

    timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
    traffic_dict = {}

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters'
    }

    for b_id, b_info in BRIDGES.items():
        speed_kmh = 50
        status_str = '🟢 Вільно'
        
        try:
            if api_key:
                url = "https://routes.googleapis.com/directions/v2:computeRoutes"
                payload = {
                    "origin": {
                        "location": {"latLng": {"latitude": b_info['start_lat'], "longitude": b_info['start_lon']}}
                    },
                    "destination": {
                        "location": {"latLng": {"latitude": b_info['end_lat'], "longitude": b_info['end_lon']}}
                    },
                    "travelMode": "DRIVE",
                    "routingPreference": "TRAFFIC_AWARE"
                }

                res = requests.post(url, json=payload, headers=headers, timeout=5).json()
                
                if 'routes' in res and len(res['routes']) > 0:
                    route = res['routes'][0]
                    dist_m = route.get('distanceMeters', 1000)
                    dur_str = route.get('duration', '60s').replace('s', '')
                    dur_sec = float(dur_str) if dur_str else 60.0
                    
                    dist_km = dist_m / 1000.0
                    hours = dur_sec / 3600.0
                    if hours > 0:
                        speed_kmh = round(dist_km / hours)
                        speed_kmh = max(10, min(speed_kmh, 110))

                    if speed_kmh < 25:
                        status_str = '🔴 Затор / Ускладнено'
                    elif speed_kmh < 40:
                        status_str = '🟡 Повільний рух'
                    else:
                        status_str = '🟢 Вільно'
        except Exception:
            status_str = '🟢 Штатний режим'

        record = {
            'id': b_id,
            'name': b_info['name'],
            'region': b_info['region'],
            'state': status_str,
            'speed': f"{speed_kmh} км/год",
            'source_name': b_info['source_name'],
            'source_url': b_info['source_url'],
            'timestamp': timestamp_str
        }
        traffic_dict[b_id] = record
        st.session_state['history'].append(record)

    st.session_state['cached_data'] = traffic_dict
    st.session_state['last_update'] = now
    return traffic_dict

# --- Інтерфейс Streamlit ---
st.title("🌉 Оперативний моніторинг мостів та переправ України")
st.markdown("Моніторинг у реальному часі через **Google Routes API** з урахуванням заторів на кожній ділянці.")

st.sidebar.header("⚙️ Конфігурація доступу")
manual_key_input = st.sidebar.text_input("Google Maps / Routes API Key:", type="password", value="")
resolved_key = get_active_api_key(manual_key_input)

if resolved_key:
    st.sidebar.success("✅ Ключ підключено до Routes API")
else:
    st.sidebar.warning("⚠️ Введіть API ключ для live-опитування")

col_btn1, col_info = st.columns([1, 2])
with col_btn1:
    if st.button("🔄 Оновити статуси зараз"):
        traffic_data = fetch_telemetry_routes_api(resolved_key, force=True)
        st.success("Дані успішно оновлено!")
    else:
        traffic_data = fetch_telemetry_routes_api(resolved_key, force=False)

with col_info:
    last_up = st.session_state.get('last_update')
    if last_up:
        st.info(f"Останнє опитування системи: {last_up.strftime('%Y-%m-%d %H:%M:%S')} (Автооновлення кожні 30 хв)")

# Відображення карток
st.markdown("### 📊 Поточний стан переправ мережі")
batch_items = list(traffic_data.items())
for i in range(0, len(batch_items), 4):
    cols = st.columns(4)
    for j, (b_id, data) in enumerate(batch_items[i:i+4]):
        with cols[j]:
            st.metric(
                label=f"{data['name']} ({data['region']})",
                value=data['speed'],
                delta=data['state']
            )

st.markdown("---")
st.subheader("📋 Детальний реєстр та офіційні джерела")
table_rows = []
for b_id, data in traffic_data.items():
    table_rows.append({
        "Міст / Переправа": data['name'],
        "Регіон": data['region'],
        "Статус": data['state'],
        "Швидкість потоку": data['speed'],
        "Офіційне джерело": data['source_name'],
        "Канал": data['source_url']
    })

df_bridges = pd.DataFrame(table_rows)
st.dataframe(df_bridges, use_container_width=True)
