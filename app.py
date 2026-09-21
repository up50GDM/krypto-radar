import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from zoneinfo import ZoneInfo
import warnings
import json
import os
import locale
warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ SEITEN-KONFIGURATION
# ==========================================
st.set_page_config(page_title="steuerzentrale radar", layout="wide")

# ==========================================
# 💾 FESTPLATTEN-SPEICHER (Dauerhaftes Gedächtnis)
# ==========================================
SPEICHER_DATEI = "tresor_speicher.json"
DEFAULT_COINS = ["XXBT", "XETH", "XXRP", "SOL", "ADA", "PEPE", "SUI", "FET"]

def lade_daten():
    if os.path.exists(SPEICHER_DATEI):
        try:
            with open(SPEICHER_DATEI, 'r') as f: return json.load(f)
        except: pass
    return {"vault": {}, "watchlist": DEFAULT_COINS}

def speichere_daten(vault_data, watchlist_data):
    with open(SPEICHER_DATEI, 'w') as f:
        json.dump({"vault": vault_data, "watchlist": watchlist_data}, f)

# Initiales Laden der Festplatten-Daten beim App-Start
if 'app_loaded' not in st.session_state:
    datenbank = lade_daten()
    st.session_state.vault = datenbank.get("vault", {})
    st.session_state.meine_basis_coins = datenbank.get("watchlist", DEFAULT_COINS)
    st.session_state.fiat_wahl = "EUR"
    st.session_state.tz_wahl = "deutschland (berlin / mez)"
    st.session_state.zahlen_format = "International (75,000.34)"
    st.session_state.app_loaded = True

# ==========================================
# FORMATIERUNGS-FUNKTION (Deutsch vs International)
# ==========================================
def formatiere_zahl(zahl, dezimalstellen=2):
    """Formatiert Zahlen basierend auf der Nutzerauswahl in der Seitenleiste"""
    try:
        if st.session_state.zahlen_format == "Deutsch (75.000,34)":
            format_str = f"{{:,.{dezimalstellen}f}}"
            return format_str.format(zahl).replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            return f"{zahl:,.{dezimalstellen}f}"
    except:
        return f"{zahl:.{dezimalstellen}f}"

# ==========================================
# DAS REINE LEXIKON 
# ==========================================
ECHTE_NAMEN = {
    "XBT": "Bitcoin", "XXBT": "Bitcoin", "ETH": "Ethereum", "XETH": "Ethereum",
    "XRP": "Ripple", "XXRP": "Ripple", "SOL": "Solana", "ADA": "Cardano", 
    "DOGE": "Dogecoin", "XDG": "Dogecoin", "DOT": "Polkadot", "LINK": "Chainlink",
    "BCH": "Bitcoin Cash", "LTC": "Litecoin", "XLTC": "Litecoin", "PEPE": "Pepe", 
    "SUI": "Sui", "FET": "Fetch.ai", "XMR": "Monero", "XXMR": "Monero", "ARB": "Arbitrum"
}

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
st.session_state.meine_basis_coins = list(dict.fromkeys(st.session_state.meine_basis_coins))

def get_clean_name(api_key):
    raw_name = ALLE_COINS_DICT.get(api_key, api_key)
    if " ➔ " in raw_name:
        parts = raw_name.split(" ➔ ")
        kurzel = parts[0].replace('XX', 'X').replace('Z', '')
        name = parts[1]
        if name.upper() == kurzel.upper(): return name
        return f"{name} ({kurzel})"
    return api_key

@st.cache_data(ttl=300)
def fetch_global_ticker(fiat):
    try:
        res = requests.get("https://api.kraken.com/0/public/Ticker").json()
        if res.get('error'): return "Ticker-Daten derzeit nicht verfügbar."
        
        valid_pairs = []
        for pair_name, data in res['result'].items():
            if pair_name.endswith(fiat) or pair_name.endswith(f"Z{fiat}"):
                c, o, v = float(data['c'][0]), float(data['o']), float(data['v'][1])
                if (c * v) >= 1000000 and o > 0:
                    pct = ((c - o) / o) * 100
                    base_asset = pair_name.replace(fiat, "").replace(f"Z{fiat}", "")
                    valid_pairs.append({'name': ECHTE_NAMEN.get(base_asset, base_asset.replace('XX', 'X')), 'pct': pct})
        
        valid_pairs.sort(key=lambda x: x['pct'], reverse=True)
        top_10, flop_10 = valid_pairs[:10], sorted(valid_pairs[-10:], key=lambda x: x['pct']) 
        
        ticker_items = ["🔥 TOP 10 GEWINNER:"] + [f"🟢 {item['name']}: +{item['pct']:.2f}%" for item in top_10] + ["  |  🩸 TOP 10 VERLIERER:"] + [f"🔴 {item['name']}: {item['pct']:.2f}%" for item in flop_10]
        return " &nbsp;&nbsp;&nbsp;&nbsp; ".join(ticker_items)
    except: return "Ticker Offline"

