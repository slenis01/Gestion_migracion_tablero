import streamlit as st
import pandas as pd
import base64
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import unicodedata

# ── Config de página ─────────────────────────────────────────────────
st.set_page_config(page_title="Tablero Gestión migración", layout="wide", initial_sidebar_state="expanded")

# ── Rutas ────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent
EXPORT_DIR = (APP_DIR / "Resultado")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = APP_DIR / "assets"
ARCHIVO_FIJO = EXPORT_DIR / "estado_gestion_todos.xlsx"
HOJA_DETALLE = "Detalle"

# ── Estilos por estado ───────────────────────────────────────────────
estilos_estado = {
    "Pendiente Migrar": {"emoji": "🛬", "color": "#394ae6"},
    "Alistamiento": {"emoji": "🛫", "color": "#ffb703"},
    "Migrado": {"emoji": "✅", "color": "#00b300"},
    "Migrado A Tiempo": {"emoji": "✅", "color": "#00b300"},
    "Migrado Vencido": {"emoji": "⚠️", "color": "#ff8800"},
    "Migrado (fecha faltante)": {"emoji": "⚠️", "color": "#ff8800"},
    "Por Reprogramar": {"emoji": "✏️", "color":  "#03ffff"},
    "Reprogramado": {"emoji": "🔁", "color": "#cf88f0"},
    "Reprogramado_Pendiente": {"emoji": "⏳", "color": "#cf88f0"},
    "Reprogramado_vencido": {"emoji": "⚠️", "color": "#ff8800"},
    "Vencido": {"emoji": "🔴", "color": "#ff032d"},
    "Aun A Tiempo": {"emoji": "🕐", "color": "#808080"},
    "En Ruta": {"emoji": "🚚", "color": "#9aa0a6"},
}

# ── Utilidades UI ────────────────────────────────────────────────────
def _file_to_b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()

def detectar_columna_estado(df: pd.DataFrame) -> str | None:
    # candidatos directos
    for col in ["Resultado_Evaluacion", "Estado_Migracion_Texto"]:
        if col in df.columns:
            return col
    # búsqueda flexible (normaliza nombres)
    norm_cols = {c: str(c).strip().lower().replace(" ", "_") for c in df.columns}
    # heurística: alguna columna que contenga "estado" y "migr"
    for original, norm in norm_cols.items():
        if "estado" in norm and "migr" in norm:
            return original
    # fallback: alguna que contenga solo "estado"
    for original, norm in norm_cols.items():
        if "estado" in norm:
            return original
    return None


def mostrar_estado_html(conteo_dict, porcentaje_dict, titulo):
    st.markdown(f"<div style='font-size:22px;margin-top:20px;margin-left:10px;font-weight:bold;color:#ccc'>{titulo}</div>", unsafe_allow_html=True)
    for estado, cantidad in conteo_dict.items():
        pct = porcentaje_dict.get(estado, 0)
        estilo = estilos_estado.get(estado, {"emoji": "📌", "color": "gray"})
        st.markdown(
            f"""
            <div style='display:flex;align-items:center;margin:8px 0 8px 15px;font-size:20px;color:{estilo['color']}'>
                <span style='font-size:24px;margin-right:10px;'>{estilo['emoji']}</span>
                <span><strong>{estado}</strong>: {cantidad:,} puntos
                <span style='font-size:16px;color:#888'>({pct:.1f}%)</span></span>
            </div>
            """,
            unsafe_allow_html=True
        )

def _norm_txt(s):
    if pd.isna(s): return s
    s = str(s).strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')  # quita tildes
    up = s.upper()
    M = {
        'ALISTAMIENTO': 'Alistamiento',
        'EN RUTA': 'En Ruta',
        'MIGRADO': 'Migrado',
        'MIGRADO A TIEMPO': 'Migrado A Tiempo',
        'MIGRADO VENCIDO': 'Migrado Vencido',
        'MIGRADO (FECHA FALTANTE)': 'Migrado (fecha faltante)',
        'PENDIENTE MIGRAR': 'Pendiente Migrar',
        'POR REPROGRAMAR': 'Por Reprogramar',
        'REPROGRAMADO': 'Reprogramado',
        'REPROGRAMADO PENDIENTE': 'Reprogramado_Pendiente',
        'REPROGRAMADO VENCIDO': 'Reprogramado_vencido',
        'AUN A TIEMPO': 'Aun A Tiempo',
        'DESISTIDO': 'Desistido',   # por si llega esta etiqueta
    }
    return M.get(up, s)

