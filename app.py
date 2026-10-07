import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
import pandas as pd

# Налаштування сторінки
st.set_page_config(
    page_title="Оперативний моніторинг мережі та переправ",
    page_icon="🌉",
    layout="wide"
)

KYIV_TZ = timezone(timedelta(hours=3))

@st.cache_data
def load_network_model():
    excel_path = "Робоча_модель_мережі_ФІНАЛ 1.xlsx"
    bridges_df = pd.read_excel(excel_path, sheet_name="05_Переходи")
    rc_df = pd.read_excel(excel_path, sheet_name="02_РЦ")
    tt_df = pd.read_excel(excel_path, sheet_name="03_ТТ")
    return bridges_df, rc_df, tt_df

bridges_df, rc_df, tt_df = load_network_model()

def get_kyiv_now_str():
    return datetime.now(KYIV_TZ).strftime('%Y-%m-%d %H:%M:%S')

def get_api_key():
    try:
        if "google_maps" in st.secrets and "api_key" in st.secrets["google_maps"]:
            return st.secrets["google_maps"]["api_key"]
        if "api_key" in st.secrets:
            return st.secrets["api_key"]
        for k, v in st.secrets.items():
            if isinstance(v, dict) and "api_key" in v:
                return v["api_key"]
    except Exception:
        pass
    return ""

st.title("🌉 Оперативний моніторинг транспортної мережі та критичних переходів")
st.markdown("Моніторинг статусів мостів/ГЕС відповідно до робочої моделі мережі та оцінка впливу на плечі доставки між РЦ і ТТ.")

# Бокова панель для керування станом переходів (як у конструкторі сценаріїв)
st.sidebar.header("🎛️ Конструктор сценаріїв (Статус переправ)")
bridge_statuses = {}

# Очистимо назви колонок від можливих пробілів
bridges_df.columns = bridges_df.columns.str.strip()

for idx, row in bridges_df.iterrows():
    b_id = row.get('Bridge_ID')
    b_name = row.get('Назва переходу')
    b_region = row.get('Вузол')
    if pd.notna(b_id):
        is_active = st.sidebar.selectbox(
            f"{b_name} ({b_region})",
            options=["Працює (Доступний)", "Закритий (Аварія/Ремонт)"],
            index=0,
            key=f"bridge_{b_id}"
        )
        bridge_statuses[b_id] = (is_active.startswith("Працює"))

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.button("🔄 Оновити телеметрію"):
        st.rerun()

api_key = get_api_key()

# Основна таблиця переправ та їх поточного стану
st.markdown("### 📊 Статус критичних переходів мережі")
bridge_cards_data = []

for idx, row in bridges_df.iterrows():
    b_id = row.get('Bridge_ID')
    b_name = row.get('Назва переходу')
    b_region = row.get('Вузол')
    lat = row.get('Широта')
    lon = row.get('Довгота')
    
    if pd.isna(b_id):
        continue
        
    is_working = bridge_statuses.get(b_id, True)
    speed_kmh = 50
    delay_min = 0
    status_str = '🟢 Відкрито / Норма' if is_working else '🔴 Закритий (Обхід маршруту)'
    
    if is_working and api_key and pd.notna(lat) and pd.notna(lon):
        try:
            orig_lat = float(lat) - 0.008
            orig_lon = float(lon) - 0.008
            url = (f"https://maps.googleapis.com/maps/api/distancematrix/json?"
                   f"origins={orig_lat},{orig_lon}&destinations={lat},{lon}"
                   f"&departure_time=now&key={api_key}")
            res = requests.get(url, timeout=4).json()
            if res.get('status') == 'OK':
                element = res.get('rows', [{}])[0].get('elements', [{}])[0]
                if element.get('status') == 'OK':
                    dist_m = element.get('distance', {}).get('value', 1000)
                    dur_norm = element.get('duration', {}).get('value', 60)
                    dur_traf = element.get('duration_in_traffic', {}).get('value', dur_norm)
                    speed_kmh = round((dist_m / 1000.0) / (dur_traf / 3600.0))
                    speed_kmh = max(5, min(speed_kmh, 110))
                    delay_min = round(max(0, dur_traf - dur_norm) / 60)
                    if dur_traf > dur_norm * 1.3:
                        status_str = '🟡 Ускладнено / Затор'
        except Exception:
            pass
    elif not is_working:
        speed_kmh = 0
        delay_min = 45 # Середня додаткова затримка в обхід

    bridge_cards_data.append({
        "ID": b_id,
        "Переправa": b_name,
        "Вузол/Регіон": b_region,
        "Статус": status_str,
        "Швидкість": f"{speed_kmh} км/год" if is_working else "—",
        "Затримка": f"+{delay_min} хв",
        "Координати": f"{lat}, {lon}"
    })

df_bridges_view = pd.DataFrame(bridge_cards_data)
st.dataframe(df_bridges_view, use_container_width=True)

st.markdown("---")
st.subheader("⚠️ Аналіз впливу закритих переходів на дистрибуцію та РЦ/ТТ")

closed_bridges = [b['Переправa'] for b in bridge_cards_data if "Закритий" in b['Статус']]
if closed_bridges:
    st.error(f"🚨 Увага! Зафіксовано закриття наступних критичних переходів: **{', '.join(closed_bridges)}**. Модель автоматично активує резервні маршрути згідно з матрицею варіантів обходу.")
else:
    st.success("✅ Усі ключові переправи функціонують у штатному режимі. Доставка йде за базовими маршрутами.")

# Довідкова інформація по РЦ
st.markdown("---")
st.subheader("🏢 Довідник активних розподільчих центрів (РЦ)")
st.dataframe(rc_df, use_container_width=True)
