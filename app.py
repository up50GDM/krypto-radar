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

# ==========================================
# ❓ ZENTRALES INHALTSVERZEICHNIS & HILFE
# ==========================================
with st.expander("❓ HILFE & ERKLÄRUNG (Hier klicken, um alle Funktionen des Radars zu verstehen)"):
    st.markdown("""
    ### 🧭 System-Handbuch: So liest du das Radar
    Dieses Dashboard ist ein rationales Messinstrument. Es trifft keine Entscheidungen aus dem Bauch heraus, sondern filtert Marktrauschen durch nackte Mathematik.

    #### 1. Die Messgeräte (Was bedeuten die Zahlen?)
    *   **Aktueller Kurs:** Der echte Live-Preis direkt von der Krypto-Börse Kraken.
    *   **RSI (Der Puls des Marktes):** Zeigt als Zahl zwischen 0 und 100, ob ein Markt gesund atmet oder heißläuft.
        *   🟢 **45 bis 65:** Gesunde Zone (Perfekte Vorbereitung für Einstiege).
        *   🟡 **65 bis 75:** Warnzone (Der Markt wird heißer).
        *   🔴 **Ab 75:** Gefahr! (Der Markt wird von Gier getrieben, ein Absturz ist hochwahrscheinlich).
        *   🧊 **Unter 45:** Zu kalt (Panik-Abverkauf läuft).
    *   **SMA 200 (Die rote Linie im Chart):** Der Durchschnittspreis der letzten 200 Zeitabschnitte. Das ist die härteste Grenze des Systems. Sie trennt Aufwärts- von Abwärtstrends.

    #### 2. Die Radar-Signale (Was ist zu tun?)
    *   🟢 **NEUTRAL (Abwarten - Finger weg):** Der Markt ist ziellos. Hände stillhalten schützt dein Kapital.
    *   🔥 **KAUF-ZONE (Einstieg prüfen):** Der Kurs liegt über der roten Linie, das Volumen explodiert und der Puls (RSI) ist kühl. Die Mathematik gibt grünes Licht.
    *   ⚠️ **VERKAUF (Markt überhitzt):** Der Puls ist im roten Bereich (RSI > 75). Zeit, in der Steuerzentrale über eine Gewinnsicherung nachzudenken.
    *   🩸 **VERKAUF (Trendbruch):** Lebensgefahr. Der Kurs ist unter die rote Trend-Linie gestürzt. Die Reißleine muss gezogen werden.

    #### 3. Der Order-Plan (Rechner)
    Das System rechnet dir live aus, wo du deine Absicherungen bei Kraken eintragen musst, basierend auf deiner eingestellten Kaufsumme.
    *   🛑 **Notbremse (-3%):** Dein eiserner Stop-Loss. Fällt der Kurs um 3%, rettet dich dieses Limit vor einem Totalabsturz.
    *   🎯 **Ziel (+X%):** Dein Take-Profit. Der Punkt, an dem du rational und ohne Emotionen deinen Gewinn mitnimmst.

    #### 4. Die Bedienung
    *   **Sortieren:** Klicke einfach auf **⬆️ Hoch** oder **⬇️ Runter** neben einem Währungsnamen, um deine Prioritäten-Liste anzupassen.
    *   **Einblenden/Ausblenden:** Nutze das Auswahlfeld ganz links in der Leiste, um neue Währungen zu aktivieren oder zu entfernen.
    """)

COIN_NAMEN = {
    "XBTEUR": "Bitcoin", "ETHEUR": "Ethereum", "SOLEUR": "Solana", 
    "PEPEEUR": "Pepe", "SUIEUR": "Sui", "FETEUR": "Fetch.ai", "ARBEUR": "Arbitrum"
}

# Gedächtnis für deine Sortierung
if 'meine_coins' not in st.session_state:
    st.session_state.meine_coins = ["XBTEUR", "ETHEUR", "SOLEUR", "PEPEEUR", "SUIEUR", "FETEUR", "ARBEUR"]

# ==========================================
# ⚙️ SEITENLEISTE: BEDIENFELDER
# ==========================================
st.sidebar.header("🎛️ Deine Einstellungen")

alle_kraken_coins = ["XBTEUR", "ETHEUR", "SOLEUR", "PEPEEUR", "SUIEUR", "FETEUR", "ARBEUR", "ADAEUR", "DOGEEUR", "DOTEUR", "LINKEUR"]

auswahl = st.sidebar.multiselect(
    "Währungen an/aus (Sortierung machst du rechts!):", 
    options=alle_kraken_coins, 
    default=st.session_state.meine_coins
)

neue_liste = [c for c in st.session_state.meine_coins if c in auswahl]
for c in auswahl:
    if c not in neue_liste:
        neue_liste.append(c)
st.session_state.meine_coins = neue_liste

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

for i, coin in enumerate(st.session_state.meine_coins):
    anzeige_name = COIN_NAMEN.get(coin, "Altcoin")
    
    col_t1, col_t2, col_t3 = st.columns([6, 1, 1])
    with col_t1:
        st.markdown(f"### {coin} ({anzeige_name})")
    with col_t2:
        if i > 0:
            if st.button("⬆️ Hoch", key=f"up_{coin}"):
                st.session_state.meine_coins[i], st.session_state.meine_coins[i-1] = st.session_state.meine_coins[i-1], st.session_state.meine_coins[i]
                st.rerun()
    with col_t3:
        if i < len(st.session_state.meine_coins) - 1:
            if st.button("⬇️ Runter", key=f"down_{coin}"):
                st.session_state.meine_coins[i], st.session_state.meine_coins[i+1] = st.session_state.meine_coins[i+1], st.session_state.meine_coins[i]
                st.rerun()
    
    df_live = fetch_kraken_ohlcv(coin, interval=240)
    
    if df_live is None:
        st.error(f"⚠️ Fehler: Keine Daten für {coin}.")
        st.markdown("---")
        continue

    aktuelle_kerze = df_live.iloc[-1]
    preis = aktuelle_kerze['close']
    rsi = aktuelle_kerze['rsi']
    sma = aktuelle_kerze['sma_200']
    vol = aktuelle_kerze['volume_ratio']

    status = "🟢 NEUTRAL (Abwarten - Finger weg)"
    if preis > sma and (45 <= rsi <= 65) and vol >= 2.0: status = "🔥 KAUF-ZONE (Einstieg prüfen)"
    elif rsi >= 75: status = "⚠️ VERKAUF (Markt überhitzt)"
    elif preis < sma: status = "🩸 VERKAUF (Trendbruch unter rote Linie)"

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
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_live['timestamp'], y=df_live['close'], 
            mode='lines', line=dict(color='#4da6ff', width=2), name='Kurs',
            hovertemplate='<b>Kurs:</b> %{y:.4f} €<br><b>Zeit:</b> %{x|%d.%m.%Y - %H:%M} Uhr<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=df_live['timestamp'], y=df_live['sma_200'], 
            mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='SMA 200 (Trend)',
            hovertemplate='<b>Trend-Grenze:</b> %{y:.4f} €<br><b>Zeit:</b> %{x|%d.%m.%Y - %H:%M} Uhr<extra></extra>'
        ))
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickformat="%d.%m.", tickfont=dict(size=10, color='gray'), showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color='gray'), showgrid=True, gridcolor='#333333'),
            showlegend=False,
            height=200,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.caption("🔴 **Rote Linie: Makro-Trend (SMA 200)** ➔ Fällt der Kurs (Blau) darunter, ist das ein Trendbruch.")

    st.markdown("---")
