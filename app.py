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
                
                # Перевіримо що прийшло від API у терміналі
                if 'routes' in res:
                    route = res['routes'][0]
                    dist_m = route.get('distanceMeters', 1000)
                    # Routes API повертає duration у вигляді "123.45s" або схожому
                    dur_str = str(route.get('duration', '60s')).replace('s', '')
                    dur_sec = float(dur_str)
                    
                    dist_km = dist_m / 1000.0
                    hours = dur_sec / 3600.0
                    if hours > 0:
                        calculated_speed = round(dist_km / hours)
                        if calculated_speed > 5:  # якщо порахувало адекватно
                            speed_kmh = calculated_speed

                    if speed_kmh < 25:
                        status_str = '🔴 Затор / Ускладнено'
                    elif speed_kmh < 40:
                        status_str = '🟡 Повільний рух'
                    else:
                        status_str = '🟢 Вільно'
                else:
                    # Якщо немає маршруту, виводимо помилку з відповіді Google у статус для розуміння
                    status_str = f"⚠️ {res.get('error', {}).get('message', 'API Error')[:30]}"
        except Exception as e:
            status_str = f"⚠️ Помилка: {str(e)[:20]}"
