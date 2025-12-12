import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import os

st.set_page_config(
    page_title="Dashboard de Análisis de Emociones",
    layout="wide"
)

st.title("📊 Dashboard de Análisis de Emociones")
st.markdown(
    "Este dashboard intenta consumir datos desde la API de FastAPI. "
    "Si la API no está disponible, utiliza el archivo CSV local."
)

API_URL = "http://127.0.0.1:8000"
CSV_LOCAL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "emotions_extended.csv"
)


# 👇 Ya NO usamos @st.cache_data para poder usar toasts sin problemas
def load_data():
    # 1) Intentar API
    try:
        # 🔔 Toast flotante: intento de conexión
        st.toast("Intentando obtener datos desde la API...", icon="🔄")

        response = requests.get(f"{API_URL}/emociones", timeout=3)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)

        # 🔔 Toast flotante: éxito con la API
        st.toast("Datos cargados desde la API ✅", icon="✅")

        return df, "api"

    except Exception:
        # 🔔 Toast flotante: fallo API, se usa CSV
        st.toast(
            "No se pudo conectar con la API. Se usará el CSV local.",
            icon="⚠️"
        )

    # 2) Fallback: CSV local
    if not os.path.exists(CSV_LOCAL_PATH):
        st.error(f"No se encontró el archivo CSV local en: {CSV_LOCAL_PATH}")
        return None, "none"

    df = pd.read_csv(CSV_LOCAL_PATH)

    # 🔔 Toast flotante: CSV cargado
    st.toast("Datos cargados desde el CSV local ✅", icon="📁")

    return df, "csv"


df, origen = load_data()

if df is None or df.empty:
    st.stop()

# -------------------------------
#  Definir columnas correctamente

# Eje de tiempo
if "timestamp_sec" in df.columns:
    eje_tiempo = "timestamp_sec"
elif "time" in df.columns:
    eje_tiempo = "time"
else:
    eje_tiempo = "frame"

# Asegurar que eje_tiempo sea numérico
df[eje_tiempo] = pd.to_numeric(df[eje_tiempo], errors="coerce")

# SOLO columnas numéricas de emociones
EMOTION_COLS = ["angry", "disgust", "fear",
                "happy", "sad", "surprise", "neutral"]

# Asegurar que existan y sean numéricas
EMOTION_COLS = [c for c in EMOTION_COLS if c in df.columns]
num_df = df[EMOTION_COLS].apply(pd.to_numeric, errors="coerce")

st.caption(
    f"Fuente de datos actual: **{ 'API FastAPI' if origen == 'api' else 'CSV local' }**"
)

# ============================================================
#  RESUMEN GENERAL

st.subheader("📌 Resumen General de Emociones (promedios)")

resumen_series = num_df.mean().sort_values(ascending=False)
resumen_df = pd.DataFrame(resumen_series, columns=["Promedio"])

fig_resumen = px.bar(
    resumen_df,
    x=resumen_df.index,
    y="Promedio",
    title="Promedio de cada emoción detectada",
    color="Promedio",
)
st.plotly_chart(fig_resumen, use_container_width=True)

emo_top = resumen_df["Promedio"].idxmax()
val_top = resumen_df["Promedio"].max()
st.metric("Emoción predominante global", emo_top, f"{val_top:.2f}")

# ============================================================
#  EVOLUCIÓN TEMPORAL - EMOCIÓN PREDOMINANTE

st.subheader("🧠 Emoción predominante a lo largo del video")

df["predominante"] = num_df.idxmax(axis=1)

fig_predom = px.scatter(
    df,
    x=eje_tiempo,
    y="predominante",
    color="predominante",
    title="Emoción predominante a lo largo del tiempo",
    height=500
)
st.plotly_chart(fig_predom, use_container_width=True)

# ============================================================
#  HEATMAP EMOCIONAL (PLOTLY - VIRIDIS)

st.subheader("🌡️ Mapa de calor de emociones a lo largo del tiempo")

if len(df) > 1 and len(EMOTION_COLS) > 0:
    # Para que el heatmap sea legible, agrupamos el tiempo en segmentos
    num_bins = min(30, len(df))  # máximo 30 columnas en el mapa

    # Creamos una copia de trabajo para no ensuciar df original
    temp = df[[eje_tiempo] + EMOTION_COLS].copy()

    temp["time_bin"] = pd.cut(
        temp[eje_tiempo],
        bins=num_bins,
        include_lowest=True
    )

    # Promedio de emociones por segmento de tiempo
    heat_df = temp.groupby("time_bin")[EMOTION_COLS].mean().T

    # Renombrar columnas a algo más simple (Segmento 1, 2, 3…)
    heat_df.columns = [f"Seg {i+1}" for i in range(len(heat_df.columns))]

    fig_heat = px.imshow(
        heat_df,
        aspect="auto",
        color_continuous_scale="Viridis",
        labels={
            "x": "Segmentos del video",
            "y": "Emoción",
            "color": "Intensidad promedio"
        },
        title="Mapa de calor de intensidad emocional por segmentos del video",
    )

    st.plotly_chart(fig_heat, use_container_width=True)

    st.caption(
        "Cada columna representa un segmento del video. "
        "Los colores más intensos indican mayor probabilidad de la emoción en ese tramo."
    )
else:
    st.info("No hay suficientes datos para generar el mapa de calor.")

# ============================================================
#  EMOCIÓN ESPECÍFICA + RANGO DE TIEMPO

st.subheader("📈 Evolución de una emoción específica")

# Selector de emoción y texto explicativo
col_filtro, col_texto = st.columns([1, 3])

with col_filtro:
    emo_sel = st.selectbox("Selecciona la emoción", EMOTION_COLS)

with col_texto:
    st.write(
        "La gráfica muestra cómo varía la probabilidad de la emoción "
        f"**{emo_sel}** a lo largo del video. "
        "Puedes ajustar el rango de tiempo para hacer zoom en una parte específica."
    )

# Slider de rango de tiempo
min_t = float(df[eje_tiempo].min())
max_t = float(df[eje_tiempo].max())

# Evitar que step sea 0
if max_t > min_t:
    step_value = (max_t - min_t) / 100
else:
    step_value = 1.0

rango_inicio, rango_fin = st.slider(
    "Rango de tiempo",
    min_value=min_t,
    max_value=max_t,
    value=(min_t, max_t),
    step=step_value,
    format="%.2f"
)

# Filtrar por rango seleccionado
mask = (df[eje_tiempo] >= rango_inicio) & (df[eje_tiempo] <= rango_fin)
df_filtrado = df.loc[mask]

fig_line = px.line(
    df_filtrado,
    x=eje_tiempo,
    y=emo_sel,
    title=f"Evolución de {emo_sel} entre {rango_inicio:.2f} y {rango_fin:.2f}",
)
st.plotly_chart(fig_line, use_container_width=True)

# ============================================================
#  TABLA COMPLETA

st.subheader("📄 Datos Detectados (Tabla Completa)")
st.dataframe(df, use_container_width=True)

st.success("Dashboard cargado correctamente 🎉")
