import json
import re
from openai import OpenAI
from .logic import AnalizadorProgramasSociales
from .config import CONSTANTES_MAPEO

class AgenteAnaliticoLLM:
    def __init__(self, df_completo, api_key):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        self.motor = AnalizadorProgramasSociales(df_completo)
        
        self.system_prompt = """Eres un Asistente de Política Social.
        TU MISIÓN: Traducir preguntas a JSON para la herramienta 'ejecutar_analisis'.
        
        MAPEO DE INTENCIONES:
        - "Perfil", "Cuántos", "Demografía" -> intencion="conteo_general"
        - "Beca", "Pensión", "Programa" -> intencion="elegibilidad"
        - "Brechas", "No reciben" -> intencion="brechas"
        - "Vulnerabilidad", "Intensidad" -> intencion="vulnerabilidad" (Es el análisis global 0-3 carencias. NO pidas especificar tipo).
        - "Cruzar", "Tabla", "Relación" -> intencion="tabla_cruzada"
        """
        
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _definir_master_tool(self):
        return [{
            "type": "function",
            "function": {
                "name": "ejecutar_analisis",
                "description": "Motor analítico.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intencion": {
                            "type": "string",
                            "enum": ["conteo_general", "elegibilidad", "brechas", "vulnerabilidad", "tabla_cruzada"]
                        },
                        "filtros": {
                            "type": "object",
                            "properties": {
                                "rango_edad": {"type": "array", "items": {"type": "integer"}},
                                "sexo": {"type": "string", "enum": ["Mujer", "Hombre"]},
                                "ubicacion": {"type": "string"},
                                "programa_social": {"type": "string", "enum": list(CONSTANTES_MAPEO["PROGRAMAS"].keys())},
                                "carencia_tipo": {"type": "string", "enum": ["salud", "educacion", "seguridad_social"]},
                                "grupo_especial": {"type": "string", "enum": ["ninguno", "jefas_familia"]},
                                "variable_fila": {"type": "string", "enum": list(CONSTANTES_MAPEO["VARIABLES_CRUCE"].keys())},
                                "variable_columna": {"type": "string", "enum": list(CONSTANTES_MAPEO["VARIABLES_CRUCE"].keys())}
                            }
                        }
                    },
                    "required": ["intencion", "filtros"]
                }
            }
        }]

    def _router_maestro(self, args):
        intencion = args.get('intencion')
        filtros = args.get('filtros', {})
        if filtros.get('grupo_especial') == 'jefas_familia':
            filtros['sexo'] = 'Mujer'
            filtros['parentesco'] = 'jefe'

        try:
            if intencion == 'conteo_general': return self.motor.analisis_general(filtros)
            elif intencion == 'elegibilidad': return self.motor.analizar_elegibilidad(filtros)
            elif intencion == 'brechas': return self.motor.analizar_brechas(filtros)
            elif intencion == 'vulnerabilidad': return self.motor.analizar_vulnerabilidad(filtros)
            elif intencion == 'tabla_cruzada': return self.motor.tabla_cruzada(filtros)
            return {"error": "Intención no reconocida"}
        except Exception as e:
            return {"error_interno": str(e)}

    def _normalizar_salida_llm(self, msg):
        if msg.tool_calls:
            try: return json.loads(msg.tool_calls[0].function.arguments)
            except: pass
        content = msg.content or ""
        if "<|tool" in content:
            try:
                match = re.search(r"<\|tool sep\|>(.*?)<\|tool call end\|>", content, re.DOTALL)
                if match: return json.loads(match.group(1).strip())
            except: pass
        try:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match: return json.loads(match.group(0))
        except: pass
        return None

    def procesar(self, consulta: str):
            # Limpieza periódica de memoria
            if len(self.messages) > 6:
                self.messages = [{"role": "system", "content": self.system_prompt}]
                
            self.messages.append({"role": "user", "content": consulta})
            
            try:
                # FASE 1: OBTENER INTENCIÓN (LLM)
                resp = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=self.messages,
                    tools=self._definir_master_tool(),
                    tool_choice="auto", 
                    temperature=0.0 
                )
                msg = resp.choices[0].message
                args = self._normalizar_salida_llm(msg)

                if args:
                    # FASE 2: EJECUCIÓN PYTHON
                    resultado = self._router_maestro(args)
                    
                    # Guardar historial técnico
                    self.messages.append(msg)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": msg.tool_calls[0].id if msg.tool_calls else "call_fallback",
                        "name": "ejecutar_analisis",
                        "content": json.dumps(resultado, default=str)
                    })
                    
                    # FASE 3: EXTRACCIÓN HÍBRIDA
                    tabla_visual = resultado.get('tabla_visual', None)
                    
                    # FASE 4: EL ANALISTA ESTRATÉGICO (Creatividad Activada 🧠)
                    mensajes_narrador = [
                        {"role": "system", "content": "Eres un Estratega Senior de Política Social."},
                        {"role": "user", "content": f"""
                        Analiza los siguientes datos JSON resultantes de una consulta sobre la Alcaldía Álvaro Obregón:
                        {json.dumps(resultado, default=str)}

                        INSTRUCCIONES DE ANÁLISIS:
                        1. IGNORA el campo 'tabla_visual' (yo ya lo mostraré aparte).
                        2. Realiza una interpretación PROFUNDA y NARRATIVA de los datos numéricos.
                        3. Busca activamente:
                        - Brechas de género (¿Las mujeres están más afectadas?).
                        - Vulnerabilidad por edad (¿Niños o ancianos en riesgo?).
                        - Patrones atípicos o alarmantes.
                        4. Usa un tono profesional, empático y orientado a la toma de decisiones.
                        5. NO repitas los números fila por fila (eso aburre), explica QUÉ SIGNIFICAN esos números para la política social.
                        6. Estructura tu respuesta con subtítulos claros (Markdown).
                        """}
                    ]
                    
                    final = self.client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=mensajes_narrador, 
                        temperature=0.7 # Subimos temperatura para recuperar creatividad y elocuencia
                    )
                    
                    texto_analisis = final.choices[0].message.content
                    
                    # FASE 5: ENSAMBLAJE FINAL
                    # La tabla va primero (Dato duro) + Análisis profundo después (Interpretación)
                    if tabla_visual:
                        return f"{tabla_visual}\n\n{texto_analisis}"
                    else:
                        return texto_analisis

                return msg.content

            except Exception as e:
                return f"❌ Error técnico: {e}"