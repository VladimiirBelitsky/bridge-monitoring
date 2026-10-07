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
HISTORY_FILE = "traffic_history.csv"

# Реєстр 16 критичних вузлів
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

def fetch_distance_matrix_telemetry(api_key):
    """
    Використовує Google Distance Matrix API для масового збору даних за один запит.
    Це повністю вирішує проблему лімітів (оскільки запит один, а не 16 окремих).
    """
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

    # Формуємо списки координат для масового запиту в Distance Matrix
    origins = []
    destinations = []
    bridge_ids = list(BRIDGES.keys())

    for b_id in bridge_ids:
        b = BRIDGES[b_id]
        origins.append(f"{b['start_lat']},{b['start_lon']}")
        destinations.append(f"{b['end_lat']},{b['end_lon']}")

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "|".join(origins),
        "destinations": "|".join(destinations),
        "mode": "driving",
        "departure_time": "now",
        "traffic_model": "pessimistic",
        "key": api_key
    }

    batch_records = []
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") == "OK":
            rows = data.get("rows", [])
            for i, b_id in enumerate(bridge_ids):
                b_info = BRIDGES[b_id]
                speed_str = "Н/Д"
                status_str = "❌ Дані недоступні"

                try:
                    element = rows[i]["elements"][i]  # Зіставляємо origin[i] з destination[i] за індексом
                    if element.get("status") == "OK":
                        dist_m = element.get("distance", {}).get("value", 0)
                        # Використовуємо duration_in_traffic, якщо є звіт про затори, інакше звичайний duration
                        dur_sec = element.get("duration_in_traffic", {}).get("value", element.get("duration", {}).get("value", 0))

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
                    else:
                        status_str = f"❌ Статус елемента: {element.get('status')}"
                except Exception:
                    status_str = "❌ Помилка розбору елемента"

                record = {
                    'timestamp': timestamp_str, 'id': b_id, 'name': b_info['name'],
                    'region': b_info['region'], 'state': status_str, 'speed': speed_str,
                    'source_name': b_info['source_name'], 'source_url': b_info['source_url']
                }
                traffic_dict[b_id] = record
                batch_records.append(record)
        else:
            err_msg = data.get("error_message", data.get("status", "Unknown Error"))
            for b_id, b_info in BRIDGES.items():
                record = {
                    'timestamp': timestamp_str, 'id': b_id, 'name': b_info['name'],
                    'region': b_info['region'], 'state': f"❌ Помилка API: {err_msg}", 'speed': 'Н/Д',
                    'source_name': b_info['source_name'], 'source_url': b_info['source_url']
                }
                traffic_dict[b_id] = record
                batch_records.append(record)
    except Exception as e:
        for b_id, b_info in BRIDGES.items():
            record = {
                'timestamp': timestamp_str, 'id': b_id, 'name': b_info['name'],
                'region': b_info['region'], 'state': "❌ Помилка мережі", 'speed': 'Н/Д',
                'source_name': b_info['source_name'], 'source_url': b_info['source_url']
            }
            traffic_dict[b_id] = record
            batch_records.append(record)

    save_to_history_csv(batch_records)
    return traffic_dict

# --- Інтерфейс ---
st.title("🌉 Оперативний моніторинг мостів та переправ України")
st.markdown("Строгий контроль трафіку на основі **масових даних Google Distance Matrix API (без симуляцій)**.")

st.sidebar.header("⚙️ Конфігурація доступу")
manual_key_input = st.sidebar.text_input("Google Maps API Key (якщо треба перевизначити):", type="password", value="")
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
            st.session_state['cached_live'] = fetch_distance_matrix_telemetry(resolved_key)
            st.success("Дані успішно оновлено через Distance Matrix API!")
        else:
            if 'cached_live' not in st.session_state:
                st.session_state['cached_live'] = fetch_distance_matrix_telemetry(resolved_key)

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
