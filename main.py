from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse
import urllib3
from datetime import datetime

# Desactivar advertencias de seguridad SSL (común en sitios gubernamentales)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="EcoDash API Definitiva")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BCH_URL = "https://bchapi-am.azure-api.net/api/v1/indicadores"
BCH_KEY = "d41d091369a344cba429d461ac4d6cbe"

def fetch_con_bypass(url, headers=None, params=None):
    """
    Intenta extraer la data directamente. Si el firewall del Banco Central 
    bloquea la IP de Render (AWS), utiliza un proxy interno para evadirlo.
    """
    # Construir la URL completa con parámetros
    full_url = url
    if params:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
    # Intento 1: Directo
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Fallo directo a {url}: {e}")

    # Intento 2: Bypass de IP mediante proxy
    try:
        proxy_url = f"https://api.allorigins.win/raw?url={urllib.parse.quote(full_url)}"
        res = requests.get(proxy_url, timeout=15, verify=False)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Fallo bypass a {url}: {e}")
        
    return None

@app.get("/api/datos-maestros")
def get_datos_maestros():
    respuesta = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "bch": None,
        "embi": None,
        "errores": []
    }

    # 1. EXTRACCIÓN DEL BANCO CENTRAL DE HONDURAS (BCH)
    headers = {
        "Ocp-Apim-Subscription-Key": BCH_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "application/json"
    }
    params = {"formato": "Json"}

    tc_data = fetch_con_bypass(f"{BCH_URL}/4/cifras", headers=headers, params=params)
    inf_data = fetch_con_bypass(f"{BCH_URL}/2/cifras", headers=headers, params=params)

    if tc_data and inf_data and isinstance(tc_data, list) and isinstance(inf_data, list):
        tc_data.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        inf_data.sort(key=lambda x: x.get('fecha', ''), reverse=True)

        respuesta["bch"] = {
            "tipo_cambio_actual": float(tc_data[0]['valor']) if len(tc_data) > 0 else 0,
            "inflacion_actual": float(inf_data[0]['valor']) if len(inf_data) > 0 else 0,
            "historico_tc": [
                {"fecha": item['fecha'].split('T')[0], "tasa": float(item['valor'])} 
                for item in tc_data[:30]
            ]
        }
    else:
        respuesta["errores"].append("BCH bloqueó la conexión y los proxies de respaldo.")

    # 2. EXTRACCIÓN DEL RIESGO PAÍS (EMBI vía BCRP)
    embi_url = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04698XD/json"
    embi_data = fetch_con_bypass(embi_url, headers=headers)
    
    if embi_data and 'periods' in embi_data:
        respuesta["embi"] = float(embi_data['periods'][-1]['values'][0])
    else:
        respuesta["errores"].append("BCRP bloqueó la conexión y los proxies de respaldo.")

    return respuesta
