import pandas as pd
import os

class DataIntegrator:
    def cargar_y_unir_datasets(self, ruta_base: str = None):
        """Carga inteligente de datos buscando desde la raíz"""
        # Rutas posibles para ejecución local o despliegue
        rutas_posibles = ["data/01_data/", "../data/01_data/", "./data/01_data/"]
        
        if ruta_base is None:
            for r in rutas_posibles:
                if os.path.exists(r) and os.path.exists(f"{r}/CaracteristicasPersona.csv"):
                    ruta_base = r
                    break
        
        if not ruta_base:
            raise FileNotFoundError("❌ No se encontró la carpeta 'data/01_data'. Verifica la estructura.")

        print(f"📂 Cargando datos desde: {ruta_base}")
        try:
            df_hog = pd.read_csv(f"{ruta_base}/CaracteristicasHogar.csv")
            df_per = pd.read_csv(f"{ruta_base}/CaracteristicasPersona.csv")
            df_car = pd.read_csv(f"{ruta_base}/CarenciasPersona.csv")
            df_int = pd.read_csv(f"{ruta_base}/IntervencionesPotencialesPAPEPersona.csv")

            # Merge consolidado
            df_full = df_per.merge(df_car, on=['id_hogar', 'id_persona'], how='inner')
            df_full = df_full.merge(df_int, on=['id_hogar', 'id_persona'], how='inner')
            df_full = df_full.merge(df_hog, on='id_hogar', how='left')

            # Limpieza preventiva
            df_full = df_full[(df_full['edad_persona'] >= 0) & (df_full['edad_persona'] <= 120)]
            
            return df_full
        except Exception as e:
            print(f"❌ Error crítico cargando CSVs: {e}")
            return pd.DataFrame()