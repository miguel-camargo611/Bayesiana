import pandas as pd
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, 'data', 'birds_pollution_merged.csv')
OUTPUT_FILE = os.path.join(BASE_DIR, 'data', 'copeton_occupancy_ready.csv')
SPECIES_NAME = 'Zonotrichia capensis'

def prepare_data():
    print(f"Loading merged dataset from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # 1. Filter for Complete Checklists only
    # This is critical for inferring absences (y=0)
    print("Filtering for complete checklists (ALL SPECIES REPORTED == 1)...")
    df_comp = df[df['ALL SPECIES REPORTED'] == 1].copy()
    
    # 2. Identify records where the species was detected
    print(f"Identifying detections for {SPECIES_NAME}...")
    # Get IDs of checklists where the species was seen
    checklists_with_species = df_comp[df_comp['SCIENTIFIC NAME'] == SPECIES_NAME]['SAMPLING EVENT IDENTIFIER'].unique()
    
    # 3. Create the occupancy-ready structure
    # We group by checklist to have one row per visit
    # Since all observations in the same checklist share the same effort and pollution data,
    # we can take the first record of each group.
    
    print("Building occupancy-ready structure...")
    # Select checklist-level metadata and covariates
    cols_to_keep = [
        'SAMPLING EVENT IDENTIFIER', 'nearest_station', 'distance_km',
        'pm10_ugm3', 'pm25_ugm3', 'so2_ugm3', 'co_ppm', 'no2_ppb', 'o3_ppb',
        'DURATION MINUTES', 'EFFORT DISTANCE KM', 'NUMBER OBSERVERS', 
        'PROTOCOL NAME', 'OBSERVATION DATE', 'TIME OBSERVATIONS STARTED'
    ]
    
    # Drop observation-specific columns like SCIENTIFIC NAME or OBSERVATION COUNT
    # to get one row per sampling event
    df_events = df_comp.drop_duplicates(subset=['SAMPLING EVENT IDENTIFIER'])[cols_to_keep].copy()
    
    # 4. Define 'y' (Response Variable)
    # y = 1 if checklist is in checklists_with_species, else 0
    df_events['y_copeton'] = df_events['SAMPLING EVENT IDENTIFIER'].isin(checklists_with_species).astype(int)
    
    # 5. Add Seasonality (Month) as an extra covariate
    df_events['month'] = pd.to_datetime(df_events['OBSERVATION DATE']).dt.month
    
    # 6. Reorder columns for clarity
    final_cols = [
        'SAMPLING EVENT IDENTIFIER', 'nearest_station', 'y_copeton',
        'pm10_ugm3', 'pm25_ugm3', 'so2_ugm3', 'co_ppm', 'no2_ppb', 'o3_ppb',
        'DURATION MINUTES', 'EFFORT DISTANCE KM', 'NUMBER OBSERVERS', 
        'PROTOCOL NAME', 'month', 'OBSERVATION DATE', 'TIME OBSERVATIONS STARTED', 'distance_km'
    ]
    df_final = df_events[final_cols]
    
    # Final Summary
    print("\n--- Pilot Model Dataset Summary ---")
    print(f"Total Sites (Stations): {df_final['nearest_station'].nunique()}")
    print(f"Total Sampling Events (Replicates): {len(df_final)}")
    print(f"Total Detections (y=1): {df_final['y_copeton'].sum()}")
    print(f"Total Absences (y=0): {len(df_final) - df_final['y_copeton'].sum()}")
    print("\nDetections per station:")
    print(df_final.groupby('nearest_station')['y_copeton'].sum())
    
    print(f"\nSaving model-ready data to {OUTPUT_FILE}...")
    df_final.to_csv(OUTPUT_FILE, index=False)
    print("Done!")

if __name__ == "__main__":
    prepare_data()
