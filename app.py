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
st.set_page_config(page_title="steuerzentrale radar", layout="wide")

# ==========================================
# 💾 FELSENFESTES GEDÄCHTNIS (Session State)
# ==========================================
if 'investition' not in st.session_state: st.session_state.investition = 500
if 'ziel_prozent' not in st.session_state: st.session_state.ziel_prozent = 15
if 'meine_basis_coins' not in st.session_state: st.session_state.meine_basis_coins = ["XBT", "ETH", "SOL", "PEPE"]
if 'geoeffnete_charts' not in st.session_state: st.session_state.geoeffnete_charts = []
if 'fiat_wahl' not in st.session_state: st.session_state.fiat_wahl = "EUR"
if 'tz_wahl' not in st.session_state: st.session_state.tz_wahl = "deutschland (berlin / mez)"

# Portfolio-Gedächtnis
if 'port_coin' not in st.session_state: st.session_state.port_coin = "XBT"
if 'port_menge' not in st.session_state: st.session_state.port_menge = 0.0
if 'port_kaufpreis' not in st.session_state: st.session_state.port_kaufpreis = 0.0

# ==========================================
# 🎛️ EINSTELLUNGEN & SEITENLEISTE
# ==========================================
st.sidebar.header("⚙️ system-einstellungen")

if st.sidebar.button("🔄 alles auf werkseinstellungen"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("---")

zeitzonen_optionen = {
    "deutschland (berlin / mez)": "Europe/Berlin",
    "england (london / gmt)": "Europe/London",
    "schweiz (zürich / cet)": "Europe/Zurich",
    "usa (new york / est)": "America/New_York",
    "japan (tokyo / jst)": "Asia/Tokyo"
}
tz_keys = list(zeitzonen_optionen.keys())
gewaehlte_tz_label = st.sidebar.selectbox("🌍 lokale zeitzone:", tz_keys, index=tz_keys.index(st.session_state.tz_wahl) if st.session_state.tz_wahl in tz_keys else 0)
st.session_state.tz_wahl = gewaehlte_tz_label
aktuelle_zeitzone = ZoneInfo(zeitzonen_optionen[gewaehlte_tz_label])

FIAT_SYMBOLE = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "chf", "CAD": "ca$", "AUD": "au$", "JPY": "¥"}
fiat_keys = list(FIAT_SYMBOLE.keys())
basis_waehrung = st.sidebar.selectbox("💵 fiat-währung:", fiat_keys, index=fiat_keys.index(st.session_state.fiat_wahl) if st.session_state.fiat_wahl in fiat_keys else 0)
st.session_state.fiat_wahl = basis_waehrung
w_symbol = FIAT_SYMBOLE.get(basis_waehrung, basis_waehrung)

st.sidebar.markdown("---")
st.sidebar.header("🎛️ deine watchlist")

COIN_BASIS = {
    "XBT": "bitcoin (1)", "ETH": "ethereum (2)", "SOL": "solana (5)", 
    "ADA": "cardano (10)", "DOT": "polkadot (15)", "LINK": "chainlink (16)",
    "BCH": "bitcoin cash (17)", "LTC": "litecoin (21)", "PEPE": "pepe (24)", 
    "SUI": "sui (28)", "FET": "fetch.ai (33)", "XMR": "monero (35)", "ARB": "arbitrum (42)"
}

auswahl = st.sidebar.multiselect(
    "währungen suchen/hinzufügen:", 
    options=list(COIN_BASIS.keys()), 
    default=st.session_state.meine_basis_coins,
    format_func=lambda x: f"{x} ➔ {COIN_BASIS.get(x, x)}"
)
st.session_state.meine_basis_coins = auswahl

st.session_state.geoeffnete_charts = st.sidebar.multiselect(
    "📊 dauerhaft geöffnete charts:", 
    options=st.session_state.meine_basis_coins,
    default=[c for c in st.session_state.geoeffnete_charts if c in st.session_state.meine_basis_coins],
    help="Diese Charts bleiben bei jedem Neuladen automatisch aufgeklappt."
)

st.sidebar.markdown("---")
st.sidebar.subheader("💼 mein portfolio (Trailing Stop)")