# ── Fuente/logo (opcional) ───────────────────────────────────────────
font_path = ASSETS_DIR / "CIBFONTSANS-REGULAR.OTF"
if font_path.exists():
    st.markdown(
        f"""
        <style>
            @font-face {{
                font-family: 'CIBFont';
                src: url(data:font/otf;base64,{_file_to_b64(font_path)}) format('opentype');
            }}
            * {{ font-family: 'CIBFont', sans-serif !important; }}
            .plotly-graph-div {{ font-family: 'CIBFont', sans-serif !important; }}
        </style>
        """,
        unsafe_allow_html=True
    )

logo_vs2 = ASSETS_DIR / "Logotipo_Wompi_VS2.png"
logo_wh  = ASSETS_DIR / "Logotipo_Wompi_WH.png"
if logo_vs2.exists() and logo_wh.exists():
    st.markdown("""
        <style>
            #logo-claro { display:block; }
            #logo-oscuro { display:none; }
            @media (prefers-color-scheme: dark) {
                #logo-claro { display:none; }
                #logo-oscuro { display:block; }
            }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div id="logo-claro"><img src="data:image/png;base64,{_file_to_b64(logo_vs2)}" width="300"></div>
        <div id="logo-oscuro"><img src="data:image/png;base64,{_file_to_b64(logo_wh)}"  width="300"></div>
        """,
        unsafe_allow_html=True
    )

# ── Archivo fuente + autorefresco ────────────────────────────────────
st.markdown("### 📄 Archivo fuente")
if not ARCHIVO_FIJO.exists():
    st.error(f"No se encontró el archivo {ARCHIVO_FIJO.relative_to(APP_DIR)}")
    st.stop()
st.caption(f"📄 Usando: {ARCHIVO_FIJO.name} • Ruta relativa: {ARCHIVO_FIJO.relative_to(APP_DIR)}")

ultima_modificacion_actual = ARCHIVO_FIJO.stat().st_mtime
if "ultima_modificacion" not in st.session_state:
    st.session_state.ultima_modificacion = ultima_modificacion_actual

if ultima_modificacion_actual != st.session_state.ultima_modificacion:
    st.session_state._mostrar_banner_autorefresco = True
    st.session_state.ultima_modificacion = ultima_modificacion_actual
    st.cache_data.clear()
    st.rerun()

if st.button("🔄 Recargar datos"):
    st.cache_data.clear()
    st.rerun()

try:
    from zoneinfo import ZoneInfo
    TZ_BOG = ZoneInfo("America/Bogota")
except Exception:
    TZ_BOG = None

if st.session_state.get("_mostrar_banner_autorefresco"):
    fecha_str = (
        datetime.fromtimestamp(st.session_state.ultima_modificacion, TZ_BOG).strftime("%Y-%m-%d %H:%M:%S")
        if TZ_BOG else
        datetime.fromtimestamp(st.session_state.ultima_modificacion).strftime("%Y-%m-%d %H:%M:%S")
    )
    st.success(f"♻ Archivo actualizado automáticamente: {ARCHIVO_FIJO.name} • {fecha_str}")
    st.session_state._mostrar_banner_autorefresco = False

