import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ==========================================
# ⚙️ SEITEN-KONFIGURATION
# ==========================================
st.set_page_config(page_title="Steuerzentrale Radar", layout="wide")
st.title("🚀 Krypto-Steuerzentrale | Live-Radar")

# Speicher für deine Währungen (damit sie beim Neuladen bleiben)
if 'meine_coins' not in st.session_state:
    st.session_state.meine_coins = ["ETHEUR", "XBTEUR", "SOLEUR"]

# ==========================================
# ⚙️ SEITENLEISTE: BEDIENFELDER (Deine Schieberegler)
# ==========================================
st.sidebar.header("🎛️ Deine Einstellungen")

# 1. Neue Währungen hinzufügen
neuer_coin = st.sidebar.text_input("Neuen Coin hinzufügen (z.B. PEPEEUR):").upper()
if st.sidebar.button("➕ Hinzufügen"):
    if neuer_coin and neuer_coin not in st.session_state.meine_coins:
        st.session_state.meine_coins.append(neuer_coin)
        st.rerun()

# 2. Investitions-Regler
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Order-Rechner")
investition = st.sidebar.slider("Geplante Kaufsumme (€)", min_value=50, max_value=5000, value=500, step=50)
ziel_prozent = st.sidebar.slider("Ziel-Gewinn Take-Profit (%)", min_value=1, max_value=100, value=15, step=1)

# ==========================================
# MODUL 1: DATEN & INDIKATOREN (Mit Zwischenspeicher)
# ==========================================
@st.cache_data(ttl=300) # Aktualisiert die Daten maximal alle 5 Minuten (schont Kraken API)
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
        
        # Indikatoren
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
st.write(f"Letztes Update: {datetime.now().strftime('%d.%m.%Y - %H:%M:%S')} (Daten werden alle 5 Min. aktualisiert)")

for coin in st.session_state.meine_coins:
    st.markdown(f"### {coin}")
    df_live = fetch_kraken_ohlcv(coin, interval=240)
    
    if df_live is None:
        st.error(f"Fehler beim Laden von {coin}. Bitte Kürzel prüfen.")
        if st.button(f"🗑️ {coin} entfernen", key=f"del_{coin}"):
            st.session_state.meine_coins.remove(coin)
            st.rerun()
        continue

    aktuelle_kerze = df_live.iloc[-1]
    preis = aktuelle_kerze['close']
    rsi = aktuelle_kerze['rsi']
    sma = aktuelle_kerze['sma_200']
    vol = aktuelle_kerze['volume_ratio']

    # Zonen-Logik
    status = "🟢 NEUTRAL (Abwarten)"
    status_color = "normal"
    if preis > sma and (45 <= rsi <= 65) and vol >= 2.0:
        status = "🔥 KAUF-ZONE"
        status_color = "inverse"
    elif rsi >= 75:
        status = "⚠️ VERKAUF (Überhitzt)"
        status_color = "off"
    elif preis < sma:
        status = "🩸 VERKAUF (Trendbruch)"
        status_color = "off"

    # Layout mit Spalten für Übersichtlichkeit
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.metric(label="Aktueller Kurs", value=f"{preis:.4f} €")
        st.metric(label="RSI (Puls)", value=f"{rsi:.1f}")
        
    with col2:
        st.metric(label="SMA 200 (Trend)", value=f"{sma:.4f} €")
        st.info(f"Signal: **{status}**")
        
    with col3:
        # Der Risk-Reward Rechner
        coins_gekauft = investition / preis
        limit_3_pct_preis = preis * 0.97
        verlust_euro = investition - (coins_gekauft * limit_3_pct_preis)
        
        ziel_preis = preis * (1 + (ziel_prozent / 100))
        gewinn_euro = (coins_gekauft * ziel_preis) - investition
        
        st.markdown(f"**Dein Order-Plan für {investition} €:**")
        st.markdown(f"- **Menge:** Du erhältst ca. {coins_gekauft:.4f} {coin.replace('EUR', '')}")
        st.markdown(f"- 🛑 **Notbremse (-3%):** Order bei **{limit_3_pct_preis:.4f} €** (Max. Verlust: -{verlust_euro:.2f} €)")
        st.markdown(f"- 🎯 **Ziel (+{ziel_prozent}%):** Order bei **{ziel_preis:.4f} €** (Gewinn: +{gewinn_euro:.2f} €)")
        if st.button(f"🗑️ {coin} löschen", key=f"del_{coin}"):
            st.session_state.meine_coins.remove(coin)
            st.rerun()

    st.markdown("---")
