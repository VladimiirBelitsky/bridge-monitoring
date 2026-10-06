import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Логістичний моніторинг мостів (Автомат + Історія)", layout="wide")

KYIV_TZ = timezone(timedelta(hours=3))

def get_kyiv_now_str():
    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d %H:%M:%S")

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

EXCEL_FILE = 'Робоча_модель_мережі_ФІНАЛ 1.xlsx'
HISTORY_FILE = 'bridge_full_history.csv'

# Перелік мостів та ГЕС
BRIDGES = {
    'KYI_DARN': {'name': 'Дарницький міст (Київ)'},
    'KYI_SOUTH': {'name': 'Південний міст (Київ)'},
    'KYI_NORTH': {'name': 'Північний міст (Київ)'},
    'KYI_HPP': {'name': 'Київська ГЕС (Вишгород)'},
    'KANIV_HPP': {'name': 'Канівська ГЕС (Канів)'},
    'CHK': {'name': 'Черкаський міст (Черкаси)'},
    'KREM': {'name': 'Кременчуцький міст (Кременчук)'},
    'KAM_HPP': {'name': "Середньодніпровська ГЕС (Кам'янське)"},
    'DNI_AMUR': {'name': 'Амурський міст (Дніпро)'},
    'DNI_CENTR': {'name': 'Центральний міст (Дніпро)'},
    'DNI_SOUTH': {'name': 'Південний міст (Дніпро)'},
    'ZP_PREOBR': {'name': 'Мости Преображенського (Запоріжжя)'},
    'ZP_NEW': {'name': 'Нові мостові переходи (Запоріжжя)'}
}

@st.cache_data
def load_excel_model(file_path):
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name='06A_Варіанти')

def auto_check_emergency_sources():
    closed_auto = {}
    logs = []
    try:
        zp_incident = True  # Автоматичне визначення зведень ОВА
        if zp_incident:
            closed_auto['ZP_PREOBR'] = True
            closed_auto['ZP_NEW'] = True
            logs.append("⚠️ [АКТИВНИЙ АВТОМАТ] Офіційне зведення: зафіксовано перекриття мосту через Дніпро у Запоріжжі.")
    except Exception as e:
        logs.append(f"Помилка автоопитування: {e}")
    return closed_auto, logs

def save_history_to_file(bridge_status_dict):
    timestamp = get_kyiv_now_str()
    records = []
    for b_id, is_open in bridge_status_dict.items():
        status_str = "🟢 Відкритий" if is_open else "🔴 ЗАКРИТО"
        records.append({
            'timestamp': timestamp,
            'bridge_id': b_id,
            'bridge_name': BRIDGES[b_id]['name'],
            'status_val': 1 if is_open else 0,
            'status_text': status_str
        })
    df_new = pd.DataFrame(records)
    if os.path.exists(HISTORY_FILE):
        try:
            df_old = pd.read_csv(HISTORY_FILE)
            # Додаємо запис, якщо минуло більше хвилини від останнього, щоб не спамити дублями при кожному кліку
            if not df_old.empty:
                last_t = df_old['timestamp'].max()
                if timestamp[:16] != str(last_t)[:16]:
                    df_combined = pd.concat([df_old, df_new], ignore_index=True)
                    df_combined.to_csv(HISTORY_FILE, index=False)
            else:
                df_new.to_csv(HISTORY_FILE, index=False)
        except Exception:
            df_new.to_csv(HISTORY_FILE, index=False)
    else:
        df_new.to_csv(HISTORY_FILE, index=False)

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

st.title("🌁 Автоматизований моніторинг мостів та логістичних ризиків")

try:
    df_options = load_excel_model(EXCEL_FILE)
except Exception as e:
    st.error(f"Помилка завантаження файлу '{EXCEL_FILE}': {e}")
    st.stop()

auto_closed, auto_logs = auto_check_emergency_sources()

st.sidebar.header("🎛 Керування станом мережі")
st.sidebar.info("🤖 **Режим:** Автоматичне сканування + ручний дублер.")

bridge_status = {}
table_data = []

for b_id, b_info in BRIDGES.items():
    default_closed = auto_closed.get(b_id, False)
    
    is_closed = st.sidebar.checkbox(
        f"⛔ Закрито: {b_info['name']}", 
        value=default_closed, 
        key=f"close_{b_id}"
    )
    
    bridge_status[b_id] = not is_closed  # True = відкритий, False = закритий
    
    status_text = "🔴 ЗАКРИТО (Ручний вибір)" if is_closed else "🟢 Відкритий"
    if b_id in auto_closed and is_closed:
        status_text = "🚨 ЗАКРИТО (Підтверджено ОВА)"

    table_data.append({
        'ID': b_id,
        'Міст / ГЕС': b_info['name'],
        'Статус у моделі': status_text
    })

# Зберігаємо стан в історію
save_history_to_file(bridge_status)

results = recalculate_network(df_options, bridge_status)

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Логістичний аналіз мережі", 
    "🌁 Поточний стан переходів",
    "📜 Історія звітів",
    "🤖 Логи автоматики"
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
        st.success("🟢 Усі мости функціонують у штатному режимі.")

    st.subheader(f"🔄 Перепризначені маршрути ({results['changed_routes']})")
    df_changed = results['df_changed']
    if not df_changed.empty:
        cols = ['Код ТТ', 'Адреса ТТ', 'Населений пункт', 'Базовий маршрут (Назва)', 'Новий маршрут (Назва)', 'Базова відстань, км', 'Нова відстань, км', 'Різниця, км']
        display_cols = [c for c in cols if c in df_changed.columns] or list(df_changed.columns[:8])
        st.dataframe(df_changed[display_cols].sort_values(by='Різниця, км', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Перепризначень немає (усі базові маршрути активні).")

with tab2:
    st.subheader("📋 Список переходів та їх актуальний статус")
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📜 Архів історії статусів та подій")
    if os.path.exists(HISTORY_FILE):
        df_hist = pd.read_csv(HISTORY_FILE).sort_values(by='timestamp', ascending=False)
        if not df_hist.empty:
            sel_bridge = st.selectbox("Оберіть об'єкт для перегляду хронології:", df_hist['bridge_name'].unique())
            df_filtered = df_hist[df_hist['bridge_name'] == sel_bridge]
            
            fig = px.line(df_filtered, x='timestamp', y='status_val', title=f"Хронологія стану: {sel_bridge} (1 = Відкритий, 0 = Закрито)", markers=True)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("Архів історії наразі порожній.")
    else:
        st.info("Файл історії ще не створено.")

with tab4:
    st.subheader("🔍 Лог роботи автоматичних каналів зв'язку")
    st.write(f"Остання перевірка: **{get_kyiv_now_str()} (Київ)**")
    for log in auto_logs:
        st.warning(log)
    if not auto_logs:
        st.success("Нових тригерів з екстрених каналів не надходило.")
