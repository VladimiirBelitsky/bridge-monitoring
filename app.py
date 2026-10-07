import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
import pandas as pd

# Налаштування сторінки
st.set_page_config(
    page_title="Моніторинг ланцюгів постачання: РЦ та ТТ",
    page_icon="🚚",
    layout="wide"
)

KYIV_TZ = timezone(timedelta(hours=3))

# Реєстр логістичних вузлів (РЦ та торгові точки) з координатами
LOGISTIC_POINTS = {
    'RC_KYIV': {'name': 'РЦ Київ (Головний хаб)', 'lat': 50.4501, 'lon': 30.5234, 'region': 'Київський регіон'},
    'MUKACHEVO': {'name': 'ТТ / РЦ Мукачево', 'lat': 48.4451, 'lon': 22.7175, 'region': 'Закарпатська обл.'},
    'LVIV_1': {'name': 'ТТ Львів (Схід/Центр)', 'lat': 49.8397, 'lon': 24.0297, 'region': 'Львівська обл.'},
    'RIVNE_1': {'name': 'ТТ Рівне (Холодний склад)', 'lat': 50.6199, 'lon': 26.2516, 'region': 'Рівненська обл.'},
    'VINNYTSIA': {'name': 'ТТ Вінниця (Дистрибуція)', 'lat': 49.2331, 'lon': 28.4682, 'region': 'Вінницька обл.'},
    'KROPIVNYTSKYI': {'name': 'ТТ Кропивницький', 'lat': 48.5132, 'lon': 32.2597, 'region': 'Кіровоградська обл.'},
    'DNIPRO_HPP': {'name': 'ТТ Дніпро (Південний напрямок)', 'lat': 48.4647, 'lon': 35.0462, 'region': 'Дніпропетровська обл.'},
    'ZAPORIZHZHIA': {'name': 'ТТ Запоріжжя (Хаб)', 'lat': 47.8388, 'lon': 35.1396, 'region': 'Запорізька обл.'},
    'PERVOMAYSK': {'name': 'ТТ Первомайськ (Транзит)', 'lat': 48.0474, 'lon': 30.8523, 'region': 'Миколаївська обл.'},
    'FRANKIVSK': {'name': 'ТТ Івано-Франківськ', 'lat': 48.9226, 'lon': 24.7111, 'region': 'Івано-Франківська обл.'}
}

def get_kyiv_now_str():
    return datetime.now(KYIV_TZ).strftime('%Y-%m-%d %H:%M:%S')

def fetch_logistics_telemetry():
    traffic_dict = {}
    timestamp = get_kyiv_now_str()
    
    api_key = ""
    try:
        api_key = st.secrets["google_maps"]["api_key"]
    except Exception as e:
        st.error(f"Помилка читання st.secrets для Google Maps: {e}")
    
    for p_id, p_info in LOGISTIC_POINTS.items():
        if p_id == 'RC_KYIV':
            traffic_dict[p_id] = {
                'name': p_info['name'],
                'region': p_info['region'],
                'state': 'Головний хаб (Активний)',
                'speed': 0,
                'source': 'Базовий вузол РЦ',
                'timestamp': timestamp,
                'lat': p_info['lat'],
                'lon': p_info['lon']
            }
            continue
            
        speed_kmh = 50
        status_str = 'Очікування даних'
        source_desc = 'Немає зєднання'
        
        try:
            if api_key:
                orig_lat = LOGISTIC_POINTS['RC_KYIV']['lat']
                orig_lon = LOGISTIC_POINTS['RC_KYIV']['lon']
                dest_lat = p_info['lat']
                dest_lon = p_info['lon']
                
                url = (f"https://maps.googleapis.com/maps/api/distancematrix/json?"
                       f"origins={orig_lat},{orig_lon}&destinations={dest_lat},{dest_lon}"
                       f"&departure_time=now&key={api_key}")
                
                res = requests.get(url, timeout=6).json()
                
                if res.get('status') == 'OK':
                    element = res.get('rows', [{}])[0].get('elements', [{}])[0]
                    if element.get('status') == 'OK':
                        distance_meters = element.get('distance', {}).get('value', 10000)
                        dur_norm = element.get('duration', {}).get('value', 3600)
                        dur_traf = element.get('duration_in_traffic', {}).get('value', dur_norm)
                        
                        distance_km = distance_meters / 1000.0
                        hours_in_traffic = dur_traf / 3600.0
                        
                        speed_kmh = round(distance_km / hours_in_traffic) if hours_in_traffic > 0 else 50
                        speed_kmh = max(10, min(speed_kmh, 120))
                        
                        if dur_traf > dur_norm * 1.3 or speed_kmh < 35:
                            status_str = 'Повільний рух / Затор'
                        else:
                            status_str = 'Норма (Графік дотримано)'
                            
                        source_desc = "Google Maps API (Live Telemetry)"
                    else:
                        status_str = 'Помилка елемента API'
                        source_desc = element.get('status', 'Unknown')
                else:
                    status_str = 'Помилка API статусу'
                    source_desc = res.get('status', 'Unknown')
            else:
                status_str = 'Відсутній API ключ'
                source_desc = 'Перевірте secrets.toml'
                
        except Exception as err:
            status_str = 'Помилка звʼязку'
            source_desc = str(err)

        traffic_dict[p_id] = {
            'name': p_info['name'],
            'region': p_info['region'],
            'state': status_str,
            'speed': speed_kmh,
            'source': source_desc,
            'timestamp': timestamp,
            'lat': p_info['lat'],
            'lon': p_info['lon']
        }
        
    return traffic_dict

