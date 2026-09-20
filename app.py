import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ SEITEN-KONFIGURATION & AUTO-REFRESH
# ==========================================
st.set_page_config(page_title="Steuerzentrale Radar", layout="wide")
st.markdown('<meta http-equiv="refresh" content="300">', unsafe_allow_html=True)

st.title("🚀 Krypto-Steuerzentrale | Live-Radar")

with st.expander("❓ HILFE & ERKLÄRUNG (Hier klicken, um alle Funktionen des Radars zu verstehen)"):
    st.markdown("""
    ### 🧭 System-Handbuch: So liest du das Radar
    Dieses Dashboard filtert Marktrauschen durch nackte Mathematik.

    #### 1. Die Messgeräte
    *   **Aktueller Kurs:** Live-Preis direkt von Kraken.
    *   **RSI (Der Puls):** 
        *   🟢 **45 bis 65:** Gesunde Zone (Perfekt für Einstiege).
        *   🟡 **65 bis 75:** Warnzone (Der Markt wird heiß).
        *   🔴 **Ab 75:** Gefahr! (Überhitzung, Absturz wahrscheinlich).
    *   **SMA 200 (Rote Linie):** Die harte Grenze zwischen Aufwärts- und Abwärtstrend.

    #### 2. Die Radar-Signale
    *   🟢 **NEUTRAL:** Der Markt ist ziellos. Finger weg!
    *   🔥 **KAUF-ZONE:** Kurs über roter Linie, Volumen hoch, RSI kühl. Einstieg prüfen.
    *   ⚠️ **VERKAUF (Überhitzt):** RSI über 75. Gewinnsicherung prüfen.
    *   🩸 **VERKAUF (Trendbruch):** Kurs stürzt unter rote Linie. Reißleine ziehen!

    #### 3. Der Chart
    Das System nutzt 4-Stunden-Blöcke. Der Zeitstempel am unteren Rand zeigt den *Start* des 4-Stunden-Blocks an. Der **Preis** (blaue Linie) ist der Live-Preis dieser Sekunde!
    """)

# ==========================================
# 🏆 RANGLISTE & NAMEN (Das neue Lexikon)
# ==========================================
COIN_NAMEN = {
    "XBTEUR": "Bitcoin (EUR) - Platz 1", 
    "ETHEUR": "Ethereum (EUR) - Platz 2", 
    "SOLEUR": "Solana (EUR) - Platz 5", 
    "ADAEUR": "Cardano (EUR) - Platz 10", 
    "DOTEUR": "Polkadot (EUR) - Platz 15", 
    "LINKEUR": "Chainlink (EUR) - Platz 16",
    "BCHEUR": "Bitcoin Cash (EUR) - Platz 17",
    "LTCEUR": "Litecoin (EUR) - Platz 21",
    "PEPEEUR": "Pepe (EUR) - Platz 24", 
    "SUIEUR": "Sui (EUR) - Platz 28", 
    "FETEUR": "Fetch.ai (EUR) - Platz 33", 
    "XMREUR": "Monero (EUR) - Platz 35",
    "ARBEUR": "Arbitrum (EUR) - Platz 42", 
    
    "XBTUSD": "Bitcoin (USD) - Platz 1", 
    "ETHUSD": "Ethereum (USD) - Platz 2", 
    "SOLUSD": "Solana (USD) - Platz 5"
}

if 'meine_coins' not in st.session_state:
    st.session_state.meine_coins = ["XBTEUR", "ETHEUR", "SOLEUR", "PEPEEUR", "SUIEUR", "FETEUR"]

# ==========================================
# ⚙️ SEITENLEISTE: BEDIENFELDER 
# ==========================================
st.sidebar.header("🎛️ Deine Einstellungen")

# Die sortierte Liste für das Dropdown
alle_kraken_coins = list(COIN_NAMEN.keys())

# Formatierung für das Dropdown, damit die Platzierungen direkt beim Suchen sichtbar sind
def format_coin_label(coin_code):
    return f"{coin_code} ➔ {COIN_NAMEN.get(coin_code, coin_code)}"

