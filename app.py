import html
import time
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="IDX Smart Screener",
    page_icon="📊",
    layout="wide",
)

# =========================================================
# STYLE
# =========================================================

CSS = """
<style>
.stApp { background:#070b12; }
.block-container { max-width:1500px; padding-top:1rem; }

.hero {
    background:linear-gradient(135deg,#101827,#0b111c);
    border:1px solid #202c3d;
    border-radius:18px;
    padding:24px 28px;
    margin-bottom:18px;
}
.hero h1 { margin:0; font-size:32px; }
.hero p { color:#8e9bad; margin:6px 0 0; }

.badge {
    display:inline-block;
    margin:12px 6px 0 0;
    padding:5px 10px;
    border-radius:999px;
    background:#142235;
    color:#8fc7ff;
    border:1px solid #263850;
    font-size:11px;
}

.card {
    background:#0d141f;
    border:1px solid #1d2a3a;
    border-radius:16px;
    padding:16px;
    margin-bottom:14px;
}

.ticker { font-size:21px; font-weight:800; color:#f3f7fb; }

.setup {
    margin-left:6px;
    padding:4px 8px;
    border-radius:999px;
    background:#172435;
    color:#9bcfff;
    font-size:9px;
    font-weight:800;
}

.price { font-size:18px; font-weight:750; margin-top:5px; }
.pos { color:#4ade80; }
.neg { color:#fb7185; }

.score-row {
    display:flex;
    align-items:center;
    gap:12px;
    margin:12px 0;
}

.score { font-size:27px; font-weight:900; min-width:42px; }

.bar {
    height:7px;
    background:#182231;
    border-radius:99px;
    overflow:hidden;
}

.fill { height:100%; border-radius:99px; }

.grid {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:7px;
}

.box {
    background:#111a27;
    border-radius:9px;
    padding:9px;
}

.entry { border-left:3px solid #55c2ff; }
.tp { border-left:3px solid #4ade80; }
.sl { border-left:3px solid #fb7185; }

.label { color:#718096; font-size:9px; font-weight:700; }
.value { font-size:14px; font-weight:800; margin-top:2px; }

.info {
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    gap:6px;
    margin-top:8px;
}

.info div {
    background:#101823;
    border-radius:8px;
    padding:7px;
}

.info small { color:#718096; font-size:8px; }
.info b { display:block; font-size:11px; margin-top:2px; }

.reason {
    border-top:1px solid #1b2735;
    margin-top:10px;
    padding-top:9px;
    color:#a8b4c5;
    font-size:11px;
    line-height:1.5;
}

.note {
    padding:11px 14px;
    border-radius:10px;
    margin-bottom:14px;
    background:#211c0f;
    border:1px solid #55451b;
    color:#d9c78b;
    font-size:12px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =========================================================
# IDX UNIVERSE
# =========================================================

IDX_URL = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/128.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.idx.co.id/",
    "Origin": "https://www.idx.co.id",
}

@st.cache_data(ttl=86400, show_spinner=False)
def get_idx_universe():
    """
    Ambil universe saham IDX secara dinamis.

    Jalur utama:
    Yahoo Finance screener -> exchange JKT + region ID.
    Ini menghindari HTTP 403 dari endpoint IDX yang sering memblokir
    request server-side seperti Streamlit Cloud.

    Jalur kedua:
    Endpoint profil perusahaan IDX dengan curl_cffi.

    Scanner TIDAK akan memakai daftar ticker hardcoded yang tidak lengkap.
    """
    errors = []

    # =====================================================
    # 1) PRIMARY: YAHOO FINANCE SCREENER
    # =====================================================
    try:
        from yfinance import EquityQuery

        query = EquityQuery(
            "and",
            [
                EquityQuery("eq", ["region", "id"]),
                EquityQuery("eq", ["exchange", "JKT"]),
            ],
        )

        all_symbols = []
        offset = 0
        page_size = 250

        # Yahoo membatasi custom screener maksimal 250 hasil per request.
        # Empat-lima halaman sudah cukup untuk universe IDX saat ini.
        for _ in range(10):
            response = yf.screen(
                query,
                offset=offset,
                size=page_size,
                sortField="ticker",
                sortAsc=True,
            )

            quotes = response.get("quotes", [])

            if not quotes:
                break

            before = len(all_symbols)

            for quote in quotes:
                symbol = str(quote.get("symbol", "")).strip().upper()

                if symbol.endswith(".JK"):
                    symbol = symbol[:-3]

                if (
                    2 <= len(symbol) <= 6
                    and symbol.isalnum()
                ):
                    all_symbols.append(symbol)

            all_symbols = list(dict.fromkeys(all_symbols))

            # Tidak ada tambahan data -> selesai.
            if len(all_symbols) == before:
                break

            # Jika halaman terakhir kurang dari 250, selesai.
            if len(quotes) < page_size:
                break

            offset += page_size

        if len(all_symbols) >= 500:
            return all_symbols

        errors.append(
            f"Yahoo Finance hanya mengembalikan {len(all_symbols)} ticker."
        )

    except Exception as error:
        errors.append(
            "Yahoo Finance screener: " + str(error)
        )

    # =====================================================
    # 2) SECONDARY: IDX ENDPOINT
    # =====================================================
    try:
        from curl_cffi import requests as curl_requests

        idx_url = (
            "https://www.idx.co.id/"
            "primary/ListedCompany/GetCompanyProfiles"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
            ),
            "Accept": (
                "application/json, text/plain, */*"
            ),
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Referer": (
                "https://www.idx.co.id/id/"
                "perusahaan-tercatat/profil-perusahaan/"
            ),
        }

        response = curl_requests.get(
            idx_url,
            params={
                "start": 0,
                "length": 9999,
                "code": "",
            },
            headers=headers,
            timeout=30,
            impersonate="chrome",
        )

        response.raise_for_status()
        payload = response.json()

        rows = payload.get("data", [])
        tickers = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            code = str(
                row.get("KodeEmiten", "")
            ).strip().upper()

            if (
                2 <= len(code) <= 6
                and code.isalnum()
            ):
                tickers.append(code)

        tickers = list(dict.fromkeys(tickers))

        if len(tickers) >= 500:
            return tickers

        errors.append(
            f"IDX endpoint hanya mengembalikan {len(tickers)} ticker."
        )

    except Exception as error:
        errors.append(
            "IDX endpoint: " + str(error)
        )

    raise RuntimeError(
        "Universe IDX tidak berhasil diambil secara lengkap.\n\n"
        + "\n".join(errors)
    )

# =========================================================
# TIMEFRAME
# =========================================================

TIMEFRAMES = {
    "Daily": ("1y", "1d"),
    "1H": ("180d", "1h"),
    "15M": ("60d", "15m"),
    "5M": ("30d", "5m"),
}

# =========================================================
# MARKET DATA
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def download_batch(symbols, period, interval):
    yahoo_symbols = [f"{s}.JK" for s in symbols]

    try:
        return yf.download(
            tickers=list(yahoo_symbols),
            period=period,
            interval=interval,
            auto_adjust=False,
            group_by="ticker",
            threads=False,
            progress=False,
        )
    except Exception:
        return None

def extract_symbol(raw, symbol):
    if raw is None or raw.empty:
        return None

    yahoo_symbol = f"{symbol}.JK"

    try:
        if isinstance(raw.columns, pd.MultiIndex):
            level0 = list(raw.columns.get_level_values(0))
            level1 = list(raw.columns.get_level_values(1))

            if yahoo_symbol in level0:
                df = raw[yahoo_symbol].copy()
            elif yahoo_symbol in level1:
                df = raw.xs(yahoo_symbol, axis=1, level=1).copy()
            else:
                return None
        else:
            df = raw.copy()

        needed = ["Open", "High", "Low", "Close", "Volume"]

        if not all(col in df.columns for col in needed):
            return None

        df = df[needed].copy()

        for col in needed:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        if len(df) < 60:
            return None

        return df

    except Exception:
        return None

# =========================================================
# TECHNICAL ENGINE
# =========================================================

def analyze_stock(df, symbol, mode, min_price, max_price):
    if df is None or len(df) < 60:
        return None

    try:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        open_ = df["Open"]
        volume = df["Volume"]

        df["MA5"] = close.rolling(5).mean()
        df["MA10"] = close.rolling(10).mean()
        df["MA20"] = close.rolling(20).mean()
        df["MA50"] = close.rolling(50).mean()
        df["VolMA20"] = volume.rolling(20).mean()

        prev_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        df["ATR14"] = true_range.rolling(14).mean()

        df["PrevHigh10"] = high.shift(1).rolling(10).max()
        df["PrevLow10"] = low.shift(1).rolling(10).min()
        df["PrevHigh20"] = high.shift(1).rolling(20).max()
        df["PrevLow20"] = low.shift(1).rolling(20).min()

        x = df.iloc[-1]
        p = df.iloc[-2]

        price = float(x["Close"])

        if not min_price <= price <= max_price:
            return None

        atr = float(x["ATR14"])
        vol_ma = float(x["VolMA20"])

        if not np.isfinite(atr) or atr <= 0:
            return None

        if not np.isfinite(vol_ma) or vol_ma <= 0:
            return None

        vol_ratio = float(x["Volume"]) / vol_ma
        change = (price / float(p["Close"]) - 1) * 100

        ma5 = float(x["MA5"])
        ma10 = float(x["MA10"])
        ma20 = float(x["MA20"])
        ma50 = float(x["MA50"])

        support = float(x["PrevLow10"])
        resistance10 = float(x["PrevHigh10"])
        resistance20 = float(x["PrevHigh20"])

        bullish = float(x["Close"]) > float(x["Open"])
        fast_trend = ma5 > ma10 and ma10 > ma20
        main_trend = price > ma20 and ma20 > ma50
        breakout = price > resistance20

        near_support = (
            price >= support
            and (price - support) / price <= 0.03
        )

        structure_up = (
            float(x["High"]) > float(x["PrevHigh10"])
            and float(x["Low"]) > float(x["PrevLow10"])
        )

        score = 0
        reasons = []

        if price > ma20:
            score += 15
            reasons.append("Harga di atas MA20")

        if ma20 > ma50:
            score += 15
            reasons.append("MA20 di atas MA50")

        if bullish:
            score += 10
            reasons.append("Candle terakhir bullish")

        if vol_ratio > 1.0:
            score += 10
            reasons.append(f"Volume {vol_ratio:.2f}x rata-rata")

        if vol_ratio > 1.5:
            score += 5
            reasons.append("Volume spike > 1.5x")

        if breakout:
            score += 15
            reasons.append("Breakout high 20 periode")

        if change > 1:
            score += 10
            reasons.append(f"Momentum +{change:.2f}%")

        if structure_up:
            score += 10
            reasons.append("Struktur high/low menguat")

        if near_support:
            score += 10
            reasons.append("Harga dekat support")

        score = min(score, 100)

        # ---------------- Entry ----------------

        if breakout:
            entry_low = max(
                resistance20,
                price - 0.5 * atr,
            )
        else:
            entry_low = max(
                support,
                price - 0.5 * atr,
            )

        entry_high = price

        if entry_low >= entry_high:
            entry_low = entry_high - 0.5 * atr

        entry_low = max(1, entry_low)
        entry_mid = (entry_low + entry_high) / 2

        # ---------------- Stop Loss ----------------

        sl = support - 0.25 * atr

        if sl >= entry_mid:
            sl = entry_mid - atr

        sl = max(1, sl)

        risk = entry_mid - sl

        if risk <= 0:
            return None

        # ---------------- Take Profit ----------------

        resistances = sorted(
            [
                value
                for value in (resistance10, resistance20)
                if value > entry_mid
            ]
        )

        tp1 = entry_mid + risk

        if resistances and resistances[0] < entry_mid + 1.25 * risk:
            tp1 = resistances[0]

        tp2 = entry_mid + 2 * risk

        if resistances and resistances[-1] > tp1:
            if resistances[-1] < entry_mid + 3 * risk:
                tp2 = resistances[-1]

        rr1 = (tp1 - entry_mid) / risk
        rr2 = (tp2 - entry_mid) / risk

        # ---------------- Setup ----------------

        if breakout and vol_ratio >= 1.2:
            setup = "BREAKOUT"
        elif near_support:
            setup = "NEAR SUPPORT"
        elif main_trend and fast_trend:
            setup = "MOMENTUM"
        else:
            setup = "WATCH"

        # ---------------- Filter ----------------

        if mode == "⚡ Scalping Besok":
            qualifies = (
                score >= 55
                and (
                    vol_ratio >= 1
                    or breakout
                    or near_support
                )
            )
        else:
            qualifies = (
                score >= 60
                and main_trend
                and (fast_trend or structure_up)
            )

        if not qualifies:
            return None

        return {
            "ticker": symbol,
            "price": price,
            "change": change,
            "volume": float(x["Volume"]),
            "vol_ratio": vol_ratio,
            "ma20": ma20,
            "ma50": ma50,
            "support": support,
            "resistance": resistance10,
            "score": score,
            "setup": setup,
            "entry_low": entry_low,
            "entry_high": entry_high,
            "tp1": tp1,
            "tp2": tp2,
            "sl": sl,
            "rr1": rr1,
            "rr2": rr2,
            "reasons": reasons,
            "frame": df.copy(),
        }

    except Exception:
        return None

# =========================================================
# DISPLAY
# =========================================================

def rp(value):
    return f"Rp {int(round(value)):,}".replace(",", ".")

def render_card(item):
    score = int(item["score"])

    if score >= 80:
        score_color = "#4ade80"
    elif score >= 70:
        score_color = "#55c2ff"
    else:
        score_color = "#facc15"

    change = float(item["change"])
    change_class = "pos" if change >= 0 else "neg"
    sign = "+" if change >= 0 else ""

    reasons_html = "".join(
        "<div>✓ " + html.escape(str(reason)) + "</div>"
        for reason in item["reasons"][:5]
    )

    card_html = (
        '<div class="card">'
        '<div>'
        '<span class="ticker">'
        + html.escape(item["ticker"])
        + '</span>'
        '<span class="setup">'
        + html.escape(item["setup"])
        + '</span>'
        '</div>'

        '<div class="price">'
        + rp(item["price"])
        + ' <span class="'
        + change_class
        + '">'
        + sign
        + f'{change:.2f}%'
        + '</span>'
        '</div>'

        '<div class="score-row">'
        '<div class="score" style="color:'
        + score_color
        + '">'
        + str(score)
        + '</div>'

        '<div style="flex:1">'
        '<div style="font-size:9px;color:#718096;font-weight:700;">'
        'TECHNICAL SCORE'
        '</div>'

        '<div class="bar">'
        '<div class="fill" style="width:'
        + str(score)
        + '%;background:'
        + score_color
        + ';"></div>'
        '</div>'
        '</div>'
        '</div>'

        '<div class="grid">'

        '<div class="box entry">'
        '<div class="label">ENTRY</div>'
        '<div class="value">'
        + rp(item["entry_low"])
        + " - "
        + rp(item["entry_high"])
        + '</div>'
        '</div>'

        '<div class="box tp">'
        '<div class="label">TP1</div>'
        '<div class="value">'
        + rp(item["tp1"])
        + '</div>'
        '</div>'

        '<div class="box tp">'
        '<div class="label">TP2</div>'
        '<div class="value">'
        + rp(item["tp2"])
        + '</div>'
        '</div>'

        '<div class="box sl">'
        '<div class="label">STOP LOSS</div>'
        '<div class="value">'
        + rp(item["sl"])
        + '</div>'
        '</div>'

        '</div>'

        '<div class="info">'

        '<div>'
        '<small>VOL RATIO</small>'
        '<b>'
        + f'{item["vol_ratio"]:.2f}x'
        + '</b>'
        '</div>'

        '<div>'
        '<small>SUPPORT</small>'
        '<b>'
        + rp(item["support"])
        + '</b>'
        '</div>'

        '<div>'
        '<small>R/R TP2</small>'
        '<b>1 : '
        + f'{item["rr2"]:.2f}'
        + '</b>'
        '</div>'

        '</div>'

        '<div class="reason">'
        '<b>Alasan:</b>'
        + reasons_html
        + '</div>'

        '</div>'
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )

# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="hero">
        <h1>📊 IDX SMART SCREENER</h1>
        <p>Dynamic IDX Universe • Persiapan malam • Konfirmasi intraday besok</p>
        <span class="badge">⚡ SCALPING</span>
        <span class="badge">📈 SWING</span>
        <span class="badge">🧠 MULTI-TF</span>
        <span class="badge">🇮🇩 IDX</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Scanner Settings")

mode = st.sidebar.radio(
    "Mode",
    ["⚡ Scalping Besok", "📈 Swing"],
)

timeframe = st.sidebar.selectbox(
    "Timeframe Scan",
    ["Daily", "1H", "15M", "5M"],
)

min_price = st.sidebar.number_input(
    "Harga Minimum",
    min_value=1,
    value=50,
    step=10,
)

max_price = st.sidebar.number_input(
    "Harga Maksimum",
    min_value=10,
    value=100000,
    step=100,
)

batch_size = st.sidebar.select_slider(
    "Batch Download",
    options=[15, 25, 35, 50],
    value=25,
)

if st.sidebar.but
