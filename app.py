import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
import threading
import time
import io
from datetime import datetime, timezone, timedelta
import random
import re

st.set_page_config(page_title="Автономний логістичний моніторинг мостів", layout="wide")

# =========================================================
# ЧАСОВИЙ ПОЯС КИЄВА (UTC+3)
# =========================================================
KYIV_TZ = timezone(timedelta(hours=3))

def get_kyiv_now_str():
    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d %H:%M:%S")

# =========================================================
# БЛОК АВТОРИЗАЦІЇ
# =========================================================
def check_password():
    try:
        correct_user = st.secrets.get("credentials", {}).get("username", "admin")
        correct_pass = st.secrets.get("credentials", {}).get("password", "avrora2026")
    except Exception:
        correct_user = "admin"
        correct_pass = "avrora2026"

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("### 🔒 Вхід у систему")
            with st.form("login_form", clear_on_submit=False):
                st.text_input("Логін", key="input_username")
                st.text_input("Пароль", type="password", key="input_password")
                
                submit_button = st.form_submit_button("Увійти", use_container_width=True)

                if submit_button:
                    user_val = st.session_state.get("input_username", "")
                    pass_val = st.session_state.get("input_password", "")
                    
                    if user_val == correct_user and pass_val == correct_pass:
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("❌ Невірний логін або пароль")
        return False

    return True

if not check_password():
    st.stop()

with st.sidebar:
    st.write("👤 **Авторизовано**")
    if st.button("🚪 Вийти"):
        st.session_state["password_correct"] = False
        st.rerun()

# =========================================================
# БАЗА ДАНИХ 13 МОСТІВ ТА ГЕС (З РОЗШИРЕНИМИ ТРИГЕРАМИ)
# =========================================================
EXCEL_FILE = 'Робоча_модель_мережі_ФІНАЛ 1.xlsx'
HISTORY_FILE = 'bridge_history.csv'

BRIDGES = {
    'KYI_DARN': {'name': 'Дарницький міст (Київ)', 'coords': [(30.5891, 50.4168), (30.5978, 50.4152)], 'normal_speed': 50, 'query': 'Дарницький міст Київ перекрито удар аварія'},
    'KYI_SOUTH': {'name': 'Південний міст (Київ)', 'coords': [(30.5621, 50.3942), (30.5789, 50.3921)], 'normal_speed': 60, 'query': 'Південний міст Київ перекрито обмежено рух'},
    'KYI_NORTH': {'name': 'Північний міст (Київ)', 'coords': [(30.5352, 50.4908), (30.5521, 50.4912)], 'normal_speed': 60, 'query': 'Північний міст Київ перекрито аварія'},
    'KYI_HPP': {'name': 'Київська ГЕС (Вишгород)', 'coords': [(30.4912, 50.5885), (30.5051, 50.5889)], 'normal_speed': 40, 'query': 'Київська ГЕС Вишгород пошкоджено перекрито'},
    'KANIV_HPP': {'name': 'Канівська ГЕС (Канів)', 'coords': [(31.4682, 49.7612), (31.4791, 49.7625)], 'normal_speed': 50, 'query': 'Канівська ГЕС перекрито удар'},
    'CHK': {'name': 'Черкаський міст (Черкаси)', 'coords': [(32.0321, 49.4812), (32.0612, 49.4951)], 'normal_speed': 50, 'query': 'Черкаський міст через Дніпро перекрито аварія'},
    'KREM': {'name': 'Кременчуцький міст (Кременчук)', 'coords': [(33.4112, 49.0521), (33.4215, 49.0582)], 'normal_speed': 40, 'query': 'Кременчуцький міст перекрито пошкоджено'},
    'KAM_HPP': {'name': "Середньодніпровська ГЕС (Кам'янське)", 'coords': [(34.5421, 48.5521), (34.5512, 48.5582)], 'normal_speed': 40, 'query': "Середньодніпровська ГЕС Кам'янське перекрито"},
    'DNI_AMUR': {'name': 'Амурський міст (Дніпро)', 'coords': [(35.0251, 48.4851), (35.0298, 48.4891)], 'normal_speed': 40, 'query': 'Амурський міст Дніпро перекрито аварія'},
    'DNI_CENTR': {'name': 'Центральний міст (Дніпро)', 'coords': [(35.0512, 48.4712), (35.0589, 48.4782)], 'normal_speed': 50, 'query': 'Центральний міст Дніпро перекрито'},
    'DNI_SOUTH': {'name': 'Південний міст (Дніпро)', 'coords': [(35.1012, 48.4112), (35.1089, 48.4082)], 'normal_speed': 50, 'query': 'Південний міст Дніпро перекрито удар'},
    'ZP_PREOBR': {'name': 'Мости Преображенського (Запоріжжя)', 'coords': [(35.0812, 47.8312), (35.0921, 47.8351)], 'normal_speed': 40, 'query': 'Мости Преображенського Запоріжжя перекрито удар пошкоджено'},
    'ZP_NEW': {'name': 'Нові мостові переходи (Запоріжжя)', 'coords': [(35.0712, 47.8412), (35.0851, 47.8451)], 'normal_speed': 50, 'query': 'нові мости Запоріжжя перекрито рух удар'}
}

