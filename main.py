from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime
import yfinance as yf

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
        self.indicators = {
            "tipo_cambio_venta": "4",
            "inflacion_interanual": "2"
        }

    def get_indicator(self, indicator_id, limit=30):
        """Obtiene datos limpios en JSON de la API de Azure del BCH"""
        url = f"{self.base_url}/{indicator_id}/cifras?formato=Json&clave={self.api_key}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # Verificar que sea una lista con datos
                if isinstance(data, list) and len(data) > 0:
                    # Ordenar de más reciente a más antiguo
                    data.sort(key=lambda x: x.get('fecha', ''), reverse=True)
                    return data[:limit]
        except Exception as e:
            print(f"Error fetching indicator {indicator_id} from Azure: {e}")
        return []

def get_wti_live_data():
    """Conecta a Yahoo Finance para extraer WTI en tiempo real."""
    try:
        wti = yf.Ticker("CL=F")
        todays_data = wti.history(period='1d')
        
        if not todays_data.empty:
            current_price = float(todays_data['Close'].iloc[0])
            high = float(todays_data['High'].iloc[0])
            low = float(todays_data['Low'].iloc[0])
            open_price = float(todays_data['Open'].iloc[0])
            change = ((current_price - open_price) / open_price) * 100
            
            return {
                "price": round(current_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "change": round(change, 2)
            }
    except Exception as e:
        print(f"Error extrayendo WTI: {e}")
    return {"price": 0.0, "high": 0.0, "low": 0.0, "change": 0.0}

extractor = BCHAzureExtractor()

@app.get("/api/bch/latest")
def get_latest_data():
    print("Obteniendo datos en vivo desde Azure BCH...")
    
    # 1. Datos del BCH (Tipo de cambio 30 días, Inflación 1 dato)
    tc_data = extractor.get_indicator(extractor.indicators["tipo_cambio_venta"], limit=30)
    inf_data = extractor.get_indicator(extractor.indicators["inflacion_interanual"], limit=1)
    
    # Extraer el dato más reciente
    latest_tc = tc_data[0] if tc_data else {"valor": 0, "fecha": ""}
    latest_inf = inf_data[0] if inf_data else {"valor": 0, "fecha": ""}

    # Formatear el historial para el gráfico
    historico_tc = []
    for item in tc_data:
        fecha_limpia = item['fecha'].split('T')[0] # Limpiar la 'T' del formato ISO
        historico_tc.append({
            "fecha": fecha_limpia,
            "tasa": float(item['valor'])
        })
    # Invertir para que el gráfico vaya de izquierda (antiguo) a derecha (reciente)
    historico_tc.reverse()
    
    # 2. Datos del Mercado Internacional (Petróleo WTI)
    wti_data = get_wti_live_data()
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "inflacion": {"valor": float(latest_inf["valor"]), "fecha": latest_inf["fecha"]},
            "tipo_cambio": {"venta": float(latest_tc["valor"]), "fecha": latest_tc["fecha"]},
            "historico_tipo_cambio": historico_tc,
            "commodities": {
                "wti": wti_data
            }
        }
    }
