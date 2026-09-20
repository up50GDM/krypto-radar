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
st.set_page_config(page_title="steuerzentrale radar", layout="wide")
st.markdown('<meta http-equiv="refresh" content="300">', unsafe_allow_html=True)

# ==========================================
# 🎛️ EINSTELLUNGEN (Globale Parameter)
# ==========================================
st.sidebar.header("⚙️ system-einstellungen")

# 1. Börsen-Auswahl
st.sidebar.selectbox("🏛️ krypto-börse (api):", ["kraken", "binance (in vorbereitung)", "coinbase (in vorbereitung)"])
st.sidebar.caption("⚠️ kann nur geändert werden, wenn die api-schnittstelle aktiv ist.")

st.sidebar.markdown("---")

# 2. Lokale Zeitzone (Mit exakten Programmier-Namen, damit kein Fehler mehr auftritt)
zeitzonen_optionen = {
    "deutschland (berlin / mez)": "Europe/Berlin",
    "england (london / gmt)": "Europe/London",
    "schweiz (zürich / cet)": "Europe/Zurich",
    "usa (new york / est)": "America/New_York",
    "japan (tokyo / jst)": "Asia/Tokyo",
    "weltzeit (utc)": "UTC"
}
gewaehlte_tz_label = st.sidebar.selectbox("🌍 lokale zeitzone:", list(zeitzonen_optionen.keys()))
aktuelle_zeitzone = ZoneInfo(zeitzonen_optionen[gewaehlte_tz_label])

# 3. Fiat-Währung
FIAT_SYMBOLE = {
    "EUR": "€", "USD": "$", "GBP": "£", "CHF": "chf", "CAD": "ca$", "AUD": "au$", "JPY": "¥"
}
basis_waehrung = st.sidebar.selectbox("💵 bevorzugte fiat-währung:", list(FIAT_SYMBOLE.keys()))

st.sidebar.markdown("---")
st.sidebar.header("🎛️ deine watchlist")

st.title("🚀 krypto-steuerzentrale | live-radar")

with st.expander("❓ hilfe & erklärung (hier klicken, um alle funktionen zu verstehen)"):
    st.markdown("""
    ### 🧭 system-handbuch: so liest du das radar
    dieses dashboard filtert marktrauschen durch nackte mathematik.

    #### 1. die messgeräte
    *   **aktueller kurs:** live-preis direkt von der börse.
    *   **rsi (der puls):** 
        *   🟢 **45 bis 65:** gesunde zone (perfekt für einkäufe).
        *   🟡 **65 bis 75:** warnzone (der markt wird heiß).
        *   🔴 **ab 75:** gefahr! (überhitzung, absturz wahrscheinlich).
    *   **sma 200 (rote linie):** die harte grenze zwischen aufwärts- und abwärtstrend.

    #### 2. die radar-signale
    *   🟢 **neutral:** der markt ist ziellos. finger weg!
    *   🔥 **kauf-zone:** kurs über roter linie, volumen hoch, rsi kühl. einstieg prüfen.
    *   ⚠️ **verkauf (überhitzt):** rsi über 75. gewinnsicherung prüfen.
    *   🩸 **verkauf (trendbruch):** kurs stürzt unter rote linie. reißleine ziehen!
    """)

COIN_BASIS = {
    "XBT": "bitcoin - platz 1", 
    "ETH": "ethereum - platz 2", 
    "SOL": "solana - platz 5", 
    "ADA": "cardano - platz 10", 
    "DOT": "polkadot - platz 15", 
    "LINK": "chainlink - platz 16",
    "BCH": "bitcoin cash - platz 17",
    "LTC": "litecoin - platz 21",
    "PEPE": "pepe - platz 24", 
    "SUI": "sui - platz 28", 
    "FET": "fetch.ai - platz 33", 
    "XMR": "monero - platz 35",
    "ARB": "arbitrum - platz 42"
}

if 'meine_basis_coins' not in st.session_state:
    st.session_state.meine_basis_coins = ["XBT", "ETH", "SOL", "PEPE", "SUI", "FET"]

alle_basis_coins = list(COIN_BASIS.keys())

def format_basis_label(basis_code):
    return f"{basis_code} ➔ {COIN_BASIS.get(basis_code, basis_code)}"

auswahl = st.sidebar.multiselect(
    "währungen suchen (tippen/scrollen):", 
    options=alle_basis_coins, 
    default=st.session_state.meine_basis_coins,
    format_func=format_basis_label
)

neue_liste = [c for c in st.session_state.meine_basis_coins if c in auswahl]
for c in auswahl:
    if c not in neue_liste: neue_liste.append(c)
