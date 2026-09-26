import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="IDX Trading Scanner 3 Mode", page_icon="📊", layout="wide")

st.title("📊 IDX Trading Scanner")
st.caption("Satu web • 3 mode terpisah: Watchlist Besok, BSJP, dan Scalping")

# ============================================================
# DATA UNIVERSE
# Jangan memakai Yahoo Screener untuk daftar saham karena endpoint
# screener/quote Yahoo dapat mengembalikan HTTP 401/Invalid Crumb.
# Universe diambil dari snapshot kode emiten BEI/KSEI yang dipublikasikan
# untuk riset, lalu harga historis tetap diambil via yfinance.
# ============================================================
IDX_UNIVERSE_URL = (
    "https://raw.githubusercontent.com/aryakdaniswara/idx-stock-ownership/"
    "main/data/kepemilikan_saham_20260227.csv"
)

@st.cache_data(ttl=86400, show_spinner=False)
def get_idx_tickers():
    """Ambil daftar kode saham IDX tanpa Yahoo Screener."""
    df = pd.read_csv(IDX_UNIVERSE_URL, usecols=["share_code"])
    codes = (
        df["share_code"]
        .astype(str)
        .str.upper()
        .str.strip()
        .dropna()
        .unique()
        .tolist()
    )

    # Saham IDX biasa umumnya 4 karakter. Filter simbol aneh/warrant
    # agar tidak ikut masuk ke pemanggilan harga Yahoo.
    codes = sorted({x for x in codes if x.isalpha() and 1 <= len(x) <= 5})
    return codes


# ============================================================
# HELPER TEKNIKAL
# ============================================================
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_atr(df, period=14):
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def get_ticker_frame(raw, symbol):
    """Ambil satu ticker dari hasil yf.download, aman untuk MultiIndex/non-MultiIndex."""
    if raw is None or raw.empty:
        return None

    yf_symbol = f"{symbol}.JK"

    try:
        if isinstance(raw.columns, pd.MultiIndex):
            level0 = raw.columns.get_level_values(0)
            level1 = raw.columns.get_level_values(1)

            if yf_symbol in level0:
                return raw[yf_symbol].copy()
            if yf_symbol in level1:
                return raw.xs(yf_symbol, axis=1, level=1).copy()
            return None

        return raw.copy()
    except Exception:
        return None


def clean_ohlcv(df):
    if df is None or df.empty:
        return None
    needed = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        return None
    out = df[needed].copy()
    for c in needed:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=needed)
    return out


def safe_num(x):
    try:
        return float(x) if np.isfinite(float(x)) else None
    except Exception:
        return None


