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
if 'investition' not in st.session_state: st.session_state.investition = 300.0
if 'ziel_prozent' not in st.session_state: st.session_state.ziel_prozent = 10.0
if 'stop_prozent' not in st.session_state: st.session_state.stop_prozent = 3.0
if 'fiat_wahl' not in st.session_state: st.session_state.fiat_wahl = "EUR"
if 'tz_wahl' not in st.session_state: st.session_state.tz_wahl = "deutschland (berlin / mez)"

if 'port_coin' not in st.session_state: st.session_state.port_coin = "XXRP"
if 'port_menge' not in st.session_state: st.session_state.port_menge = 0.0
if 'port_kaufpreis' not in st.session_state: st.session_state.port_kaufpreis = 0.0

# ==========================================
# DAS REINE LEXIKON 
# ==========================================
ECHTE_NAMEN = {
    "XBT": "Bitcoin", "XXBT": "Bitcoin", 
    "ETH": "Ethereum", "XETH": "Ethereum",
    "XRP": "Ripple", "XXRP": "Ripple",
    "SOL": "Solana", "ADA": "Cardano", 
    "DOGE": "Dogecoin", "XDG": "Dogecoin",
    "DOT": "Polkadot", "LINK": "Chainlink",
    "BCH": "Bitcoin Cash", "LTC": "Litecoin", "XLTC": "Litecoin",
    "PEPE": "Pepe", "SUI": "Sui", "FET": "Fetch.ai", 
    "XMR": "Monero", "XXMR": "Monero", "ARB": "Arbitrum"
}

# ==========================================
# DYNAMISCHES KRAKEN-UNIVERSUM 
# ==========================================
@st.cache_data(ttl=3600)
def fetch_kraken_assets():
    try:
        res = requests.get("https://api.kraken.com/0/public/Assets").json()
        assets = {}
        for key, val in res['result'].items():
            altname = val['altname']
            if altname not in ['EUR', 'USD', 'GBP', 'CHF', 'CAD', 'AUD', 'JPY']:
                sauberer_name = ECHTE_NAMEN.get(key, ECHTE_NAMEN.get(altname, altname))
                assets[key] = f"{key} ➔ {sauberer_name}"
        return assets
    except:
        return {"XXRP": "XXRP ➔ Ripple", "XXBT": "XXBT ➔ Bitcoin"}

ALLE_COINS_DICT = fetch_kraken_assets()

if 'meine_basis_coins' not in st.session_state: 
    st.session_state.meine_basis_coins = ["SOL", "PEPE", "SUI", "FET", "ADA"]

def get_clean_name(api_key):
    raw_name = ALLE_COINS_DICT.get(api_key, api_key)
    if " ➔ " in raw_name:
        parts = raw_name.split(" ➔ ")
        kurzel = parts[0].replace('XX', 'X').replace('Z', '')
        name = parts[1]
        if name.upper() == kurzel.upper():
            return name
        return f"{name} ({kurzel})"
    return api_key

# ==========================================
# TICKER (Live Rauschfilter)
# ==========================================
@st.cache_data(ttl=300)
def fetch_global_ticker(fiat):
    try:
        res = requests.get("https://api.kraken.com/0/public/Ticker").json()
        if res.get('error'): return "Ticker-Daten derzeit nicht verfügbar."
        
        valid_pairs = []
        for pair_name, data in res['result'].items():
            if pair_name.endswith(fiat) or pair_name.endswith(f"Z{fiat}"):
                c = float(data['c'][0]) 
                o = float(data['o'])    
                v = float(data['v'][1]) 
                volumen_fiat = c * v 
                
                if volumen_fiat >= 1000000 and o > 0:
                    pct = ((c - o) / o) * 100
                    base_asset = pair_name.replace(fiat, "").replace(f"Z{fiat}", "")
                    display_name = ECHTE_NAMEN.get(base_asset, base_asset.replace('XX', 'X'))
                    valid_pairs.append({'name': display_name, 'pct': pct})
        
        valid_pairs.sort(key=lambda x: x['pct'], reverse=True)
        top_10 = valid_pairs[:10]
        flop_10 = valid_pairs[-10:]
        flop_10.sort(key=lambda x: x['pct']) 
        
        ticker_items = ["🔥 TOP 10 GEWINNER:"]
        for item in top_10: ticker_items.append(f"🟢 {item['name']}: +{item['pct']:.2f}%")
        ticker_items.append("  |  🩸 TOP 10 VERLIERER:")
        for item in flop_10: ticker_items.append(f"🔴 {item['name']}: {item['pct']:.2f}%")
            
        return " &nbsp;&nbsp;&nbsp;&nbsp; ".join(ticker_items)
    except: return "Ticker Offline"

