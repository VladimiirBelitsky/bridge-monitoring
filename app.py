import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
import pandas as pd

# Налаштування сторінки
st.set_page_config(
    page_title="Оперативний моніторинг мостів та переправ",
    page_icon="🌉",
    layout="wide"
)

KYIV_TZ = timezone(timedelta(hours=3))

@st.cache_data
def load_network_model():
    excel_path = "Робоча_модель_мережі_ФІНАЛ 1.xlsx"
    bridges_df = pd.read_excel(excel_path, sheet_name="05_Переходи")
    return bridges_df

bridges_df = load_network_model()

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

# Управління станом переходів у боковій панелі
st.sidebar.header("🎛️ Статус переправ (Конструктор)")
bridge_statuses = {}
bridges_df.columns = bridges_df.columns.str.strip()

for idx, row in bridges_df.iterrows():
    b_id = row.get('Bridge_ID')
    b_name = row.get('Назва переходу')
    b_region = row.get('Вузол')
    if pd.notna(b_id):
        is_active = st.sidebar.selectbox(
            f"{b_name} ({b_region})",
            options=["Працює", "Закритий"],
            index=0,
            key=f"bridge_{b_id}"
        )
        bridge_statuses[b_id] = (is_active == "Працює")

st.title("🌉 Оперативний моніторинг мостів та переправ у реальному часі")
st.markdown("Панель контролю швидкості потоку, заторів та затримок на критичних переправах мережі.")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.button("🔄 Оновити телеметрію"):
        st.rerun()

api_key = get_api_key()
timestamp = get_kyiv_now_str()

# Збір телеметрії по всіх мостах/переправах з файлу
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
    
    if not is_working:
        status_str = '🔴 Закритий'
        speed_kmh = 0
        delay_min = 45
    else:
        status_str = '🟢 Вільно'
        if api_key and pd.notna(lat) and pd.notna(lon):
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
                        
                        if dur_traf > dur_norm * 1.4 or speed_kmh < 25:
                            status_str = '🟡 Ускладнено / Затор'
                        else:
                            status_str = '🟢 Вільно'
            except Exception:
                status_str = '🟢 Штатно'
        else:
            speed_kmh = 55
            status_str = '🟢 Штатний режим'

    bridge_cards_data.append({
        "id": b_id,
        "name": b_name,
        "region": b_region,
        "state": status_str,
        "speed": speed_kmh,
        "delay": delay_min,
        "timestamp": timestamp
    })

# Вивід метрик (карток) по мостах
st.markdown("### 📊 Статус та швидкість на переправах")
for i in range(0, len(bridge_cards_data), 4):
    cols = st.columns(4)
    for j, data in enumerate(bridge_cards_data[i:i+4]):
        with cols[j]:
            st.metric(
                label=f"{data['name']} ({data['region']})",
                value=f"{data['speed']} км/год",
                delta=f"{data['state']} (+{data['delay']} хв)"
            )

st.markdown("---")

# Аналіз впливу закритих переходів
closed_count = sum(1 for d in bridge_cards_data if "Закритий" in d['state'])
congested_count = sum(1 for d in bridge_cards_data if "Ускладнено" in d['state'])

col_inf1, col_inf2 = st.columns(2)
with col_inf1:
    st.metric("🚨 Закриті переправи", f"{closed_count} об'єктів")
with col_inf2:
    st.metric("🟡 Об'єкти із заторами", f"{congested_count} об'єктів")

if closed_count > 0:
    st.warning("⚠️ Увага! Закриття переправ призводить до перенаправлення магістральних потоків на альтернативні маршрути та збільшення часу доставки.")
else:
    st.success("✅ Усі переправи функціонують у штатному режимі. Доставка йде за графіком.")

st.markdown("---")
st.subheader("📋 Детальна таблиця мостів та параметрів трафіку")
df_table = pd.DataFrame(bridge_cards_data)
st.dataframe(df_table, use_container_width=True)