# ==========================================
# 🎛️ EINSTELLUNGEN & SEITENLEISTE
# ==========================================
with st.sidebar.expander("📚 system-handbuch & legende", expanded=False):
    st.markdown("""
    **Signal-Farben (Regime):**
    *   ⚪ **Neutral:** Abwarten.
    *   🥶 **Blauer Diamant (Crash-Zone):** RSI < 30. Absolute Panik am Markt.
    *   🟢 **Grünes Dreieck (Trend-Dip):** RSI < 35 & Kurs über der roten SMA-Trendlinie. 
    *   ❌ **Rotes X (Verkauf):** RSI > 75 (Überhitzt) oder Kurs fällt unter die Trendlinie.
    
    **Die DCA-Regel (Nachkaufen):**
    Nutze den Nachkauf-Simulator nur zur Berechnung des Break-Even. Kaufe niemals stur in einen Abwärtstrend, sondern warte auf ein System-Go.
    """)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ system-einstellungen")

if st.sidebar.button("🔄 alles auf werkseinstellungen (Löscht Tresor!)"):
    st.session_state.clear()
    if os.path.exists(SPEICHER_DATEI): os.remove(SPEICHER_DATEI)
    st.rerun()

st.sidebar.markdown("---")

# Format-Umschalter
format_optionen = ["International (75,000.34)", "Deutsch (75.000,34)"]
gewaehltes_format = st.sidebar.selectbox("🔢 zahlenformat:", format_optionen, index=format_optionen.index(st.session_state.zahlen_format))
st.session_state.zahlen_format = gewaehltes_format

zeitzonen_optionen = {
    "deutschland (berlin / mez)": "Europe/Berlin", "england (london / gmt)": "Europe/London",
    "schweiz (zürich / cet)": "Europe/Zurich", "usa (new york / est)": "America/New_York", "japan (tokyo / jst)": "Asia/Tokyo"
}
tz_keys = list(zeitzonen_optionen.keys())
gewaehlte_tz_label = st.sidebar.selectbox("🌍 lokale zeitzone:", tz_keys, index=tz_keys.index(st.session_state.tz_wahl))
st.session_state.tz_wahl = gewaehlte_tz_label
aktuelle_zeitzone = ZoneInfo(zeitzonen_optionen[gewaehlte_tz_label])

FIAT_SYMBOLE = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "chf", "CAD": "ca$", "AUD": "au$", "JPY": "¥"}
fiat_keys = list(FIAT_SYMBOLE.keys())
basis_waehrung = st.sidebar.selectbox("💵 fiat-währung:", fiat_keys, index=fiat_keys.index(st.session_state.fiat_wahl))
st.session_state.fiat_wahl = basis_waehrung
w_symbol = FIAT_SYMBOLE.get(basis_waehrung, basis_waehrung)

st.sidebar.markdown("---")
st.sidebar.header("🎛️ deine watchlist")

auswahl = st.sidebar.multiselect(
    "währungen suchen/hinzufügen:", 
    options=list(ALLE_COINS_DICT.keys()), 
    default=[c for c in st.session_state.meine_basis_coins if c in ALLE_COINS_DICT],
    format_func=lambda x: ALLE_COINS_DICT.get(x, x)
)

if auswahl != st.session_state.meine_basis_coins:
    st.session_state.meine_basis_coins = list(dict.fromkeys(auswahl))
    speichere_daten(st.session_state.vault, st.session_state.meine_basis_coins)
    st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 🗄️ DER ISOLIERTE EINGABE-TRESOR (Speichert lokal)
# ==========================================
st.sidebar.subheader("💼 tresor & bestände")

tresor_coin = st.sidebar.selectbox(
    "Für welchen Coin möchtest du Daten eintragen?", 
    st.session_state.meine_basis_coins,
    format_func=lambda x: ALLE_COINS_DICT.get(x, x)
) if len(st.session_state.meine_basis_coins) > 0 else None

