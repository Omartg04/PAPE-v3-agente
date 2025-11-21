import sys
import os

# Obtener la ruta absoluta del directorio actual (frontend)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Obtener la ruta padre (la raíz del proyecto)
root_dir = os.path.dirname(current_dir)
# Agregar la raíz al path de Python
sys.path.append(root_dir)

import streamlit as st
import time
from src.data_loader import DataIntegrator
from src.agent import AgenteAnaliticoLLM
from src.config import get_api_key

# Configuración de Página
st.set_page_config(page_title="Agente Política Social V3", page_icon="🏛️", layout="wide")

st.title("🏛️ Agente de Política Social: Álvaro Obregón")
st.markdown("---")

# --- 1. Inicialización del Sistema (Cacheado) ---
@st.cache_resource
def iniciar_sistema():
    """Carga datos y prepara el agente una sola vez"""
    loader = DataIntegrator()
    try:
        df = loader.cargar_y_unir_datasets()
        if df.empty: return None
        return df
    except Exception as e:
        st.error(f"Error iniciando sistema: {e}")
        return None

# --- 2. Sidebar de Configuración ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Manejo de API Key
    api_key = get_api_key() # Intenta cargar de .env
    if not api_key:
        api_key = st.text_input("Ingresa tu DeepSeek API Key", type="password")
    
    if api_key:
        st.success("API Key cargada")
    else:
        st.warning("Necesitas una API Key para continuar")

    st.markdown("### 💡 Capacidades V3")
    st.markdown("- **A:** Ranking Geográfico")
    st.markdown("- **B:** Diagnóstico Carencias")
    st.markdown("- **C:** Brechas de Cobertura")
    st.markdown("- **D:** Vulnerabilidad (0-3)")
    st.markdown("- **E:** Tablas Cruzadas")

# --- 3. Lógica Principal ---
if not api_key:
    st.info("👈 Por favor configura tu API Key en el menú lateral.")
    st.stop()

df = iniciar_sistema()

if df is None:
    st.error("❌ No se pudieron cargar los datos. Verifica la carpeta 'data/01_data'.")
    st.stop()

# Inicializar agente en sesión
if "agente" not in st.session_state:
    st.session_state.agente = AgenteAnaliticoLLM(df, api_key)

# Historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Renderizar chat previo
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 4. Input de Usuario ---
if prompt := st.chat_input("Escribe tu consulta (ej: 'Jefas de familia con carencia de salud en el Centro')"):
    # Mostrar usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar respuesta
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analizando datos con Arquitectura V3..."):
            try:
                inicio = time.time()
                respuesta = st.session_state.agente.procesar(prompt)
                tiempo = time.time() - inicio
                
                st.markdown(respuesta)
                st.caption(f"⏱️ Procesado en {tiempo:.2f}s")
                
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")