# ── Cargar Excel ─────────────────────────────────────────────────────
@st.cache_data
def cargar_todos(ruta_excel: Path, mtime: float) -> pd.DataFrame:
    try:
        df = pd.read_excel(ruta_excel, sheet_name=HOJA_DETALLE)
    except Exception:
        df = pd.read_excel(ruta_excel)

    if 'fecha_ruta' in df.columns:
        df['fecha_ruta'] = pd.to_datetime(df['fecha_ruta'], errors='coerce')

    if 'Codigo_Punto' in df.columns:
        df['Codigo_Punto'] = df['Codigo_Punto'].astype(str).str.strip()

    if 'paquetes_logisticos' in df.columns:
        df['paquetes_logisticos'] = df['paquetes_logisticos'].astype(str).str.strip().str.title()

    col_estado = detectar_columna_estado(df)
    if col_estado:
        df[col_estado] = df[col_estado].apply(_norm_txt)

    return df

df_todos = cargar_todos(ARCHIVO_FIJO, st.session_state.ultima_modificacion)
if df_todos.empty:
    st.warning("El archivo no tiene datos para mostrar.")
    st.stop()

# ── Selector de paquete ──────────────────────────────────────────────
if 'paquetes_logisticos' not in df_todos.columns:
    st.error("El archivo no contiene la columna 'paquetes_logisticos'.")
    st.stop()

paquetes = sorted([p for p in df_todos['paquetes_logisticos'].dropna().unique()])
paquete_sel = st.selectbox("📦 Selecciona paquete logístico", ['Todos'] + paquetes, index=0)

df_detalle = df_todos if paquete_sel == 'Todos' else df_todos[df_todos['paquetes_logisticos'] == paquete_sel]
if df_detalle.empty:
    st.warning("No hay puntos para el paquete seleccionado.")
    st.stop()



# ── 🗃️ Estado migración - Paquete Seleccionado (Total) ──────────────
st.markdown("<h2 style='text-align:center;margin-top:6px;'>🗃️ Estado migración - Paquete Seleccionado</h2>", unsafe_allow_html=True)

df_paquete_total = df_detalle.copy()
if {'Codigo_Punto','fecha_ruta'}.issubset(df_paquete_total.columns):
    df_paquete_total = (
        df_paquete_total.sort_values('fecha_ruta')
        .groupby('Codigo_Punto', as_index=False)
        .tail(1)  # último estado por punto
    )

col_estado_grupo = detectar_columna_estado(df_paquete_total)
if not col_estado_grupo:
    st.error("No encuentro la columna de estado ('Resultado_Evaluacion' o 'Estado_Migracion_Texto').")
    st.stop()

total_puntos = df_paquete_total['Codigo_Punto'].nunique() if 'Codigo_Punto' in df_paquete_total.columns else len(df_paquete_total)

df_agrupado_total = (
    df_paquete_total.groupby([col_estado_grupo], dropna=False)
    .size().reset_index(name='Cantidad')
    .sort_values('Cantidad', ascending=False)
)
total_safe = max(int(df_agrupado_total['Cantidad'].sum()), 1)
df_agrupado_total['Porcentaje'] = df_agrupado_total['Cantidad'] / total_safe * 100

conteo_estado = dict(zip(df_agrupado_total[col_estado_grupo], df_agrupado_total['Cantidad']))
df_estado_pct = dict(zip(df_agrupado_total[col_estado_grupo], df_agrupado_total['Porcentaje'].round(1)))

col_total, col_estado, col_grafico = st.columns([1.2, 2, 5])

with col_total:
    st.markdown(
        f"""
        <div style='text-align:center;font-size:100px;font-weight:800;line-height:0.95'>{total_puntos}</div>
        <div style='text-align:center;font-size:16px;margin-top:6px;'>Total puntos del paquete</div>
        """,
        unsafe_allow_html=True
    )

with col_estado:
    mostrar_estado_html(conteo_estado, df_estado_pct, "📋 Estado actual")

