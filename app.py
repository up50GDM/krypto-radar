import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# ⚙️ SEITEN-KONFIGURATION
# ==========================================
st.set_page_config(page_title="Steuerzentrale Radar", layout="wide")
st.title("🚀 Krypto-Steuerzentrale | Live-Radar")

COIN_NAMEN = {
    "XBTEUR": "Bitcoin", "ETHEUR": "Ethereum", "SOLEUR": "Solana", 
    "PEPEEUR": "Pepe", "SUIEUR": "Sui", "FETEUR": "Fetch.ai", "ARBEUR": "Arbitrum"
}

# ==========================================
# ⚙️ SEITENLEISTE: BEDIENFELDER (Mit Worterkennung)
# ==========================================
st.sidebar.header("🎛️ Deine Einstellungen")

# Die Worterkennung (Dropdown)
alle_kraken_coins = ["XBTEUR", "ETHEUR", "SOLEUR", "PEPEEUR", "SUIEUR", "FETEUR", "ARBEUR", "ADAEUR", "DOGEEUR", "DOTEUR", "LINKEUR"]
gewaehlte_coins = st.sidebar.multiselect(
    "Währungen suchen / auswählen:", 
    options=alle_kraken_coins, 
    default=["XBTEUR", "ETHEUR", "SOLEUR", "PEPEEUR"] # Diese bleiben für immer gespeichert
)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Order-Rechner")
investition = st.sidebar.slider("Geplante Kaufsumme (€)", min_value=50, max_value=5000, value=500, step=50)
ziel_prozent = st.sidebar.slider("Ziel-Gewinn Take-Profit (%)", min_value=1, max_value=100, value=15, step=1)

# ==========================================
# MODUL 1: DATENBESCHAFFUNG
# ==========================================
@st.cache_data(ttl=300)
def fetch_kraken_ohlcv(pair: str, interval: int = 240):
    url = "https://api.kraken.com/0/public/OHLC"
    try:
        response = requests.get(url, params={'pair': pair, 'interval': interval}).json()
        if len(response.get('error', [])) > 0: return None
        result_key = list(response['result'].keys())[0]
        df = pd.DataFrame(response['result'][result_key], columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        delta = df['close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
        df['rsi'] = 100 - (100 / (1 + gain / loss))
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        return df
    except:
        return None

# ==========================================
# MODUL 2: DASHBOARD AUFBAU
# ==========================================
st.write(f"Letztes Update: {datetime.now().strftime('%d.%m.%Y - %H:%M:%S')} (Daten laden alle 5 Min. neu)")
st.markdown("---")

for coin in gewaehlte_coins:
    anzeige_name = COIN_NAMEN.get(coin, "Altcoin")
    st.markdown(f"### {coin} ({anzeige_name})")
    
    df_live = fetch_kraken_ohlcv(coin, interval=240)
    
    if df_live is None:
        st.error(f"⚠️ Fehler: Keine Daten für {coin}.")
        continue

    aktuelle_kerze = df_live.iloc[-1]
    preis = aktuelle_kerze['close']
    rsi = aktuelle_kerze['rsi']
    sma = aktuelle_kerze['sma_200']
    vol = aktuelle_kerze['volume_ratio']

    # Signal-Logik
    status = "🟢 NEUTRAL (Abwarten)"
    if preis > sma and (45 <= rsi <= 65) and vol >= 2.0: status = "🔥 KAUF-ZONE"
    elif rsi >= 75: status = "⚠️ VERKAUF (Überhitzt)"
    elif preis < sma: status = "🩸 VERKAUF (Trendbruch)"

    # Die neue RSI-Ampel
    if rsi >= 75: rsi_ampel = "🔴"
    elif rsi >= 65: rsi_ampel = "🟡"
    elif rsi >= 45: rsi_ampel = "🟢"
    else: rsi_ampel = "🧊"

    dezimalstellen = 8 if preis < 0.01 else 4
    
    col1, col2, col3 = st.columns([1, 1.5, 2])
    
    with col1:
        st.metric(label="Aktueller Kurs", value=f"{preis:.{dezimalstellen}f} €")
        st.metric(label=f"RSI (Puls) {rsi_ampel}", value=f"{rsi:.1f}")
        st.info(f"**{status}**")
        
    with col2:
        st.markdown(f"**Order-Plan für {investition} €:**")
        coins_gekauft = investition / preis
        limit_3_pct_preis = preis * 0.97
        verlust_euro = investition - (coins_gekauft * limit_3_pct_preis)
        ziel_preis = preis * (1 + (ziel_prozent / 100))
        gewinn_euro = (coins_gekauft * ziel_preis) - investition
        
        st.markdown(f"- 🪙 **Menge:** {coins_gekauft:,.2f} Stück")
        st.markdown(f"- 🛑 **Notbremse (-3%):** Limit bei **{limit_3_pct_preis:.{dezimalstellen}f} €** (Verlust: -{verlust_euro:.2f} €)")
        st.markdown(f"- 🎯 **Ziel (+{ziel_prozent}%):** Limit bei **{ziel_preis:.{dezimalstellen}f} €** (Gewinn: +{gewinn_euro:.2f} €)")

    with col3:
        # Interaktiver Plotly-Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['close'], mode='lines', line=dict(color='#4da6ff', width=2), name='Kurs'))
        fig.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['sma_200'], mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='SMA 200'))
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickformat="%d.%m.\n%H:%M", tickfont=dict(size=10, color='gray'), showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color='gray'), showgrid=True, gridcolor='#333333'),
            showlegend=False,
            height=250,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