st.session_state.port_coin = st.sidebar.selectbox("welchen coin besitzt du?", st.session_state.meine_basis_coins, index=st.session_state.meine_basis_coins.index(st.session_state.port_coin) if st.session_state.port_coin in st.session_state.meine_basis_coins else 0)
st.session_state.port_menge = st.sidebar.number_input("meine menge (stück)", min_value=0.0, value=st.session_state.port_menge, step=0.01)
st.session_state.port_kaufpreis = st.sidebar.number_input(f"mein kaufkurs ({w_symbol})", min_value=0.0, value=st.session_state.port_kaufpreis, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 order-rechner (Neu-Einstieg)")

st.session_state.investition = st.sidebar.number_input("geplante kaufsumme", min_value=10, value=st.session_state.investition, step=50)
st.session_state.ziel_prozent = st.sidebar.number_input("ziel-gewinn take-profit (%)", min_value=1, max_value=1000, value=st.session_state.ziel_prozent, step=1)

# ==========================================
# DATENBESCHAFFUNG & TICKER
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
        return df, datetime.now(aktuelle_zeitzone).strftime('%H:%M:%S')
    except: return None

@st.cache_data(ttl=300)
def fetch_global_ticker(fiat):
    try:
        top_coins = ["XBT", "ETH", "SOL", "ADA", "DOGE", "PEPE", "SUI"]
        pairs = ",".join([f"{c}{fiat}" for c in top_coins])
        res = requests.get("https://api.kraken.com/0/public/Ticker", params={"pair": pairs}).json()
        if res.get('error'): return "Ticker-Daten derzeit nicht verfügbar."
        
        ticker_items = []
        for pair_name, data in res['result'].items():
            name = pair_name.replace(fiat, "").replace("XXBTZ", "XBT").replace("XETHZ", "ETH")
            c = float(data['c'][0])
            o = float(data['o'])
            pct = ((c - o) / o) * 100 if o > 0 else 0
            sym = "🟢" if pct >= 0 else "🔴"
            ticker_items.append(f"{sym} {name}: {pct:+.2f}%")
        return " &nbsp;&nbsp; | &nbsp;&nbsp; ".join(ticker_items)
    except: return "Ticker Offline"

# ==========================================
# HAUPTBEREICH
# ==========================================
st.title("🚀 krypto-steuerzentrale | live-radar")

# Laufband (Ticker)
ticker_text = fetch_global_ticker(st.session_state.fiat_wahl)
st.markdown(f"<marquee style='font-size: 16px; font-weight: bold; color: #d4d4d4; background-color: #1e1e1e; padding: 5px; border-radius: 5px;'>{ticker_text}</marquee>", unsafe_allow_html=True)

# Weltuhren
with st.expander("🌍 weltuhren & börsen-öffnungszeiten (Wann kommt das große Geld?)"):
    col_u1, col_u2, col_u3, col_u4 = st.columns(4)
    ny_time = datetime.now(ZoneInfo("America/New_York")).strftime('%H:%M')
    lon_time = datetime.now(ZoneInfo("Europe/London")).strftime('%H:%M')
    ger_time = datetime.now(ZoneInfo("Europe/Berlin")).strftime('%H:%M')
    tok_time = datetime.now(ZoneInfo("Asia/Tokyo")).strftime('%H:%M')
    
    col_u1.metric("🗽 New York (Wall Street)", f"{ny_time} Uhr")
    col_u2.metric("🎡 London (LSE)", f"{lon_time} Uhr")
    col_u3.metric("🥨 Berlin/Zürich", f"{ger_time} Uhr")
    col_u4.metric("🗼 Tokyo (TSE)", f"{tok_time} Uhr")
    
    st.markdown("""
    *Krypto-Börsen laufen 24/7. Die höchste Volatilität entsteht jedoch, wenn traditionelle Aktienmärkte öffnen:*
    *   🇺🇸 **USA (Wall Street):** 15:30 - 22:00 Uhr (MEZ) -> *Die wichtigsten Stunden für den Markt.*
    *   🇬🇧 **Europa (London/Frankfurt):** 09:00 - 17:30 Uhr (MEZ)
    *   🇯🇵 **Asien (Tokyo):** 02:00 - 08:00 Uhr (MEZ)
    """)

# ==========================================
# MODUL 2: DAS FRAGMENTIERTE COCKPIT
# ==========================================
@st.fragment(run_every=300)
def live_radar_cockpit():
    st.write(f"🔄 **autopilot aktiv:** (radar zuletzt lautlos aktualisiert: {datetime.now(aktuelle_zeitzone).strftime('%H:%M:%S')})")
    st.markdown("---")

    for i, basis_coin in enumerate(st.session_state.meine_basis_coins):
        anzeige_name = COIN_BASIS.get(basis_coin, "altcoin")
        voller_coin_name = f"{basis_coin}{st.session_state.fiat_wahl}"
        
        daten_paket = fetch_kraken_ohlcv(voller_coin_name, interval=240)
        
        if daten_paket is None:
            st.error(f"⚠️ handelspaar **{voller_coin_name}** wird auf dieser börse aktuell nicht angeboten.")
            st.markdown("---")
            continue

        df_live, ping_zeit = daten_paket
        aktuelle_kerze = df_live.iloc[-1]
        preis = aktuelle_kerze['close']
        rsi = aktuelle_kerze['rsi']
        sma = aktuelle_kerze['sma_200']
        vol = aktuelle_kerze['volume_ratio']

        # KLARE SIGNAL-LOGIK (Keine farbliche Verwirrung mehr)
        status = "⚪ neutral (abwarten / halten)"
        if preis > sma and (45 <= rsi <= 65) and vol >= 2.0: status = "🟢 KAUF-ZONE (einstieg prüfen)"
        elif rsi >= 75: status = "🔴 VERKAUF (markt überhitzt)"
        elif preis < sma: status = "🔴 VERKAUF (trendbruch unter rote linie)"

        # RSI Ampel ist nur noch Grau (Neutral), außer bei Gefahr oder echtem Kaufsignal
        rsi_ampel = "⚪"
        if status.startswith("🟢"): rsi_ampel = "🟢"
        elif rsi >= 75 or status.startswith("🔴"): rsi_ampel = "🔴"
        elif rsi <= 45: rsi_ampel = "🧊" # Panik/Abverkauf
        
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
            if i > 0 and st.button("⬆️", key=f"up_{basis_coin}"):
                st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i-1] = st.session_state.meine_basis_coins[i-1], st.session_state.meine_basis_coins[i]
                st.rerun()
        with col_k5:
            st.markdown("<br>", unsafe_allow_html=True)
            if i < len(st.session_state.meine_basis_coins) - 1 and st.button("⬇️", key=f"down_{basis_coin}"):
                st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i+1] = st.session_state.meine_basis_coins[i+1], st.session_state.meine_basis_coins[i]
                st.rerun()

        # Selektives Aufklappen anhand der Sidebar-Auswahl
        is_expanded = basis_coin in st.session_state.geoeffnete_charts

        with st.expander(f"📊 plan & chart für {voller_coin_name}", expanded=is_expanded):
            
            # PORTFOLIO-ANZEIGE (Nur wenn dieser Coin im Bestand eingetragen wurde)
            if basis_coin == st.session_state.port_coin and st.session_state.port_menge > 0:
                st.success(f"💼 **Dein Bestand:** {st.session_state.port_menge} Stück (Kaufkurs: {st.session_state.port_kaufpreis} {w_symbol})")
                
                aktueller_wert = st.session_state.port_menge * preis
                investiert = st.session_state.port_menge * st.session_state.port_kaufpreis
                pnl = aktueller_wert - investiert
                pnl_pct = (pnl / investiert) * 100 if investiert > 0 else 0
                
                # Trailing Stop: 3% unter dem *aktuellen* Höchstwert (hier vereinfacht zum Live-Preis)
                trailing_stop = preis * 0.97
                
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Aktueller Wert", f"{aktueller_wert:.2f} {w_symbol}")
                col_p2.metric("Gewinn / Verlust", f"{pnl:.2f} {w_symbol}", f"{pnl_pct:.2f}%")
                col_p3.metric("🚨 Empfohlener Trailing-Stop (-3%)", f"{trailing_stop:.{dezimalstellen}f} {w_symbol}")
                st.markdown("---")

            col_d1, col_d2 = st.columns([1, 1.5])
            
            with col_d1:
                st.info(f"**signal: {status}**")
                st.markdown(f"**order-rechner (Neu-Einstieg für {st.session_state.investition} {w_symbol}):**")
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
                    hovertemplate=f'<b>kurs:</b> %{{y:.4f}} {w_symbol}<br><b>zeit:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'
                ))
                fig.add_trace(go.Scatter(
                    x=df_live['timestamp'], y=df_live['sma_200'], 
                    mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='sma 200',
                    hovertemplate=f'<b>trend-grenze:</b> %{{y:.4f}} {w_symbol}<br><b>zeit:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'
                ))
                
                # GRÜNE UND ROTE MARKER IM CHART!
                kauf_signale = df_live[(df_live['close'] > df_live['sma_200']) & (df_live['rsi'] >= 45) & (df_live['rsi'] <= 65) & (df_live['volume_ratio'] >= 2.0)]
                verkauf_signale = df_live[(df_live['rsi'] >= 75) | (df_live['close'] < df_live['sma_200'])]

                fig.add_trace(go.Scatter(
                    x=kauf_signale['timestamp'], y=kauf_signale['close'],
                    mode='markers', marker=dict(color='green', size=10, symbol='triangle-up'), name='Kauf-Signal'
                ))
                fig.add_trace(go.Scatter(
                    x=verkauf_signale['timestamp'], y=verkauf_signale['close'],
                    mode='markers', marker=dict(color='red', size=8, symbol='x'), name='Verkauf-Signal'
                ))
                
                fig.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(range=[df_live['timestamp'].iloc[-100], df_live['timestamp'].iloc[-1] + pd.Timedelta(hours=48)], showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='#333333'),
                    showlegend=False, height=200, hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{voller_coin_name}")
                st.caption("🟢 **Grünes Dreieck:** Kauf-Signal der Vergangenheit | ❌ **Rotes X:** Verkaufs-Signal")

        st.markdown("---")

live_radar_cockpit()
