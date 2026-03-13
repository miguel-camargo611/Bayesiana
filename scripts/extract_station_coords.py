import requests
import pandas as pd
import time

API_KEY = "f7d1cdb86501e027edfe02aca5094351ce53f2cb1b13133ffbb8f14950fbc64c"
BASE_URL = "https://api.openaq.org/v3"

headers = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}

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

def extract_coords():
    meta = []
    for s_id, s_name in STATIONS.items():
        print(f"Fetching metadata for {s_name} (ID: {s_id})...")
        success = False
        for attempt in range(3):
            try:
                r = requests.get(f"{BASE_URL}/locations/{s_id}", headers=headers, timeout=30)
                if r.status_code == 200:
                    results = r.json().get('results', [])
                    if results:
                        loc = results[0]
                        meta.append({
                            "station_id": s_id,
                            "station_name": s_name,
                            "lat": loc['coordinates']['latitude'],
                            "lon": loc['coordinates']['longitude']
                        })
                        print(f"  + Success")
                        success = True
                        break
                    else:
                        print(f"  !!! No results for {s_name}")
                else:
                    print(f"  !!! Error {r.status_code} for {s_name} (Attempt {attempt+1})")
            except Exception as e:
                print(f"  !!! Exception for {s_name}: {str(e)} (Attempt {attempt+1})")
            time.sleep(2)
            
    if meta:
        df = pd.DataFrame(meta)
        import os
        # Project root is one level up from this script
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(BASE_DIR, 'data', 'bogota_stations_coords.csv')
        df.to_csv(output_path, index=False)
        print(f"\nSaved {len(meta)} station coordinates to {output_path}")
    else:
        print("\nNo metadata captured.")

if __name__ == "__main__":
    extract_coords()
