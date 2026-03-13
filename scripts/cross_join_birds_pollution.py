import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIRDS_OBS_FILE = os.path.join(BASE_DIR, 'data', 'ebd_CO-CUN_smp_relJan-2026', 'ebd_CO-CUN_smp_relJan-2026.txt')
BIRDS_SAMP_FILE = os.path.join(BASE_DIR, 'data', 'ebd_CO-CUN_smp_relJan-2026', 'ebd_CO-CUN_smp_relJan-2026_sampling.txt')
POLLUTION_FILE = os.path.join(BASE_DIR, 'data', 'bogota_pollution_hourly.csv')
STATIONS_FILE = os.path.join(BASE_DIR, 'data', 'bogota_stations_coords.csv')
OUTPUT_FILE = os.path.join(BASE_DIR, 'data', 'birds_pollution_merged.csv')

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6371 * c
    return km

def run_join():
    print("Loading datasets...")
    # Load pollution data
    df_poll = pd.read_csv(POLLUTION_FILE)
    # Convert UTC to Bogota Time (UTC-5)
    df_poll['datetime'] = pd.to_datetime(df_poll['datetime'])
    df_poll['datetime_local'] = df_poll['datetime'] - pd.Timedelta(hours=5)
    df_poll['date'] = df_poll['datetime_local'].dt.date.astype(str)
    df_poll['hour'] = df_poll['datetime_local'].dt.hour
    
    # Pivot pollutants to wide format
    print("Pivoting pollution data...")
    df_poll_wide = df_poll.pivot_table(
        index=['station_name', 'date', 'hour'], 
        columns='parameter', 
        values='value', 
        aggfunc='mean'
    ).reset_index()
    
    # Load stations
    df_stations = pd.read_csv(STATIONS_FILE)
    
    # Load sampling data (checklists)
    print("Loading sampling events...")
    samp_cols = [
        'SAMPLING EVENT IDENTIFIER', 'LATITUDE', 'LONGITUDE', 
        'OBSERVATION DATE', 'TIME OBSERVATIONS STARTED', 
        'DURATION MINUTES', 'EFFORT DISTANCE KM', 'NUMBER OBSERVERS',
        'ALL SPECIES REPORTED', 'PROTOCOL NAME', 'PROTOCOL CODE'
    ]
    df_samp = pd.read_csv(BIRDS_SAMP_FILE, sep='\t', usecols=samp_cols)
    
    # Filter for Bogota area
    df_samp = df_samp[
        (df_samp['LATITUDE'] >= 4.4) & (df_samp['LATITUDE'] <= 4.8) &
        (df_samp['LONGITUDE'] >= -74.3) & (df_samp['LONGITUDE'] <= -73.9)
    ].copy()
    print(f"Filtered to {len(df_samp)} checklists in Bogota area.")
    
    # Load observations and join
    print("Loading observations and joining with sampling events...")
    obs_cols = ['SAMPLING EVENT IDENTIFIER', 'SCIENTIFIC NAME', 'COMMON NAME', 'OBSERVATION COUNT']
    # We only load observations for the checklists we already filtered
    df_obs = pd.read_csv(BIRDS_OBS_FILE, sep='\t', usecols=obs_cols)
    
    # Join observations with sampling info
    df_birds = df_obs.merge(df_samp, on='SAMPLING EVENT IDENTIFIER', how='inner')
    print(f"Total bird observations in Bogota area: {len(df_birds)}")

    # Temporal Processing for Birds
    print("Processing bird timestamps...")
    def round_time(time_str):
        try:
            # Handle HH:MM or HH:MM:SS
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = int(parts[1])
            if minute >= 30:
                return (hour + 1) % 24
            return hour
        except:
            return np.nan

    df_birds['matched_hour'] = df_birds['TIME OBSERVATIONS STARTED'].apply(round_time)
    df_birds = df_birds.dropna(subset=['matched_hour'])
    df_birds['matched_hour'] = df_birds['matched_hour'].astype(int)
    
    # Spatial Matching: Assign nearest station
    print("Calculating nearest stations (this may take a moment)...")
    unique_coords = df_birds[['LATITUDE', 'LONGITUDE']].drop_duplicates()
    
    def find_nearest(row):
        # Calculate distances to all stations
        distances = df_stations.apply(
            lambda s: haversine(row['LATITUDE'], row['LONGITUDE'], s['lat'], s['lon']), 
            axis=1
        )
        idx = distances.idxmin()
        return pd.Series([df_stations.loc[idx, 'station_name'], distances.min()])

    unique_coords[['nearest_station', 'distance_km']] = unique_coords.apply(find_nearest, axis=1)
    
    # Merge distance info back
    df_birds = df_birds.merge(unique_coords, on=['LATITUDE', 'LONGITUDE'], how='left')
    
    # The Join
    print("Performing final join...")
    # Merge birds + pollution
    # We join on nearest_station, Date and rounded Hour
    df_final = df_birds.merge(
        df_poll_wide,
        left_on=['nearest_station', 'OBSERVATION DATE', 'matched_hour'],
        right_on=['station_name', 'date', 'hour'],
        how='left'
    )
    
    # Cleanup redundant or internal match columns
    # Keep 'TIME OBSERVATIONS STARTED' as it might be useful as a raw covariate
    df_final = df_final.drop(columns=['station_name', 'date', 'hour'])
    
    # Rename pollutant columns to include units for clarity
    p_rename = {
        'co': 'co_ppm', 'no2': 'no2_ppb', 'o3': 'o3_ppb',
        'pm10': 'pm10_ugm3', 'pm25': 'pm25_ugm3', 'so2': 'so2_ugm3'
    }
    df_final = df_final.rename(columns=p_rename)

    # FILTERING: Keep only records that have at least one valid pollutant measurement
    # This effectively keeps data for the 2021-2024 period where matches exist.
    pollutant_cols = list(p_rename.values())
    df_final = df_final.dropna(subset=pollutant_cols, how='all')
    print(f"Filtered to {len(df_final)} records within the 2021-2024 pollution data range.")
    
    # Reorder columns to be more readable
    cols = ['SAMPLING EVENT IDENTIFIER', 'SCIENTIFIC NAME'] if 'SCIENTIFIC NAME' in df_final.columns else ['SAMPLING EVENT IDENTIFIER']
    remaining_cols = [c for c in df_final.columns if c not in cols]
    df_final = df_final[cols + remaining_cols]

    print(f"Saving joined data to {OUTPUT_FILE}...")
    df_final.to_csv(OUTPUT_FILE, index=False)
    
    # Summary of NaNs for the user
    pollutants_new = [c for c in df_final.columns if c in p_rename.values()]
    nan_counts = df_final[pollutants_new].isna().sum()
    print("\nSummary of missing pollution data (NaNs):")
    print(nan_counts)
    print(f"\nNote: High NaN counts are due to bird observations ranging from {df_birds['OBSERVATION DATE'].min()} to {df_birds['OBSERVATION DATE'].max()},")
    print(f"while the pollution dataset only covers the period 2021-2024.")
    
    print(f"Done! Final shape: {df_final.shape}")

if __name__ == "__main__":
    run_join()
