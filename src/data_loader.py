import pandas as pd
import os
import requests
from io import StringIO

class DataIntegrator:

    def __init__(self):
        # 📌 URL BASE donde están alojados los CSV en GitHub Releases
        self.URL_BASE = "https://github.com/Omartg04/PAPE-v3-agente/releases/download/v1.0/"

        # 📌 nombres de los archivos esperados
        self.FILES = {
            "hogar": "CaracteristicasHogar.csv",
            "persona": "CaracteristicasPersona.csv",
            "carencias": "CarenciasPersona.csv",
            "intervenciones": "IntervencionesPotencialesPAPEPersona.csv"
        }

    # --------------------------------------------------

    def _leer_csv_url(self, url: str):
        """Descargar CSV desde una URL y devolverlo como DataFrame."""
        print(f"⬇️ Descargando desde: {url}")
        resp = requests.get(url)

        if resp.status_code != 200:
            raise FileNotFoundError(f"❌ No se pudo descargar: {url} (status {resp.status_code})")

        return pd.read_csv(StringIO(resp.text))

    # --------------------------------------------------

    def cargar_y_unir_datasets(self, ruta_base: str = None):
        """Carga inteligente: primero local, luego remoto vía GitHub Releases."""

        rutas_posibles = [
            "data/01_data/",
            "./data/01_data/",
            "../data/01_data/"
        ]

        # -------------------------
        # 1️⃣ Intento de carga local
        # -------------------------
        if ruta_base is None:
            for r in rutas_posibles:
                if os.path.exists(os.path.join(r, self.FILES["persona"])):
                    ruta_base = r
                    break

        if ruta_base:
            try:
                print(f"📂 Cargando datos desde carpeta local: {ruta_base}")

                df_hog = pd.read_csv(os.path.join(ruta_base, self.FILES["hogar"]))
                df_per = pd.read_csv(os.path.join(ruta_base, self.FILES["persona"]))
                df_car = pd.read_csv(os.path.join(ruta_base, self.FILES["carencias"]))
                df_int = pd.read_csv(os.path.join(ruta_base, self.FILES["intervenciones"]))

            except Exception as e:
                print(f"⚠️ Error cargando localmente ({e}). Intentando remoto…")
                ruta_base = None  # Forzar cambio a URL

        # -------------------------
        # 2️⃣ Si falla local → cargar desde GitHub Releases
        # -------------------------
        if not ruta_base:
            print("🌐 Cargando datos desde GitHub Releases (modo nube)…")

            try:
                df_hog = self._leer_csv_url(self.URL_BASE + self.FILES["hogar"])
                df_per = self._leer_csv_url(self.URL_BASE + self.FILES["persona"])
                df_car = self._leer_csv_url(self.URL_BASE + self.FILES["carencias"])
                df_int = self._leer_csv_url(self.URL_BASE + self.FILES["intervenciones"])

            except Exception as e:
                raise FileNotFoundError(
                    f"❌ Falló la carga remota desde GitHub Releases.\n"
                    f"Verifica que los archivos existen en:\n{self.URL_BASE}\n\n"
                    f"Error original:\n{e}"
                )

        # -------------------------
        # 3️⃣ Unificación de datasets
        # -------------------------
        df_full = df_per.merge(df_car, on=['id_hogar', 'id_persona'], how='inner')
        df_full = df_full.merge(df_int, on=['id_hogar', 'id_persona'], how='inner')
        df_full = df_full.merge(df_hog, on='id_hogar', how='left')

        # Limpieza básica
        df_full = df_full[(df_full['edad_persona'] >= 0) & (df_full['edad_persona'] <= 120)]

        print("✅ Datos cargados y unificados correctamente.")
        return df_full
