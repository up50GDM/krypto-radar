import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from zoneinfo import ZoneInfo
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ SEITEN-KONFIGURATION
# ==========================================
st.set_page_config(page_title="Steuerzentrale Radar", layout="wide")

# ==========================================
# 💾 FELSENFESTES GEDÄCHTNIS (Session State)
# ==========================================
if 'investition' not in st.session_state:
    st.session_state.investition = 500
if 'ziel_prozent' not in st.session_state:
    st.session_state.ziel_prozent = 15
if 'meine_basis_coins' not in st.session_state:
    st.session_state.meine_basis_coins = ["XBT", "ETH", "SOL", "PEPE"]
if 'fiat_wahl' not in st.session_state:
    st.session_state.fiat_wahl = "EUR"
if 'tz_wahl' not in st.session_state:
    st.session_state.tz_wahl = "deutschland (berlin / mez)"
if 'alle_aufklappen' not in st.session_state:
    st.session_state.alle_aufklappen = False
if 'calc_input' not in st.session_state:
    st.session_state.calc_input = ""
if 'calc_result' not in st.session_state:
    st.session_state.calc_result = ""

# ==========================================
# 🧮 TASCHENRECHNER (Funktionen)
# ==========================================
def calculate():
    try:
        # Sichere Auswertung von Basis-Mathematik
        st.session_state.calc_result = str(eval(st.session_state.calc_input, {"__builtins__": None}, {}))
    except Exception:
        st.session_state.calc_result = "Fehler"

# ==========================================
# 🎛️ EINSTELLUNGEN & SEITENLEISTE
# ==========================================
st.sidebar.header("⚙️ system-einstellungen")

if st.sidebar.button("🔄 auf werkseinstellungen zurücksetzen"):
    st.session_state.investition = 500
    st.session_state.ziel_prozent = 15
    st.session_state.meine_basis_coins = ["XBT", "ETH", "SOL", "PEPE"]
    st.session_state.fiat_wahl = "EUR"
    st.session_state.tz_wahl = "deutschland (berlin / mez)"
    st.session_state.alle_aufklappen = False
    st.rerun()

st.sidebar.markdown("---")

# Taschenrechner in der Seitenleiste (Ausklappbar)
with st.sidebar.expander("🧮 taschenrechner", expanded=False):
    st.text_input("Berechnung eingeben (z.B. 1500 * 0.03):", key="calc_input", on_change=calculate)
    if st.session_state.calc_result:
        st.markdown(f"**Ergebnis:** `{st.session_state.calc_result}`")
    st.caption("Nutze: + (Plus), - (Minus), * (Mal), / (Geteilt)")

st.sidebar.markdown("---")

st.sidebar.selectbox("🏛️ krypto-börse (api):", ["kraken", "binance (in vorbereitung)", "coinbase (in vorbereitung)"])
st.sidebar.caption("⚠️ kann nur geändert werden, wenn die api-schnittstelle aktiv ist.")

st.sidebar.markdown("---")

zeitzonen_optionen = {
    "deutschland (berlin / mez)": "Europe/Berlin",
    "england (london / gmt)": "Europe/London",
    "schweiz (zürich / cet)": "Europe/Zurich",
    "usa (new york / est)": "America/New_York",
    "japan (tokyo / jst)": "Asia/Tokyo",
    "weltzeit (utc)": "UTC"
}

tz_keys = list(zeitzonen_optionen.keys())
gewaehlte_tz_label = st.sidebar.selectbox(
    "🌍 lokale zeitzone:", 
    tz_keys, 
    index=tz_keys.index(st.session_state.tz_wahl) if st.session_state.tz_wahl in tz_keys else 0,
    key="select_tz_safe"
)
st.session_state.tz_wahl = gewaehlte_tz_label
aktuelle_zeitzone = ZoneInfo(zeitzonen_optionen[gewaehlte_tz_label])

