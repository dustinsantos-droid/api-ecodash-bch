<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoDash | Inteligencia Económica</title>
    
    <!-- Tailwind CSS para los estilos -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- React y ReactDOM -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    
    <!-- Dependencia requerida por Recharts -->
    <script src="https://unpkg.com/prop-types@15.8.1/prop-types.min.js"></script>
    
    <!-- Babel para compilar React en el navegador -->
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    
    <!-- Recharts para el gráfico -->
    <script src="https://unpkg.com/recharts@2.1.12/umd/Recharts.js"></script>
</head>
<body class="bg-slate-50">
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect } = React;
        const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } = window.Recharts;

        // --- DATOS SIMULADOS (FALLBACK DEL HISTÓRICO) ---
        const generateHistoricalData = () => {
            const data = [];
            const today = new Date();
            let baseRate = 24.65; 
            for (let i = 30; i >= 0; i--) {
                const date = new Date(today);
                date.setDate(date.getDate() - i);
                baseRate = baseRate + (Math.random() * 0.04 - 0.02);
                data.push({
                    fecha: date.toLocaleDateString('es-HN', { day: '2-digit', month: 'short' }),
                    tasa: parseFloat(baseRate.toFixed(4))
                });
            }
            return data;
        };

        const fiscalNews = [
            { id: 1, title: "Inflación en Honduras asciende a 2.01% en el primer trimestre", category: "BCH", time: "Reciente", icon: "📈", url: "https://www.elheraldo.hn/economia/inflacion-honduras-asciende-2-01-primer-trimestre-2025-BP25199392" },
            { id: 2, title: "FMI da luz verde: La economía hondureña se mantiene resiliente", category: "Macro", time: "Reciente", icon: "🏛️", url: "https://ediciones.elheraldo.hn/media/pdfs/EH2025-06-12-lxZWigDa2KaK.pdf" },
            { id: 3, title: "Honduras registró la tasa de inflación más alta en Centroamérica (4.98%)", category: "Estadística", time: "Histórico", icon: "📊", url: "https://www.elheraldo.hn/economia/honduras-registro-2025-tasa-inflacion-mas-alta-centroamerica-AH28949999" },
        ];

        const externalNews = [
            { id: 1, title: "El quintal de café cierra en cifra récord de $425 en la Bolsa de NY", category: "Commodities", time: "Reciente", icon: "☕", url: "https://www.laprensa.hn/economia/quintal-cafe-precio-honduras-bolsa-nueva-york-JD24270876" },
            { id: 2, title: "Exportaciones de café hondureño aumentan 87% superando los $1.600 millones", category: "Balanza Comercial", time: "Reciente", icon: "🚢", url: "https://www.laprensa.hn/honduras/honduras-exportaciones-cafe-aumentan-cifras-NF26018306" },
            { id: 3, title: "Cotización en vivo: Futuros del Petróleo Crudo WTI", category: "Energía", time: "En vivo", icon: "⚡", url: "https://es.investing.com/commodities/crude-oil" },
        ];

        const maNews = [
            { id: 1, title: "La FTC abre investigación de gran alcance sobre monopolio de Microsoft", category: "Antitrust", time: "Reciente", icon: "⚖️", url: "https://www.xataka.com/empresas-y-economia/ftc-ha-abierto-investigacion-gran-alcance-microsoft-bloomberg-vuelve-fantasma-monopolio" },
            { id: 2, title: "Meta gana juicio antimonopolio y evitará vender WhatsApp e Instagram", category: "Tech M&A", time: "Reciente", icon: "💼", url: "https://www.eleconomista.es/tecnologia/noticias/13650683/11/25/meta-gana-en-estados-unidos-un-juicio-antimonopolio-que-evitara-que-tenga-que-vender-whatsapp-e-instagram.html" },
            { id: 3, title: "La FTC presenta una demanda sin precedentes contra Amazon por logística", category: "Regulación", time: "Reciente", icon: "🏢", url: "https://www.xataka.com/empresas-y-economia/amazon-se-enfrenta-a-enorme-acusacion-monopolio-eeuu-ftc-17-fiscales-generales-acaban-demandarle" },
        ];

        // --- COMPONENTE DE TARJETAS METRICAS CLICABLES ---
        const MetricCard = ({ title, value, change, isPositive, icon, suffix = "", prefix = "", subtitle = "", isAlert = false, url = null }) => {
            const baseBg = isAlert ? "bg-rose-50 border-rose-200" : "bg-white border-slate-200";
            const iconBg = isAlert ? "bg-rose-100 text-rose-700" : "bg-slate-50 text-slate-700";
            const titleColor = isAlert ? "text-rose-700" : "text-slate-500";
            const valueColor = isAlert ? "text-rose-800" : "text-slate-900";
            const subtitleColor = isAlert ? "text-rose-600 font-semibold" : "text-slate-400";
            const trendColor = isAlert ? (isPositive ? 'text-rose-600' : 'text-rose-800') : (isPositive ? 'text-emerald-600' : 'text-rose-600');
            const trendIcon = isPositive ? '↗️' : '↘️';

            const CardContent = (
                <div className={`p-6 rounded-2xl border shadow-sm transition-all duration-300 h-full ${baseBg} ${url ? 'hover:shadow-md hover:-translate-y-1 hover:border-blue-300 cursor-pointer' : ''}`}>
                    <div className="flex justify-between items-start mb-4">
                        <div className={`p-3 rounded-xl text-xl ${iconBg}`}>
                            {icon}
                        </div>
                        <div className={`flex items-center space-x-1 text-sm font-bold ${trendColor}`}>
                            <span>{trendIcon}</span>
                            <span>{Math.abs(change)}%</span>
                        </div>
                    </div>
                    <div>
                        <h3 className={`text-sm font-semibold mb-1 flex items-center ${titleColor}`}>
                            {title}
                            {isAlert && <span className="ml-1.5">⚠️</span>}
                        </h3>
                        <div className={`text-3xl font-bold tracking-tight ${valueColor}`}>
                            {prefix}{value}{suffix}
                        </div>
                        {subtitle && <p className={`text-xs mt-1 ${subtitleColor}`}>{subtitle}</p>}
                    </div>
                </div>
            );

            if (url) {
                return <a href={url} target="_blank" rel="noopener noreferrer" className="block no-underline h-full">{CardContent}</a>;
            }
            return CardContent;
        };

        const NewsMonitor = ({ title, icon, items }) => (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col h-full">
                <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
                    <span className="mr-2 text-xl">{icon}</span>
                    {title}
                </h3>
                <div className="flex-1 overflow-y-auto pr-2 space-y-5">
                    {items.map((news) => (
                        <a key={news.id} href={news.url} target="_blank" rel="noopener noreferrer" className="group cursor-pointer block no-underline">
                            <div className="flex items-start space-x-3">
                                <div className="mt-1 p-2 bg-slate-50 rounded-lg border border-slate-100 text-lg group-hover:bg-blue-50 transition-colors">
                                    {news.icon}
                                </div>
                                <div>
                                    <div className="flex items-center space-x-2 mb-1">
                                        <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
                                            {news.category}
                                        </span>
                                        <span className="text-xs font-medium text-slate-400">&bull; {news.time}</span>
                                    </div>
                                    <p className="text-sm font-semibold text-slate-700 group-hover:text-blue-700 transition-colors leading-snug">
                                        {news.title}
                                    </p>
                                </div>
                            </div>
                        </a>
                    ))}
                </div>
            </div>
        );

        const App = () => {
            const [rates, setRates] = useState({ HNL: 26.30 });
            const [inflationData, setInflationData] = useState({ price: 4.23, change: -0.15 });
            const [loading, setLoading] = useState(true);
            const [lastUpdate, setLastUpdate] = useState('');
            const [chartData, setChartData] = useState([]);
            
            const [wtiData, setWtiData] = useState({ price: 0, high: 0, low: 0, change: 0 });

            const commodities = {
                coffee: { price: 1.75, change: -1.2 },
                embi: { price: 345, change: 5.2 }
            };

            const sefinData = {
                ejecucionGasto: { value: 14.2, change: 1.5 },
                inversionProductiva: { value: 8.5, change: 0.8 },
