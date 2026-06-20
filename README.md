# Aplicación Streamlit: delitos CDMX

## Estructura requerida

```text
proyecto/
├── app.py
├── requirements.txt
├── datos.pkl
└── 2025_1_09_MUN/
    ├── 2025_1_09_MUN.shp
    ├── 2025_1_09_MUN.shx
    ├── 2025_1_09_MUN.dbf
    ├── 2025_1_09_MUN.prj
    └── demás archivos asociados
```

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicación

1. Crea un repositorio en GitHub.
2. Sube todos los archivos de la estructura anterior.
3. En Streamlit Community Cloud selecciona el repositorio.
4. Indica `app.py` como archivo principal.
5. Comparte la URL generada.

No subas información sensible o institucional a un repositorio público.