auswahl = st.sidebar.multiselect(
    "Währungen suchen (Tippen oder scrollen):", 
    options=alle_kraken_coins, 
    default=st.session_state.meine_coins,
    format_func=format_coin_label
)

neue_liste = [c for c in st.session_state.meine_coins if c in auswahl]
for c in auswahl:
    if c not in neue_liste:
        neue_liste.append(c)
st.session_state.meine_coins = neue_liste

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Order-Rechner")
investition = st.sidebar.number_input("Geplante Kaufsumme", min_value=10, value=500, step=50)
ziel_prozent = st.sidebar.number_input("Ziel-Gewinn Take-Profit (%)", min_value=1, max_value=1000, value=15, step=1)

# ==========================================
# MODUL 1: DATENBESCHAFFUNG
# ==========================================
@st.cache_data(ttl=240)
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
jetzt_string = datetime.now().strftime('%d.%m.%Y - %H:%M:%S')
st.write(f"🔄 **Autopilot aktiv:** Die Seite aktualisiert sich automatisch alle 5 Minuten. (Letzter Scan: {jetzt_string} Uhr)")
st.markdown("---")

for i, coin in enumerate(st.session_state.meine_coins):
    anzeige_name = COIN_NAMEN.get(coin, "Altcoin")
    w_symbol = "€" if "EUR" in coin else "$" if "USD" in coin else ""
    
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
        st.metric(label=f"Live-Kurs auf Kraken", value=f"{preis:.{dezimalstellen}f} {w_symbol}")
        st.metric(label=f"RSI (Puls) {rsi_ampel}", value=f"{rsi:.1f}")
        st.info(f"**{status}**")
        st.caption(f"⚡ Live abgerechnet um: {datetime.now().strftime('%H:%M')} Uhr")
        
    with col2:
        st.markdown(f"**Order-Plan für {investition} {w_symbol}:**")
        coins_gekauft = investition / preis
        limit_3_pct_preis = preis * 0.97
        verlust = investition - (coins_gekauft * limit_3_pct_preis)
        ziel_preis = preis * (1 + (ziel_prozent / 100))
        gewinn = (coins_gekauft * ziel_preis) - investition
        
        st.markdown(f"- 🪙 **Menge:** {coins_gekauft:,.2f} Stück")
        st.markdown(f"- 🛑 **Notbremse (-3%):** Limit bei **{limit_3_pct_preis:.{dezimalstellen}f} {w_symbol}** (Verlust: -{verlust:.2f} {w_symbol})")
        st.markdown(f"- 🎯 **Ziel (+{ziel_prozent}%):** Limit bei **{ziel_preis:.{dezimalstellen}f} {w_symbol}** (Gewinn: +{gewinn:.2f} {w_symbol})")

    with col3:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_live['timestamp'], y=df_live['close'], 
            mode='lines', line=dict(color='#4da6ff', width=2), name='Kurs',
            hovertemplate=f'<b>Kurs:</b> %{{y:.4f}} {w_symbol}<br><b>Block-Start:</b> %{{x|%d.%m. - %H:%M}} Uhr<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=df_live['timestamp'], y=df_live['sma_200'], 
            mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='SMA 200 (Trend)',
            hovertemplate=f'<b>Trend-Grenze:</b> %{{y:.4f}} {w_symbol}<br><b>Block-Start:</b> %{{x|%d.%m. - %H:%M}} Uhr<extra></extra>'
        ))
        
        letzter_zeitpunkt = df_live['timestamp'].iloc[-1]
        zukunft = letzter_zeitpunkt + pd.Timedelta(hours=48)
        start_ansicht = df_live['timestamp'].iloc[-100]
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(range=[start_ansicht, zukunft], tickformat="%d.%m.", tickfont=dict(size=10, color='gray'), showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color='gray'), showgrid=True, gridcolor='#333333'),
            showlegend=False,
            height=200,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.caption("🔴 **Rote Linie: Makro-Trend (SMA 200)** ➔ Fällt der Kurs (Blau) darunter, ist das ein Trendbruch.")

    st.markdown("---")
