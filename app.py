import streamlit as st
import yfinance as yf
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="IDX Stock Dashboard PRO", layout="wide")

# Styling Dark Mode Dashboard
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .card-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .badge-score {
        background-color: #1f6feb;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        float: right;
    }
    .green-text { color: #3fb950; font-weight: bold; }
    .red-text { color: #f85149; font-weight: bold; }
    .metric-container {
        display: flex;
        justify-content: space-between;
        background: #0d1117;
        padding: 8px;
        border-radius: 8px;
        margin: 8px 0;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 PRO Stock Dashboard (Auto Candle SL/TP)")
st.caption("SL diset dari Low Candle | TP diset dari High Candle | Full IDX & IPO Screener")

# --- MASTER DAFTAR TICKER IDX LENGKAP (INCL. IPO TERBARU) ---
ALL_IDX_TICKERS = [
    # IPO Terbaru & Saham Ramai
    "WBSA", "CUAN", "BREN", "AMMN", "PANI", "HUMI", "STRK", "DOOH", "KAYU", "GTRA",
    "FWCT", "NINE", "OASA", "VKTR", "BIPI", "COAL", "MEDC", "BRMS", "PSAB", "BUMI",
    "AADI", "ADMR", "MBSS", "LSIP", "MLPT", "JSPT", "GOTO", "BSBK", "WIFI", "ANTM",
    "BBCA", "BBRI", "BMRI", "BBNI", "ASII", "TLKM", "PGAS", "ENRG", "DEWA", "RAJA",
    "CGAS", "TOSK", "SMGA", "MSJA", "ALII", "MKAP", "RGAS", "BHER", "MREI", "SAGA",
    "NICE", "NEST", "BABY", "HYGN", "AREA", "SOLA", "PART", "BATR", "MANG", "FMAX",
    # Saham IDX Reguler
    "AALI", "ABBA", "ABDA", "ABMM", "ACES", "ACST", "ADEL", "ADHI", "ADCP", "ADRO", 
    "AGAR", "AGII", "AGRO", "AGRS", "AHAP", "AIMS", "AISA", "AKRA", "AKSI", "ALDO", 
    "AMAG", "AMAR", "AMFG", "AMIN", "AMRT", "ANDI", "APEX", "APIC", "APLN", "ARCI", 
    "ARNA", "ARTA", "ASGR", "ASJT", "ASRI", "ASRM", "AUTO", "BABP", "BACA", "BAJA", 
    "BBHI", "BBKP", "BBLD", "BBMD", "BBRM", "BBTN", "BCAT", "BCIC", "BDMN", "BEBS", 
    "BEST", "BFIN", "BGTG", "BHIT", "BIRD", "BISI", "BJBR", "BJTM", "BKSL", "BKSW", 
    "BLTA", "BLTZ", "BMAS", "BMTR", "BNBR", "BNGA", "BNII", "BNLI", "BOGA", "BOLT", 
    "BOSS", "BSDE", "BSIM", "BTPS", "BVIC", "BRPT", "BUKA", "CASA", "CAST", "CEKA", 
    "CENT", "CFIN", "CINT", "CITA", "CITY", "CLPI", "CMNP", "CMRY", "CNTX", "CPIN", 
    "CPRO", "CSAP", "CSIS", "CSRA", "CTRA", "DART", "DGGN", "DILD", "DIVA", "DKFT", 
    "DLTA", "DMAS", "DNAR", "DNET", "DOID", "DRMA", "DSFI", "DSNG", "DSSD", "DUTI", 
    "DVLA", "ECII", "ELSA", "EMTK", "EPMT", "ERAA", "ERTX", "ESSA", "ESTI", "ETWA", 
    "EXCL", "FAST", "FASW", "FIRE", "FMII", "FORU", "FPNI", "FREN", "GAAA", "GDST", 
    "GEMS", "GGRM", "GIAA", "GJTL", "GLOB", "GLVA", "GOOD", "GPRA", "GSMF", "GTBO", 
    "GWSA", "GZCO", "HATM", "HDFA", "HDTX", "HEAL", "HERO", "HEXA", "HITS", "HMSP", 
    "HOKI", "HOME", "HOPE", "HRTA", "HRUM", "IATA", "IBST", "ICBP", "ICON", "IDPR", 
    "IGAR", "IIKP", "IKAI", "IKBI", "IMAS", "INAF", "INCF", "INCI", "INDF", "INDY", 
    "INKP", "INPC", "INPP", "INRU", "INTD", "INTP", "IPCC", "IPCM", "IPOL", "IPTV", 
    "IRRA", "ISAT", "ISSP", "ITMG", "JARR", "JAST", "JECC", "JKSW", "JPFA", "JRPT", 
    "JSMR", "JTPE", "KBLI", "KBLM", "KBAG", "KARW", "KDSI", "KIAS", "KICI", "KIJA", 
    "KKGI", "KLBF", "KMDS", "KOBX", "KOIN", "KAEF", "KPAL", "KPIG", "KRAS", "KREN", 
    "LCGP", "LEAD", "LION", "LMPI", "LMSH", "LPCK", "LPGI", "LPLI", "LPKR", "LPCR", 
    "LRNA", "LTLS", "LUCK", "MAIN", "MAMI", "MAPA", "MAPI", "MARI", "MASA", "MBAP", 
    "MBTO", "MCAS", "MCOL", "MDKA", "MDKI", "MDLN", "MDRN", "MEGA", "MERK", "METR", 
    "MFIN", "MIKA", "MINA", "MIRA", "MITI", "MKPI", "MLBI", "MLIA", "MNCN", "MPMX", 
    "MPPA", "MRAT", "MSIN", "MTDL", "MTFN", "MTLA", "MTPS", "MYOR", "MYRX", "MYTX", 
    "NELY", "NFCX", "NICK", "NICL", "NIKL", "NIPS", "NIRO", "NISP", "NOBU", "NRCA", 
    "OBMD", "PALM", "PANR", "PANS", "PBID", "PBRX", "PDES", "PEHA", "PGJO", "PGLI", 
    "PJAA", "PKPK", "PLIN", "PMJS", "PNBN", "PNBS", "PNIN", "PNLF", "POLI", "POLL", 
    "POLY", "POOL", "PORT", "POWR", "PPGL", "PPRO", "PRDA", "PRIM", "PSDN", "PSGO", 
    "PTBA", "PTDU", "PTPP", "PTRO", "PTSN", "PUDP", "PWON", "PYFA", "RAAM", "RALS", 
    "RANC", "RBMS", "RDTX", "REAL", "RELI", "RICY", "RIGS", "RIMO", "ROTI", "RODA", 
    "SAME", "SAMF", "SAPX", "SBAT", "SCCO", "SCMA", "SCNP", "SDMU", "SDPC", "SFA", 
    "SGER", "SGMW", "SGRO", "SHID", "SILO", "SIMP", "SIPD", "SKBM", "SKLT", "SKYB", 
    "SLIS", "SMBR", "SMCB", "SMDM", "SMDR", "SMGR", "SMKL", "SMMA", "SMRA", "SMRU", 
    "SMSM", "SOCI", "SOFA", "SOHO", "SONA", "SOSI", "SRIL", "SRSN", "SRTG", "SSIA", 
    "SSMS", "SSSS", "SSTC", "STAA", "STAT", "STTP", "SUGI", "SULI", "SUPR", "SURE", 
    "TALF", "TARA", "TAXI", "TBIG", "TBLA", "TBMS", "TCID", "TCMM", "TELE", "TFCO", 
    "TGRA", "TIFA", "TINS", "TIRA", "TKIM", "TMAS", "TMPO", "TNCA", "TOBA", "TOTL", 
    "TOWR", "TPIA", "TPMA", "TRAM", "TRIM", "TRIN", "TRIO", "TRST", "TRUK", "TSPC", 
    "TUGU", "ULTJ", "UNIC", "UNIQ", "UNVR", "URBN", "VRNA", "WICC", "WIIM", "WINS", 
    "WMPP", "WOOD", "WOWS", "WSBP", "WSKT", "WTON", "YPAS", "YULE", "ZBRA", "ZINC", "ZONE"
]

# Unikkan Ticker
ALL_TICKERS = list(dict.fromkeys(ALL_IDX_TICKERS))

# --- SIDEBAR ---
st.sidebar.header("⚙️ Setting Scan Saham")

# Input Saham Manual Jika Ada Saham Hari Ini Yang Baru Listing
custom_input = st.sidebar.text_input("Tambah Saham Spesifik (Pisah Koma):", value="")
if custom_input:
    custom_list = [x.strip().upper() for x in custom_input.split(",") if x.strip()]
    FINAL_TICKERS = list(dict.fromkeys(custom_list + ALL_TICKERS))
else:
    FINAL_TICKERS = ALL_TICKERS

scan_limit = st.sidebar.slider("Jumlah Saham Yang Di-scan:", min_value=20, max_value=len(FINAL_TICKERS), value=150, step=20)
min_price = st.sidebar.number_input("Harga Minimum (Rp):", value=50, step=10)
max_price = st.sidebar.number_input("Harga Maksimum (Rp):", value=3000, step=100)

@st.cache_data(ttl=300)
def fetch_data(symbol):
    ticker = f"{symbol}.JK" if not symbol.endswith(".JK") else symbol
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 3:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['Vol_MA'] = df['Volume'].rolling(min(10, len(df))).mean()
        df['Change_%'] = df['Close'].pct_change() * 100
        return df
    except Exception:
        return None

if st.button(f"🚀 Scan Dashboard ({scan_limit} Saham BEI)", use_container_width=True):
    results_mom = []
    results_breakout = []
    results_value = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    selected_tickers = FINAL_TICKERS[:scan_limit]
    total_tickers = len(selected_tickers)
    
    for i, symbol in enumerate(selected_tickers):
        status_text.text(f"Scanning ({i+1}/{total_tickers}): {symbol}")
        progress_bar.progress((i + 1) / total_tickers)
        
        df = fetch_data(symbol)
        if df is None:
            continue
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) > 2 else prev
        
        close = float(latest['Close'])
        change = float(latest['Change_%']) if pd.notnull(latest['Change_%']) else 0.0
        vol = int(latest['Volume'])
        vol_ma = float(latest['Vol_MA']) if latest['Vol_MA'] > 0 else 1
        vol_ratio = vol / vol_ma
        
        if not (min_price <= close <= max_price):
            continue
            
        # HITUNG SL & TP OTOMATIS DARI CANDLE (Support & Resistance)
        # SL: Gunakan Low candle kemarin (atau Low 2 hari terakhir mana yang paling rendah)
        sl_price = int(min(float(prev['Low']), float(latest['Low'])))
        # Jika SL ternyata sama atau lebih tinggi dari close, pasang 2% di bawah close sebagai buffer
        if sl_price >= close:
            sl_price = int(close * 0.98)
            
        # TP1: Gunakan High candle kemarin/resistance terdekat
        tp1_price = int(max(float(prev['High']), float(latest['High'])))
        # Jika TP ternyata kurang dari close, proyeksi TP ke atas berdasarkan resisten sebelumnya
        if tp1_price <= close:
            tp1_price = int(close * 1.04)
            
        card_data = {
            "ticker": symbol.replace(".JK", ""),
            "close": int(close),
            "change": round(change, 2),
            "vol_ratio": round(vol_ratio, 2),
            "tp1": tp1_price,
            "sl": sl_price,
            "entry": f"{int(sl_price + (close - sl_price)*0.5)}-{int(close)}"
        }
        
        # Pengelompokan Kategori Card
        if change > 2 and vol_ratio > 1.2:
            card_data["score"] = int(70 + (change * 2))
            card_data["reason"] = f"Volume Spike ({round(vol_ratio,1)}x) & Momentum Naik."
            results_mom.append(card_data)
        elif close > float(prev['High']):
            card_data["score"] = int(65 + (vol_ratio * 5))
            card_data["reason"] = f"Breakout Candle High Kemarin (Rp {int(prev['High'])})."
            results_breakout.append(card_data)
        else:
            card_data["score"] = int(60 + (vol_ratio * 3))
            card_data["reason"] = f"Area Konsolidasi Support Candle (Low Rp {sl_price})."
            results_value.append(card_data)

    status_text.success("✅ Auto-scan Selesai!")
    progress_bar.empty()
    
    st.session_state['data_mom'] = results_mom
    st.session_state['data_break'] = results_breakout
    st.session_state['data_val'] = results_value

# Helper function render card
def render_card(item):
    change_color = "green-text" if item["change"] >= 0 else "red-text"
    change_sign = "+" if item["change"] >= 0 else ""
    
    html = f"""
    <div class="card-box">
        <span class="badge-score">{item['score']} SCORE</span>
        <h3 style="margin:0; color:#58a6ff;">📌 {item['ticker']}</h3>
        <p style="margin:0; font-size: 1.2rem; font-weight:bold;">
            Rp {item['close']} <span class="{change_color}">({change_sign}{item['change']}%)</span>
        </p>
        
        <div class="metric-container">
            <div><b>Area Buy:</b> Rp {item['entry']}</div>
            <div><b>Vol Spike:</b> {item['vol_ratio']}x</div>
        </div>
        
        <div class="metric-container">
            <div style="color:#3fb950;"><b>TP (Resisten):</b> Rp {item['tp1']}</div>
            <div style="color:#f85149;"><b>SL (Support):</b> Rp {item['sl']}</div>
        </div>
        
        <p style="font-size:0.8rem; color:#8b949e; margin-top:8px;">
            💡 <b>Analisa Candle:</b> {item['reason']}
        </p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- SHOW DASHBOARD COLUMNS ---
if 'data_mom' in st.session_state:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("⚡ Technical Momentum")
        st.caption("Volume spike + trending naik pesat")
        for item in st.session_state['data_mom']:
            render_card(item)
            
    with col2:
        st.subheader("🚀 Breakout High")
        st.caption("Tembus High Candle Sebelumnya")
        for item in st.session_state['data_break']:
            render_card(item)
            
    with col3:
        st.subheader("💎 Near Support / Base")
        st.caption("Dekat Low Candle / Support Terdekat")
        for item in st.session_state['data_val']:
            render_card(item)
