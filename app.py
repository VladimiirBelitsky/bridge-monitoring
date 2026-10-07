for b_id, b_info in BRIDGES.items():
        speed_kmh = 50
        status_str = '🟢 Вільно'
        delay_min = 0
        
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
                
                if 'routes' in res and len(res['routes']) > 0:
                    route = res['routes'][0]
                    dist_m = route.get('distanceMeters', 1000)
                    
                    dur_str = route.get('duration', '60s').replace('s', '')
                    dur_sec = float(dur_str) if dur_str else 60.0
                    
                    dist_km = dist_m / 1000.0
                    hours = dur_sec / 3600.0
                    if hours > 0:
                        speed_kmh = round(dist_km / hours)
                        speed_kmh = max(10, min(speed_kmh, 110))

                    if speed_kmh < 25:
                        status_str = '🔴 Затор / Ускладнено'
                    elif speed_kmh < 40:
                        status_str = '🟡 Повільний рух'
                    else:
                        status_str = '🟢 Вільно'
        except Exception:
            pass
