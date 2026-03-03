from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import yfinance as yf

app = FastAPI(title="API EcoDash Honduras")

# Permitir conexión desde tu página web
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
        """Obtiene solo el último dato."""
        headers = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': 'http://schemas.microsoft.com/sharepoint/soap/GetListItems'}
        try:
            response = requests.post(self.soap_url, data=self._build_soap_payload(indicator_id, limit=1), headers=headers, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                row = root.find('.//z:row', {'z': '#RowsetSchema'})
                if row is not None:
                    fecha_limpia = row.get('ows_Fecha').split(' ')[0]
                    return {"fecha": fecha_limpia, "valor": float(row.get('ows_Valor'))}
        except Exception as e:
            print(f"Error BCH: {e}")
        return None

    def get_historical_indicator(self, indicator_id, limit=30):
        """Obtiene un historial de datos y los ordena para el gráfico."""
        headers = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': 'http://schemas.microsoft.com/sharepoint/soap/GetListItems'}
        historical_data = []
        try:
            response = requests.post(self.soap_url, data=self._build_soap_payload(indicator_id, limit), headers=headers, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                rows = root.findall('.//z:row', {'z': '#RowsetSchema'})
                
                for row in rows:
                    fecha_raw = row.get('ows_Fecha').split(' ')[0]
                    historical_data.append({
                        "fecha": fecha_raw,
                        "tasa": float(row.get('ows_Valor'))
                    })
                
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
