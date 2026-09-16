import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="IDX OHLCV Stock Screener", layout="wide")

st.title("📈 Stock Screener OHLCV - V1")
st.caption("Screener saham berbasis pergerakan harga dan volume (OHLCV)")

# --- SIDEBAR PARAMETERS ---
st.sidebar.header("⚙️ Setting Screener")

# Input Ticker List
default_tickers = "BBCA.JK, BBRI.JK, BMRI.JK, BBNI.JK, TLKM.JK, ASII.JK, GOTO.JK, AMRT.JK, ANTM.JK, PGAS.JK"
ticker_input = st.sidebar.text_area("Daftar Ticker (Pisahkan dengan koma):", value=default_tickers, height=100)
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

# Timeframe & Period
timeframe = st.sidebar.selectbox("Timeframe / Interval:", ["1d", "1h", "15m"], index=0)
period_map = {"1d": "1y", "1h": "1mo", "15m": "5d"}

# Strategy Selection
st.sidebar.subheader("🎯 Strategi Filter")
strategy = st.sidebar.radio(
    "Pilih Kondisi Screener:",
    [
        "Semua Saham (Tanpa Filter)",
        "Uptrend (Close > MA)",
        "Volume Spike (Volume > Avg Vol)",
        "Breakout High (Close > Highest High N-Days)"
    ]
)

# Dynamic Indicator Parameters
ma_period = st.sidebar.number_input("Periode Moving Average (MA):", min_value=5, max_value=200, value=20)
vol_mult = st.sidebar.slider("Volume Multiplier (x Avg Volume):", min_value=1.0, max_value=5.0, value=1.5, step=0.1)
breakout_lookback = st.sidebar.number_input("Lookback Breakout (Hari):", min_value=5, max_value=100, value=20)

# --- FUNCTION FETCH DATA & INDICATORS ---
@st.cache_data(ttl=300)
def fetch_ohlcv_data(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty or len(df) < 20:
            return None
        
        # Flatten MultiIndex Columns jika ada
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        
        # Kalkulasi Indikator Dasar
        df['MA'] = df['Close'].rolling(window=ma_period).mean()
        df['Vol_MA'] = df['Volume'].rolling(window=ma_period).mean()
        df['Prev_High_N'] = df['High'].shift(1).rolling(window=breakout_lookback).max()
        df['Change_%'] = df['Close'].pct_change() * 100
        
        return df
    except Exception:
        return None

# --- RUN SCREENER ---
if st.button("🚀 Jalankan Screener", use_container_width=True):
    results = []
    
    with st.spinner("Mengambil data & menganalisis..."):
        for symbol in tickers:
            df = fetch_ohlcv_data(symbol, period_map[timeframe], timeframe)
            if df is None:
                continue
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Pengecekan Kondisi berdasarkan Strategi
            is_match = False
            
            if strategy == "Semua Saham (Tanpa Filter)":
                is_match = True
            elif strategy == "Uptrend (Close > MA)":
                is_match = latest['Close'] > latest['MA']
            elif strategy == "Volume Spike (Volume > Avg Vol)":
                is_match = latest['Volume'] > (latest['Vol_MA'] * vol_mult)
            elif strategy == "Breakout High (Close > Highest High N-Days)":
                is_match = latest['Close'] > prev['Prev_High_N']

            if is_match:
                results.append({
                    "Ticker": symbol,
                    "Close": round(float(latest['Close']), 2),
                    "Change (%)": round(float(latest['Change_%']), 2),
                    "Volume": int(latest['Volume']),
                    f"MA {ma_period}": round(float(latest['MA']), 2),
                    "Vol Spike": round(float(latest['Volume'] / latest['Vol_MA']), 2) if latest['Vol_MA'] > 0 else 0
                })

    # Display Results
    st.session_state['results_df'] = pd.DataFrame(results)

# --- SHOW TABLE & CHART ---
if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
    res_df = st.session_state['results_df']
    st.subheader(f"📊 Hasil Screener ({len(res_df)} Saham Memenuhi Syarat)")
    st.dataframe(res_df, use_container_width=True)
    
    # Detail View / Candlestick Chart
    st.divider()
    st.subheader("🔍 Detail Candlestick Chart")
    selected_ticker = st.selectbox("Pilih Saham untuk Dilihat Chart-nya:", res_df["Ticker"].tolist())
    
    if selected_ticker:
        chart_df = fetch_ohlcv_data(selected_ticker, period_map[timeframe], timeframe)
        if chart_df is not None:
            fig = go.Figure()
            
            # Candlestick
            fig.add_trace(go.Candlestick(
                x=chart_df.index,
                open=chart_df['Open'],
                high=chart_df['High'],
                low=chart_df['Low'],
                close=chart_df['Close'],
                name="OHLC"
            ))
            
            # Line MA
            fig.add_trace(go.Scatter(
                x=chart_df.index,
                y=chart_df['MA'],
                mode='lines',
                name=f'MA {ma_period}',
                line=dict(color='orange', width=1.5)
            ))
            
            fig.update_layout(
                title=f"Chart OHLCV - {selected_ticker}",
                xaxis_rangeslider_visible=False,
                height=500,
                template="plotly_dark"
            )
            
            st.plotly_chart(fig, use_container_width=True)

elif 'results_df' in st.session_state and st.session_state['results_df'].empty:
    st.warning("Tidak ada saham yang memenuhi kriteria filter saat ini.")
          
