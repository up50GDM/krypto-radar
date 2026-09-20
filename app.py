import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ SEITEN-KONFIGURATION
# ==========================================
st.set_page_config(page_title="Steuerzentrale Radar", layout="wide")
st.title("🚀 Krypto-Steuerzentrale | Live-Radar")

# KLARE NAMEN ZUORDNEN
COIN_NAMEN = {
    "XBTEUR": "Bitcoin",
    "ETHEUR": "Ethereum",
    "SOLEUR": "Solana",
    "PEPEEUR": "Pepe",
    "SUIEUR": "Sui",
    "FETEUR": "Fetch.ai",
    "ARBEUR": "Arbitrum"
}

# HANDBUCH / REGELWERK (Aufklappbar, um Platz zu sparen)
with st.expander("📖 Handbuch & Strategie (Hier aufklappen für Erklärungen)"):
    st.markdown("""
    **1. Die Zonen-Logik:**
    * 🟢 **NEUTRAL:** Kein mathematischer Vorteil. Hände stillhalten.
    * 🔥 **KAUF-ZONE:** Makro-Trend intakt (Kurs über SMA 200), RSI abgekühlt (45-65), starkes Volumen.
    * ⚠️ **VERKAUF (Überhitzt):** RSI klettert über 75. Der Markt ist gierig, ein Rücksetzer ist hochwahrscheinlich. Gewinnsicherung planen.
    * 🩸 **VERKAUF (Trendbruch):** Kurs stürzt unter SMA 200. Der Makro-Trend ist gebrochen.

    **2. Die Indikatoren:**
    * **SMA 200:** Der Trend-Wächter (rote gestrichelte Linie im Chart). Zieht die harte Grenze zwischen Bullen- und Bärenmarkt.
    * **RSI:** Der Puls des Marktes. Reagiert viel schneller als der Preis und warnt vor Überhitzung.
    """)

# Speicher für deine Währungen
if 'meine_coins' not in st.session_state:
    st.session_state.meine_coins = ["XBTEUR", "ETHEUR", "SOLEUR"]

# ==========================================
# ⚙️ SEITENLEISTE: BEDIENFELDER
# ==========================================
st.sidebar.header("🎛️ Deine Einstellungen")

neuer_coin = st.sidebar.text_input("Neuen Coin hinzufügen (z.B. PEPEEUR):").upper()
if st.sidebar.button("➕ Hinzufügen"):
    if neuer_coin and neuer_coin not in st.session_state.meine_coins:
        st.session_state.meine_coins.append(neuer_coin)
        st.rerun()

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
        if len(response.get('error', [])) > 0:
            return None
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

for coin in st.session_state.meine_coins:
    anzeige_name = COIN_NAMEN.get(coin, "Altcoin")
    st.markdown(f"### {coin} ({anzeige_name})")
    
    df_live = fetch_kraken_ohlcv(coin, interval=240)
    
    if df_live is None:
        st.error(f"⚠️ Fehler: {coin} auf Kraken nicht gefunden. Hast du 'EUR' am Ende vergessen?")
        if st.button(f"🗑️ {coin} löschen", key=f"err_{coin}"):
            st.session_state.meine_coins.remove(coin)
            st.rerun()
        continue

    aktuelle_kerze = df_live.iloc[-1]
    preis = aktuelle_kerze['close']
    rsi = aktuelle_kerze['rsi']
    sma = aktuelle_kerze['sma_200']
    vol = aktuelle_kerze['volume_ratio']

    status = "🟢 NEUTRAL (Abwarten)"
    if preis > sma and (45 <= rsi <= 65) and vol >= 2.0:
        status = "🔥 KAUF-ZONE"
    elif rsi >= 75:
        status = "⚠️ VERKAUF (Überhitzt)"
    elif preis < sma:
        status = "🩸 VERKAUF (Trendbruch)"

    # Komma-Logik für extrem billige Coins (PEPE)
    dezimalstellen = 8 if preis < 0.01 else 4
    
    col1, col2, col3 = st.columns([1, 1.5, 2])
    
    with col1:
        st.metric(label="Aktueller Kurs", value=f"{preis:.{dezimalstellen}f} €")
        st.metric(label="RSI (Puls)", value=f"{rsi:.1f}")
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
        if st.button(f"🗑️ {coin} ausblenden", key=f"del_{coin}"):
            st.session_state.meine_coins.remove(coin)
            st.rerun()

    with col3:
        # Chart einbauen, farblich an Dark Mode angepasst
        fig, ax = plt.subplots(figsize=(6, 2.5))
        fig.patch.set_facecolor('#0e1117') 
        ax.set_facecolor('#0e1117')
        
        ax.plot(df_live['timestamp'], df_live['close'], color='#4da6ff', linewidth=1.5, label='Kurs')
        ax.plot(df_live['timestamp'], df_live['sma_200'], color='#ff4d4d', linestyle='--', linewidth=1.5, label='SMA 200 (Trend)')
        
        ax.tick_params(axis='x', colors='white', labelsize=8)
        ax.tick_params(axis='y', colors='white', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#555555')
        ax.grid(True, alpha=0.1)
        ax.legend(loc='upper left', fontsize=8, facecolor='#0e1117', edgecolor='none', labelcolor='white')
        
        st.pyplot(fig)

    st.markdown("---")
