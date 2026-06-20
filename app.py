import unicodedata
from pathlib import Path

import branca.colormap as cm
import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Análisis de delitos de la CDMX",
    page_icon="🗺️",
    layout="wide"
)

st.title("Tarea 2: análisis territorial de delitos")
st.caption("Luis Alberto De la Peña Chávez")

st.markdown(
    """
Con un dataset extenso real (INEGI, Datos Abiertos MX, Kaggle):

Se trabajó con los datos de las [Carpetas de investigación de la Fiscalía General
de Justicia de la Ciudad de México](https://archivo.datos.cdmx.gob.mx/FGJ/carpetas/carpetasFGJ_acumulado_2025_01.csv).
La información se simplificó mediante una
agrupación por alcaldía y categoría general del delito, con el propósito de
comparar territorialmente el número de registros.

1. Aplica **una técnica de simplificación** justificada (`groupby`/`resample`/muestreo).
2. Construye **una visualización interactiva** (Plotly o Altair) y **un mapa coroplético**.
3. Pide a una herramienta de IA un *insight* sobre el dataset y **valídalo o refútalo** con tu propio análisis.

En 3-4 líneas: ¿qué decisión de agregación tomaste y cómo cambiaría la historia con otra?

"""
)


@st.cache_data
def cargar_datos():

    ruta_datos = Path("agrupacion_delitos.parquet")
    ruta_shp = Path("2025_1_09_MUN/2025_1_09_MUN.shp")

    if not ruta_datos.exists():
        raise FileNotFoundError(
            "No se encontró agrupacion_delitos.parquet "
            "en la carpeta principal del proyecto."
        )

    if not ruta_shp.exists():
        raise FileNotFoundError(
            "No se encontró el archivo "
            "2025_1_09_MUN/2025_1_09_MUN.shp."
        )

    agrupacion = pd.read_parquet(ruta_datos)
    municipio = gpd.read_file(ruta_shp)

    return agrupacion, municipio


def normalizar_texto(texto):

    texto = str(texto).upper().strip()
    texto = unicodedata.normalize("NFKD", texto)

    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

def preparar_informacion(agrupacion, municipio):

    agrupacion = agrupacion.copy()
    municipio = municipio.copy()

    # Asegurar que la columna de alcaldía exista
    if "alcaldia_hecho" not in agrupacion.columns:
        raise ValueError(
            "El archivo Parquet no contiene la columna alcaldia_hecho."
        )

    # Identificar columnas numéricas
    columnas_numericas = agrupacion.select_dtypes(
        include="number"
    ).columns.tolist()

    # Crear Total solamente si todavía no existe
    if "Total" not in agrupacion.columns:
        agrupacion["Total"] = agrupacion[
            columnas_numericas
        ].sum(axis=1)

    agrupacion["alcaldia_union"] = (
        agrupacion["alcaldia_hecho"]
        .apply(normalizar_texto)
    )

    municipio["alcaldia_union"] = (
        municipio["NOMGEO"]
        .apply(normalizar_texto)
    )

    municipio_mapa = municipio.merge(
        agrupacion,
        on="alcaldia_union",
        how="left"
    )

    categorias = [
        columna
        for columna in agrupacion.columns
        if columna not in [
            "alcaldia_hecho",
            "alcaldia_union"
        ]
        and pd.api.types.is_numeric_dtype(
            agrupacion[columna]
        )
    ]

    municipio_mapa[categorias] = (
        municipio_mapa[categorias]
        .fillna(0)
    )

    municipio_mapa = municipio_mapa.to_crs(
        epsg=4326
    )

    categorias = ["Total"] + sorted(
        categoria
        for categoria in categorias
        if categoria != "Total"
    )

    return agrupacion, municipio_mapa, categorias


def construir_mapa(municipio_mapa, categoria):

    minimo = float(
        municipio_mapa[categoria].min()
    )

    maximo = float(
        municipio_mapa[categoria].max()
    )

    if minimo == maximo:
        maximo = minimo + 1

    escala = cm.linear.YlOrRd_09.scale(
        minimo,
        maximo
    )

    escala.caption = (
        f"Número de registros: {categoria}"
    )

    centro = (
        municipio_mapa
        .geometry
        .unary_union
        .centroid
    )

    mapa = folium.Map(
        location=[
            centro.y,
            centro.x
        ],
        zoom_start=10,
        tiles="CartoDB positron"
    )

    folium.GeoJson(
        municipio_mapa,
        style_function=lambda feature: {
            "fillColor": escala(
                feature["properties"].get(
                    categoria,
                    0
                )
            ),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.75
        },
        highlight_function=lambda feature: {
            "weight": 3,
            "fillOpacity": 0.9
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "NOMGEO",
                categoria
            ],
            aliases=[
                "Alcaldía:",
                f"{categoria}:"
            ],
            localize=True,
            sticky=False
        )
    ).add_to(mapa)

    escala.add_to(mapa)

    return mapa