# ==========================================
# 🎛️ EINSTELLUNGEN & SEITENLEISTE
# ==========================================
st.sidebar.header("⚙️ system-einstellungen")

if st.sidebar.button("🔄 alles auf werkseinstellungen"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

zeitzonen_optionen = {
    "deutschland (berlin / mez)": "Europe/Berlin", "england (london / gmt)": "Europe/London",
    "schweiz (zürich / cet)": "Europe/Zurich", "usa (new york / est)": "America/New_York",
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
st.sidebar.header("🎛️ deine watchlist (Alle Coins!)")

auswahl = st.sidebar.multiselect(
    "währungen suchen/hinzufügen:", 
    options=list(ALLE_COINS_DICT.keys()), 
    default=[c for c in st.session_state.meine_basis_coins if c in ALLE_COINS_DICT],
    format_func=lambda x: ALLE_COINS_DICT.get(x, x)
)
st.session_state.meine_basis_coins = auswahl

st.sidebar.markdown("---")
st.sidebar.subheader("💼 mein portfolio (Bestand)")

port_auswahl = st.sidebar.selectbox(
    "welchen coin besitzt du?", 
    st.session_state.meine_basis_coins, 
    index=0 if st.session_state.port_coin not in st.session_state.meine_basis_coins else st.session_state.meine_basis_coins.index(st.session_state.port_coin),
    format_func=lambda x: ALLE_COINS_DICT.get(x, x)
) if len(st.session_state.meine_basis_coins) > 0 else None

if port_auswahl: st.session_state.port_coin = port_auswahl

st.session_state.port_menge = st.sidebar.number_input("meine menge (stück)", min_value=0.0, value=float(st.session_state.port_menge), step=10.0)
st.session_state.port_kaufpreis = st.sidebar.number_input(f"mein kaufkurs ({w_symbol})", min_value=0.0, value=float(st.session_state.port_kaufpreis), step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 risiko-management & order")

st.session_state.investition = st.sidebar.number_input("geplante kaufsumme", min_value=10.0, value=float(st.session_state.investition), step=50.0)
st.session_state.ziel_prozent = st.sidebar.number_input("ziel-gewinn take-profit (%)", min_value=1.0, max_value=1000.0, value=float(st.session_state.ziel_prozent), step=1.0)
st.session_state.stop_prozent = st.sidebar.number_input("stop-loss / trailing-stop (%)", min_value=0.1, max_value=100.0, value=float(st.session_state.stop_prozent), step=0.5)

# ==========================================
# HAUPTBEREICH
# ==========================================
st.title("🚀 krypto-steuerzentrale | live-radar")

ticker_text = fetch_global_ticker(st.session_state.fiat_wahl)
st.markdown(f"<marquee style='font-size: 15px; font-weight: bold; color: #d4d4d4; background-color: #1e1e1e; padding: 6px; border-radius: 5px; border: 1px solid #333;'>{ticker_text}</marquee>", unsafe_allow_html=True)

with st.expander("🌍 weltuhren & börsen-öffnungszeiten (Wann kommt das große Geld?)"):
    col_u1, col_u2, col_u3, col_u4 = st.columns(4)
    col_u1.metric("🗽 New York (Wall Street)", f"{datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M')} Uhr")
    col_u2.metric("🎡 London (LSE)", f"{datetime.now(ZoneInfo('Europe/London')).strftime('%H:%M')} Uhr")
    col_u3.metric("🥨 Berlin/Zürich", f"{datetime.now(ZoneInfo('Europe/Berlin')).strftime('%H:%M')} Uhr")
    col_u4.metric("🗼 Tokyo (TSE)", f"{datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%H:%M')} Uhr")

col_m1, col_m2 = st.columns([2, 5])
with col_m1:
    if st.button("☑️ Alle aufklappen"):
        for c in st.session_state.meine_basis_coins: st.session_state[f"chk_{c}"] = True
        st.rerun()
with col_m2:
    if st.button("🔲 Alle zuklappen"):
        for c in st.session_state.meine_basis_coins: st.session_state[f"chk_{c}"] = False
        st.rerun()

# ==========================================
# MODUL 2: DAS FRAGMENTIERTE COCKPIT
# ==========================================
@st.fragment(run_every=300)
def live_radar_cockpit():
    st.write(f"🔄 **autopilot aktiv:** (radar zuletzt lautlos aktualisiert: {datetime.now(aktuelle_zeitzone).strftime('%H:%M:%S')})")
    st.markdown("---")

    for i, basis_coin in enumerate(st.session_state.meine_basis_coins):
        anzeige_name_sauber = get_clean_name(basis_coin)
        pair_request = f"{basis_coin}{st.session_state.fiat_wahl}"
        
        try:
            url = "https://api.kraken.com/0/public/OHLC"
            response = requests.get(url, params={'pair': pair_request, 'interval': 240}).json()
            if len(response.get('error', [])) > 0:
                response = requests.get(url, params={'pair': f"{basis_coin}Z{st.session_state.fiat_wahl}", 'interval': 240}).json()
                if len(response.get('error', [])) > 0:
                    alt_base = basis_coin[1:] if basis_coin.startswith('X') or basis_coin.startswith('Z') else basis_coin
                    response = requests.get(url, params={'pair': f"{alt_base}{st.session_state.fiat_wahl}", 'interval': 240}).json()
                    if len(response.get('error', [])) > 0: continue

            result_key = list(response['result'].keys())[0]
            df_live = pd.DataFrame(response['result'][result_key], columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            df_live['timestamp'] = pd.to_datetime(df_live['timestamp'], unit='s')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df_live[numeric_cols] = df_live[numeric_cols].apply(pd.to_numeric, errors='coerce')
            
            df_live['amplitude'] = (df_live['high'] - df_live['low']) / df_live['low'] * 100
            delta = df_live['close'].diff()
            gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
            df_live['rsi'] = 100 - (100 / (1 + gain / loss))
            df_live['volume_ratio'] = df_live['volume'] / df_live['volume'].rolling(20).mean()
            df_live['sma_200'] = df_live['close'].rolling(200).mean()
            ping_zeit = datetime.now(aktuelle_zeitzone).strftime('%H:%M:%S')
        except: continue

        aktuelle_kerze = df_live.iloc[-1]
        preis = aktuelle_kerze['close']
        rsi = aktuelle_kerze['rsi']
        sma = aktuelle_kerze['sma_200']
        vol = aktuelle_kerze['volume_ratio']
        volatilitaet_14 = df_live['amplitude'].tail(14).mean()

        status = "⚪ neutral (abwarten / halten)"
        if preis > sma and (45 <= rsi <= 65) and vol >= 2.0: status = "🟢 KAUF-ZONE (einstieg prüfen)"
        elif rsi >= 75: status = "🔴 VERKAUF (markt überhitzt)"
        elif preis < sma: status = "🔴 VERKAUF (trendbruch unter rote linie)"

        if status.startswith("🟢"): 
            rsi_ampel, rand_farbe, dca_icon = "🟢", "#00cc66", "🟢"
        elif rsi >= 75 or status.startswith("🔴"): 
            rsi_ampel, rand_farbe, dca_icon = "🔴", "#ff4d4d", "🔴"
        else: 
            rsi_ampel = "🧊" if rsi <= 45 else "⚪"
            rand_farbe, dca_icon = "#555555", "⚪"
        
        dezimalstellen = 6 if preis < 1.0 else 4

        col_k1, col_k2, col_k3, col_k4 = st.columns([2.5, 2, 1.5, 3])
        
        with col_k1:
            st.markdown(f"### {anzeige_name_sauber}<br><span style='font-size:14px; color:#888888;'>ping: {ping_zeit}</span>", unsafe_allow_html=True)
        with col_k2:
            st.metric(label=f"live-kurs ({st.session_state.fiat_wahl})", value=f"{preis:.{dezimalstellen}f} {w_symbol}")
        with col_k3:
            st.metric(label=f"rsi (puls)", value=f"{rsi:.1f} {rsi_ampel}")
        
        # DER NEUE TELEPORT-BLOCK (Alle Funktionen ergonomisch vereint)
        with col_k4:
            st.markdown("<br>", unsafe_allow_html=True)
            nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 1, 1, 2])
            
            with nav_col1:
                if i > 0 and st.button("🔝", key=f"top_{basis_coin}", help="Sofort auf Platz 1 teleportieren"):
                    st.session_state.meine_basis_coins.remove(basis_coin)
                    st.session_state.meine_basis_coins.insert(0, basis_coin)
                    st.rerun()
            with nav_col2:
                if i > 0 and st.button("⬆️", key=f"up_{basis_coin}"):
                    st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i-1] = st.session_state.meine_basis_coins[i-1], st.session_state.meine_basis_coins[i]
                    st.rerun()
            with nav_col3:
                if i < len(st.session_state.meine_basis_coins) - 1 and st.button("⬇️", key=f"down_{basis_coin}"):
                    st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i+1] = st.session_state.meine_basis_coins[i+1], st.session_state.meine_basis_coins[i]
                    st.rerun()
            with nav_col4:
                neu_platz = st.selectbox(
                    "Platz", 
                    options=range(1, len(st.session_state.meine_basis_coins) + 1), 
                    index=i, 
                    key=f"sel_pos_{basis_coin}", 
                    label_visibility="collapsed",
                    help="Exakten Platz wählen"
                )
                if (neu_platz - 1) != i:
                    st.session_state.meine_basis_coins.remove(basis_coin)
                    st.session_state.meine_basis_coins.insert(neu_platz - 1, basis_coin)
                    st.rerun()

        if f"chk_{basis_coin}" not in st.session_state: st.session_state[f"chk_{basis_coin}"] = False
        is_open = st.checkbox(f"📊 Chart & Risikomanagement für {anzeige_name_sauber.split(' (')[0]} einblenden", key=f"chk_{basis_coin}")

        if is_open:
            st.markdown(f"""<div style="border-left: 3px solid {rand_farbe}; padding-left: 15px; margin-bottom: 20px;">""", unsafe_allow_html=True)
            
            if basis_coin == st.session_state.port_coin and st.session_state.port_menge > 0:
                st.success(f"💼 **Dein Bestand:** {st.session_state.port_menge} Stück (Kaufkurs: {st.session_state.port_kaufpreis} {w_symbol})")
                aktueller_wert = st.session_state.port_menge * preis
                investiert = st.session_state.port_menge * st.session_state.port_kaufpreis
                pnl = aktueller_wert - investiert
                pnl_pct = (pnl / investiert) * 100 if investiert > 0 else 0
                zusatz_menge = st.session_state.investition / preis
                neue_gesamtmenge = st.session_state.port_menge + zusatz_menge
                neues_investment = investiert + st.session_state.investition
                neuer_durchschnitt = neues_investment / neue_gesamtmenge if neue_gesamtmenge > 0 else 0
                trailing_stop = preis * (1 - (st.session_state.stop_prozent / 100))
                
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Aktueller Wert", f"{aktueller_wert:.2f} {w_symbol}")
                col_p2.metric("Gewinn / Verlust", f"{pnl:.2f} {w_symbol}", f"{pnl_pct:.2f}%")
                col_p3.metric(f"🚨 Trailing-Stop (-{st.session_state.stop_prozent}%)", f"{trailing_stop:.{dezimalstellen}f} {w_symbol}")
                
                dca_html = f"""<div style="background-color: #1a1a1a; border: 2px solid {rand_farbe}; border-radius: 8px; padding: 15px; margin-bottom: 20px;"><span style="font-size: 15px; color: #e0e0e0; line-height: 1.5;">{dca_icon} <b>Nachkauf-Simulation (DCA):</b> Wenn du jetzt {st.session_state.investition:.2f} {w_symbol} investierst, sinkt dein Durchschnitts-Kaufpreis von <b>{st.session_state.port_kaufpreis:.4f} {w_symbol}</b> auf <b>{neuer_durchschnitt:.4f} {w_symbol}</b>.</span></div>"""
                st.markdown(dca_html, unsafe_allow_html=True)

            col_d1, col_d2 = st.columns([1, 2])
            with col_d1:
                st.info(f"**signal: {status}**")
                st.markdown(f"**order-rechner (Neu-Einstieg für {st.session_state.investition} {w_symbol}):**")
                coins_gekauft = st.session_state.investition / preis
                limit_stop_preis = preis * (1 - (st.session_state.stop_prozent / 100))
                verlust = st.session_state.investition - (coins_gekauft * limit_stop_preis)
                ziel_preis = preis * (1 + (st.session_state.ziel_prozent / 100))
                gewinn = (coins_gekauft * ziel_preis) - st.session_state.investition
                
                st.markdown(f"- 🪙 **menge:** {coins_gekauft:,.2f} stück")
                st.markdown(f"- 🛑 **stop (-{st.session_state.stop_prozent}%):** limit bei **{limit_stop_preis:.{dezimalstellen}f} {w_symbol}** (-{verlust:.2f} {w_symbol})")
                st.markdown(f"- 🎯 **ziel (+{st.session_state.ziel_prozent}%):** limit bei **{ziel_preis:.{dezimalstellen}f} {w_symbol}** (+{gewinn:.2f} {w_symbol})")
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.session_state.stop_prozent <= volatilitaet_14:
                    st.warning(f"⚠️ **Volatilitäts-Warnung:** {anzeige_name_sauber.split(' (')[0]} schwankt aktuell im Schnitt um **{volatilitaet_14:.1f}%**. Dein Stop ({st.session_state.stop_prozent}%) ist zu eng.")
                else:
                    st.success(f"🛡️ **Risiko-Check:** Dein Stop ({st.session_state.stop_prozent}%) liegt sicher außerhalb der normalen Schwankung ({volatilitaet_14:.1f}%).")

            with col_d2:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['close'], mode='lines', line=dict(color='#4da6ff', width=2), name='kurs', hovertemplate=f'<b>kurs:</b> %{{y:.4f}} {w_symbol}<br><b>zeit:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'))
                fig.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['sma_200'], mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='sma 200', hovertemplate=f'<b>trend-grenze:</b> %{{y:.4f}} {w_symbol}<br><b>zeit:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'))
                
                kauf_signale = df_live[(df_live['close'] > df_live['sma_200']) & (df_live['rsi'] >= 45) & (df_live['rsi'] <= 65) & (df_live['volume_ratio'] >= 2.0)]
                verkauf_signale = df_live[(df_live['rsi'] >= 75) | (df_live['close'] < df_live['sma_200'])]

                fig.add_trace(go.Scatter(x=kauf_signale['timestamp'], y=kauf_signale['close'], mode='markers', marker=dict(color='green', size=10, symbol='triangle-up'), name='Kauf-Signal'))
                fig.add_trace(go.Scatter(x=verkauf_signale['timestamp'], y=verkauf_signale['close'], mode='markers', marker=dict(color='red', size=8, symbol='x'), name='Verkauf-Signal'))
                
                fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(range=[df_live['timestamp'].iloc[-100], df_live['timestamp'].iloc[-1] + pd.Timedelta(hours=48)], showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333333'), showlegend=False, height=200, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{basis_coin}")
                st.caption("🟢 **Grünes Dreieck:** Kauf-Signal | ❌ **Rotes X:** Verkaufs-Signal / Trendbruch")
            
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

live_radar_cockpit()
