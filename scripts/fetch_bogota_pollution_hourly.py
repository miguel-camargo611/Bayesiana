import requests
import json
import pandas as pd
from datetime import datetime

# OpenAQ API v3
API_KEY = "f7d1cdb86501e027edfe02aca5094351ce53f2cb1b13133ffbb8f14950fbc64c"
BASE_URL = "https://api.openaq.org/v3"

headers = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}

# Verified Station IDs for RMCAB (Provider 158) based on user's list
# Consolidatd list from Provider 158 (RMCAB/Bogotá)
STATIONS = {
    8518: "Guaymaral",
    8519: "Kennedy",
    8520: "Puente Aranda",
    8522: "Suba",
    8523: "Tunal",
    8524: "Usaquen",
    10812: "Las Ferias",
    10705: "San Cristobal",
    10677: "Carvajal - Sevillana",
    10535: "Centro de Alto Rendimiento",
    10499: "Fontibon",
    10730: "MinAmbiente",
    10626: "Jazmin",
    10490: "Ciudad Bolivar",
    10848: "Bolivia",
    268068: "Colina",
    10841: "Bosa",
    8025: "Usme",
    268067: "Movil Fontibon"
}

def fetch_hourly_measurements(location_id, location_name, start_date, end_date):
    # Fetch sensors first
    sensor_url = f"{BASE_URL}/locations/{location_id}/sensors"
    s_res = requests.get(sensor_url, headers=headers)
    all_meas = []
    if s_res.status_code == 200:
        sensors = s_res.json()['results']
        for sensor in sensors:
            s_id = sensor['id']
            p_name = sensor['parameter']['name']
            u_name = sensor['parameter']['units']
            
            print(f"    * Fetching for {location_name} sensor {s_id} ({p_name})...")
            
            page = 1
            while True:
                meas_url = f"{BASE_URL}/sensors/{s_id}/measurements"
                params = {
                    "datetime_from": start_date,
                    "datetime_to": end_date,
                    "limit": 1000,
                    "page": page
                }
                
                success = False
                for attempt in range(3):
                    try:
                        m_res = requests.get(meas_url, headers=headers, params=params, timeout=30)
                        if m_res.status_code == 200:
                            data = m_res.json()
                            results = data['results']
                            success = True
                            break
                        else:
                            print(f"      - Error page {page} (Attempt {attempt+1}): {m_res.status_code}")
                    except Exception as e:
                        print(f"      - Exception page {page} (Attempt {attempt+1}): {str(e)}")
                    
                if not success:
                    print(f"      !!! Skipping sensor {s_id} page {page} after failures.")
                    break
                
                if not results:
                    break
                        
                if not results:
                    break
                        
                print(f"      + Page {page}: {len(results)} records")
                for r in results:
                    period = r.get('period', {})
                    date_val = None
                    if isinstance(period, dict):
                        # OpenAQ v3 structure: period -> datetimeFrom -> utc
                        dt_from = period.get('datetimeFrom')
                        if isinstance(dt_from, dict):
                            date_val = dt_from.get('utc')
                        else:
                            # Fallback for other potential v3 variations or v2-like
                            date_val = period.get('start') or period.get('utc')
                    
                    # Last resort fallback to top-level date or day
                    if not date_val:
                        date_val = r.get('date', {}).get('utc') or r.get('day')
                    
                    if date_val:
                        all_meas.append({
                            "station_name": location_name,
                            "station_id": location_id,
                            "sensor_id": s_id,
                            "parameter": p_name,
                            "value": r['value'],
                            "unit": u_name,
                            "datetime": date_val
                        })
                    else:
                        # Only print if we are really stuck
                        pass
                
                if len(results) < 1000:
                    break
                page += 1
    return all_meas

if __name__ == "__main__":
    import os
    # Project root is one level up from this script
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(BASE_DIR, 'data', 'bogota_pollution_hourly.csv')
    
    # Range: 2021 to 2024
    start = "2021-01-01T00:00:00Z"
    end = "2024-03-01T00:00:00Z"
    
    # Process all stations
    final_data_count = 0
    for s_id, s_name in STATIONS.items():
        print(f"Processing station {s_name} (ID: {s_id})...")
        try:
            data = fetch_hourly_measurements(s_id, s_name, start, end)
            if data:
                # Append to file incrementally
                df_temp = pd.DataFrame(data)
                header = not os.path.exists(output_path)
                df_temp.to_csv(output_path, mode='a', index=False, header=header)
                print(f"  + Saved {len(data)} records for {s_name}")
                final_data_count += len(data)
            else:
                print(f"  - No data returned for {s_name}")
        except Exception as e:
            print(f"  !!! Critical error for station {s_name}: {str(e)}")
            continue # Move to next station
    
    if final_data_count > 0:
        print(f"\nCompleted processing. Total records added in this run: {final_data_count}")
        print(f"Final file size: {os.path.getsize(output_path)} bytes")
    else:
        print("\nNo data fetched.")