FIAT_SYMBOLE = {
    "EUR": "€", "USD": "$", "GBP": "£", "CHF": "chf", "CAD": "ca$", "AUD": "au$", "JPY": "¥"
}
fiat_keys = list(FIAT_SYMBOLE.keys())
basis_waehrung = st.sidebar.selectbox(
    "💵 bevorzugte fiat-währung:", 
    fiat_keys, 
    index=fiat_keys.index(st.session_state.fiat_wahl) if st.session_state.fiat_wahl in fiat_keys else 0,
    key="select_fiat_safe"
)
st.session_state.fiat_wahl = basis_waehrung

st.sidebar.markdown("---")
st.sidebar.header("🎛️ deine watchlist")

COIN_BASIS = {
    "XBT": "bitcoin - platz 1", "ETH": "ethereum - platz 2", "SOL": "solana - platz 5", 
    "ADA": "cardano - platz 10", "DOT": "polkadot - platz 15", "LINK": "chainlink - platz 16",
    "BCH": "bitcoin cash - platz 17", "LTC": "litecoin - platz 21", "PEPE": "pepe - platz 24", 
    "SUI": "sui - platz 28", "FET": "fetch.ai - platz 33", "XMR": "monero - platz 35",
    "ARB": "arbitrum - platz 42"
}
alle_basis_coins = list(COIN_BASIS.keys())

def format_basis_label(basis_code):
    return f"{basis_code} ➔ {COIN_BASIS.get(basis_code, basis_code)}"

auswahl = st.sidebar.multiselect(
    "währungen suchen (tippen/scrollen):", 
    options=alle_basis_coins, 
    default=st.session_state.meine_basis_coins,
    format_func=format_basis_label,
    key="multiselect_coins_safe"
)
st.session_state.meine_basis_coins = auswahl

st.sidebar.markdown("---")
st.sidebar.subheader("💰 order-rechner (Neu-Investition)")

investition = st.sidebar.number_input(
    "geplante kaufsumme", 
    min_value=10, 
    value=st.session_state.investition, 
    step=50,
    key="input_invest_safe"
)
st.session_state.investition = investition

ziel_prozent = st.sidebar.number_input(
    "ziel-gewinn take-profit (%)", 
    min_value=1, 
    max_value=1000, 
    value=st.session_state.ziel_prozent, 
    step=1,
    key="input_ziel_safe"
)
st.session_state.ziel_prozent = ziel_prozent

# ==========================================
# HAUPTBEREICH
# ==========================================
st.title("🚀 krypto-steuerzentrale | live-radar")

# 🌍 WELTUHREN & ÖFFNUNGSZEITEN (Ausklappbar)
with st.expander("🌍 weltuhren & börsen-öffnungszeiten (Wann kommt das große Geld?)"):
    col_u1, col_u2, col_u3, col_u4 = st.columns(4)
    # Weltzeiten live berechnen
    utc_now = datetime.utcnow()
    ny_time = datetime.now(ZoneInfo("America/New_York")).strftime('%H:%M')
    lon_time = datetime.now(ZoneInfo("Europe/London")).strftime('%H:%M')
    ger_time = datetime.now(ZoneInfo("Europe/Berlin")).strftime('%H:%M')
    tok_time = datetime.now(ZoneInfo("Asia/Tokyo")).strftime('%H:%M')
    
    col_u1.metric("🗽 New York (Wall Street)", f"{ny_time} Uhr")
    col_u2.metric("🎡 London (LSE)", f"{lon_time} Uhr")
    col_u3.metric("🥨 Berlin/Zürich", f"{ger_time} Uhr")
    col_u4.metric("🗼 Tokyo (TSE)", f"{tok_time} Uhr")
    
    st.markdown("""
    *Krypto-Börsen laufen 24/7. Aber die höchste Volatilität (stärkste Kursbewegungen) entsteht, wenn die traditionellen Aktienmärkte öffnen und Institutionen Geld umschichten:*
    *   🇺🇸 **USA (Wall Street):** 15:30 - 22:00 Uhr (MEZ) -> *Die wichtigsten Stunden für den Krypto-Markt.*
    *   🇬🇧 **Europa (London/Frankfurt):** 09:00 - 17:30 Uhr (MEZ)
    *   🇯🇵 **Asien (Tokyo):** 02:00 - 08:00 Uhr (MEZ)
    """)

