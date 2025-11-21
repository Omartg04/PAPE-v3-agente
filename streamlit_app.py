"""
PAPE V3 BETA: Autenticación + Rate Limiting (10 consultas/día)
Diseñado para desplegar hoy mismo a personal de la alcaldía
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
from src.agent import AgenteAnaliticoLLM
from src.data_loader import DataIntegrator


# ============================================================================
# 1. SISTEMA DE AUTENTICACIÓN SIMPLE
# ============================================================================

class GestorAutenticacion:
    """Maneja login de usuarios (sin BD, usa JSON local por ahora)"""
    
    def __init__(self, archivo_usuarios: str = "datos/usuarios.json"):
        self.archivo = archivo_usuarios
        Path(self.archivo).parent.mkdir(parents=True, exist_ok=True)
        self._garantizar_archivo()
    
    def _garantizar_archivo(self):
        """Crea archivo si no existe"""
        if not os.path.exists(self.archivo):
            usuarios_default = {
                "admin@alcaldia.mx": {
                    "password_hash": self._hash_password("admin123"),
                    "nombre": "Admin PAPE",
                    "rol": "administrador",
                    "activo": True,
                    "fecha_creacion": datetime.now().isoformat()
                },
                "funcionario@alcaldia.mx": {
                    "password_hash": self._hash_password("func123"),
                    "nombre": "Funcionario Test",
                    "rol": "analista",
                    "activo": True,
                    "fecha_creacion": datetime.now().isoformat()
                }
            }
            with open(self.archivo, 'w') as f:
                json.dump(usuarios_default, f, indent=2)
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hashea contraseña (producción: usar bcrypt)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validar_credenciales(self, email: str, password: str) -> tuple[bool, str, str]:
        """Valida email/password. Retorna (es_valido, nombre, rol)"""
        try:
            with open(self.archivo, 'r') as f:
                usuarios = json.load(f)
            
            if email not in usuarios:
                return False, "", ""
            
            usuario = usuarios[email]
            
            if not usuario.get("activo", False):
                return False, "Usuario desactivado", ""
            
            if usuario["password_hash"] != self._hash_password(password):
                return False, "Contraseña incorrecta", ""
            
            return True, usuario["nombre"], usuario["rol"]
        
        except Exception as e:
            return False, f"Error: {e}", ""
    
    def registrar_usuario(self, email: str, password: str, nombre: str, rol: str = "analista"):
        """Crea nuevo usuario (solo admin)"""
        try:
            with open(self.archivo, 'r') as f:
                usuarios = json.load(f)
            
            if email in usuarios:
                return False, "Email ya registrado"
            
            usuarios[email] = {
                "password_hash": self._hash_password(password),
                "nombre": nombre,
                "rol": rol,
                "activo": True,
                "fecha_creacion": datetime.now().isoformat()
            }
            
            with open(self.archivo, 'w') as f:
                json.dump(usuarios, f, indent=2)
            
            return True, "Usuario creado exitosamente"
        
        except Exception as e:
            return False, f"Error: {e}"


# ============================================================================
# 2. SISTEMA DE RATE LIMITING (10 consultas/día)
# ============================================================================

class GestorRateLimiting:
    """Controla: máximo 10 consultas por día por usuario"""
    
    def __init__(self, archivo_limites: str = "datos/limites_uso.json"):
        self.archivo = archivo_limites
        Path(self.archivo).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.archivo):
            with open(self.archivo, 'w') as f:
                json.dump({}, f)
    
    def obtener_uso_hoy(self, email: str) -> dict:
        """Retorna: {consultas_hoy, limite, puede_consultar, proxima_disponible}"""
        try:
            with open(self.archivo, 'r') as f:
                limites = json.load(f)
            
            hoy = datetime.now().date().isoformat()
            
            if email not in limites:
                limites[email] = {}
            
            # Si no hay registro de hoy, crear uno
            if hoy not in limites[email]:
                limites[email][hoy] = {
                    "consultas": 0,
                    "primera_consulta": None,
                    "historial": []
                }
            
            datos_hoy = limites[email][hoy]
            consultas = datos_hoy.get("consultas", 0)
            limite = 10
            puede_consultar = consultas < limite
            
            # Calcular próxima disponible (mañana a las 00:00)
            mañana = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0)
            proxima = mañana.isoformat()
            
            return {
                "consultas_hoy": consultas,
                "limite": limite,
                "puede_consultar": puede_consultar,
                "proxima_disponible": proxima,
                "porcentaje_uso": round((consultas / limite) * 100, 1)
            }
        
        except Exception as e:
            st.error(f"Error leyendo limites: {e}")
            return {
                "consultas_hoy": 0,
                "limite": 10,
                "puede_consultar": True,
                "proxima_disponible": "",
                "porcentaje_uso": 0
            }
    
    def registrar_consulta(self, email: str, consulta: str):
        """Registra una consulta exitosa"""
        try:
            with open(self.archivo, 'r') as f:
                limites = json.load(f)
            
            hoy = datetime.now().date().isoformat()
            
            if email not in limites:
                limites[email] = {}
            if hoy not in limites[email]:
                limites[email][hoy] = {
                    "consultas": 0,
                    "primera_consulta": None,
                    "historial": []
                }
            
            limites[email][hoy]["consultas"] += 1
            
            if limites[email][hoy]["primera_consulta"] is None:
                limites[email][hoy]["primera_consulta"] = datetime.now().isoformat()
            
            limites[email][hoy]["historial"].append({
                "timestamp": datetime.now().isoformat(),
                "consulta": consulta[:100]  # Primeros 100 chars
            })
            
            with open(self.archivo, 'w') as f:
                json.dump(limites, f, indent=2)
        
        except Exception as e:
            st.warning(f"Error registrando consulta: {e}")
    
    def limpiar_limites_antiguos(self, dias_retencion: int = 30):
        """Limpia registros más viejos de N días"""
        try:
            with open(self.archivo, 'r') as f:
                limites = json.load(f)
            
            fecha_limite = (datetime.now() - timedelta(days=dias_retencion)).date().isoformat()
            
            for email in limites:
                fechas_a_eliminar = [f for f in limites[email] if f < fecha_limite]
                for fecha in fechas_a_eliminar:
                    del limites[email][fecha]
            
            with open(self.archivo, 'w') as f:
                json.dump(limites, f, indent=2)
        
        except Exception as e:
            st.warning(f"Error limpiando limites: {e}")


# ============================================================================
# 3. INTERFAZ STREAMLIT CON AUTENTICACIÓN
# ============================================================================

def main():
    st.set_page_config(
        page_title="PAPE V3 - Política Social",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Estilos
    st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 12px;
        border-radius: 4px;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 12px;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # ESTADO DE SESIÓN
    # ========================================================================
    
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "email_usuario" not in st.session_state:
        st.session_state.email_usuario = None
    if "nombre_usuario" not in st.session_state:
        st.session_state.nombre_usuario = None
    if "rol_usuario" not in st.session_state:
        st.session_state.rol_usuario = None
    
    # ========================================================================
    # PÁGINA DE LOGIN (Si no autenticado)
    # ========================================================================
    
    if not st.session_state.autenticado:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("---")
            st.title("🏛️ PAPE V3")
            st.subheader("Agente de Política Social Álvaro Obregón")
            st.markdown("---")
            
            # Tabs: Login / Registro (solo para demo, en prod controlar con permisos)
            tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "👤 Registro (Demo)"])
            
            with tab1:
                st.markdown("### Inicia sesión con tus credenciales")
                
                email = st.text_input("📧 Email", key="login_email")
                password = st.text_input("🔑 Contraseña", type="password", key="login_password")
                
                if st.button("✅ Ingresar", use_container_width=True):
                    gestor_auth = GestorAutenticacion()
                    es_valido, nombre, rol = gestor_auth.validar_credenciales(email, password)
                    
                    if es_valido:
                        st.session_state.autenticado = True
                        st.session_state.email_usuario = email
                        st.session_state.nombre_usuario = nombre
                        st.session_state.rol_usuario = rol
                        st.success(f"✅ Bienvenido, {nombre}!")
                        st.rerun()
                    else:
                        st.error(f"❌ {nombre}")
                
                st.markdown("---")
                st.markdown("""
                **Credenciales de Prueba:**
                - 📧 funcionario@alcaldia.mx
                - 🔑 func123
                """)
            
            with tab2:
                st.markdown("### Crear Nueva Cuenta (Solo Demo)")
                
                nuevo_email = st.text_input("📧 Email", key="reg_email")
                nuevo_nombre = st.text_input("👤 Nombre Completo", key="reg_nombre")
                nueva_password = st.text_input("🔑 Contraseña", type="password", key="reg_password")
                nueva_password_conf = st.text_input("🔑 Confirmar Contraseña", type="password", key="reg_password_conf")
                
                if st.button("✅ Crear Cuenta", use_container_width=True):
                    if nueva_password != nueva_password_conf:
                        st.error("Las contraseñas no coinciden")
                    elif len(nueva_password) < 6:
                        st.error("La contraseña debe tener al menos 6 caracteres")
                    else:
                        gestor_auth = GestorAutenticacion()
                        exito, mensaje = gestor_auth.registrar_usuario(
                            nuevo_email, nueva_password, nuevo_nombre
                        )
                        if exito:
                            st.success(mensaje)
                        else:
                            st.error(mensaje)
    
    # ========================================================================
    # APLICACIÓN PRINCIPAL (Si autenticado)
    # ========================================================================
    
    else:
        # SIDEBAR: Información de usuario + Rate Limit
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"### 👤 Usuario")
            st.markdown(f"**{st.session_state.nombre_usuario}**")
            st.markdown(f"*{st.session_state.email_usuario}*")
            st.markdown(f"📌 Rol: `{st.session_state.rol_usuario}`")
            
            # Rate Limiting
            gestor_limites = GestorRateLimiting()
            uso = gestor_limites.obtener_uso_hoy(st.session_state.email_usuario)
            
            st.markdown("---")
            st.markdown("### 📊 Uso del Día")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Consultas Usadas", f"{uso['consultas_hoy']}/{uso['limite']}")
            with col2:
                st.metric("Disponible", uso['limite'] - uso['consultas_hoy'])
            
            # Barra de progreso
            st.progress(uso['porcentaje_uso'] / 100)
            
            if not uso['puede_consultar']:
                st.warning(
                    f"⚠️ **Límite alcanzado**\n\n"
                    f"Próximas consultas disponibles mañana a las 00:00"
                )
            
            st.markdown("---")
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                st.session_state.autenticado = False
                st.session_state.email_usuario = None
                st.rerun()
        
        # CONTENIDO PRINCIPAL
        st.title("🏛️ PAPE V3 - Análisis de Política Social")
        st.markdown(f"*Alcaldía Álvaro Obregón | Usuario: {st.session_state.nombre_usuario}*")
        
        # Cargar agente
        @st.cache_resource
        def cargar_agente():
            integrador = DataIntegrator()
            df = integrador.cargar_y_unir_datasets()
            api_key = os.getenv("DEEPSEEK_API_KEY")
            return AgenteAnaliticoLLM(df, api_key)
        
        agente = cargar_agente()
        
        # Si no puede consultar
        if not uso['puede_consultar']:
            st.error("❌ Has alcanzado el límite de 10 consultas por día.")
            st.info("Próximas consultas disponibles mañana a las 00:00.")
            st.stop()
        
        # Input de consulta
        st.markdown("---")
        
        consulta = st.chat_input(
            "¿Qué necesitas analizar?",
            disabled=not uso['puede_consultar']
        )
        
        if consulta:
            # Guardar en historial
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Mostrar consulta del usuario
            with st.chat_message("user"):
                st.markdown(consulta)
            
            # Procesar
            with st.spinner("🔍 Analizando..."):
                try:
                    respuesta = agente.procesar(consulta)
                    
                    # Registrar en rate limiting
                    gestor_limites.registrar_consulta(
                        st.session_state.email_usuario,
                        consulta
                    )
                    
                    # Guardar en historial
                    st.session_state.chat_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "usuario": st.session_state.nombre_usuario,
                        "consulta": consulta,
                        "respuesta": respuesta
                    })
                
                except Exception as e:
                    respuesta = f"❌ Error: {str(e)}"
            
            # Mostrar respuesta
            with st.chat_message("assistant"):
                st.markdown(respuesta)
            
            # Actualizar contador en tiempo real
            st.rerun()
        
        # Mostrar historial si existe
        if "chat_history" in st.session_state and st.session_state.chat_history:
            st.markdown("---")
            st.markdown("### 📋 Historial de Consultas")
            
            for i, item in enumerate(reversed(st.session_state.chat_history[-5:]), 1):
                with st.expander(f"{i}. {item['consulta'][:50]}..."):
                    st.markdown(f"**Hora:** {item['timestamp']}")
                    st.markdown(f"**Consulta:**\n{item['consulta']}")
                    st.markdown("**Respuesta:**")
                    st.markdown(item['respuesta'])


if __name__ == "__main__":
    main()