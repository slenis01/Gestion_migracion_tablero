import streamlit as st
import pandas as pd
import base64
import os
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
#from streamlit_extras import st_autorefresh


# ─────────────────────────────────────────────────────────────────────
# Configuración de página
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tablero Gestión migración",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────
EXPORT_DIR = Path(r"C:\Users\slenis.BANCOLOMBIA\Documents\Gestion_migracion_tablero\Resultado")  # ajusta si cambia
PATRON = "estado_gestion_*.xlsx"
HOJA_DETALLE = "Detalle"

# Estilos por estado
estilos_estado = {
    "Pendiente Migrar": {"emoji": "🛬", "color": "#394ae6"},
    "Alistamiento": {"emoji": "🛫", "color": "#ffb703"},
    "Migrado": {"emoji": "✅", "color": "#00b300"},
    "Migrado a Tiempo": {"emoji": "✅", "color": "#00b300"},
    "Migrado Vencido": {"emoji": "⚠️", "color": "#ff8800"},
    "Migrado (fecha faltante)": {"emoji": "⚠️", "color": "#ff8800"},
    "Por Reprogramar": {"emoji": "✏️", "color":  "#03ffff"},
    "Reprogramado": {"emoji": "🔁", "color": "#cf88f0"},
    "Reprogramado_Pendiente": {"emoji": "⏳", "color": "#cf88f0"},
    "Reprogramado_vencido": {"emoji": "⚠️", "color": "#ff8800"},
    "Vencido": {"emoji": "🔴", "color": "#ff032d"},
    "Aun a tiempo": {"emoji": "🕐", "color": "#808080"}
}

# ─────────────────────────────────────────────────────────────────────
# Utilidades UI
# ─────────────────────────────────────────────────────────────────────
def get_font_base64(font_path):
    with open(font_path, 'rb') as font_file:
        return base64.b64encode(font_file.read()).decode()

def mostrar_estado_html(conteo_dict, porcentaje_dict, titulo):
    st.markdown(f"""
    <div style='font-size: 22px; margin-top: 20px; margin-left: 10px; font-weight: bold; color: #333333;'>
        {titulo}
    </div>
    """, unsafe_allow_html=True)
    for estado, cantidad in conteo_dict.items():
        pct = porcentaje_dict.get(estado, 0)
        estilo = estilos_estado.get(estado, {"emoji": "📌", "color": "gray"})
        st.markdown(
            f"""
            <div style='display:flex; align-items:center; margin:8px 0 8px 15px; font-size:20px; color:{estilo['color']};'>
                <span style='font-size:24px; margin-right:10px;'>{estilo['emoji']}</span>
                <span><strong>{estado}</strong>: {cantidad:,} puntos
                <span style='font-size:16px; color:#666;'>({pct:.1f}%)</span></span>
            </div>
            """,
            unsafe_allow_html=True
        )

def detectar_columna_estado(df: pd.DataFrame) -> str | None:
    if 'Resultado_Evaluacion' in df.columns:
        return 'Resultado_Evaluacion'
    if 'Estado_Migracion_Texto' in df.columns:
        return 'Estado_Migracion_Texto'
    return None

def tiene_fecha_ruta(df: pd.DataFrame) -> bool:
    return 'fecha_ruta' in df.columns and pd.api.types.is_datetime64_any_dtype(df['fecha_ruta'])

# ─────────────────────────────────────────────────────────────────────
# Estilos globales / fuentes / logos
# ─────────────────────────────────────────────────────────────────────
font_path = os.path.join('assets', 'CIBFONTSANS-REGULAR.OTF')
if os.path.exists(font_path):
    font_base64 = get_font_base64(font_path)
    st.markdown(
        f"""
        <style>
            @font-face {{
                font-family: 'CIBFont';
                src: url(data:font/otf;base64,{font_base64}) format('opentype');
            }}
            * {{ font-family: 'CIBFont', sans-serif !important; }}
            .plotly-graph-div {{ font-family: 'CIBFont', sans-serif !important; }}
        </style>
        """,
        unsafe_allow_html=True
    )