# Hilfe & Erklärung
with st.expander("❓ hilfe & erklärung (hier klicken, um alle funktionen zu verstehen)"):
    st.markdown("""
    ### 🧭 system-handbuch: so liest du das radar
    dieses dashboard filtert marktrauschen durch nackte mathematik.
    #### die radar-signale (Farb-Logik angepasst!)
    *   ⚪ **neutral:** der markt ist ziellos. grau = kein stress, nichts tun.
    *   🟢 **kauf-zone:** kurs über roter linie, rsi kühl. starkes kaufsignal.
    *   🔴 **verkauf / gefahr:** markt überhitzt (rsi > 75) oder trendbruch (unter roter linie).
    """)

# ==========================================
# MASTER-SCHALTER (Alle auf/zu)
# ==========================================
col_m1, col_m2 = st.columns([1, 5])
with col_m1:
    if st.button("🔽 Alle aufklappen" if not st.session_state.alle_aufklappen else "🔼 Alle zuklappen"):
        st.session_state.alle_aufklappen = not st.session_state.alle_aufklappen
        st.rerun()

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
# MODUL 2: DAS FRAGMENTIERTE COCKPIT
# ==========================================
@st.fragment(run_every=300)
def live_radar_cockpit():
    jetzt_string = datetime.now(aktuelle_zeitzone).strftime('%d.%m.%Y - %H:%M:%S')
    st.write(f"🔄 **autopilot aktiv:** (radar zuletzt lautlos aktualisiert: {jetzt_string})")
    st.markdown("---")

    w_symbol = FIAT_SYMBOLE.get(st.session_state.fiat_wahl, st.session_state.fiat_wahl)

    for i, basis_coin in enumerate(st.session_state.meine_basis_coins):
        anzeige_name = COIN_BASIS.get(basis_coin, "altcoin")
        voller_coin_name = f"{basis_coin}{st.session_state.fiat_wahl}"
        
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

        # NEUE FARBLOGIK: Neutral ist jetzt Grau (⚪). Klare Signale (Grün/Rot)
        status = "⚪ neutral (abwarten - finger weg)"
        if preis > sma and (45 <= rsi <= 65) and vol >= 2.0: status = "🟢 KAUF-ZONE (einstieg prüfen)"
        elif rsi >= 75: status = "🔴 VERKAUF (markt überhitzt)"
        elif preis < sma: status = "🔴 VERKAUF (trendbruch unter rote linie)"

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

        # Nutzung des Master-Schalters für das Aufklappen
        with st.expander(f"📊 order-plan & chart für {voller_coin_name}", expanded=st.session_state.alle_aufklappen):
            col_d1, col_d2 = st.columns([1, 1.5])
            
            with col_d1:
                st.info(f"**signal: {status}**")
                st.markdown(f"**order-plan für {st.session_state.investition} {w_symbol}:**")
                coins_gekauft = st.session_state.investition / preis
                limit_3_pct_preis = preis * 0.97
                verlust = st.session_state.investition - (coins_gekauft * limit_3_pct_preis)
                ziel_preis = preis * (1 + (st.session_state.ziel_prozent / 100))
                gewinn = (coins_gekauft * ziel_preis) - st.session_state.investition
                
                st.markdown(f"- 🪙 **menge:** {coins_gekauft:,.2f} stück")
                st.markdown(f"- 🛑 **stop (-3%):** limit bei **{limit_3_pct_preis:.{dezimalstellen}f} {w_symbol}** (-{verlust:.2f} {w_symbol})")
                st.markdown(f"- 🎯 **ziel (+{st.session_state.ziel_prozent}%):** limit bei **{ziel_preis:.{dezimalstellen}f} {w_symbol}** (+{gewinn:.2f} {w_symbol})")

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
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{voller_coin_name}")
                st.caption("🔴 **rote linie: makro-trend (sma 200)** ➔ fällt der kurs darunter, droht ein trendbruch.")

        st.markdown("---")

live_radar_cockpit()