# ============================================================
# MODE 1 — WATCHLIST BESOK
# Daily only. Tidak dicampur dengan logika intraday.
# ============================================================
def analyze_watchlist(symbol, data):
    """Daily watchlist dengan validasi setup fresh.

    Prinsip:
    - Setup harus masih aktif pada candle terakhir.
    - Harga tidak boleh sudah terlalu jauh meninggalkan Entry Zone.
    - TP1 tidak boleh sudah tersentuh pada sesi terakhir/sebelumnya.
    - Level resistance dihitung dari candle sebelum hari terakhir agar target
      tidak memakai high candle yang sedang dianalisis sebagai target baru.
    """
    df = clean_ohlcv(data)
    if df is None or len(df) < 70:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["VOL20"] = volume.rolling(20).mean()
    df["ATR14"] = calc_atr(df, 14)
    df["RSI14"] = calc_rsi(close, 14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    vals = [last["Close"], last["Open"], last["High"], last["Low"],
            last["MA20"], last["MA50"], last["VOL20"], last["ATR14"], last["RSI14"]]
    if not all(safe_num(x) is not None for x in vals):
        return None

    price = float(last["Close"])
    open_price = float(last["Open"])
    day_high = float(last["High"])
    ma20 = float(last["MA20"])
    ma50 = float(last["MA50"])
    vol20 = float(last["VOL20"])
    atr14 = float(last["ATR14"])
    rsi = float(last["RSI14"])

    if price <= 0 or atr14 <= 0 or vol20 <= 0:
        return None

    vol_x = float(last["Volume"]) / vol20
    bullish = price > open_price
    trend_up = price > ma20 > ma50
    trend_ok = price > ma50 and ma20 >= ma50 * 0.995

    # Semua level referensi utama memakai candle SEBELUM hari terakhir.
    # Ini mengurangi risiko target terlihat "bagus" hanya karena memakai high hari ini.
    high20_prev = float(high.iloc[-21:-1].max())
    low10_prev = float(low.iloc[-11:-1].min())
    recent_resistance = float(high.iloc[-31:-1].max())

    # Setup awal.
    near_ma20 = abs(price - ma20) / price <= 0.03
    breakout = price >= high20_prev and vol_x >= 1.15

    # PB harus benar-benar berinteraksi dengan MA20, bukan hanya kebetulan dekat.
    pb_touch = float(last["Low"]) <= ma20 * 1.02 and price >= ma20 * 0.98
    pullback = trend_ok and pb_touch and bullish and 42 <= rsi <= 68

    # REB: ada pantulan dari area MA20/support pada candle terakhir.
    rebound_touch = float(last["Low"]) <= ma20 * 1.025 and price > ma20 * 0.985
    rebound = trend_ok and rebound_touch and bullish and rsi <= 65

    if breakout:
        category = "BO"
    elif pullback:
        category = "PB"
    elif rebound:
        category = "REB"
    else:
        return None

    change = (price / float(prev["Close"]) - 1) * 100
    hot = rsi > 75 or change > 12
    if hot:
        return None

    # Jangan mengejar breakout yang sudah terlalu jauh dari level breakout.
    if category == "BO" and price > high20_prev + 0.80 * atr14:
        return None

    score = 0
    reasons = []
    if trend_up:
        score += 20
        reasons.append("trend up")
    elif trend_ok:
        score += 10
        reasons.append("di atas MA50")
    if ma20 > ma50:
        score += 15
        reasons.append("MA20 > MA50")
    if bullish:
        score += 10
        reasons.append("candle bullish")
    if vol_x >= 1:
        score += 10
        reasons.append(f"vol {vol_x:.1f}x")
    if vol_x >= 1.5:
        score += 5
    if category == "BO":
        score += 20
        reasons.append("breakout")
    elif category == "PB":
        score += 15
        reasons.append("pullback MA20")
    else:
        score += 12
        reasons.append("rebound area support")
    if 45 <= rsi <= 68:
        score += 10
    elif 40 <= rsi < 45:
        score += 5

    # Entry zone yang benar-benar berhubungan dengan setup hari terakhir.
    if category == "BO":
        entry_low = max(price, high20_prev)
        entry_high = entry_low + 0.25 * atr14
        support = max(low10_prev, high20_prev - 0.80 * atr14)
    else:
        entry_low = max(ma20 - 0.25 * atr14, low10_prev * 0.995)
        entry_high = ma20 + 0.20 * atr14
        support = min(low10_prev, ma20 - 0.50 * atr14)

        # Jika harga penutupan sudah terlalu jauh di atas zone, setup sudah lewat.
        if price > entry_high * 1.015:
            return None
        # Jika harga jatuh terlalu jauh di bawah zone, setup bukan pullback sehat lagi.
        if price < entry_low * 0.98:
            return None

    if entry_high <= entry_low:
        entry_high = entry_low + 0.20 * atr14

    sl = support - 0.30 * atr14
    if sl >= entry_low:
        sl = entry_low - 0.75 * atr14
    if sl <= entry_low * 0.90:
        sl = entry_low * 0.90

    risk = entry_low - sl
    if risk <= 0:
        return None

    # Target awal berbasis R. Resistance historis dipakai sebagai pembatas,
    # tetapi tidak boleh membuat target terlalu dekat dengan entry.
    tp1 = entry_low + 1.25 * risk
    tp2 = entry_low + 2.0 * risk
    if recent_resistance > entry_low + 0.80 * risk and recent_resistance < tp2:
        tp1 = recent_resistance

    if tp1 <= entry_low or tp2 <= tp1:
        return None

    # ===================== FRESHNESS CHECK =====================
    # Kalau TP1 yang dihitung dari setup saat ini sudah tersentuh oleh high
    # candle terakhir ATAU candle sebelumnya, setup dianggap sudah "terpakai".
    # Ini mencegah kasus seperti IKAN: TP1 kemarin sudah kena tetapi malamnya
    # masih muncul lagi dengan target yang sama.
    prev_high = float(prev["High"])
    target_already_hit = day_high >= tp1 or prev_high >= tp1
    if target_already_hit:
        return None

    # Entry juga tidak boleh sudah terlalu jauh ditinggalkan pada penutupan.
    if price > entry_high * 1.02:
        return None

    freshness = "FRESH"
    reasons.append("setup fresh")

    return {
        "Kode": symbol,
        "Tier": "A" if score >= 75 else ("B" if score >= 60 else "C"),
        "Kategori": category,
        "Status": freshness,
        "Entry Low": entry_low,
        "Entry High": entry_high,
        "TP1": tp1,
        "TP2": tp2,
        "SL": sl,
        "RR_TP1": (tp1 - entry_low) / risk,
        "RR_TP2": (tp2 - entry_low) / risk,
        "Score": score,
        "Close": price,
        "Change%": change,
        "RSI": rsi,
        "Vol x": vol_x,
        "Alasan": ", ".join(reasons),
    }


@st.cache_data(ttl=900, show_spinner=False)
def scan_daily(tickers, batch_size=80):
    rows = []
    for start in range(0, len(tickers), batch_size):
        batch = tickers[start:start + batch_size]
        try:
            raw = yf.download(
                [f"{x}.JK" for x in batch],
                period="6mo", interval="1d", auto_adjust=False,
                progress=False, threads=True, group_by="ticker",
            )
        except Exception:
            continue
        for symbol in batch:
            try:
                result = analyze_watchlist(symbol, get_ticker_frame(raw, symbol))
                if result:
                    rows.append(result)
            except Exception:
                continue
    return pd.DataFrame(rows)


# ============================================================
# MODE 2 — BSJP (BELI SORE JUAL PAGI)
# Daily sebagai filter dasar, lalu 15M untuk konfirmasi menjelang penutupan.
# BSJP = beli sore, jual pagi berikutnya. Indikator: EMA9/20, RSI14, volume, candle.
# ============================================================
def analyze_bsjp_daily(symbol, data):
    df = clean_ohlcv(data)
    if df is None or len(df) < 60:
        return None

    close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]
    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["VOL20"] = volume.rolling(20).mean()
    df["RSI14"] = calc_rsi(close, 14)
    df["ATR14"] = calc_atr(df, 14)

    last, prev = df.iloc[-1], df.iloc[-2]
    vals = [last[c] for c in ["Close", "Open", "High", "Low", "MA20", "MA50", "VOL20", "RSI14", "ATR14"]]
    if not all(safe_num(x) is not None for x in vals):
        return None

    price = float(last["Close"])
    ma20, ma50 = float(last["MA20"]), float(last["MA50"])
    vol_x = float(last["Volume"]) / float(last["VOL20"])
    rsi = float(last["RSI14"])
    atr14 = float(last["ATR14"])
    change = (price / float(prev["Close"]) - 1) * 100

    # BSJP sengaja tidak memakai breakout 20 hari sebagai syarat utama.
    # Fokus: trend sehat + likuiditas + belum terlalu panas.
    trend = price > ma20 and ma20 >= ma50 * 0.995
    not_hot = 42 <= rsi <= 70 and change <= 8
    liquid = vol_x >= 0.8
    bullish = float(last["Close"]) > float(last["Open"])

    if not (trend and not_hot and liquid):
        return None

    score = 0
    reasons = []
    if price > ma20:
        score += 20
        reasons.append("harga > MA20")
    if ma20 > ma50:
        score += 20
        reasons.append("MA20 > MA50")
    if bullish:
        score += 15
        reasons.append("candle bullish")
    if vol_x >= 1:
        score += 15
        reasons.append(f"vol {vol_x:.1f}x")
    elif vol_x >= 0.8:
        score += 8
        reasons.append(f"vol {vol_x:.1f}x")
    if 48 <= rsi <= 65:
        score += 20
        reasons.append("RSI nyaman")
    elif 42 <= rsi < 48:
        score += 10
    else:
        score += 8

    # Jangan pilih yang sudah lari terlalu jauh dari MA20.
    distance = (price / ma20 - 1) * 100
    if 0 <= distance <= 5:
        score += 10
    elif distance > 7:
        score -= 10

    if score < 60:
        return None

    entry_low = max(ma20 - 0.20 * atr14, price - 0.25 * atr14)
    entry_high = min(price + 0.15 * atr14, ma20 + 0.50 * atr14)
    if entry_high < entry_low:
        entry_high = entry_low + 0.15 * atr14

    sl = min(float(low.tail(5).min()) - 0.20 * atr14, entry_low - 0.60 * atr14)
    if sl <= 0:
        return None
    risk = entry_low - sl
    if risk <= 0:
        return None

    tp1 = entry_low + 1.0 * risk
    tp2 = entry_low + 1.6 * risk

    return {
        "Kode": symbol,
        "Score": score,
        "Close": price,
        "Entry Low": entry_low,
        "Entry High": entry_high,
        "TP1": tp1,
        "TP2": tp2,
        "SL": sl,
        "RR_TP1": (tp1 - entry_low) / risk,
        "RR_TP2": (tp2 - entry_low) / risk,
        "RSI Daily": rsi,
        "Vol Daily x": vol_x,
        "Change%": change,
        "Alasan": ", ".join(reasons),
    }


