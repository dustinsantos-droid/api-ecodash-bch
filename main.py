from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime

app = FastAPI(title="API EcoDash Honduras")

# Permitir conexión desde tu página de Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BCHAzureExtractor:
    def __init__(self):
        # Conexión directa a la API Moderna de Azure del BCH
        self.base_url = "https://bchapi-am.azure-api.net/api/v1/indicadores"
        self.api_key = "d41d091369a344cba429d461ac4d6cbe"

    def get_indicator(self, indicator_id, limit=30):
        """Obtiene datos limpios en JSON de la API de Azure del BCH"""
        url = f"{self.base_url}/{indicator_id}/cifras"
        
        # Enviamos la clave tanto en los parámetros como en los Headers (Estándar de Azure APIM)
        params = {'formato': 'Json', 'clave': self.api_key}
        headers = {
            'Ocp-Apim-Subscription-Key': self.api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # Verificar que sea una lista con datos
                if isinstance(data, list) and len(data) > 0:
                    # Ordenar de más reciente a más antiguo
                    data.sort(key=lambda x: x.get('fecha', ''), reverse=True)
                    return data[:limit]
            else:
                print(f"BCH API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error fetching indicator {indicator_id} from Azure: {e}")
        return []

extractor = BCHAzureExtractor()

@app.get("/api/bch/latest")
def get_latest_data():
    print("Obteniendo datos en vivo desde Azure BCH...")
    
    # Extraer Tipo de Cambio e Inflación (SIN YAHOO FINANCE)
    tc_data = extractor.get_indicator("4", limit=30)
    inf_data = extractor.get_indicator("2", limit=1)
    
    latest_tc = tc_data[0] if tc_data else {"valor": 0, "fecha": ""}
    latest_inf = inf_data[0] if inf_data else {"valor": 0, "fecha": ""}

    # Formatear el historial para el gráfico
    historico_tc = []
    for item in tc_data:
        if 'fecha' in item and 'valor' in item:
            fecha_limpia = item['fecha'].split('T')[0]
            historico_tc.append({
                "fecha": fecha_limpia,
                "tasa": float(item['valor'])
            })
    # Invertir para gráfico cronológico
    historico_tc.reverse()
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "inflacion": {"valor": float(latest_inf.get("valor", 0)), "fecha": latest_inf.get("fecha", "")},
            "tipo_cambio": {"venta": float(latest_tc.get("valor", 0)), "fecha": latest_tc.get("fecha", "")},
            "historico_tipo_cambio": historico_tc
        }
    }