if tresor_coin:
    gespeichert = st.session_state.vault.get(tresor_coin, {
        "menge": 0.0, "kaufpreis": 0.0, "investition": 300.0, "ziel": 10.0, "stop": 3.0, "timestamp": "Noch nicht gespeichert"
    })

    with st.sidebar.form(key=f"form_{tresor_coin}"):
        st.caption(f"Letzte Speicherung: {gespeichert['timestamp']}")
        # format="%0.8f" erzwingt die hohe Genauigkeit in der Eingabe (bis 8 Stellen)
        menge = st.number_input("Bestand (Stück)", min_value=0.0, value=float(gespeichert["menge"]), step=0.001, format="%0.8f")
        kaufpreis = st.number_input(f"Kaufkurs ({w_symbol})", min_value=0.0, value=float(gespeichert["kaufpreis"]), step=0.1, format="%0.8f")
        st.markdown("---")
        investition = st.number_input("Geplante Neu-Investition", min_value=10.0, value=float(gespeichert["investition"]), step=50.0, format="%0.2f")
        ziel = st.number_input("Ziel-Take-Profit (%)", min_value=1.0, value=float(gespeichert["ziel"]), step=1.0, format="%0.2f")
        stop = st.number_input("Individueller Stop-Loss (%)", min_value=0.1, value=float(gespeichert["stop"]), step=0.5, format="%0.2f")
        
        submit = st.form_submit_button(f"💾 Werte für {get_clean_name(tresor_coin)} dauerhaft versiegeln")
        
        if submit:
            st.session_state.vault[tresor_coin] = {
                "menge": menge, "kaufpreis": kaufpreis, "investition": investition, 
                "ziel": ziel, "stop": stop, "timestamp": datetime.now(aktuelle_zeitzone).strftime('%H:%M:%S')
            }
            speichere_daten(st.session_state.vault, st.session_state.meine_basis_coins)
            st.rerun()

st.sidebar.markdown("---")

# ==========================================
# HAUPTBEREICH
# ==========================================
st.title("🚀 krypto-steuerzentrale | live-radar")

ticker_text = fetch_global_ticker(st.session_state.fiat_wahl)
st.markdown(f"<marquee style='font-size: 15px; font-weight: bold; color: #d4d4d4; background-color: #1e1e1e; padding: 6px; border-radius: 5px; border: 1px solid #333;'>{ticker_text}</marquee>", unsafe_allow_html=True)

with st.expander("🌍 weltuhren & börsen-öffnungszeiten", expanded=True):
    col_u1, col_u2, col_u3, col_u4 = st.columns(4)
    col_u1.metric("🗽 New York (Wall Street)", f"{datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M')} Uhr")
    col_u1.caption("Handelszeit: 15:30 - 22:00 MEZ")
    
    col_u2.metric("🎡 London (LSE)", f"{datetime.now(ZoneInfo('Europe/London')).strftime('%H:%M')} Uhr")
    col_u2.caption("Handelszeit: 09:00 - 17:30 MEZ")
    
    col_u3.metric("🥨 Berlin/Zürich", f"{datetime.now(ZoneInfo('Europe/Berlin')).strftime('%H:%M')} Uhr")
    col_u3.caption("Handelszeit: 09:00 - 17:30 MEZ")
    
    col_u4.metric("🗼 Tokyo (TSE)", f"{datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%H:%M')} Uhr")
    col_u4.caption("Handelszeit: 02:00 - 08:00 MEZ")
    
    st.markdown("*Die Krypto-Märkte laufen 24/7, aber das größte institutionelle Volumen (Smart Money) drängt in den Markt, wenn die traditionellen Aktienbörsen öffnen.*")

col_m1, col_m2 = st.columns([2, 5])
with col_m1:
    if st.button("☑️ Alle Charts aufklappen"):
        for c in st.session_state.meine_basis_coins: st.session_state[f"chk_{c}"] = True
        st.rerun()
with col_m2:
    if st.button("🔲 Alle Charts zuklappen"):
        for c in st.session_state.meine_basis_coins: st.session_state[f"chk_{c}"] = False
        st.rerun()