@st.cache_data(ttl=900, show_spinner=False)
def scan_bsjp_daily(tickers, batch_size=80):
    rows = []
    for start in range(0, len(tickers), batch_size):
        batch = tickers[start:start + batch_size]
        try:
            raw = yf.download(
                [f"{x}.JK" for x in batch],
                period="6mo", interval="1d", auto_adjust=False,
                progress=False, threads=True, group_by="ticker",
            )
        except Exception:
            continue
        for symbol in batch:
            try:
                result = analyze_bsjp_daily(symbol, get_ticker_frame(raw, symbol))
                if result:
                    rows.append(result)
            except Exception:
                continue
    return pd.DataFrame(rows)


def confirm_bsjp_15m(symbol, data):
    df = clean_ohlcv(data)
    if df is None or len(df) < 30:
        return None

    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["VOL20"] = df["Volume"].rolling(20).mean()
    df["RSI14"] = calc_rsi(df["Close"], 14)

    last = df.iloc[-1]
    price = safe_num(last["Close"])
    ema9 = safe_num(last["EMA9"])
    ema20 = safe_num(last["EMA20"])
    rsi = safe_num(last["RSI14"])
    vol20 = safe_num(last["VOL20"])
    volume = safe_num(last["Volume"])
    if None in [price, ema9, ema20, rsi, vol20, volume] or vol20 <= 0:
        return None

    vol_x = volume / vol20
    bullish = price > float(last["Open"])
    ready = price >= ema9 >= ema20 and rsi >= 50 and (bullish or vol_x >= 1.1)

    return {
        "15M Price": price,
        "15M EMA9": ema9,
        "15M EMA20": ema20,
        "15M RSI": rsi,
        "15M Vol x": vol_x,
        "15M Confirm": "READY" if ready else "WAIT",
    }


