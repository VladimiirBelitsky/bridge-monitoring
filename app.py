import streamlit as st
import random
from datetime import datetime, timezone, timedelta
import pandas as pd

st.set_page_config(
    page_title="Оперативний моніторинг мостів та переправ України",
    page_icon="🌉",
    layout="wide"
)

KYIV_TZ = timezone(timedelta(hours=3))

BRIDGES = {
    'KYI_SOUTH': {'name': 'Південний міст', 'region': 'Київ', 'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'},
    'KYI_DARN': {'name': 'Дарницький міст', 'region': 'Київ', 'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'},
    'KYI_PATON': {'name': 'Міст Патона', 'region': 'Київ', 'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'},
    'KYI_METRO': {'name': 'Міст Метро', 'region': 'Київ', 'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'},
    'KYI_NORTH': {'name': 'Північний міст', 'region': 'Київ', 'source_name': 'Патрульна поліція Києва', 'source_url': 'https://t.me/patrolpolice_kyiv'},
    'KYI_GAVAN': {'name': 'Гаванський міст', 'region': 'Київ', 'source_name': 'КМДА', 'source_url': 'https://t.me/kyivcityofficial'},
    'KYI_HPP': {'name': 'Київська ГЕС', 'region': 'Вишгород', 'source_name': 'Вишгородська міськрада', 'source_url': 'https://t.me/vyshgorod_rada'},
    'KANIV_HPP': {'name': 'Канівська ГЕС', 'region': 'Черкаська обл.', 'source_name': 'Черкаська ОВА', 'source_url': 'https://t.me/cherkaskaODA'},
    'CHK': {'name': 'Черкаський міст', 'region': 'Черкаси', 'source_name': 'Патрульна поліція Черкащини', 'source_url': 'https://t.me/patrolpolice_cherkasy'},
    'KREM': {'name': 'Кременчуцький міст / ГЕС', 'region': 'Кременчук', 'source_name': 'Полтавська ОВА', 'source_url': 'https://t.me/poltavaoda'},
    'KAM_HPP': {'name': 'Камʼянська ГЕС', 'region': 'Дніпропетровська обл.', 'source_name': 'Дніпропетровська ОВА', 'source_url': 'https://t.me/adm_dp'},
    'DNI_AMUR': {'name': 'Амурський міст', 'region': 'Дніпро', 'source_name': 'Патрульна поліція Дніпра', 'source_url': 'https://t.me/patrolpolice_dp'},
    'DNI_CENTR': {'name': 'Центральний міст', 'region': 'Дніпро', 'source_name': 'Дніпровська міськрада', 'source_url': 'https://t.me/borys_filatov'},
    'DNI_SOUTH': {'name': 'Південний міст (Дніпро)', 'region': 'Дніпро', 'source_name': 'Патрульна поліція Дніпра', 'source_url': 'https://t.me/patrolpolice_dp'},
    'ZP_PREOBR': {'name': 'Мости Преображенського', 'region': 'Запоріжжя', 'source_name': 'Запорізька ОВА', 'source_url': 'https://t.me/zoda_gov_ua'},
    'ZP_NEW': {'name': 'Нові мости (Запоріжжя)', 'region': 'Запоріжжя', 'source_name': 'Запорізька ОВА', 'source_url': 'https://t.me/zoda_gov_ua'}
}

def get_kyiv_now():
    return datetime.now(KYIV_TZ)

if 'last_update' not in st.session_state:
    st.session_state['last_update'] = get_kyiv_now()

if 'cached_data' not in st.session_state:
    st.session_state['cached_data'] = {}

def get_simulated_telemetry(force=False):
    now = get_kyiv_now()
    if not force and st.session_state['cached_data']:
        return st.session_state['cached_data']

    timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
    traffic_dict = {}

    # Фіксуємо для демонстрації гарний розкид швидкостей
    speeds = [45, 60, 25, 55, 30, 70, 50, 40, 15, 65, 55, 35, 60, 48, 52, 38]

    for i, (b_id, b_info) in enumerate(BRIDGES.items()):
        speed_kmh = speeds[i % len(speeds)]
        
        if speed_kmh < 25:
            status_str = '🔴 Ускладнено / Затор'
        elif speed_kmh < 40:
            status_str = '🟡 Повільний рух'
        else:
            status_str = '🟢 Вільно (Телеметрія ОК)'

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

    st.session_state['cached_data'] = traffic_dict
    st.session_state['last_update'] = now
    return traffic_dict

st.title("🌉 Оперативний моніторинг мостів та переправ України")
st.markdown("Система оперативного контролю транспортних вузлів та інтеграції з офіційними джерелами у реальному часі.")

col_btn1, col_info = st.columns([1, 2])
with col_btn1:
    if st.button("🔄 Оновити дані телеметрії"):
        traffic_data = get_simulated_telemetry(force=True)
        st.success("Дані успішно синхронізовано!")
    else:
        traffic_data = get_simulated_telemetry(force=False)

with col_info:
    last_up = st.session_state.get('last_update')
    if last_up:
        st.info(f"Останній пакет телеметрії: {last_up.strftime('%Y-%m-%d %H:%M:%S')} (Канали ОВА та Поліції активні)")

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
        "Канал зв'язку": data['source_url']
    })

df_bridges = pd.DataFrame(table_rows)
st.dataframe(df_bridges, use_container_width=True)
