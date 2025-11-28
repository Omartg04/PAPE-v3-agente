import pandas as pd
from .config import CONSTANTES_MAPEO
from typing import Dict

class AnalizadorProgramasSociales:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _aplicar_filtros(self, filtros: Dict) -> pd.DataFrame:
            df_f = self.df.copy()

            # 1. Geográfico (CORREGIDO PARA AGEBs)
            ub = filtros.get('ubicacion')
            if ub:
                # Limpieza: quitamos "ageb", "colonia", etc. para dejar solo el nombre/número
                ub_clean = ub.lower()\
                    .replace('colonia', '')\
                    .replace('pueblo', '')\
                    .replace('barrio', '')\
                    .replace('ageb', '')\
                    .strip() # <--- ¡AGREGADO .replace('ageb', '')!
                
                term = ub_clean if len(ub_clean) > 0 else ub
                
                # Buscamos en ambas columnas convirtiendo a string
                mascara = (
                    df_f['colonia'].astype(str).str.contains(term, case=False, na=False) |
                    df_f['ageb'].astype(str).str.contains(term, case=False, na=False)
                )
                df_f = df_f[mascara]

            # ... resto de filtros (edad, sexo, etc.) igual ...
            edad = filtros.get('rango_edad')
            if edad and len(edad) == 2:
                df_f = df_f[(df_f['edad_persona'] >= edad[0]) & (df_f['edad_persona'] <= edad[1])]

            sexo = filtros.get('sexo')
            if sexo:
                df_f = df_f[df_f['sexo_persona'] == sexo]

            parentesco = filtros.get('parentesco')
            if parentesco:
                val_real = CONSTANTES_MAPEO['PARENTESCOS'].get(parentesco.lower(), parentesco)
                df_f = df_f[df_f['parentesco_persona'] == val_real]

            carencia = filtros.get('carencia_tipo')
            if carencia:
                col = CONSTANTES_MAPEO['CARENCIAS'].get(carencia)
                if col:
                    df_f = df_f[df_f[col] == 'yes']

            return df_f

    def analisis_general(self, filtros: Dict) -> Dict:
        df_base = self._aplicar_filtros(filtros)
        if df_base.empty: return {"aviso": "Sin datos para estos filtros."}
        
        top_geo = df_base['colonia'].value_counts().head(5).to_dict()
        
        return {
            "total_personas": len(df_base),
            "hogares_unicos": df_base['id_hogar'].nunique(),
            "edad_promedio": round(df_base['edad_persona'].mean(), 1),
            "distribucion_sexo": df_base['sexo_persona'].value_counts().to_dict(),
            "top_5_colonias": top_geo
        }

    def analizar_elegibilidad(self, filtros: Dict) -> Dict:
        prog_key = filtros.get('programa_social')
        col_prog = CONSTANTES_MAPEO['PROGRAMAS'].get(prog_key)
        
        if not col_prog: return {"error": f"Programa no encontrado: {prog_key}"}

        df_base = self._aplicar_filtros(filtros)
        df_elegibles = df_base[df_base[col_prog] == 'yes']
        
        return {
            "programa": prog_key,
            "poblacion_objetivo": len(df_elegibles),
            "tasa_elegibilidad": round((len(df_elegibles)/len(df_base)*100), 1) if len(df_base)>0 else 0,
            "perfil_demografico": {
                "edad_promedio": round(df_elegibles['edad_persona'].mean(), 1) if not df_elegibles.empty else 0,
                "mujeres": int(df_elegibles[df_elegibles['sexo_persona'] == 'Mujer'].shape[0])
            }
        }

    def analizar_brechas(self, filtros: Dict) -> Dict:
        prog_key = filtros.get('programa_social')
        col_prog = CONSTANTES_MAPEO['PROGRAMAS'].get(prog_key)
        
        df_base = self._aplicar_filtros(filtros)
        df_elegibles = df_base[df_base[col_prog] == 'yes']
        
        # Brecha: Elegible + "No tiene" apoyo
        df_brecha = df_elegibles[
            (df_elegibles['recibe_apoyos_sociales'] == 'No tiene') | 
            (df_elegibles['recibe_apoyos_sociales'].isna())
        ]
        
        return {
            "analisis": "Brechas de Cobertura",
            "programa": prog_key,
            "total_elegibles": len(df_elegibles),
            "personas_sin_apoyo": len(df_brecha),
            "porcentaje_brecha": round((len(df_brecha)/len(df_elegibles)*100), 1) if not df_elegibles.empty else 0
        }

    def analizar_vulnerabilidad(self, filtros: Dict) -> Dict:
        df_base = self._aplicar_filtros(filtros)
        cols_carencias = list(CONSTANTES_MAPEO['CARENCIAS'].values())
        
        df_base['intensidad'] = (df_base[cols_carencias] == 'yes').sum(axis=1)
        conteo = df_base['intensidad'].value_counts().sort_index().to_dict()
        
        return {
            "analisis": "Intensidad de Vulnerabilidad",
            "distribucion_carencias (0 a 3)": conteo,
            "total_personas": len(df_base)
        }

    def tabla_cruzada(self, filtros: Dict) -> Dict:
            var_fil = filtros.get('variable_fila')
            var_col = filtros.get('variable_columna')
            
            col_real_fil = CONSTANTES_MAPEO['VARIABLES_CRUCE'].get(var_fil)
            col_real_col = CONSTANTES_MAPEO['VARIABLES_CRUCE'].get(var_col)
            
            if not col_real_fil or not col_real_col:
                return {"error": "Variables inválidas para cruce."}
                
            df_base = self._aplicar_filtros(filtros)
            
            # Agrupación segura para edad
            if col_real_fil == 'edad_persona':
                df_base['edad_cat'] = pd.cut(df_base['edad_persona'], bins=[0,12,18,30,60,120], labels=['0-12','13-18','19-30','31-60','60+'])
                col_real_fil = 'edad_cat'
            if col_real_col == 'edad_persona':
                df_base['edad_cat'] = pd.cut(df_base['edad_persona'], bins=[0,12,18,30,60,120], labels=['0-12','13-18','19-30','31-60','60+'])
                col_real_col = 'edad_cat'

            try:
                # 1. CALCULAMOS con los nombres reales (Seguridad ante todo)
                crosstab = pd.crosstab(df_base[col_real_fil], df_base[col_real_col], margins=True, margins_name="TOTAL")
                
                # 2. EMBELLECEMOS los nombres solo para la visualización
                mapa_visual = {
                    'presencia_carencia_salud_persona': 'Salud',
                    'presencia_rezago_educativo_persona': 'Educación',
                    'presencia_carencia_seguridad_social_persona': 'Seg. Social',
                    'sexo_persona': 'Sexo',
                    'colonia': 'Colonia',
                    'parentesco_persona': 'Parentesco',
                    'edad_cat': 'Rango Edad'
                }
                
                # Renombrar índice y columnas del resultado si existen en el mapa
                if crosstab.index.name in mapa_visual:
                    crosstab.index.name = mapa_visual[crosstab.index.name]
                
                if crosstab.columns.name in mapa_visual:
                    crosstab.columns.name = mapa_visual[crosstab.columns.name]

                # 3. RENDERIZADO
                tabla_md = crosstab.to_markdown(tablefmt="pipe")
                
                return {
                    "analisis": f"Cruce {var_fil} vs {var_col}",
                    "tabla_visual": tabla_md,
                    "datos_json": crosstab.to_dict()
                }
            except Exception as e:
                return {"error": f"Error generando tabla: {str(e)}"}