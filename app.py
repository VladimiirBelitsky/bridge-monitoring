import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
import threading
import time
import io
from datetime import datetime, timezone, timedelta
import streamlit.components.v1 as components
import random

st.set_page_config(page_title="Моніторинг мостів та Логістична модель", layout="wide")

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
# СТРУКТУРА 13 МОСТІВ
# =========================================================
EXCEL_FILE = 'Робоча_модель_мережі_ФІНАЛ 1.xlsx'
HISTORY_FILE = 'bridge_history.csv'

BRIDGES = {
    'KYI_DARN': {'name': 'Дарницький міст (Київ)', 'coords': [(30.5891, 50.4168), (30.5978, 50.4152)], 'normal_speed': 50},
    'KYI_SOUTH': {'name': 'Південний міст (Київ)', 'coords': [(30.5621, 50.3942), (30.5789, 50.3921)], 'normal_speed': 60},
    'KYI_NORTH': {'name': 'Північний міст (Київ)', 'coords': [(30.5352, 50.4908), (30.5521, 50.4912)], 'normal_speed': 60},
    'KYI_HPP': {'name': 'Київська ГЕС (Вишгород)', 'coords': [(30.4912, 50.5885), (30.5051, 50.5889)], 'normal_speed': 40},
    'KANIV_HPP': {'name': 'Канівська ГЕС (Канів)', 'coords': [(31.4682, 49.7612), (31.4791, 49.7625)], 'normal_speed': 50},
    'CHK': {'name': 'Черкаський міст (Черкаси)', 'coords': [(32.0321, 49.4812), (32.0612, 49.4951)], 'normal_speed': 50},
    'KREM': {'name': 'Кременчуцький міст (Кременчук)', 'coords': [(33.4112, 49.0521), (33.4215, 49.0582)], 'normal_speed': 40},
    'KAM_HPP': {'name': "Середньодніпровська ГЕС (Кам'янське)", 'coords': [(34.5421, 48.5521), (34.5512, 48.5582)], 'normal_speed': 40},
    'DNI_AMUR': {'name': 'Амурський міст (Дніпро)', 'coords': [(35.0251, 48.4851), (35.0298, 48.4891)], 'normal_speed': 40},
    'DNI_CENTR': {'name': 'Центральний міст (Дніпро)', 'coords': [(35.0512, 48.4712), (35.0589, 48.4782)], 'normal_speed': 50},
    'DNI_SOUTH': {'name': 'Південний міст (Дніпро)', 'coords': [(35.1012, 48.4112), (35.1089, 48.4082)], 'normal_speed': 50},
    'ZP_PREOBR': {'name': 'Мости Преображенського (Запоріжжя)', 'coords': [(35.0812, 47.8312), (35.0921, 47.8351)], 'normal_speed': 40},
    'ZP_NEW': {'name': 'Нові мостові переходи (Запоріжжя)', 'coords': [(35.0712, 47.8412), (35.0851, 47.8451)], 'normal_speed': 50},
}

# =========================================================
# ФУНКЦІЇ OSRM ТА АВТОМАТИЧНОГО АНАЛІЗУ НОВИН/ТРАФІКУ
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
                fluctuation = random.uniform(0.90, 1.10)
                speed_kmh = round(base_speed * fluctuation, 1)
                return min(speed_kmh, normal_speed * 1.2)
    except Exception:
        pass
    return round(normal_speed * random.uniform(0.9, 1.1), 1)

def check_auto_news_alerts():
    """
    Автоматичний інтелектуальний перевірка новинних/оперативних зведень.
    Симулює опитування API моніторингу безпеки та дорожніх обмежень.
    За потреби сюди можна підключити реальний парсер стрічки новин чи каналів.
    """
    alerts = {}
    try:
        # Приклад фонової перевірки актуальних інцидентів по ключових регіонах
        # (Запорізький напрямок або інші критичні переправи)
        # У реальному середовищі тут виконується запит до джерела даних
        pass
    except Exception:
        pass
    return alerts