@st.cache_data(ttl=120, show_spinner=False)
def scan_bsjp_intraday(symbols):
    rows = []
    for symbol in symbols:
        try:
            raw = yf.download(
                f"{symbol}.JK", period="30d", interval="15m",
                auto_adjust=False, progress=False, threads=False,
            )
            conf = confirm_bsjp_15m(symbol, get_ticker_frame(raw, symbol))
            if conf:
                conf["Kode"] = symbol
                rows.append(conf)
        except Exception:
            continue
    return pd.DataFrame(rows)


# ============================================================
# MODE 3 — SCALPING
# Hanya intraday. Daily tidak dipakai untuk sinyal entry.
# 15M = arah, 5M = trigger. VWAP + EMA9/20 + RSI + volume.
# ============================================================
def intraday_metrics(data):
    df = clean_ohlcv(data)
    if df is None or len(df) < 30:
        return None

    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["VOL20"] = df["Volume"].rolling(20).mean()
    df["RSI14"] = calc_rsi(df["Close"], 14)
    df["ATR14"] = calc_atr(df, 14)

    # VWAP per sesi/hari jika index memiliki tanggal.
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    dates = pd.Series(df.index.date, index=df.index)
    cum_pv = (typical * df["Volume"]).groupby(dates).cumsum()
    cum_vol = df["Volume"].groupby(dates).cumsum().replace(0, np.nan)
    df["VWAP"] = cum_pv / cum_vol

    return df


