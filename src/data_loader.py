import pandas as pd
import os

class DataIntegrator:

    def __init__(self):
        # 📌 URL BASE donde subirás los CSV (GitHub Releases recomendado)
        self.URL_BASE = "https://github.com/Omartg04/PAPE-v3-agente/releases/download/data-v1/"

        # 📌 lista de archivos a cargar
        self.FILES = {
            "hogar": "CaracteristicasHogar.csv",
            "persona": "CaracteristicasPersona.csv",
            "carencias": "CarenciasPersona.csv",
            "intervenciones": "IntervencionesPotencialesPAPEPersona.csv"
        }

    def cargar_y_unir_datasets(self, ruta_base: str = None):
        """Carga inteligente: local → remoto (GitHub Releases)"""

        rutas_posibles = [
            "data/01_data/",
            "./data/01_data/",
            "../data/01_data/"
        ]

        # 1️⃣ Intentar carga local
        if ruta_base is None:
            for r in rutas_posibles:
                if os.path.exists(r) and os.path.exists(os.path.join(r, self.FILES["persona"])):
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
                print("⚠️ Error local, cambiando a carga remota…", e)
                ruta_base = None  # Forzar cambio a remoto

        # 2️⃣ Si no existe local → cargar desde URLs
        if not ruta_base:
            print("🌐 Cargando datos desde URLs externas (GitHub Releases)")

            try:
                df_hog = pd.read_csv(self.URL_BASE + self.FILES["hogar"])
                df_per = pd.read_csv(self.URL_BASE + self.FILES["persona"])
                df_car = pd.read_csv(self.URL_BASE + self.FILES["carencias"])
                df_int = pd.read_csv(self.URL_BASE + self.FILES["intervenciones"])
            except Exception as e:
                raise FileNotFoundError(
                    f"❌ No se pudieron cargar datos desde URLs.\n"
                    f"Verifica que los archivos existen en:\n{self.URL_BASE}\n\nError: {e}"
                )

        # 3️⃣ Unificación de datasets
        df_full = df_per.merge(df_car, on=['id_hogar', 'id_persona'], how='inner')
        df_full = df_full.merge(df_int, on=['id_hogar', 'id_persona'], how='inner')
        df_full = df_full.merge(df_hog, on='id_hogar', how='left')

        df_full = df_full[(df_full['edad_persona'] >= 0) & (df_full['edad_persona'] <= 120)]

        return df_full