# =========================================================
# ГЛИБОКИЙ АВТОМАТИЧНИЙ АНАЛІЗАТОР (OSRM + MULTI-SOURCE SEARCH)
# =========================================================
def fetch_bridge_speed(coords, normal_speed):
    try:
        lon1, lat1 = coords[0]
        lon2, lat2 = coords[1]
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false&t={time.time()}"
        res = requests.get(url, timeout=5).json()
        if 'routes' in res and len(res['routes']) > 0:
            duration_sec = res['routes'][0]['duration']
            distance_m = res['routes'][0]['distance']
            if duration_sec > 0:
                base_speed = (distance_m / 1000) / (duration_sec / 3600)
                return round(base_speed, 1)
    except Exception:
        pass
    return normal_speed

def smart_autonomous_check(b_id, b_info, speed_threshold):
    """
    Повністю автономна перевірка: аналізує швидкість через OSRM 
    ТА шукає критичні згадки у відкритих джерелах/новинах.
    """
    spd = fetch_bridge_speed(b_info['coords'], b_info['normal_speed'])
    
    # Пошуковий запит для виявлення екстрених зведень (удар, перекриття, пошкодження)
    is_emergency_detected = False
    emergency_reason = ""
    
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(b_info['query'] + ' сьогодні новини')}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            html_lower = response.text.lower()
            critical_keywords = [
                'перекрито', 'обмежено рух', 'рух перекрито', 'рух заборонено', 
                'удар', 'влучання', 'пошкоджено міст', 'аварійне перекриття', 
                'зруйновано', 'вибух', 'приліт'
            ]
            for kw in critical_keywords:
                if kw in html_lower:
                    is_emergency_detected = True
                    emergency_reason = f"Сигнал тривоги в джерелах: '{kw}'"
                    break
    except Exception:
        pass

    # Визначення фінального статусу
    if is_emergency_detected:
        return 0.0, f"🔴 ЗАКРИТО (Авто-моніторинг: {emergency_reason})"
    elif spd <= speed_threshold:
        return spd, f"🟡 ЗАКРИТО (Авто: критичне падіння швидкості до {spd} км/год)"
    else:
        return spd, "🟢 Відкритий"

def save_speeds_to_history(data_payload):
    timestamp = get_kyiv_now_str()
    records = []
    for b_id, info in data_payload.items():
        records.append({
            'timestamp': timestamp,
            'bridge_id': b_id,
            'bridge_name': BRIDGES[b_id]['name'],
            'speed': info['speed'],
            'status': info['status']
        })
    df_new = pd.DataFrame(records)
    if os.path.exists(HISTORY_FILE):
        try:
            df_old = pd.read_csv(HISTORY_FILE)
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        except Exception:
            df_combined = df_new
    else:
        df_combined = df_new
    df_combined.to_csv(HISTORY_FILE, index=False)

