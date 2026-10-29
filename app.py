import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
import pandas as pd
import os
import time
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Оперативний моніторинг мостів та переправ України",
    page_icon="🌉",
    layout="wide"
)

# Автоматичне оновлення сторінки раз на 30 хвилин
st_autorefresh(interval=30 * 60 * 1000, key="datarefresh")

KYIV_TZ = timezone(timedelta(hours=3))
HISTORY_FILE = "bridges_traffic_log.csv"  # Уніфіковано назву файлу з основінм скриптом

# Реєстр 16 критичних вузлів з точними координатами та еталонними відстанями
BRIDGES = {
    'KYI_SOUTH': {
        'name': 'Південний міст', 'region': 'Київ', 
        'start_lat': 50.398383, 'start_lon': 30.567013, 
        'end_lat': 50.394345, 'end_lon': 30.599063,
        'baseline_km': 2.8,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_DARN': {
        'name': 'Дарницький міст', 'region': 'Київ', 
        'start_lat': 50.418943, 'start_lon': 30.597587, 
        'end_lat': 50.413308, 'end_lon': 30.575035, 
        'baseline_km': 2.3,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_PATON': {
        'name': 'Міст Патона', 'region': 'Київ', 
        'start_lat': 50.430015, 'start_lon': 30.591375, 
        'end_lat': 50.424265, 'end_lon': 30.571904, 
        'baseline_km': 2.1,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_METRO': {
        'name': 'Міст Метро', 'region': 'Київ', 
        'start_lat': 50.441491, 'start_lon': 30.560397, 
        'end_lat': 50.445658, 'end_lon': 30.575147, 
        'baseline_km': 2.0,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_NORTH': {
        'name': 'Північний міст', 'region': 'Київ', 
        'start_lat': 50.4890, 'start_lon': 30.5310, 
        'end_lat': 50.4960, 'end_lon': 30.5620, 
        'baseline_km': 2.5,
        'source_name': 'Google Maps API', 'source_url': 'https://maps.google.com'
    },
    'KYI_GAVAN': {
        'name': 'Гаванський міст', 'region': 'Київ', 
        'start_lat': 50.467400, 'start_lon': 30.524984, 
        'end_lat': 50.475162, 'end_lon': 30.534496, 
        'baseline_km': 1.5,
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
        'name': 'Кременчуцький міст / ГЕС', 'region': 'Кременчук', 
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

def get_kyiv_now():
    return datetime.now(timezone.utc) + timedelta(hours=3)

def get_active_api_key(manual_input=""):
    if manual_input and manual_input.strip():
        return manual_input.strip()
    try:
        if "google_maps" in st.secrets and "api_key" in st.secrets["google_maps"]:
            key = st.secrets["google_maps"]["api_key"]
            if key:
                return key.strip()
        if "api_key" in st.secrets:
            key = st.secrets["api_key"]
            if key:
                return key.strip()
    except Exception:
        pass
    return ""

def save_to_history_csv(records_list):
    df_new = pd.DataFrame(records_list)
    if os.path.exists(HISTORY_FILE):
        df_new.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')

def load_history_csv():
    if os.path.exists(HISTORY_FILE):
        try:
            return pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        except Exception:
            pass
        try:
            return pd.read_csv(HISTORY_FILE, encoding='cp1251')
        except Exception:
            pass
    return pd.DataFrame(columns=['timestamp', 'id', 'name', 'region', 'state', 'speed', 'source_name', 'source_url'])

def fetch_routes_api_telemetry(api_key):
    now = get_kyiv_now()
    timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
    traffic_dict = {}
    
    if not api_key:
        for b_id, b_info in BRIDGES.items():
            traffic_dict[b_id] = {
                'timestamp': timestamp_str, 'id': b_id, 'name': b_info['name'],
                'region': b_info['region'], 'state': '⚠️ Потрібен дійсний API ключ',
                'speed': 'Н/Д', 'source_name': b_info['source_name'], 'source_url': b_info['source_url']
            }
        return traffic_dict

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters'
    }

    batch_records = []
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    for b_id, b_info in BRIDGES.items():
        speed_str = "Н/Д"
        status_str = "❌ Немає зв'язку з API"
        
        for attempt in range(3):
            try:
                payload = {
                    "origin": {"location": {"latLng": {"latitude": b_info['start_lat'], "longitude": b_info['start_lon']}}},
                    "destination": {"location": {"latLng": {"latitude": b_info['end_lat'], "longitude": b_info['end_lon']}}},
                    "travelMode": "DRIVE",
                    "routingPreference": "TRAFFIC_AWARE"
                }
                res = requests.post(url, json=payload, headers=headers, timeout=8).json()
                
                if 'routes' in res and len(res['routes']) > 0:
                    route = res['routes'][0]
                    dist_m = route.get('distanceMeters', 0)
                    dur_str = str(route.get('duration', '0s')).replace('s', '')
                    dur_sec = float(dur_str) if dur_str else 0.0
                    
                    if dist_m > 0:
                        dist_km = dist_m / 1000.0
                        
                        # Математичний детектор закриття мосту за відстаню
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
                    break
                elif 'error' in res:
                    err_code = res['error'].get('code', 'Unknown')
                    if err_code == 429:
                        status_str = "❌ Ліміт запитів (429), повторюємо..."
                        time.sleep(3.0 * (attempt + 1))
                        continue
                    else:
                        status_str = f"❌ API Error {err_code}"
                        break
                break
            except Exception:
                status_str = "❌ Помилка мережі"
                time.sleep(1.5)

        time.sleep(1.0)

        record = {
            'timestamp': timestamp_str, 'id': b_id, 'name': b_info['name'],
            'region': b_info['region'], 'state': status_str, 'speed': speed_str,
            'source_name': b_info['source_name'], 'source_url': b_info['source_url']
        }
        traffic_dict[b_id] = record
        batch_records.append(record)

    save_to_history_csv(batch_records)
    return traffic_dict

# --- Інтерфейс ---
st.title("🌉 Оперативний моніторинг мостів та переправ України")
st.markdown("Контроль трафіку на основі **сучасного Routes API та геометричного детектора**.")

st.sidebar.header("⚙️ Конфігурація доступу")
manual_key_input = st.sidebar.text_input("Routes API Key (якщо треба перевизначити):", type="password", value="")
resolved_key = get_active_api_key(manual_key_input)

if resolved_key:
    st.sidebar.success("✅ Ключ активний в системі")
else:
    st.sidebar.warning("⚠️ Потрібен API ключ для реальних даних")

tab_live, tab_history = st.tabs(["📊 Оперативна панель (Live)", "📈 Архів та історія"])

with tab_live:
    col_btn1, col_info = st.columns([1, 2])
    with col_btn1:
        if st.button("🔄 Оновити зріз з Google Maps"):
            with st.spinner("Збираємо телеметрію по 16 вузлах..."):
                st.session_state['cached_live'] = fetch_routes_api_telemetry(resolved_key)
            st.success("Дані успішно оновлено!")
        else:
            # Якщо в кеші нічого немає, підтягуємо найсвіжіші дані з CSV-файлу історії
            if 'cached_live' not in st.session_state or not st.session_state['cached_live']:
                df_hist = load_history_csv()
                if not df_hist.empty:
                    # Беремо останній зафіксований стан для кожного мосту
                    df_latest = df_hist.sort_values('timestamp').groupby('id').tail(1)
                    st.session_state['cached_live'] = {row['id']: row.to_dict() for _, row in df_latest.iterrows()}
                else:
                    st.session_state['cached_live'] = fetch_routes_api_telemetry(resolved_key)

    with col_info:
        st.info(f"Поточний час Києва: {get_kyiv_now().strftime('%Y-%m-%d %H:%M:%S')}")

    traffic_data = st.session_state.get('cached_live', {})
    if traffic_data:
        st.markdown("### 📊 Поточний стан мостової мережі (Live)")
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
        st.subheader("📋 Реєстр вузлів та офіційні джерела верифікації")
        table_rows = [{
            "Міст / Переправа": d['name'], "Регіон": d['region'], "Статус": d['state'],
            "Швидкість": d['speed'], "Джерело": d['source_name'], "Канал": d['source_url']
        } for d in traffic_data.values()]
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

with tab_history:
    st.subheader("🗂 Архів зібраних зрізів телеметрії")
    df_hist = load_history_csv()
    
    if not df_hist.empty:
        df_hist['dt'] = pd.to_datetime(df_hist['timestamp'], errors='coerce')
        
        time_filter = st.selectbox(
            "Глибина перегляду архіву:", 
            ["Останні 24 години", "Останні 7 днів", "Останній місяць (30 днів)", "За весь час"],
            index=2
        )
        
        now_dt = pd.Timestamp(get_kyiv_now().replace(tzinfo=None))
        if time_filter == "Останні 24 години":
            df_hist = df_hist[df_hist['dt'] >= (now_dt - timedelta(days=1))]
        elif time_filter == "Останні 7 днів":
            df_hist = df_hist[df_hist['dt'] >= (now_dt - timedelta(days=7))]
        elif time_filter == "Останній місяць (30 днів)":
            df_hist = df_hist[df_hist['dt'] >= (now_dt - timedelta(days=30))]

        selected_bridge = st.selectbox("Оберіть міст для аналізу ретроспективи:", df_hist['name'].unique() if not df_hist.empty else [])
        
        if selected_bridge:
            filtered_df = df_hist[df_hist['name'] == selected_bridge].sort_values(by='timestamp', ascending=False)
            st.markdown(f"**Історичні записи для обʼєкта: {selected_bridge} (знайдено записів: {len(filtered_df)})**")
            st.dataframe(filtered_df[['timestamp', 'region', 'state', 'speed', 'source_name']], use_container_width=True)
        
        st.markdown("---")
        st.download_button(
            label="📥 Завантажити повний архів історії (CSV)",
            data=df_hist.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
            file_name="bridges_traffic_history_full.csv",
            mime="text/csv"
        )
    else:
        st.info("Архів поки порожній. Натисніть кнопку «Оновити зріз з Google Maps».")