with col_grafico:
    fig_estado = go.Figure()
    fig_estado.add_trace(go.Bar(
        x=df_agrupado_total[col_estado_grupo],
        y=df_agrupado_total['Porcentaje'],
        text=df_agrupado_total['Porcentaje'].round(1).astype(str) + '%',
        textposition='inside',
        textfont=dict(size=18, color='black'),
        marker_color=[estilos_estado.get(e, {}).get('color', 'gray') for e in df_agrupado_total[col_estado_grupo]],
        hovertemplate="%{x}<br>%{text}",
        width=0.45
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

# ── 🗓️ Estado migración por fecha ───────────────────────────────────
st.markdown("---")
st.markdown("<h2 style='text-align:center;'>🗓️ Estado migración por fecha</h2>", unsafe_allow_html=True)

if 'fecha_ruta' in df_detalle.columns:
    # 1) columna segura solo con la fecha (sin hora)
    df_detalle = df_detalle.copy()
    df_detalle['fecha_dia'] = pd.to_datetime(df_detalle['fecha_ruta'], errors='coerce').dt.date

    fechas_disponibles = sorted([d for d in df_detalle['fecha_dia'].dropna().unique()])
    if not fechas_disponibles:
        st.info("No hay fechas disponibles en 'fecha_ruta' para este archivo.")
    else:
        modo = st.radio("🗓️ Tipo de análisis", ["Solo día seleccionado", "Día y anteriores"], horizontal=True)
        fecha_sel = st.selectbox(
            "📅 Fecha de corte",
            fechas_disponibles,
            format_func=lambda d: pd.to_datetime(d).strftime('%d/%m/%Y')
        )

        # 2) filtrado robusto con fecha_dia
        if modo == "Solo día seleccionado":
            df_dia = df_detalle[df_detalle['fecha_dia'] == fecha_sel]
        else:
            df_dia = df_detalle[df_detalle['fecha_dia'] <= fecha_sel]

        # 3) re-detecta la columna de estado sobre el DF filtrado
        col_estado_grupo_fecha = detectar_columna_estado(df_dia)

        # # --- DEBUG opcional: despliega insumos
        # with st.expander("🔧 Depuración por fecha"):
        #     st.write("Fecha seleccionada:", fecha_sel)
        #     st.write("Filas filtradas:", len(df_dia))
        #     st.write("Columna de estado detectada:", col_estado_grupo_fecha)
        #     st.write("Muestra:", df_dia[[c for c in ['Codigo_Punto','fecha_ruta','fecha_dia', col_estado_grupo_fecha] if c in df_dia.columns]].head(5))

        if df_dia.empty:
            st.warning("⚠️ No hay puntos programados para ese criterio.")
        else:
            df_dia = df_dia.copy()
            df_dia['Dia'] = df_dia['fecha_ruta'].dt.date

            # total puntos en ese corte
            total_dia = df_dia['Codigo_Punto'].nunique() if 'Codigo_Punto' in df_dia.columns else len(df_dia)

            # conteo de estados en ese día/corte
            conteo_estado_dia = df_dia[col_estado_grupo_fecha].value_counts().to_dict()
            df_estado_pct_dia = df_dia[col_estado_grupo_fecha].value_counts(normalize=True).mul(100).round(1).to_dict()

            # layout igual al de “Paquete Seleccionado”
            col1, col2, col3 = st.columns([1.5, 2, 5])
            with col1:
                st.markdown(f"<div style='text-align:center;font-size:100px;font-weight:700;'>{total_dia}</div>", unsafe_allow_html=True)
                st.markdown("<div style='text-align:center;font-size:16px;'>Total puntos al día</div>", unsafe_allow_html=True)
            with col2:
                mostrar_estado_html(conteo_estado_dia, df_estado_pct_dia, "📋 Estado actual")

            # evolución porcentual (multi-día)
            agrupado = (
                df_dia.groupby(['Dia', col_estado_grupo_fecha], dropna=False)
                .size().reset_index(name='Cantidad')
            )

            pivot = agrupado.pivot(index='Dia', columns=col_estado_grupo_fecha, values='Cantidad').fillna(0)
            pivot_pct = pivot.div(pivot.sum(axis=1).replace(0, 1), axis=0) * 100

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
            if only_one_day:
                fig.update_xaxes(type='category')

            with col3:
                st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Este archivo no contiene 'fecha_ruta'. Se muestra solo la distribución total por estado.")