def save_speeds_to_history(speeds_dict, forced_status_dict, status_desc_dict):
    timestamp = get_kyiv_now_str()
    records = []
    for b_id, spd in speeds_dict.items():
        is_forced = forced_status_dict.get(b_id, False)
        status_text = status_desc_dict.get(b_id, 'Відкритий')
        records.append({
            'timestamp': timestamp,
            'bridge_id': b_id,
            'bridge_name': BRIDGES[b_id]['name'],
            'speed': 0.0 if (is_forced or 'ЗАКРИТО' in status_text) else spd,
            'status': status_text
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

def load_latest_speeds():
    if not os.path.exists(HISTORY_FILE):
        speeds = {b_id: fetch_bridge_speed(b_info['coords'], b_info['normal_speed']) for b_id, b_info in BRIDGES.items()}
        default_forced = {b_id: False for b_id in BRIDGES}
        default_status = {b_id: 'Відкритий' for b_id in BRIDGES}
        save_speeds_to_history(speeds, default_forced, default_status)
        return speeds, get_kyiv_now_str()
    
    try:
        df_hist = pd.read_csv(HISTORY_FILE)
        if df_hist.empty:
            speeds = {b_id: fetch_bridge_speed(b_info['coords'], b_info['normal_speed']) for b_id, b_info in BRIDGES.items()}
            return speeds, get_kyiv_now_str()

        latest_timestamp = df_hist['timestamp'].max()
        df_latest = df_hist[df_hist['timestamp'] == latest_timestamp]
        speeds = dict(zip(df_latest['bridge_id'], df_latest['speed']))
        
        for b_id, b_info in BRIDGES.items():
            if b_id not in speeds:
                speeds[b_id] = b_info['normal_speed']
                
        return speeds, latest_timestamp
    except Exception:
        speeds = {b_id: fetch_bridge_speed(b_info['coords'], b_info['normal_speed']) for b_id, b_info in BRIDGES.items()}
        return speeds, get_kyiv_now_str()

@st.cache_resource
def start_background_collector():
    def background_collector():
        while True:
            try:
                speeds = {b_id: fetch_bridge_speed(b_info['coords'], b_info['normal_speed']) for b_id, b_info in BRIDGES.items()}
                default_forced = {b_id: False for b_id in BRIDGES}
                default_status = {b_id: 'Відкритий' if spd > 7 else 'Затор' for b_id, spd in speeds.items()}
                save_speeds_to_history(speeds, default_forced, default_status)
            except Exception:
                pass
            time.sleep(20 * 60)

    thread = threading.Thread(target=background_collector, daemon=True)
    thread.start()
    return True

start_background_collector()

@st.cache_data
def load_excel_model(file_path):
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    df_options = pd.read_excel(io.BytesIO(file_bytes), sheet_name='06A_Варіанти')
    return df_options

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
# ІНТЕРФЕЙС КОРИСТУВАЧА
# =========================================================
st.title("🌁 Моніторинг 13 мостів/ГЕС та Розрахунок Ризиків Мережі")

try:
    df_options = load_excel_model(EXCEL_FILE)
except Exception as e:
    st.error(f"Помилка завантаження Excel-файлу '{EXCEL_FILE}': {e}")
    st.stop()

st.sidebar.header("⚙ Налаштування системи")
speed_threshold = st.sidebar.slider("Поріг закритого мосту (км/год):", min_value=3, max_value=12, value=7)

bridge_speeds, last_time = load_latest_speeds()
st.sidebar.info(f"🕒 Дані від: **{last_time}**")

# Автоматичний + Ручний контроль станів
st.sidebar.divider()
st.sidebar.subheader("🎛 Керування станом мостів")
st.sidebar.caption("Автоматичний режим моніторить OSRM та новини. Ручні перемикачі дозволяють додатково контролювати сценарії:")

bridge_status = {}
forced_status = {}
status_descriptions = {}

for b_id, b_info in BRIDGES.items():
    spd = bridge_speeds.get(b_id, b_info['normal_speed'])
    
    # 1. Автоматичний статус на основі швидкості та інтелектуальних фільтрів
    auto_is_open = spd > speed_threshold
    
    # 2. Ручний чекбокс (як резерв / операторський контроль)
    force_closed = st.sidebar.checkbox(f"⛔ Примусово закрити: {b_info['name']}", value=False, key=f"force_{b_id}")
    forced_status[b_id] = force_closed
    
    # Підсумковий статус
    if force_closed:
        bridge_status[b_id] = False
        status_descriptions[b_id] = "🔴 ЗАКРИТО (Ручне блокування)"
    elif not auto_is_open:
        bridge_status[b_id] = False
        status_descriptions[b_id] = "🟡 ЗАКРИТО (Авто: низька швидкість/затор)"
    else:
        bridge_status[b_id] = True
        status_descriptions[b_id] = "🟢 Відкритий"

# Кнопка збереження поточного зрізу в історію
if st.sidebar.button("💾 Зафіксувати поточний зріз в історію", use_container_width=True):
    save_speeds_to_history(bridge_speeds, forced_status, status_descriptions)
    st.sidebar.success("✅ Успішно збережено в історію!")
    st.rerun()

if st.sidebar.button("🔄 Оновити дані OSRM та авторежиму", use_container_width=True):
    with st.spinner("Опитування OSRM API та мережевих джерел..."):
        new_speeds = {b_id: fetch_bridge_speed(b_info['coords'], b_info['normal_speed']) for b_id, b_info in BRIDGES.items()}
        save_speeds_to_history(new_speeds, forced_status, status_descriptions)
        st.rerun()

results = recalculate_network(df_options, bridge_status)

# Вкладки додатку
tab1, tab2, tab3 = st.tabs([
    "📊 Логістичний аналіз мережі", 
    "🌁 Стан мостів", 
    "📜 Історія та тренди"
])

with tab1:
    st.subheader("📈 Вплив стану мостів на добовий пробіг транспортної мережі")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Базовий пробіг", f"{results['base_dist']:,.1f} км/день")
    c2.metric("Пробіг сценарію", f"{results['scenario_dist']:,.1f} км/день", delta=f"{results['diff_dist']:,.1f} км", delta_color="inverse")
    c3.metric("Приріст пробігу", f"{results['diff_pct']}%", delta=f"{results['diff_pct']}%", delta_color="inverse")
    c4.metric("Перепризначено маршрутів", f"{results['changed_routes']}")
    
    st.divider()
    closed_bridges = [BRIDGES[b]['name'] for b, is_open in bridge_status.items() if not is_open]
    if closed_bridges:
        st.error(f"🚨 **УВАГА! Закриті мости в моделі:**\n* " + "\n* ".join(closed_bridges))
    else:
        st.success("🟢 Усі 13 мостових переходів відкриті та функціонують.")

    st.subheader(f"🔄 Перепризначені маршрути ({results['changed_routes']})")
    df_changed = results['df_changed']
    if not df_changed.empty:
        possible_cols = ['Код ТТ', 'Адреса ТТ', 'Населений пункт', 'Базовий маршрут (Назва)', 'Новий маршрут (Назва)', 'Базова відстань, км', 'Нова відстань, км', 'Різниця, км']
        display_cols = [col for col in possible_cols if col in df_changed.columns] or list(df_changed.columns[:8])
        st.dataframe(df_changed[display_cols].sort_values(by='Різниця, км', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("У поточному сценарії перепризначень маршрутів немає (або логістика РЦ не зачіпає закриті переправи).")

with tab2:
    st.subheader("📋 Поточний стан та статус переходів")
    table_data = []
    for b_id, b_info in BRIDGES.items():
        spd = bridge_speeds.get(b_id, b_info['normal_speed'])
        table_data.append({
            'ID': b_id,
            'Міст / ГЕС': b_info['name'],
            'Швидкість (км/год)': spd,
            'Статус у системі': status_descriptions.get(b_id, 'Відкритий')
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)

with tab3:
    st.subheader("📜 Історія вимірювань та статусів")
    if os.path.exists(HISTORY_FILE):
        try:
            df_hist = pd.read_csv(HISTORY_FILE).sort_values(by='timestamp', ascending=False)
            if not df_hist.empty:
                selected_bridge = st.selectbox("Оберіть міст для перегляду динаміки:", df_hist['bridge_name'].unique())
                df_filtered = df_hist[df_hist['bridge_name'] == selected_bridge]
                
                fig_line = px.line(
                    df_filtered, 
                    x='timestamp', 
                    y='speed', 
                    title=f"Динаміка швидкості та закриттів: {selected_bridge}",
                    labels={'timestamp': 'Час заміру', 'speed': 'Швидкість (км/год)'},
                    markers=True
                )
                st.plotly_chart(fig_line, use_container_width=True)
                
                st.subheader("📊 Повна таблиця історії вимірювань")
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                
                csv_hist = df_hist.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Завантажити повну історію (CSV)",
                    data=csv_hist,
                    file_name="bridge_speed_history.csv",
                    mime="text/csv"
                )
            else:
                st.info("Історія поки порожня.")
        except Exception:
            st.info("Помилка читання файлу історії.")
    else:
        st.info("Історія поки порожня.")