# --- Інтерфейс Streamlit ---
st.title("Оперативний моніторинг ланцюгів РЦ та ТТ")
st.markdown("Панель контролю транспортних потоків, швидкості доставки та розрахунку плеча між розподільчими центрами й точками на базі Google Maps API.")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.button("Оновити телеметрію"):
        st.rerun()

logistics_data = fetch_logistics_telemetry()

st.markdown("### Статус магістральних напрямків від РЦ")
non_rc_items = [(k, v) for k, v in logistics_data.items() if k != 'RC_KYIV']
for i in range(0, len(non_rc_items), 4):
    cols = st.columns(4)
    for j, (p_id, data) in enumerate(non_rc_items[i:i+4]):
        with cols[j]:
            st.metric(
                label=data['name'], 
                value=f"{data['speed']} км/год", 
                delta=data['state']
            )

st.markdown("---")

st.subheader("Розрахунок логістичного плеча (РЦ ➡️ ТТ)")
st.markdown("Оберіть початковий вузол (РЦ / склад) та пункт призначення (Торгова точка) для точного розрахунку відстані та часу в дорозі.")

r_col1, r_col2, r_col3 = st.columns([2, 2, 1])

point_options = {p_id: data['name'] for p_id, data in logistics_data.items()}

with r_col1:
    origin_point = st.selectbox("Відправлення (РЦ / Вузол)", list(point_options.keys()), format_func=lambda x: point_options[x], index=0)
with r_col2:
    dest_point = st.selectbox("Призначення (Торгова точка)", list(point_options.keys()), format_func=lambda x: point_options[x], index=min(2, len(point_options)-1))
with r_col3:
    st.write("")
    calc_route = st.button("Розрахувати плече", use_container_width=True)

if calc_route:
    orig_coords = f"{logistics_data[origin_point]['lat']},{logistics_data[origin_point]['lon']}"
    dest_coords = f"{logistics_data[dest_point]['lat']},{logistics_data[dest_point]['lon']}"
    
    api_key = ""
    try:
        api_key = st.secrets["google_maps"]["api_key"]
    except Exception:
        pass
        
    success_calc = False
    if api_key and origin_point != dest_point:
        try:
            url_m = (f"https://maps.googleapis.com/maps/api/distancematrix/json?"
                     f"origins={orig_coords}&destinations={dest_coords}"
                     f"&departure_time=now&key={api_key}")
            res_m = requests.get(url_m, timeout=5).json()
            
            if res_m.get('status') == 'OK':
                el_m = res_m.get('rows', [{}])[0].get('elements', [{}])[0]
                if el_m.get('status') == 'OK':
                    dist_txt = el_m.get('distance', {}).get('text', 'Н/Д')
                    dur_txt = el_m.get('duration', {}).get('text', 'Н/Д')
                    dur_traf_txt = el_m.get('duration_in_traffic', {}).get('text', dur_txt)
                    
                    st.success(f"Маршрут успішно побудовано: **{logistics_data[origin_point]['name']}** ➡️ **{logistics_data[dest_point]['name']}**")
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Відстань маршруту", dist_txt)
                    mc2.metric("Нормативний час", dur_txt)
                    mc3.metric("Час з урахуванням трафіку", dur_traf_txt)
                    success_calc = True
        except Exception as e:
            st.error(f"Помилка розрахунку маршруту: {e}")
            
    if not success_calc:
        if origin_point == dest_point:
            st.warning("Пункт відправлення і призначення не можуть збігатися.")
        else:
            st.error("Не вдалося отримати дані від Google Maps API для цього плеча.")

st.markdown("---")
st.subheader("Реєстр активних вузлів розподілу (РЦ та ТТ)")

table_rows = []
for p_id, data in logistics_data.items():
    table_rows.append({
        "Код вузла": p_id,
        "Об'єкт": data['name'],
        "Регіон": data['region'],
        "Статус": data['state'],
        "Швидкість": f"{data['speed']} км/год" if p_id != 'RC_KYIV' else "—",
        "Джерело телеметрії": data['source'],
        "Оновлено": data['timestamp']
    })

df_logistics = pd.DataFrame(table_rows)
st.dataframe(df_logistics, use_container_width=True)