def load_or_run_initial_check(speed_threshold):
    if not os.path.exists(HISTORY_FILE):
        payload = {}
        for b_id, b_info in BRIDGES.items():
            spd, status = smart_autonomous_check(b_id, b_info, speed_threshold)
            payload[b_id] = {'speed': spd, 'status': status}
        save_speeds_to_history(payload)
        return payload, get_kyiv_now_str()
    
    try:
        df_hist = pd.read_csv(HISTORY_FILE)
        if df_hist.empty:
            return {}, get_kyiv_now_str()
        latest_timestamp = df_hist['timestamp'].max()
        df_latest = df_hist[df_hist['timestamp'] == latest_timestamp]
        payload = {}
        for _, row in df_latest.iterrows():
            b_id = row['bridge_id']
            if b_id in BRIDGES:
                payload[b_id] = {'speed': row['speed'], 'status': row['status']}
        return payload, latest_timestamp
    except Exception:
        return {}, get_kyiv_now_str()

# Автоматичний фоновий потік оновлення даних кожні 10 хвилин
@st.cache_resource
def start_background_collector():
    def background_loop():
        while True:
            try:
                payload = {}
                for b_id, b_info in BRIDGES.items():
                    spd, status = smart_autonomous_check(b_id, b_info, 7.0)
                    payload[b_id] = {'speed': spd, 'status': status}
                save_speeds_to_history(payload)
            except Exception:
                pass
            time.sleep(10 * 60)

    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    return True

start_background_collector()

@st.cache_data
def load_excel_model(file_path):
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name='06A_Варіанти')

def recalculate_network(df_options, bridge_status_dict):
    bridge_cols = list(BRIDGES.keys()) + ['DIRECT']
    available_cols = [col for col in bridge_cols if col == 'DIRECT' or bridge_status_dict.get(col, True)]
            
    subset = df_options[available_cols]
    min_distances = subset.min(axis=1)
    best_routes = subset.idxmin(axis=1)
    
    base_dist = df_options['Базова відстань, км'].sum()
    scenario_dist = min_distances.sum()
    diff_dist = scenario_dist - base_dist
    diff_pct = (diff_dist / base_dist * 100) if base_dist > 0 else 0
    
    is_changed = best_routes != df_options['Базовий маршрут']
    
    df_details = df_options.copy()
    df_details['Новий маршрут'] = best_routes
    df_details['Нова відстань, км'] = min_distances
    df_details['Різниця, км'] = df_details['Нова відстань, км'] - df_details['Базова відстань, км']
    
    bridge_names = {k: v['name'] for k, v in BRIDGES.items()}
    bridge_names['DIRECT'] = 'Прямий маршрут (Без мосту)'
    
    df_details['Базовий маршрут (Назва)'] = df_details['Базовий маршрут'].map(bridge_names).fillna(df_details['Базовий маршрут'])
    df_details['Новий маршрут (Назва)'] = df_details['Новий маршрут'].map(bridge_names).fillna(df_details['Новий маршрут'])
    
    return {
        'base_dist': round(base_dist, 2),
        'scenario_dist': round(scenario_dist, 2),
        'diff_dist': round(diff_dist, 2),
        'diff_pct': round(diff_pct, 2),
        'changed_routes': int(is_changed.sum()),
        'df_changed': df_details[is_changed].copy(),
        'df_details': df_details
    }

# =========================================================
# ІНТЕРФЕЙС
# =========================================================
st.title("🌁 Автономний моніторинг мостів та логістичних ризиків")

try:
    df_options = load_excel_model(EXCEL_FILE)
except Exception as e:
    st.error(f"Помилка завантаження файлу '{EXCEL_FILE}': {e}")
    st.stop()

st.sidebar.header("⚙ Налаштування системи")
speed_threshold = st.sidebar.slider("Поріг швидкості затору (км/год):", min_value=3, max_value=12, value=7)

current_payload, last_time = load_or_run_initial_check(speed_threshold)
st.sidebar.info(f"🕒 Авто-синхронізація: **{last_time}**")

