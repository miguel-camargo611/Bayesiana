"""
build_presence_only_modeling_dataset.py
======================================
Construye el dataset limpio para el modelo Bayesiano principal a partir de
data/processed/copeton_presence_only_ready.csv.

Decision metodologica:
    - Usar PM10, NO2 y O3 porque tienen mejor cobertura conjunta que el set
      completo de seis contaminantes.
    - Eliminar filas con nulos en esas covariables y en y.
    - Mantener columnas de trazabilidad espacial, temporal y de fuente.

Salida:
    data/processed/copeton_presence_only_model_ready_pm10_no2_o3.csv
"""

import os

import numpy as np
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "data", "processed", "copeton_presence_only_ready.csv")
OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "copeton_presence_only_model_ready_pm10_no2_o3.csv",
)

COVARIATES = ["pm10_ugm3", "no2_ppb", "o3_ppb"]
ID_COLUMNS = [
    "y",
    "source",
    "lat",
    "lon",
    "date",
    "matched_hour",
    "month",
    "year",
    "nearest_station",
    "distance_km",
    "quadrature_weight",
    "gbifID",
    "individualCount",
]


def build_modeling_dataset():
    print("[MODEL READY] Cargando dataset presence-background...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  Entrada: {len(df):,} filas")

    required = ["y"] + COVARIATES
    missing_columns = [col for col in required if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {missing_columns}")

    for col in COVARIATES + ["y"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df_model = df.dropna(subset=required).copy()
    print(f"  Filas sin nulos en {COVARIATES}: {len(df_model):,} ({before - len(df_model):,} descartadas)")

    finite_mask = np.isfinite(df_model[COVARIATES + ["y"]]).all(axis=1)
    dropped_nonfinite = int((~finite_mask).sum())
    df_model = df_model[finite_mask].copy()
    if dropped_nonfinite:
        print(f"  Filas no finitas descartadas: {dropped_nonfinite:,}")

    df_model["y"] = df_model["y"].astype(int)
    df_model = df_model[df_model["y"].isin([0, 1])].copy()

    keep_columns = [col for col in ID_COLUMNS if col in df_model.columns] + COVARIATES
    df_model = df_model[keep_columns].copy()
    df_model = df_model.sort_values(["source", "date", "lat", "lon"]).reset_index(drop=True)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df_model.to_csv(OUTPUT_FILE, index=False)

    print(f"  Salida: {OUTPUT_FILE}")
    print(f"  Total model-ready: {len(df_model):,}")
    print("  Balance y:")
    print(df_model["y"].value_counts().sort_index().to_string())
    print("  Cobertura por estacion:")
    print(df_model.groupby(["nearest_station", "y"]).size().unstack(fill_value=0).to_string())
    print("  Medianas por grupo:")
    print(df_model.groupby("y")[COVARIATES].median().round(3).T.to_string())


if __name__ == "__main__":
    build_modeling_dataset()
