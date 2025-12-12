from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI()

# CORS para permitir conexión con Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta del CSV extendido
CSV_PATH = os.path.join(os.path.dirname(__file__), "..",
                        "data", "emociones_anuncio_expandido.csv")

# Cargar CSV limpio
df = pd.read_csv(CSV_PATH)

# Emociones numéricas
EMO_COLS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]


@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}


@app.get("/emociones")
def emociones():
    return df.to_dict(orient="records")


@app.get("/resumen")
def resumen():
    """Devuelve los promedios por emoción."""
    promedios = df[EMO_COLS].mean().to_dict()
    return promedios