if st.sidebar.button("🔄 Оновити всі дані (Сканувати мережу та новини)", use_container_width=True):
    with st.spinner("Пошук нових загроз та аналіз пропускної здатності мостів..."):
        new_payload = {}
        for b_id, b_info in BRIDGES.items():
            spd, status = smart_autonomous_check(b_id, b_info, speed_threshold)
            new_payload[b_id] = {'speed': spd, 'status': status}
        save_speeds_to_history(new_payload)
        st.success("✅ Дані оновлено успішно!")
        st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🎛 Ручний запобіжник (резерв)")
bridge_status = {}
for b_id, b_info in BRIDGES.items():
    bridge_info = current_payload.get(b_id, {'speed': b_info['normal_speed'], 'status': '🟢 Відкритий'})
    is_currently_closed = 'ЗАКРИТО' in bridge_info['status']
    
    force_closed = st.sidebar.checkbox(f"⛔ Блокувати: {b_info['name']}", value=is_currently_closed, key=f"force_{b_id}")
    
    if force_closed:
        bridge_status[b_id] = False
    else:
        bridge_status[b_id] = not is_currently_closed

results = recalculate_network(df_options, bridge_status)

# Вкладки
tab1, tab2, tab3 = st.tabs([
    "📊 Логістичний аналіз мережі", 
    "🌁 Стан мостів (Авто-моніторинг)", 
    "📜 Історія звітів"
])

with tab1:
    st.subheader("📈 Вплив закритих мостів на добовий пробіг мережі")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Базовий пробіг", f"{results['base_dist']:,.1f} км/день")
    c2.metric("Пробіг сценарію", f"{results['scenario_dist']:,.1f} км/день", delta=f"{results['diff_dist']:,.1f} км", delta_color="inverse")
    c3.metric("Приріст пробігу", f"{results['diff_pct']}%", delta=f"{results['diff_pct']}%", delta_color="inverse")
    c4.metric("Перепризначено маршрутів", f"{results['changed_routes']}")
    
    st.divider()
    closed_bridges = [BRIDGES[b]['name'] for b, is_open in bridge_status.items() if not is_open]
    if closed_bridges:
        st.error(f"🚨 **УВАГА! У модель закладено перекриття:**\n* " + "\n* ".join(closed_bridges))
    else:
        st.success("🟢 Усі мости функціонують.")

    st.subheader(f"🔄 Перепризначені маршрути ({results['changed_routes']})")
    df_changed = results['df_changed']
    if not df_changed.empty:
        cols = ['Код ТТ', 'Адреса ТТ', 'Населений пункт', 'Базовий маршрут (Назва)', 'Новий маршрут (Назва)', 'Базова відстань, км', 'Нова відстань, км', 'Різниця, км']
        display_cols = [c for c in cols if c in df_changed.columns] or list(df_changed.columns[:8])
        st.dataframe(df_changed[display_cols].sort_values(by='Різниця, км', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Перепризначень немає.")

with tab2:
    st.subheader("📋 Автоматичний статус переходів у реальному часі")
    table_data = []
    for b_id, b_info in BRIDGES.items():
        info = current_payload.get(b_id, {'speed': b_info['normal_speed'], 'status': '🟢 Відкритий'})
        table_data.append({
            'ID': b_id,
            'Міст / ГЕС': b_info['name'],
            'Швидкість (км/год)': info['speed'],
            'Статус системи': info['status']
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)

with tab3:
    st.subheader("📜 Архів історії сканувань")
    if os.path.exists(HISTORY_FILE):
        df_hist = pd.read_csv(HISTORY_FILE).sort_values(by='timestamp', ascending=False)
        if not df_hist.empty:
            sel_bridge = st.selectbox("Оберіть об'єкт для аналізу динаміки:", df_hist['bridge_name'].unique())
            df_filtered = df_hist[df_hist['bridge_name'] == sel_bridge]
            
            fig = px.line(df_filtered, x='timestamp', y='speed', title=f"Динаміка: {sel_bridge}", markers=True)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
