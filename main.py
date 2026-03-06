from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime

app = FastAPI(title="EcoDash API Definitiva")

# Permitir que tu web en Netlify lea este servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Credenciales oficiales del BCH
BCH_URL = "https://bchapi-am.azure-api.net/api/v1/indicadores"
BCH_KEY = "d41d091369a344cba429d461ac4d6cbe"

@app.get("/api/datos-maestros")
def get_datos_maestros():
    """
    Extrae BCH (TC, Inflación, Histórico) y EMBI en una sola llamada segura.
    Al hacerlo desde el servidor, evitamos los bloqueos CORS del navegador.
    """
    respuesta = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "bch": None,
        "embi": None,
        "errores": []
    }

    # 1. EXTRACCIÓN DEL BANCO CENTRAL DE HONDURAS (BCH)
    try:
        # Azure APIM requiere la clave en el Header
        headers = {
            "Ocp-Apim-Subscription-Key": BCH_KEY,
            "User-Agent": "Mozilla/5.0"
        }
        params = {"formato": "Json"}

        # Extraer Tipo de Cambio (Indicador 4) e Inflación (Indicador 2)
        res_tc = requests.get(f"{BCH_URL}/4/cifras", headers=headers, params=params, timeout=15)
        res_inf = requests.get(f"{BCH_URL}/2/cifras", headers=headers, params=params, timeout=15)

        if res_tc.status_code == 200 and res_inf.status_code == 200:
            tc_data = res_tc.json()
            inf_data = res_inf.json()

            # Ordenar para asegurar que el dato más reciente esté en la posición [0]
            tc_data.sort(key=lambda x: x.get('fecha', ''), reverse=True)
            inf_data.sort(key=lambda x: x.get('fecha', ''), reverse=True)

            # Construir el objeto de respuesta del BCH
            respuesta["bch"] = {
                "tipo_cambio_actual": float(tc_data[0]['valor']) if tc_data else 0,
                "inflacion_actual": float(inf_data[0]['valor']) if inf_data else 0,
                # Extraemos los últimos 30 días estrictamente de esta misma fuente para el gráfico
                "historico_tc": [
                    {"fecha": item['fecha'].split('T')[0], "tasa": float(item['valor'])} 
                    for item in tc_data[:30]
                ]
            }
        else:
            respuesta["errores"].append("BCH API rechazó la conexión.")
    except Exception as e:
        respuesta["errores"].append(f"Falla en extracción BCH: {str(e)}")

    # 2. EXTRACCIÓN DEL RIESGO PAÍS (EMBI vía BCRP)
    try:
        url_embi = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04698XD/json"
        res_embi = requests.get(url_embi, timeout=15)
        
        if res_embi.status_code == 200:
            embi_json = res_embi.json()
            # Navegamos el JSON del BCRP para encontrar el último valor
            ultimo_valor = embi_json['periods'][-1]['values'][0]
            respuesta["embi"] = float(ultimo_valor)
        else:
            respuesta["errores"].append("BCRP API rechazó la conexión.")
    except Exception as e:
        respuesta["errores"].append(f"Falla en extracción EMBI: {str(e)}")

    return respuesta
