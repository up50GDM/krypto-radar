import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from zoneinfo import ZoneInfo
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ SEITEN-KONFIGURATION & AUTO-REFRESH
# ==========================================
st.set_page_config(page_title="Steuerzentrale Radar", layout="wide")
st.markdown('<meta http-equiv="refresh" content="300">', unsafe_allow_html=True)

# ==========================================
# 🎛️ EINSTELLUNGEN (Globale Parameter)
# ==========================================
st.sidebar.header("⚙️ System-Einstellungen")

zeitzonen_liste = ["Europe/Berlin (MEZ)", "Europe/London (GMT)", "America/New_York (EST)", "Asia/Tokyo (JST)", "UTC"]
gewaehlte_zeitzone_str = st.sidebar.selectbox("🌍 Lokale Zeitzone:", zeitzonen_liste)
aktuelle_zeitzone = ZoneInfo(gewaehlte_zeitzone_str.split(" ")[0])

st.sidebar.selectbox("🏛️ Krypto-Börse (API):", ["Kraken", "Binance (In Vorbereitung)", "Coinbase (In Vorbereitung)"])

# Der funktionale Währungs-Schalter
basis_waehrung = st.sidebar.radio("💵 Bevorzugte Basis-Währung:", ["EUR", "USD"], horizontal=True)

st.sidebar.markdown("---")
st.sidebar.header("🎛️ Deine Watchlist")

st.title("🚀 Krypto-Steuerzentrale | Live-Radar")

with st.expander("❓ HILFE & ERKLÄRUNG (Hier klicken, um alle Funktionen des Radars zu verstehen)"):
    st.markdown("""
    ### 🧭 System-Handbuch: So liest du das Radar
    Dieses Dashboard filtert Marktrauschen durch nackte Mathematik.

    #### 1. Die Messgeräte
    *   **Aktueller Kurs:** Live-Preis direkt von der Börse.
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
    """)

# Basis-Lexikon (Wir speichern nur die Kürzel ohne Endung)
COIN_BASIS = {
    "XBT": "Bitcoin - Platz 1", 
    "ETH": "Ethereum - Platz 2", 
    "SOL": "Solana - Platz 5", 
    "ADA": "Cardano - Platz 10", 
    "DOT": "Polkadot - Platz 15", 
    "LINK": "Chainlink - Platz 16",
    "BCH": "Bitcoin Cash - Platz 17",
    "LTC": "Litecoin - Platz 21",
    "PEPE": "Pepe - Platz 24", 
    "SUI": "Sui - Platz 28", 
    "FET": "Fetch.ai - Platz 33", 
    "XMR": "Monero - Platz 35",
    "ARB": "Arbitrum - Platz 42"
}

if 'meine_basis_coins' not in st.session_state:
    st.session_state.meine_basis_coins = ["XBT", "ETH", "SOL", "PEPE", "SUI", "FET"]

alle_basis_coins = list(COIN_BASIS.keys())

def format_basis_label(basis_code):
    return f"{basis_code} ➔ {COIN_BASIS.get(basis_code, basis_code)}"

auswahl = st.sidebar.multiselect(
    "Währungen suchen (Tippen/Scrollen):", 
    options=alle_basis_coins, 
    default=st.session_state.meine_basis_coins,
    format_func=format_basis_label
)

neue_liste = [c for c in st.session_state.meine_basis_coins if c in auswahl]
for c in auswahl:
    if c not in neue_liste: neue_liste.append(c)
st.session_state.meine_basis_coins = neue_liste

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
        
        abruf_zeit = datetime.now(aktuelle_zeitzone).strftime('%H:%M:%S')
        return df, abruf_zeit
    except:
        return None

# ==========================================
# MODUL 2: DASHBOARD AUFBAU (Das Cockpit)
# ==========================================
jetzt_string = datetime.now(aktuelle_zeitzone).strftime('%d.%m.%Y - %H:%M:%S')
st.write(f"🔄 **Autopilot aktiv:** (Gesamtsystem zuletzt aktualisiert: {jetzt_string})")
st.markdown("---")