try:

    agrupacion, municipio = cargar_datos()

    agrupacion1, municipio_mapa, categorias = (
        preparar_informacion(
            agrupacion,
            municipio
        )
    )

except Exception as error:

    st.error(
        f"No fue posible cargar la información: {error}"
    )

    st.info(
        "Revisa que agrupacion_delitos.parquet "
        "y la carpeta completa del shapefile "
        "estén dentro del proyecto."
    )

    st.stop()


st.sidebar.header("Controles")

categoria_seleccionada = st.sidebar.selectbox(
    "Categoría mostrada",
    options=categorias,
    index=0
)

st.sidebar.metric(
    "Registros de la categoría",
    f"{int(agrupacion1[categoria_seleccionada].sum()):,}"
)


# =========================================================
# 1. TÉCNICA DE SIMPLIFICACIÓN
# =========================================================

st.header(
    "1. Aplica una técnica de simplificación justificada "
    "(`groupby` / `resample` / muestreo)"
)

st.markdown(
    """
Se utilizó una técnica de simplificación mediante **agrupación (`groupby`)**.
Los registros individuales de carpetas de investigación se agruparon según
la **alcaldía del hecho** y la **categoría general del delito**.

Posteriormente, se contabilizó el número de observaciones de cada combinación
y se transformó el resultado a un formato ancho, donde cada fila representa
una alcaldía y cada columna una categoría delictiva.

El tratamiento fue estrictamente necesario debido al tamaño del documento y 
su publicación en esta plataforma. Se redujo una base de casi dos 
millones de registros a una tabla resumida que permite comparar de manera 
directa la distribución territorial de los delitos.
"""
)

st.subheader(
    f"Tabla de registros por alcaldía: {categoria_seleccionada}"
)

tabla = (
    agrupacion1[
        [
            "alcaldia_hecho",
            categoria_seleccionada
        ]
    ]
    .rename(
        columns={
            "alcaldia_hecho": "Alcaldía",
            categoria_seleccionada: "Registros"
        }
    )
    .sort_values(
        "Registros",
        ascending=False
    )
    .reset_index(drop=True)
)

tabla["Registros"] = (
    tabla["Registros"]
    .fillna(0)
    .astype(int)
)

tabla_mostrada = tabla.copy()

tabla_mostrada["Registros"] = (
    tabla_mostrada["Registros"]
    .map(lambda valor: f"{valor:,}")
)

st.dataframe(
    tabla_mostrada.style.set_properties(
        **{"text-align": "center"}
    ).set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("text-align", "center")
                ]
            }
        ]
    ),
    width=800,
    hide_index=True,
    height=600
)

st.download_button(
    label="Descargar tabla en CSV",
    data=tabla.to_csv(
        index=False
    ).encode("utf-8-sig"),
    file_name=(
        f"delitos_{categoria_seleccionada}.csv"
    ),
    mime="text/csv"
)

st.divider()


# =========================================================
# 2. VISUALIZACIÓN INTERACTIVA Y MAPA COROPLÉTICO
# =========================================================

st.header(
    "2. Construye una visualización interactiva "
    "(Plotly o Altair) y un mapa coroplético"
)

st.markdown(
    """
El mapa coroplético representa el número de carpetas de investigación por
alcaldía. El color de cada polígono cambia de acuerdo con la cantidad de
registros de la categoría seleccionada.

El selector ubicado en la barra lateral permite cambiar entre el total de
registros y las distintas categorías generales del delito. Además, al colocar
el cursor sobre una alcaldía se muestran su nombre y el número correspondiente
de registros.
"""
)

st.subheader(
    f"Mapa coroplético: {categoria_seleccionada}"
)

mapa = construir_mapa(
    municipio_mapa,
    categoria_seleccionada
)

st_folium(
    mapa,
    width=None,
    height=620,
    use_container_width=True,
    returned_objects=[]
)

st.divider()


st.header(
    "3. Pide a una herramienta de IA un *insight* sobre el dataset" 
    "y **valídalo o refútalo** con tu propio análisis."
)

st.markdown(
    """
### Insight principal

El dataset está fuertemente dominado por los delitos de bajo impacto:
representan **85.4 % de los 1,997,536 registros**. Por ello, cualquier análisis
o mapa basado en el total de carpetas tenderá a reproducir principalmente el
patrón territorial de esta categoría y puede ocultar la distribución de
delitos menos frecuentes, pero de mayor gravedad.

Por ejemplo, **Cuauhtémoc e Iztapalapa concentran juntas 29.7 % de todos los
registros**. Sin embargo, esto no necesariamente significa que sean las
alcaldías con mayor riesgo. Los conteos están influidos por su población,
población flotante, actividad comercial, movilidad y presencia de agencias
del Ministerio Público.

### Validación

Estos hallazgos coinciden con lo observado en las agrupaciones. Aunque el
predominio de los delitos de bajo impacto no siempre se aprecia claramente al
mostrar el total, el selector permite examinar cada categoría por separado y
evitar que las categorías más frecuentes oculten los patrones territoriales
de los delitos menos comunes.
"""
)

st.divider()