if os.path.exists('assets/Logotipo_Wompi_VS2.png') and os.path.exists('assets/Logotipo_Wompi_WH.png'):
    st.markdown("""
        <style>
            #logo-claro { display: block; }
            #logo-oscuro { display: none; }
            @media (prefers-color-scheme: dark) {
                #logo-claro { display: none; }
                #logo-oscuro { display: block; }
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div id="logo-claro">
            <img src="data:image/png;base64,{base64.b64encode(open('assets/Logotipo_Wompi_VS2.png', 'rb').read()).decode()}" width="300">
        </div>
        <div id="logo-oscuro">
            <img src="data:image/png;base64,{base64.b64encode(open('assets/Logotipo_Wompi_WH.png', 'rb').read()).decode()}" width="300">
        </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# Selector de archivo (antes de cargar datos)
# ─────────────────────────────────────────────────────────────────────
@st.cache_data
def listar_archivos_excel(carpeta: Path, patron: str):
    archivos = sorted(carpeta.glob(patron), key=lambda p: p.stat().st_mtime, reverse=True)
    items = []
    for p in archivos:
        nombre = p.stem
        paquete = nombre.replace("estado_gestion_", "")
        ts = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        items.append((f"{paquete}  •  {ts}", p))
    return items

st.markdown("### 📂 Selecciona el paquete (archivo Excel)")
items_excel = listar_archivos_excel(EXPORT_DIR, PATRON)
if not items_excel:
    st.warning(f"No se encontraron archivos con el patrón '{PATRON}' en {EXPORT_DIR}")
    st.stop()

labels = [lbl for lbl, _ in items_excel]
seleccion = st.selectbox("Archivo disponible", labels, index=0)  # el más reciente
RUTA_EXCEL = dict(items_excel)[seleccion]  # Path del archivo elegido
st.caption(f"📄 Usando: {RUTA_EXCEL.name}  •  Ruta: {RUTA_EXCEL}")

# ──────────────────────────────────────────────
# ÚNICO BOTÓN + RECARGA AUTOMÁTICA AL DETECTAR CAMBIOS
# ──────────────────────────────────────────────
ultima_modificacion_actual = RUTA_EXCEL.stat().st_mtime
ultima_modificacion_guardada = st.session_state.get("ultima_modificacion")

# Si no existe en sesión, inicializar
if ultima_modificacion_guardada is None:
    st.session_state.ultima_modificacion = ultima_modificacion_actual

# Detectar cambios de archivo
if ultima_modificacion_actual != st.session_state.ultima_modificacion:
    # 👉 marcar bandera para mostrar banner tras el rerun
    st.session_state._mostrar_banner_autorefresco = True
    st.session_state.ultima_modificacion = ultima_modificacion_actual
    st.cache_data.clear()
    st.rerun()

# Botón manual para forzar recarga
if st.button("🔄 Recargar datos"):
    st.cache_data.clear()
    st.rerun()

# ──────────────────────────────────────────────
# Carga de datos usando mtime como dependencia
# ──────────────────────────────────────────────
HOJA_DETALLE = "Detalle"

@st.cache_data
def cargar_detalle(ruta_excel: str | Path, mtime: float) -> pd.DataFrame:
    """Carga el detalle desde Excel. 'mtime' asegura recarga si el archivo cambia."""
    df = pd.read_excel(ruta_excel, sheet_name=HOJA_DETALLE)
    if 'fecha_ruta' in df.columns:
        df['fecha_ruta'] = pd.to_datetime(df['fecha_ruta'], errors='coerce')
    return df

df_detalle = cargar_detalle(RUTA_EXCEL, st.session_state.ultima_modificacion)

# ──────────────────────────────────────────────
# Banner: “archivo actualizado automáticamente”
# ──────────────────────────────────────────────
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    TZ_BOG = ZoneInfo("America/Bogota")
except Exception:
    TZ_BOG = None

if st.session_state.get("_mostrar_banner_autorefresco"):
    fecha_str = datetime.fromtimestamp(st.session_state.ultima_modificacion, TZ_BOG).strftime("%Y-%m-%d %H:%M:%S") if TZ_BOG else datetime.fromtimestamp(st.session_state.ultima_modificacion).strftime("%Y-%m-%d %H:%M:%S")
    st.success(f"♻ Archivo actualizado automáticamente: {RUTA_EXCEL.name} • {fecha_str}")
    # limpia la bandera para no repetir el banner
    st.session_state._mostrar_banner_autorefresco = False



# ─────────────────────────────────────────────────────────────────────
# Carga de datos (cache invalidado por mtime)
# ─────────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_detalle(ruta_excel: str | Path, mtime: float) -> pd.DataFrame:
    # 'mtime' se usa SOLO para invalidar el cache cuando cambia el archivo
    df = pd.read_excel(ruta_excel, sheet_name=HOJA_DETALLE)
    if 'fecha_ruta' in df.columns:
        df['fecha_ruta'] = pd.to_datetime(df['fecha_ruta'], errors='coerce')
    return df

mtime = Path(RUTA_EXCEL).stat().st_mtime
df_detalle = cargar_detalle(RUTA_EXCEL, mtime)
if df_detalle.empty:
    st.warning("No hay datos en la hoja 'Detalle' del Excel seleccionado.")
    st.stop()

# Detectar columna de estado
col_estado_grupo = detectar_columna_estado(df_detalle)
if not col_estado_grupo:
    st.error("El archivo no contiene columnas de estado ('Resultado_Evaluacion' o 'Estado_Migracion_Texto').")
    st.stop()

# ─────────────────────────────────────────────────────────────────────
# 🗃️ Estado migración - Paquete Seleccionado (Total)
# ─────────────────────────────────────────────────────────────────────
st.markdown("<h2 style='text-align: center;'> 🗃️ Estado migración - Paquete Seleccionado</h2>", unsafe_allow_html=True)
df_paquete_total = df_detalle.copy()

total_puntos = df_paquete_total['Codigo_Punto'].nunique() if 'Codigo_Punto' in df_paquete_total.columns else len(df_paquete_total)
conteo_estado = df_paquete_total[col_estado_grupo].value_counts().to_dict()
df_estado_pct = df_paquete_total[col_estado_grupo].value_counts(normalize=True).mul(100).round(1).to_dict()

col_total, col_estado, col_grafico = st.columns([1.5, 2, 5])
with col_total:
    st.markdown(f"""
    <div style='text-align:center;font-size:100px; font-weight:700;'>
        {total_puntos}
    </div>
    <div style='text-align:center;font-size:16px;'>
        Total puntos del paquete
    </div>
    """, unsafe_allow_html=True)

with col_estado:
    mostrar_estado_html(conteo_estado, df_estado_pct, "📋 Estado actual")

with col_grafico:
    df_agrupado = (
        df_paquete_total
        .groupby([col_estado_grupo])['Codigo_Punto']
        .count()
        .reset_index(name='Cantidad')
        .sort_values('Cantidad', ascending=False)
    )
    total_safe = max(total_puntos, 1)
    df_agrupado['Porcentaje'] = df_agrupado['Cantidad'] / total_safe * 100

    fig_estado = go.Figure()
    fig_estado.add_trace(go.Bar(
        x=df_agrupado[col_estado_grupo],
        y=df_agrupado['Porcentaje'],
        text=df_agrupado['Porcentaje'].round(1).astype(str) + '%',
        textposition='inside',
        textfont=dict(size=18, color='black'),
        marker_color=[estilos_estado.get(e, {}).get('color', 'gray') for e in df_agrupado[col_estado_grupo]],
        hovertemplate="%{x}<br>%{text}",
        width=0.4
    ))
    fig_estado.update_layout(
        title="📊 Distribución por estado",
        xaxis_title="Estado",
        yaxis_title="% del total",
        height=420,
        bargap=0.15,
        margin=dict(t=40, l=20, r=20, b=40)
    )
    st.plotly_chart(fig_estado, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────
# 🗓️ Estado migración por fecha (solo si hay fecha_ruta)
# ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<h2 style='text-align: center;'> 🗓️ Estado migración por fecha</h2>", unsafe_allow_html=True)

def tiene_fecha_ruta(df: pd.DataFrame) -> bool:
    return 'fecha_ruta' in df.columns and pd.api.types.is_datetime64_any_dtype(df['fecha_ruta'])

if tiene_fecha_ruta(df_detalle):
    fechas_disponibles = sorted(df_detalle['fecha_ruta'].dropna().dt.date.unique())
    if not fechas_disponibles:
        st.info("No hay fechas disponibles en 'fecha_ruta' para este archivo.")
    else:
        modo = st.radio("🗓️ Tipo de análisis", ["Solo día seleccionado", "Día y anteriores"], horizontal=True)
        fecha_sel = st.selectbox(
            "📅 Selecciona una fecha de corte para análisis",
            fechas_disponibles,
            format_func=lambda d: pd.to_datetime(d).strftime('%d/%m/%Y')
        )

        # --- usar SOLO el subset seleccionado ---
        df_dia = df_detalle.copy()
        if modo == "Solo día seleccionado":
            df_dia = df_dia[df_dia['fecha_ruta'].dt.date == fecha_sel]
        else:
            df_dia = df_dia[df_dia['fecha_ruta'].dt.date <= fecha_sel]

        if df_dia.empty:
            st.warning("⚠️ No hay puntos programados para ese criterio.")
        else:
            # Indicadores (sobre el subset)
            total_dia = df_dia['Codigo_Punto'].nunique() if 'Codigo_Punto' in df_dia.columns else len(df_dia)
            conteo_estado_dia = df_dia[col_estado_grupo].value_counts().to_dict()
            df_estado_pct_dia = df_dia[col_estado_grupo].value_counts(normalize=True).mul(100).round(1).to_dict()

            col1, col2, col3 = st.columns([1.5, 2, 5])
            with col1:
                st.markdown(f"<div style='text-align:center;font-size:100px; font-weight:700;'>{total_dia}</div>", unsafe_allow_html=True)
                st.markdown("<div style='text-align:center;font-size:16px;'>Total puntos al día</div>", unsafe_allow_html=True)
            with col2:
                mostrar_estado_html(conteo_estado_dia, df_estado_pct_dia, "📋 Estado actual")

            # --- GRÁFICO: usar df_dia, no df_detalle ---
            df_dia = df_dia.copy()
            df_dia['Dia'] = df_dia['fecha_ruta'].dt.date
            agrupado = df_dia.groupby(['Dia', col_estado_grupo])['Codigo_Punto'].count().reset_index()

            # Pivot a porcentajes por día
            pivot = agrupado.pivot(index='Dia', columns=col_estado_grupo, values='Codigo_Punto').fillna(0)
            pivot_pct = pivot.div(pivot.sum(axis=1).replace(0, 1), axis=0) * 100

            # Anchura de barra más grande si es un solo día
            only_one_day = (pivot_pct.shape[0] == 1)
            bar_width = 0.6 if only_one_day else 0.2

            fig = go.Figure()
            for estado in pivot_pct.columns:
                color_estado = estilos_estado.get(estado, {}).get('color', 'gray')
                fig.add_trace(go.Bar(
                    x=[pd.to_datetime(d).strftime('%d/%m/%Y') for d in pivot_pct.index],
                    y=pivot_pct[estado],
                    name=estado,
                    text=pivot_pct[estado].round(1).astype(str) + '%',
                    textposition='inside',
                    textfont=dict(size=20),
                    marker_color=color_estado,
                    hovertemplate="%{x}<br>%{text}<br>%{y:.1f}%",
                    width=bar_width
                ))

            fig.update_layout(
                barmode='stack',
                title="📊 Evolución porcentual de migración",
                xaxis_title="Fecha",
                yaxis_title="% de puntos",
                height=420,
                bargap=0.2
            )

            # En modo “Solo día”, quita el margen extra del eje X
            if only_one_day:
                fig.update_xaxes(type='category')

            with col3:
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Este archivo no contiene 'fecha_ruta'. Se muestra solo la distribución total por estado.")