# ==========================================
# MODUL 2: DAS FRAGMENTIERTE COCKPIT
# ==========================================
@st.fragment(run_every=300)
def live_radar_cockpit():
    st.write(f"🔄 **autopilot aktiv:** (zuletzt lautlos aktualisiert: {datetime.now(aktuelle_zeitzone).strftime('%H:%M:%S')})")
    st.markdown("---")

    for i, basis_coin in enumerate(st.session_state.meine_basis_coins):
        c_data = st.session_state.vault.get(basis_coin, {
            "menge": 0.0, "kaufpreis": 0.0, "investition": 300.0, "ziel": 10.0, "stop": 3.0
        })

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
        if rsi < 30: status = "🥶 CRASH-ZONE (panik-kauf prüfen)"
        elif rsi < 35 and preis > sma: status = "🟢 KAUF-ZONE (trend-dip prüfen)"
        elif rsi >= 75: status = "🔴 VERKAUF (markt überhitzt)"
        elif preis < sma: status = "🔴 VERKAUF (trendbruch unter rote linie)"

        if status.startswith("🥶"): 
            rsi_ampel, rand_farbe, dca_icon = "🥶", "#0088ff", "🥶"
        elif status.startswith("🟢"): 
            rsi_ampel, rand_farbe, dca_icon = "🟢", "#00cc66", "🟢"
        elif rsi >= 75 or status.startswith("🔴"): 
            rsi_ampel, rand_farbe, dca_icon = "🔴", "#ff4d4d", "🔴"
        else: 
            rsi_ampel, rand_farbe, dca_icon = "⚪", "#555555", "⚪"
        
        dezimalstellen = 6 if preis < 1.0 else 2

        col_k1, col_k2, col_k3, col_k4 = st.columns([2.5, 2, 1.5, 3])
        
        with col_k1:
            st.markdown(f"### {anzeige_name_sauber}<br><span style='font-size:14px; color:#888888;'>ping: {ping_zeit}</span>", unsafe_allow_html=True)
        with col_k2:
            st.metric(label=f"live-kurs ({st.session_state.fiat_wahl})", value=f"{formatiere_zahl(preis, dezimalstellen)} {w_symbol}")
        with col_k3:
            st.metric(label=f"rsi (puls)", value=f"{rsi:.1f} {rsi_ampel}")
        
        with col_k4:
            st.markdown("<br>", unsafe_allow_html=True)
            nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
            with nav_col1:
                if i > 0 and st.button("🔝", key=f"top_{basis_coin}", help="Sofort auf Platz 1 setzen"):
                    st.session_state.meine_basis_coins.remove(basis_coin)
                    st.session_state.meine_basis_coins.insert(0, basis_coin)
                    speichere_daten(st.session_state.vault, st.session_state.meine_basis_coins)
                    st.rerun()
            with nav_col2:
                if i > 0 and st.button("⬆️", key=f"up_{basis_coin}"):
                    st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i-1] = st.session_state.meine_basis_coins[i-1], st.session_state.meine_basis_coins[i]
                    speichere_daten(st.session_state.vault, st.session_state.meine_basis_coins)
                    st.rerun()
            with nav_col3:
                if i < len(st.session_state.meine_basis_coins) - 1 and st.button("⬇️", key=f"down_{basis_coin}"):
                    st.session_state.meine_basis_coins[i], st.session_state.meine_basis_coins[i+1] = st.session_state.meine_basis_coins[i+1], st.session_state.meine_basis_coins[i]
                    speichere_daten(st.session_state.vault, st.session_state.meine_basis_coins)
                    st.rerun()

        if f"chk_{basis_coin}" not in st.session_state: st.session_state[f"chk_{basis_coin}"] = False
        is_open = st.checkbox(f"📊 Chart & Risikomanagement für {anzeige_name_sauber.split(' (')[0]} einblenden", key=f"chk_{basis_coin}")

        if is_open:
            st.markdown(f"""<div style="border-left: 3px solid {rand_farbe}; padding-left: 15px; margin-bottom: 20px;">""", unsafe_allow_html=True)
            
            if c_data['menge'] > 0:
                st.success(f"💼 **Dein Bestand im Tresor:** {formatiere_zahl(c_data['menge'], 4)} Stück (Kaufkurs: {formatiere_zahl(c_data['kaufpreis'], dezimalstellen)} {w_symbol})")
                aktueller_wert = c_data['menge'] * preis
                investiert = c_data['menge'] * c_data['kaufpreis']
                pnl = aktueller_wert - investiert
                pnl_pct = (pnl / investiert) * 100 if investiert > 0 else 0
                
                zusatz_menge = c_data['investition'] / preis if preis > 0 else 0
                neue_gesamtmenge = c_data['menge'] + zusatz_menge
                neues_investment = investiert + c_data['investition']
                neuer_durchschnitt = neues_investment / neue_gesamtmenge if neue_gesamtmenge > 0 else 0
                trailing_stop = preis * (1 - (c_data['stop'] / 100))
                
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Aktueller Wert", f"{formatiere_zahl(aktueller_wert, 2)} {w_symbol}")
                col_p2.metric("Gewinn / Verlust", f"{formatiere_zahl(pnl, 2)} {w_symbol}", f"{pnl_pct:.2f}%")
                col_p3.metric(f"🚨 Trailing-Stop (-{c_data['stop']}%)", f"{formatiere_zahl(trailing_stop, dezimalstellen)} {w_symbol}")
                
                dca_html = f"""<div style="background-color: #1a1a1a; border: 2px solid {rand_farbe}; border-radius: 8px; padding: 15px; margin-bottom: 20px;"><span style="font-size: 15px; color: #e0e0e0; line-height: 1.5;">{dca_icon} <b>Nachkauf-Simulation (DCA):</b> Wenn du jetzt {formatiere_zahl(c_data['investition'], 2)} {w_symbol} investierst, sinkt dein Durchschnitts-Kaufpreis von <b>{formatiere_zahl(c_data['kaufpreis'], dezimalstellen)} {w_symbol}</b> auf <b>{formatiere_zahl(neuer_durchschnitt, dezimalstellen)} {w_symbol}</b>.</span></div>"""
                st.markdown(dca_html, unsafe_allow_html=True)

            col_d1, col_d2 = st.columns([1, 2])
            with col_d1:
                st.info(f"**signal: {status}**")
                st.markdown(f"**order-rechner (Neu-Einstieg für {formatiere_zahl(c_data['investition'], 2)} {w_symbol}):**")
                coins_gekauft = c_data['investition'] / preis if preis > 0 else 0
                limit_stop_preis = preis * (1 - (c_data['stop'] / 100))
                verlust = c_data['investition'] - (coins_gekauft * limit_stop_preis)
                ziel_preis = preis * (1 + (c_data['ziel'] / 100))
                gewinn = (coins_gekauft * ziel_preis) - c_data['investition']
                
                st.markdown(f"- 🪙 **menge:** {formatiere_zahl(coins_gekauft, 4)} stück")
                st.markdown(f"- 🛑 **stop (-{c_data['stop']}%):** limit bei **{formatiere_zahl(limit_stop_preis, dezimalstellen)} {w_symbol}** (-{formatiere_zahl(verlust, 2)} {w_symbol})")
                st.markdown(f"- 🎯 **ziel (+{c_data['ziel']}%):** limit bei **{formatiere_zahl(ziel_preis, dezimalstellen)} {w_symbol}** (+{formatiere_zahl(gewinn, 2)} {w_symbol})")
                st.markdown("<br>", unsafe_allow_html=True)
                
                if c_data['stop'] <= volatilitaet_14:
                    st.warning(f"⚠️ **Volatilitäts-Warnung:** {anzeige_name_sauber.split(' (')[0]} schwankt im Schnitt um **{volatilitaet_14:.1f}%**. Dein Stop ({c_data['stop']}%) ist zu eng.")
                else:
                    st.success(f"🛡️ **Risiko-Check:** Dein Stop ({c_data['stop']}%) liegt sicher außerhalb der normalen Schwankung ({volatilitaet_14:.1f}%).")

            with col_d2:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['close'], mode='lines', line=dict(color='#4da6ff', width=2), name='kurs', hovertemplate=f'<b>kurs:</b> %{{y:.{dezimalstellen}f}} {w_symbol}<br><b>zeit:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'))
                fig.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['sma_200'], mode='lines', line=dict(color='#ff4d4d', width=2, dash='dash'), name='sma 200', hovertemplate=f'<b>trend-grenze:</b> %{{y:.{dezimalstellen}f}} {w_symbol}<br><b>zeit:</b> %{{x|%d.%m. - %H:%M}}<extra></extra>'))
                
                crash_signale = df_live[df_live['rsi'] < 30]
                trend_signale = df_live[(df_live['rsi'] < 35) & (df_live['close'] > df_live['sma_200']) & (df_live['rsi'] >= 30)]
                verkauf_signale = df_live[(df_live['rsi'] >= 75) | (df_live['close'] < df_live['sma_200'])]

                fig.add_trace(go.Scatter(x=crash_signale['timestamp'], y=crash_signale['close'], mode='markers', marker=dict(color='#0088ff', size=10, symbol='diamond'), name='Crash-Signal'))
                fig.add_trace(go.Scatter(x=trend_signale['timestamp'], y=trend_signale['close'], mode='markers', marker=dict(color='#00cc66', size=10, symbol='triangle-up'), name='Trend-Dip'))
                fig.add_trace(go.Scatter(x=verkauf_signale['timestamp'], y=verkauf_signale['close'], mode='markers', marker=dict(color='red', size=8, symbol='x'), name='Verkauf-Signal'))
                
                fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(range=[df_live['timestamp'].iloc[-100], df_live['timestamp'].iloc[-1] + pd.Timedelta(hours=48)], showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333333'), showlegend=False, height=200, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{basis_coin}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

live_radar_cockpit()
