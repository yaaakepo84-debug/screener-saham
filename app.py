import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- PAGE CONFIG ---
st.set_page_config(page_title="IDX Pro Stock Dashboard", layout="wide")

# Custom Styling Dark Mode Dashboard
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

st.title("📊 PRO Stock Screener Dashboard")
st.caption("Auto-Fetch Seluruh Saham BEI + IPO Terbaru — Dashboard Card Format")

# --- AUTO-FETCH SELURUH SAHAM IDX TERBARU ---
@st.cache_data(ttl=86400) # Simpan daftar saham selama 24 jam
def get_all_idx_tickers():
    tickers = []
    try:
        url = "https://id.wikipedia.org/wiki/Daftar_perusahaan_yang_tercatat_di_Bursa_Efek_Indonesia"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        tables = soup.find_all('table', {'class': 'wikitable'})
        for table in tables:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if cols:
                    code = cols[0].text.strip()
                    if len(code) == 4 and code.isalpha():
                        tickers.append(code)
    except Exception:
        pass
    
    # Fallback & IPO Terbaru (WBSA, BREN, CUAN, dll)
    known_recent_ipo = [
        "WBSA", "CUAN", "BREN", "AMMN", "PANI", "HUMI", "STRK", "DOOH", "KAYU", "GTRA", 
        "FWCT", "NINE", "OASA", "VKTR", "BIPI", "COAL", "MEDC", "BRMS", "PSAB", "BUMI"
    ]
    all_combined = list(dict.fromkeys(known_recent_ipo + tickers))
    return all_combined

ALL_BEI_TICKERS = get_all_idx_tickers()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Setting Dashboard")

# Fitur Tambah Saham Manual Tambahan
custom_input = st.sidebar.text_input("Tambah Saham Manual Spesifik (Pisah Koma):", value="WBSA")
custom_list = [x.strip().upper() for x in custom_input.split(",") if x.strip()]

# Gabungkan Input Manual + Seluruh Saham BEI (Anti-Duplikat)
FINAL_TICKER_LIST = list(dict.fromkeys(custom_list + ALL_BEI_TICKERS))

st.sidebar.info(f"Total Saham Terdeteksi: **{len(FINAL_TICKER_LIST)} Saham**")

scan_limit = st.sidebar.slider("Jumlah Saham Yang Di-scan:", min_value=10, max_value=len(FINAL_TICKER_LIST), value=300, step=25)
min_price = st.sidebar.number_input("Harga Minimum (Rp):", value=50, step=10)
max_price = st.sidebar.number_input("Harga Maksimum (Rp):", value=2000, step=50)

tp1_pct = st.sidebar.slider("TP 1 (%):", 1.0, 10.0, 3.0, 0.5)
sl_pct = st.sidebar.slider("SL (%):", 1.0, 7.0, 2.5, 0.5)

@st.cache_data(ttl=300)
def fetch_data(symbol):
    ticker = f"{symbol}.JK" if not symbol.endswith(".JK") else symbol
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 2:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['Vol_MA'] = df['Volume'].rolling(min(10, len(df))).mean()
        df['Change_%'] = df['Close'].pct_change() * 100
        return df
    except Exception:
        return None

if st.button(f"🚀 Scan & Generate Dashboard ({scan_limit} Saham BEI)", use_container_width=True):
    results_mom = []
    results_breakout = []
    results_value = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    selected_tickers = FINAL_TICKER_LIST[:scan_limit]
    total_tickers = len(selected_tickers)
    
    for i, symbol in enumerate(selected_tickers):
        status_text.text(f"Scanning ({i+1}/{total_tickers}): {symbol}")
        progress_bar.progress((i + 1) / total_tickers)
        
        df = fetch_data(symbol)
        if df is None:
            continue
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        close = float(latest['Close'])
        change = float(latest['Change_%']) if pd.notnull(latest['Change_%']) else 0.0
        vol = int(latest['Volume'])
        vol_ma = float(latest['Vol_MA']) if latest['Vol_MA'] > 0 else 1
        vol_ratio = vol / vol_ma
        
        if not (min_price <= close <= max_price):
            continue
            
        card_data = {
            "ticker": symbol.replace(".JK", ""),
            "close": int(close),
            "change": round(change, 2),
            "vol_ratio": round(vol_ratio, 2),
            "tp1": int(close * (1 + tp1_pct / 100)),
            "sl": int(close * (1 - sl_pct / 100)),
            "entry": f"{int(close * 0.99)}-{int(close)}"
        }
        
        # Kategori 1: Momentum Scalping
        if change > 2 and vol_ratio > 1.2:
            card_data["score"] = int(70 + (change * 2))
            card_data["reason"] = "Momentum volume & harga naik pesat."
            results_mom.append(card_data)
            
        # Kategori 2: Breakout High
        elif close > float(prev['High']):
            card_data["score"] = int(65 + (vol_ratio * 5))
            card_data["reason"] = "Breakout candle high hari sebelumnya."
            results_breakout.append(card_data)
            
        # Kategori 3: Base / Support Murah
        else:
            card_data["score"] = int(60 + (vol_ratio * 3))
            card_data["reason"] = "Area konsolidasi support & likuid."
            results_value.append(card_data)

    status_text.success("✅ Auto-scan seluruh saham selesai!")
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
            <div><b>Entry:</b> {item['entry']}</div>
            <div><b>Vol Spike:</b> {item['vol_ratio']}x</div>
        </div>
        
        <div class="metric-container">
            <div style="color:#3fb950;"><b>TP1:</b> Rp {item['tp1']}</div>
            <div style="color:#f85149;"><b>SL:</b> Rp {item['sl']}</div>
        </div>
        
        <p style="font-size:0.8rem; color:#8b949e; margin-top:8px;">
            💡 <b>Kenapa Masuk:</b> {item['reason']}
        </p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- SHOW DASHBOARD COLUMNS ---
if 'data_mom' in st.session_state:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("⚡ Technical Momentum")
        st.caption("Trending kuat — cocok untuk scalping cepat")
        for item in st.session_state['data_mom']:
            render_card(item)
            
    with col2:
        st.subheader("🚀 Breakout High")
        st.caption("Potensi penguatan melanjut breakout")
        for item in st.session_state['data_break']:
            render_card(item)
            
    with col3:
        st.subheader("💎 Near Support / Base")
        st.caption("Saham murah area support — Risk/Reward menarik")
        for item in st.session_state['data_val']:
            render_card(item)