st.session_state.meine_basis_coins = neue_liste

st.sidebar.markdown("---")
st.sidebar.subheader("💰 order-rechner")
investition = st.sidebar.number_input("geplante kaufsumme", min_value=10, value=500, step=50)
ziel_prozent = st.sidebar.number_input("ziel-gewinn take-profit (%)", min_value=1, max_value=1000, value=15, step=1)

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
st.write(f"🔄 **autopilot aktiv:** (gesamtsystem zuletzt aktualisiert: {jetzt_string})")
st.markdown("---")

w_symbol = FIAT_SYMBOLE.get(basis_waehrung, basis_waehrung)

for i, basis_coin in enumerate(st.session_state.meine_basis_coins):
    anzeige_name = COIN_BASIS.get(basis_coin, "altcoin")
    voller_coin_name = f"{basis_coin}{basis_waehrung}"
    
    daten_paket = fetch_kraken_ohlcv(voller_coin_name, interval=240)
    
    if daten_paket is None:
        st.error(f"⚠️ handelspaar **{voller_coin_name} ({anzeige_name})** wird auf dieser börse aktuell nicht angeboten.")
        st.markdown("---")
        continue

    df_live, ping_zeit = daten_paket
    aktuelle_kerze = df_live.iloc[-1]
    preis = aktuelle_kerze['close']
    rsi = aktuelle_kerze['rsi']
    sma = aktuelle_kerze['sma_200']
    vol = aktuelle_kerze['volume_ratio']

    status = "🟢 neutral (abwarten - finger weg)"
    if preis > sma and (45 <= rsi <= 65) and vol >= 2.0: status = "🔥 kauf-zone (einstieg prüfen)"
    elif rsi >= 75: status = "⚠️ verkauf (markt überhitzt)"
    elif preis < sma: status = "🩸 verkauf (trendbruch unter rote linie)"

    if rsi >= 75: rsi_ampel = "🔴"
    elif rsi >= 65: rsi_ampel = "🟡"
    elif rsi >= 45: rsi_ampel = "🟢"
    else: rsi_ampel = "🧊"
    dezimalstellen = 8 if preis < 0.01 else 4

    col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns([3.5, 2, 2, 0.5, 0.5])
    
    with col_k1:
        st.markdown(f"### {voller_coin_name}\n**{anzeige_name}**<br><span style='font-size:14px; color:#888888;'>ping: {ping_zeit}</span>", unsafe_allow_html=True)
    with col_k2:
        st.metric(label="live-kurs (börse)", value=f"{preis:.{dezimalstellen}f} {w_symbol}")
    with col_k3:
        st.metric(label=f"rsi (puls)", value=f"{rsi:.1f} {rsi_ampel}")
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

    with st.expander(f"📊 order-plan & chart für {voller_coin_name} öffnen"):
        col_d1, col_d2 = st.columns([1, 1.5])
        
        with col_d1:
            st.info(f"**signal: {status}**")
            st.markdown(f"**order-plan für {investition} {w_symbol}:**")
            coins_gekauft = investition / preis
            limit_3_pct_preis = preis * 0.97
            verlust = investition - (coins_gekauft * limit_3_pct_preis)
            ziel_preis = preis * (1 + (ziel_prozent / 100))
            gewinn = (coins_gekauft * ziel_preis) - investition
            
            st.markdown(f"- 🪙 **menge:** {coins_gekauft:,.2f} stück")
            st.markdown(f"- 🛑 **stop (-3%):** limit bei **{limit_3_pct_preis:.{dezimalstellen}f} {w_symbol}** (-{verlust:.2f} {w_symbol})")
            st.markdown(f"- 🎯 **ziel (+{ziel_prozent}%):** limit bei **{ziel_preis:.{dezimalstellen}f} {w_symbol}** (+{gewinn:.2f} {w_symbol})")

        with col_d2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_live['timestamp'], y=df_live['close'], 
                mode='lines', line=dict(color='#4da6ff', width=2), name='kurs',
                hovertemplate=f'<b>kurs:</b> %{{y:.4f}} {w_symbol}<br><b>block-start:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'
            ))
            fig.add_trace(go.Scatter(
                x=df_live['timestamp'], y=df_live['sma_200'], 
                mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='sma 200 (trend)',
                hovertemplate=f'<b>trend-grenze:</b> %{{y:.4f}} {w_symbol}<br><b>block-start:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'
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
            st.caption("🔴 **rote linie: makro-trend (sma 200)** ➔ fällt der kurs darunter, droht ein trendbruch.")

    st.markdown("---")