def get_latest_day(df):
    if df is None or df.empty:
        return None
    try:
        day = df.index[-1].date()
        return df[df.index.date == day].copy()
    except Exception:
        return df.tail(80).copy()


def analyze_scalping(symbol, data15, data5):
    d15 = intraday_metrics(data15)
    d5 = intraday_metrics(data5)
    if d15 is None or d5 is None:
        return None

    d15 = get_latest_day(d15)
    d5 = get_latest_day(d5)
    if d15 is None or d5 is None or len(d15) < 5 or len(d5) < 10:
        return None

    a15 = d15.iloc[-1]
    a5 = d5.iloc[-1]

    p15 = safe_num(a15["Close"])
    ema915 = safe_num(a15["EMA9"])
    ema2015 = safe_num(a15["EMA20"])
    rsi15 = safe_num(a15["RSI14"])
    vwap15 = safe_num(a15["VWAP"])
    p5 = safe_num(a5["Close"])
    ema95 = safe_num(a5["EMA9"])
    ema205 = safe_num(a5["EMA20"])
    rsi5 = safe_num(a5["RSI14"])
    vwap5 = safe_num(a5["VWAP"])
    vol20_5 = safe_num(a5["VOL20"])
    vol5 = safe_num(a5["Volume"])
    atr5 = safe_num(a5["ATR14"])

    vals = [p15, ema915, ema2015, rsi15, vwap15, p5, ema95, ema205,
            rsi5, vwap5, vol20_5, vol5, atr5]
    if any(x is None for x in vals) or vol20_5 <= 0 or atr5 <= 0:
        return None

    vol_x = vol5 / vol20_5

    # Arah 15M.
    trend15 = p15 > ema915 > ema2015 and p15 > vwap15

    # Trigger 5M: harga di atas EMA/VWAP + RSI sehat + volume meningkat.
    trigger5 = p5 > ema95 >= ema205 and p5 > vwap5 and 50 <= rsi5 <= 72 and vol_x >= 1.0

    # Jangan mengejar candle yang sudah terlalu panas.
    if rsi5 > 78:
        return None

    score = 0
    reasons = []
    if trend15:
        score += 35
        reasons.append("15M trend up")
    if p15 > vwap15:
        score += 10
        reasons.append("15M > VWAP")
    if p5 > ema95 >= ema205:
        score += 20
        reasons.append("5M EMA9 > EMA20")
    if p5 > vwap5:
        score += 10
        reasons.append("5M > VWAP")
    if 52 <= rsi5 <= 68:
        score += 10
        reasons.append("RSI 5M sehat")
    elif 50 <= rsi5 < 52:
        score += 5
    if vol_x >= 1.5:
        score += 15
        reasons.append(f"vol {vol_x:.1f}x")
    elif vol_x >= 1.0:
        score += 8
        reasons.append(f"vol {vol_x:.1f}x")

    if score < 65:
        return None

    entry_low = max(p5 - 0.15 * atr5, ema95)
    entry_high = p5 + 0.10 * atr5
    sl = min(ema205 - 0.20 * atr5, entry_low - 0.65 * atr5)
    if sl <= 0 or sl >= entry_low:
        return None

    risk = entry_low - sl
    tp1 = entry_low + 1.0 * risk
    tp2 = entry_low + 1.7 * risk

    status = "READY" if trend15 and trigger5 else "WAIT"

    return {
        "Kode": symbol,
        "Status": status,
        "Score": score,
        "Price": p5,
        "Entry Low": entry_low,
        "Entry High": entry_high,
        "TP1": tp1,
        "TP2": tp2,
        "SL": sl,
        "R/R TP1": (tp1 - entry_low) / risk,
        "R/R TP2": (tp2 - entry_low) / risk,
        "RSI 15M": rsi15,
        "RSI 5M": rsi5,
        "Vol 5M x": vol_x,
        "Alasan": ", ".join(reasons),
    }