w_symbol = "€" if basis_waehrung == "EUR" else "$"

for i, basis_coin in enumerate(st.session_state.meine_basis_coins):
    anzeige_name = COIN_BASIS.get(basis_coin, "Altcoin")
    
    # Der entscheidende Moment: Hier wird die Währung (EUR/USD) dynamisch drangeklebt
    voller_coin_name = f"{basis_coin}{basis_waehrung}"
    
    daten_paket = fetch_kraken_ohlcv(voller_coin_name, interval=240)
    
    if daten_paket is None:
        st.error(f"⚠️ Fehler: Keine Daten auf Kraken für {voller_coin_name} gefunden.")
        st.markdown("---")
        continue

    df_live, ping_zeit = daten_paket
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

    col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns([3.5, 2, 2, 0.5, 0.5])
    
    with col_k1:
        st.markdown(f"### {voller_coin_name}\n**{anzeige_name}**<br><span style='font-size:14px; color:#888888;'>Ping: {ping_zeit}</span>", unsafe_allow_html=True)
    with col_k2:
        st.metric(label="Live-Kurs (Börse)", value=f"{preis:.{dezimalstellen}f} {w_symbol}")
    with col_k3:
        st.metric(label=f"RSI (Puls)", value=f"{rsi:.1f} {rsi_ampel}")
    with col_k4:
        st.markdown("<br>", unsafe_allow_html=True) 
        if i > 0:
            if st.button("⬆️", key=f"up_{basis_coin}"):
                st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i-1] = st.session_state.meine_basis_coins[i-1], st.session_state.meine_basis_coins[i]
                st.rerun()
    with col_k5:
        st.markdown("<br>", unsafe_allow_html=True)
        if i < len(st.session_state.meine_basis_coins) - 1:
            if st.button("⬇️", key=f"down_{basis_coin}"):
                st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i+1] = st.session_state.meine_basis_coins[i+1], st.session_state.meine_basis_coins[i]
                st.rerun()

    with st.expander(f"📊 Order-Plan & Chart für {voller_coin_name} öffnen"):
        col_d1, col_d2 = st.columns([1, 1.5])
        
        with col_d1:
            st.info(f"**Signal: {status}**")
            st.markdown(f"**Order-Plan für {investition} {w_symbol}:**")
            coins_gekauft = investition / preis
            limit_3_pct_preis = preis * 0.97
            verlust = investition - (coins_gekauft * limit_3_pct_preis)
            ziel_preis = preis * (1 + (ziel_prozent / 100))
            gewinn = (coins_gekauft * ziel_preis) - investition
            
            st.markdown(f"- 🪙 **Menge:** {coins_gekauft:,.2f} Stück")
            st.markdown(f"- 🛑 **Stop (-3%):** Limit bei **{limit_3_pct_preis:.{dezimalstellen}f} {w_symbol}** (-{verlust:.2f} {w_symbol})")
            st.markdown(f"- 🎯 **Ziel (+{ziel_prozent}%):** Limit bei **{ziel_preis:.{dezimalstellen}f} {w_symbol}** (+{gewinn:.2f} {w_symbol})")

        with col_d2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_live['timestamp'], y=df_live['close'], 
                mode='lines', line=dict(color='#4da6ff', width=2), name='Kurs',
                hovertemplate=f'<b>Kurs:</b> %{{y:.4f}} {w_symbol}<br><b>Block-Start:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'
            ))
            fig.add_trace(go.Scatter(
                x=df_live['timestamp'], y=df_live['sma_200'], 
                mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='SMA 200 (Trend)',
                hovertemplate=f'<b>Trend-Grenze:</b> %{{y:.4f}} {w_symbol}<br><b>Block-Start:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'
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
            st.caption("🔴 **Rote Linie: Makro-Trend (SMA 200)** ➔ Fällt der Kurs darunter, droht ein Trendbruch.")

    st.markdown("---")
