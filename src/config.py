import os
from dotenv import load_dotenv

# Cargar variables de entorno si existe archivo .env
load_dotenv()

def get_api_key():
    """Recupera la API Key de forma segura"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        # Retorna None para manejarlo en la UI de Streamlit
        return None 
    return api_key.strip()

# CONSTANTES DE MAPEO (BLINDAJE)
CONSTANTES_MAPEO = {
    "PROGRAMAS": {
        "beca_benito_juarez": "es_elegible_beca_benito_juarez",
        "beca_rita_cetina": "es_elegible_beca_rita_cetina",
        "pension_adultos_mayores": "es_elegible_pension_adultos_mayores",
        "pension_mujeres_bienestar": "es_elegible_pension_mujeres_bienestar",
        "jovenes_construyendo_futuro": "es_elegible_jovenes_construyendo_futuro",
        "jovenes_escribiendo_el_futuro": "es_elegible_jovenes_escribiendo_el_futuro",
        "mi_beca_para_empezar": "es_elegible_mi_beca_para_empezar",
        "imss_bienestar": "es_elegible_imss_bienestar",
        "desde_la_cuna": "es_elegible_desde_la_cuna",
        "seguro_desempleo_cdmx": "es_elegible_seguro_desempleo_cdmx",
        "ingreso_ciudadano_universal": "es_elegible_ingreso_ciudadano_universal",
        "inea": "es_elegible_inea",
        "leche_bienestar": "es_elegible_leche_bienestar"
    },
    "CARENCIAS": {
        "salud": "presencia_carencia_salud_persona",
        "educacion": "presencia_rezago_educativo_persona",
        "seguridad_social": "presencia_carencia_seguridad_social_persona"
    },
    "PARENTESCOS": {
        "jefe": "Jefa o jefe",
        "esposa": "Esposa(o) o pareja",
        "hijo": "Hija(o)",
        "nieto": "Nieta(o)",
        "padre": "Madre o padre"
    },
    "VARIABLES_CRUCE": {
        "sexo": "sexo_persona",
        "edad": "edad_persona",
        "parentesco": "parentesco_persona",
        "colonia": "colonia",
        "carencia_salud": "presencia_carencia_salud_persona",
        "carencia_educacion": "presencia_rezago_educativo_persona",
        "carencia_seguridad": "presencia_carencia_seguridad_social_persona"
    }
}