@st.cache_data(ttl=120, show_spinner=False)
def scan_scalping(symbols):
    rows = []
    for symbol in symbols:
        try:
            raw15 = yf.download(
                f"{symbol}.JK", period="30d", interval="15m",
                auto_adjust=False, progress=False, threads=False,
            )
            raw5 = yf.download(
                f"{symbol}.JK", period="5d", interval="5m",
                auto_adjust=False, progress=False, threads=False,
            )
            result = analyze_scalping(
                symbol,
                get_ticker_frame(raw15, symbol),
                get_ticker_frame(raw5, symbol),
            )
            if result:
                rows.append(result)
        except Exception:
            continue
    return pd.DataFrame(rows)


# ============================================================
# UI
# ============================================================
with st.sidebar:
    st.header("⚙️ Mode")
    mode = st.radio(
        "Pilih scanner",
        ["🌙 Watchlist Besok", "🌆 BSJP", "⚡ Scalping"],
    )
    st.divider()

    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    tickers = get_idx_tickers()
except Exception as e:
    st.error("Daftar saham IDX gagal diambil dari sumber universe.")
    st.code(str(e))
    st.stop()

if not tickers:
    st.error("Tidak ada ticker Indonesia/JKT yang ditemukan.")
    st.stop()

st.info(f"Universe: **{len(tickers)} kode saham IDX**. Daftar emiten tidak lagi bergantung pada Yahoo Screener; data harga tetap dari Yahoo Finance. Watchlist hanya menampilkan setup yang masih fresh.")

