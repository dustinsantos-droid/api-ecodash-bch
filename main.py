from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
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

class BCHDataExtractor:
    def __init__(self):
        self.soap_url = "https://www.bch.hn/estadisticas-economicas/diseminacion-de-datos/_vti_bin/lists.asmx"
        self.indicators = {
            "tipo_cambio_venta": "4",
            "inflacion_interanual": "2"
        }

    def _build_soap_payload(self, indicator_id, limit=1):
        """Construye el XML. Acepta un límite de filas para el historial."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <GetListItems xmlns="http://schemas.microsoft.com/sharepoint/soap/">
              <listName>IndicadoresEconomicos</listName>
              <query>
                <Query>
                  <Where>
                    <Eq><FieldRef Name="Indicador_x0020_ID" /><Value Type="Number">{indicator_id}</Value></Eq>
                  </Where>
                  <OrderBy><FieldRef Name="Fecha" Ascending="FALSE" /></OrderBy>
                </Query>
              </query>
              <viewFields><ViewFields><FieldRef Name="Fecha" /><FieldRef Name="Valor" /></ViewFields></viewFields>
              <rowLimit>{limit}</rowLimit>
            </GetListItems>
          </soap:Body>
        </soap:Envelope>"""

    def get_indicator(self, indicator_id):
        """Obtiene solo el último dato con lectura infalible."""
        # Añadimos un User-Agent para que el servidor del BCH no bloquee la petición
        headers = {
            'Content-Type': 'text/xml; charset=utf-8', 
            'SOAPAction': 'http://schemas.microsoft.com/sharepoint/soap/GetListItems',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            response = requests.post(self.soap_url, data=self._build_soap_payload(indicator_id, limit=1), headers=headers, timeout=15)
            if response.status_code == 200:
                # Usamos Regex para buscar exactamente los valores, evitando errores de formato XML
                valor_match = re.search(r'ows_Valor="([^"]+)"', response.text)
                fecha_match = re.search(r'ows_Fecha="([^"]+)"', response.text)
                
                if valor_match and fecha_match:
                    fecha_limpia = fecha_match.group(1).split(' ')[0]
                    return {"fecha": fecha_limpia, "valor": float(valor_match.group(1))}
        except Exception as e:
            print(f"Error BCH: {e}")
        return None

    def get_historical_indicator(self, indicator_id, limit=30):
        """Obtiene un historial de datos para el gráfico."""
        headers = {
            'Content-Type': 'text/xml; charset=utf-8', 
            'SOAPAction': 'http://schemas.microsoft.com/sharepoint/soap/GetListItems',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        historical_data = []
        try:
            response = requests.post(self.soap_url, data=self._build_soap_payload(indicator_id, limit), headers=headers, timeout=15)
            if response.status_code == 200:
                # Encontramos todas las etiquetas de fila de la respuesta del BCH
                filas = re.findall(r'<z:row[^>]+>', response.text)
                
                for atributos in filas:
                    valor_match = re.search(r'ows_Valor="([^"]+)"', atributos)
                    fecha_match = re.search(r'ows_Fecha="([^"]+)"', atributos)
                    
                    if valor_match and fecha_match:
                        fecha_limpia = fecha_match.group(1).split(' ')[0]
                        historical_data.append({
                            "fecha": fecha_limpia,
                            "tasa": float(valor_match.group(1))
                        })
                
                if historical_data:
                    # Invertimos para que el gráfico vaya de izquierda (antiguo) a derecha (reciente)
                    historical_data.reverse()
                    return historical_data
        except Exception as e:
            print(f"Error BCH Histórico: {e}")
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

extractor = BCHDataExtractor()

@app.get("/api/bch/latest")
def get_latest_data():
    print("Obteniendo datos en vivo...")
    
    # 1. Datos del BCH
    inflacion = extractor.get_indicator(extractor.indicators["inflacion_interanual"])
    tipo_cambio = extractor.get_indicator(extractor.indicators["tipo_cambio_venta"])
    historico_tc = extractor.get_historical_indicator(extractor.indicators["tipo_cambio_venta"], limit=30)
    
    # 2. Datos del Mercado Internacional (Petróleo)
    wti_data = get_wti_live_data()
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "inflacion": {"valor": inflacion["valor"] if inflacion else 0, "fecha": inflacion["fecha"] if inflacion else ""},
            "tipo_cambio": {"venta": tipo_cambio["valor"] if tipo_cambio else 0, "fecha": tipo_cambio["fecha"] if tipo_cambio else ""},
            "historico_tipo_cambio": historico_tc,
            "commodities": {
                "wti": wti_data
            }
        }
    }