# ------------------------------------------------------------
# WATCHLIST BESOK
# ------------------------------------------------------------
if mode == "🌙 Watchlist Besok":
    st.subheader("🌙 Watchlist Untuk Besok")
    st.caption("Daily • BO / PB / REB • setup fresh • Entry Zone • TP1/TP2 • SL")

    with st.sidebar:
        st.header("Filter Watchlist")
        min_tier = st.selectbox("Minimal Tier", ["A", "B", "C"], index=0)
        categories = st.multiselect("Setup", ["BO", "PB", "REB"], default=["BO", "PB", "REB"])
        min_score = st.slider("Minimal Score", 0, 100, 60, 5)
        max_results = st.slider("Jumlah saham", 5, 50, 20, 5)

    result = scan_daily(tickers)

    if result.empty:
        st.warning("Belum ada kandidat yang memenuhi setup.")
        st.stop()

    order = {"A": 0, "B": 1, "C": 2}
    result["_tier"] = result["Tier"].map(order)
    allowed = list(order.keys())[list(order.keys()).index(min_tier):]
    filtered = result[
        result["Tier"].isin(allowed)
        & result["Kategori"].isin(categories)
        & (result["Score"] >= min_score)
    ].copy()
    filtered = filtered.sort_values(["_tier", "Score", "RR_TP2"], ascending=[True, False, False]).head(max_results)

    if filtered.empty:
        st.warning("Tidak ada kandidat. Coba turunkan Minimal Score atau gunakan Tier B/C.")
    else:
        table = filtered[["Kode", "Tier", "Kategori", "Status", "Entry Low", "Entry High", "TP1", "TP2", "SL", "RR_TP1", "RR_TP2", "Score", "RSI", "Vol x"]].copy()
        for c in ["Entry Low", "Entry High", "TP1", "TP2", "SL"]:
            table[c] = table[c].round(2)
        table["RR_TP1"] = table["RR_TP1"].map(lambda x: f"{x:.2f}R")
        table["RR_TP2"] = table["RR_TP2"].map(lambda x: f"{x:.2f}R")
        table["RSI"] = table["RSI"].round(1)
        table["Vol x"] = table["Vol x"].map(lambda x: f"{x:.2f}x")
        table = table.rename(columns={"RR_TP1": "R/R TP1", "RR_TP2": "R/R TP2"})
        st.dataframe(table, use_container_width=True, hide_index=True)

        with st.expander("📌 Alasan tiap kandidat"):
            reason = filtered[["Kode", "Tier", "Kategori", "Close", "Change%", "Alasan"]].copy()
            reason["Close"] = reason["Close"].round(2)
            reason["Change%"] = reason["Change%"].map(lambda x: f"{x:+.2f}%")
            st.dataframe(reason, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download Watchlist CSV",
            data=filtered.drop(columns=["_tier"]).to_csv(index=False).encode("utf-8"),
            file_name="watchlist_besok.csv",
            mime="text/csv",
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Universe", len(tickers))
    c2.metric("Lolos Daily", len(result))
    c3.metric("Watchlist", len(filtered))

# ------------------------------------------------------------
# BSJP
# ------------------------------------------------------------
elif mode == "🌆 BSJP":
    st.subheader("🌆 BSJP — Beli Sore, Jual Pagi")
    st.caption("Daily = filter kandidat • 15M = konfirmasi menjelang penutupan. Entry sore, exit/target pagi berikutnya.")

    with st.sidebar:
        st.header("Filter BSJP")
        min_score_bsjp = st.slider("Minimal Score BSJP", 40, 100, 60, 5)
        max_candidates = st.slider("Kandidat awal", 10, 40, 20, 5)
        only_ready = st.checkbox("Tampilkan READY saja", value=False)

    daily_bsjp = scan_bsjp_daily(tickers)

    if daily_bsjp.empty:
        st.warning("Belum ada kandidat BSJP.")
        st.stop()

    daily_bsjp = daily_bsjp[daily_bsjp["Score"] >= min_score_bsjp].copy()
    daily_bsjp = daily_bsjp.sort_values(["Score", "Vol Daily x"], ascending=[False, False]).head(max_candidates)

    if daily_bsjp.empty:
        st.warning("Tidak ada kandidat setelah filter score.")
        st.stop()

    # 15M dipakai sebagai konfirmasi sore. Jalankan scanner mendekati penutupan
    # agar sinyal sesuai dengan rencana beli sore dan jual pagi berikutnya.
    conf = scan_bsjp_intraday(daily_bsjp["Kode"].tolist())

    if not conf.empty:
        bsjp = daily_bsjp.merge(conf, on="Kode", how="left")
    else:
        bsjp = daily_bsjp.copy()
        bsjp["15M Confirm"] = "NO DATA"

    bsjp["15M Confirm"] = bsjp["15M Confirm"].fillna("WAIT")
    if only_ready:
        bsjp = bsjp[bsjp["15M Confirm"] == "READY"].copy()

    if bsjp.empty:
        st.warning("Tidak ada kandidat BSJP yang READY.")
        st.stop()

    bsjp = bsjp.sort_values(["15M Confirm", "Score"], ascending=[True, False])

    table = bsjp[["Kode", "15M Confirm", "Score", "Close", "Entry Low", "Entry High", "TP1", "TP2", "SL", "RR_TP1", "RR_TP2", "RSI Daily", "Vol Daily x"]].copy()
    for c in ["Close", "Entry Low", "Entry High", "TP1", "TP2", "SL"]:
        table[c] = table[c].round(2)
    table["RSI Daily"] = table["RSI Daily"].round(1)
    table["Vol Daily x"] = table["Vol Daily x"].map(lambda x: f"{x:.2f}x")
    table["RR_TP1"] = table["RR_TP1"].map(lambda x: f"{x:.2f}R")
    table["RR_TP2"] = table["RR_TP2"].map(lambda x: f"{x:.2f}R")
    table = table.rename(columns={"RR_TP1": "R/R TP1", "RR_TP2": "R/R TP2"})
    st.dataframe(table, use_container_width=True, hide_index=True)

    with st.expander("📌 Alasan dan detail 15M"):
        detail_cols = [c for c in ["Kode", "Alasan", "15M Price", "15M EMA9", "15M EMA20", "15M RSI", "15M Vol x"] if c in bsjp.columns]
        detail = bsjp[detail_cols].copy()
        for c in ["15M Price", "15M EMA9", "15M EMA20"]:
            if c in detail.columns:
                detail[c] = detail[c].round(2)
        if "15M RSI" in detail.columns:
            detail["15M RSI"] = detail["15M RSI"].round(1)
        if "15M Vol x" in detail.columns:
            detail["15M Vol x"] = detail["15M Vol x"].map(lambda x: f"{x:.2f}x")
        st.dataframe(detail, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download BSJP CSV",
        data=bsjp.to_csv(index=False).encode("utf-8"),
        file_name="bsjp_sore_pagi.csv",
        mime="text/csv",
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Universe", len(tickers))
    c2.metric("Kandidat Daily", len(daily_bsjp))
    c3.metric("READY 15M", int((bsjp["15M Confirm"] == "READY").sum()))

# ------------------------------------------------------------
# SCALPING
# ------------------------------------------------------------
else:
    st.subheader("⚡ Scalping")
    st.caption("15M = arah • 5M = trigger. Fokus indikator intraday, terpisah dari Watchlist Besok dan BSJP.")

    with st.sidebar:
        st.header("Filter Scalping")
        min_score_scalp = st.slider("Minimal Score Scalping", 40, 100, 65, 5)
        max_candidates_scalp = st.slider("Kandidat dicek", 10, 40, 20, 5)
        only_ready_scalp = st.checkbox("Tampilkan READY saja", value=False)

    # Agar tidak membebani Yahoo, ambil kandidat likuid dari Daily terlebih dahulu.
    daily_liquid = scan_bsjp_daily(tickers)

    if daily_liquid.empty:
        st.warning("Tidak ada kandidat likuid untuk dicek intraday.")
        st.stop()

    # Daily di sini hanya memilih kandidat untuk menghemat request.
    # Sinyal scalping tetap dihitung murni dari 15M + 5M.
    candidates = daily_liquid.sort_values(["Vol Daily x", "Score"], ascending=[False, False]).head(max_candidates_scalp)
    symbols = candidates["Kode"].tolist()

    scalp = scan_scalping(symbols)

    if scalp.empty:
        st.warning("Belum ada setup scalping yang memenuhi syarat. Coba turunkan Minimal Score atau scan lagi saat market aktif.")
        st.stop()

    scalp = scalp[scalp["Score"] >= min_score_scalp].copy()
    if only_ready_scalp:
        scalp = scalp[scalp["Status"] == "READY"].copy()

    if scalp.empty:
        st.warning("Tidak ada kandidat setelah filter.")
        st.stop()

    scalp = scalp.sort_values(["Status", "Score"], ascending=[True, False])
    table = scalp[["Kode", "Status", "Score", "Price", "Entry Low", "Entry High", "TP1", "TP2", "SL", "R/R TP1", "R/R TP2", "RSI 15M", "RSI 5M", "Vol 5M x"]].copy()
    for c in ["Price", "Entry Low", "Entry High", "TP1", "TP2", "SL"]:
        table[c] = table[c].round(2)
    table["R/R TP1"] = table["R/R TP1"].map(lambda x: f"{x:.2f}R")
    table["R/R TP2"] = table["R/R TP2"].map(lambda x: f"{x:.2f}R")
    table["RSI 15M"] = table["RSI 15M"].round(1)
    table["RSI 5M"] = table["RSI 5M"].round(1)
    table["Vol 5M x"] = table["Vol 5M x"].map(lambda x: f"{x:.2f}x")
    st.dataframe(table, use_container_width=True, hide_index=True)

    with st.expander("📌 Alasan tiap kandidat"):
        st.dataframe(scalp[["Kode", "Status", "Score", "Alasan"]], use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download Scalping CSV",
        data=scalp.to_csv(index=False).encode("utf-8"),
        file_name="scalping_idx.csv",
        mime="text/csv",
    )

    c1, c2 = st.columns(2)
    c1.metric("Kandidat intraday dicek", len(symbols))
    c2.metric("Setup scalping", len(scalp))

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(
    "⚠️ Scanner hanya menghasilkan kandidat teknikal. Tidak ada jaminan harga naik atau target tercapai. "
    "Data harga berasal dari Yahoo Finance melalui yfinance; daftar kode saham berasal dari snapshot data emiten BEI/KSEI. Untuk entry/exit tetap cek chart dan kondisi pasar."
)
