import html
import time
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import requests

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="IDX Smart Screener",
    page_icon="📊",
    layout="wide",
)

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background: #070b12;
}

.block-container {
    max-width: 1500px;
    padding-top: 1rem;
}

.hero {
    background: linear-gradient(135deg,#101827,#0b111c);
    border: 1px solid #202c3d;
    border-radius: 18px;
    padding: 24px 28px;
    margin-bottom: 18px;
}

.hero h1 {
    margin: 0;
    font-size: 32px;
}

.hero p {
    color: #8e9bad;
    margin: 6px 0 0;
}

.badge {
    display: inline-block;
    margin: 12px 6px 0 0;
    padding: 5px 10px;
    border-radius: 999px;
    background: #142235;
    color: #8fc7ff;
    border: 1px solid #263850;
    font-size: 11px;
}

.card {
    background: #0d141f;
    border: 1px solid #1d2a3a;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 14px;
}

.ticker {
    font-size: 21px;
    font-weight: 800;
    color: #f3f7fb;
}

.setup {
    margin-left: 6px;
    padding: 4px 8px;
    border-radius: 999px;
    background: #172435;
    color: #9bcfff;
    font-size: 9px;
    font-weight: 800;
}

.price {
    font-size: 18px;
    font-weight: 750;
    margin-top: 5px;
}

.pos {
    color: #4ade80;
}

.neg {
    color: #fb7185;
}

.score-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 12px 0;
}

.score {
    font-size: 27px;
    font-weight: 900;
    min-width: 42px;
}

.bar {
    height: 7px;
    background: #182231;
    border-radius: 99px;
    overflow: hidden;
}

.fill {
    height: 100%;
    border-radius: 99px;
}

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 7px;
}

.box {
    background: #111a27;
    border-radius: 9px;
    padding: 9px;
}

.entry {
    border-left: 3px solid #55c2ff;
}

.tp {
    border-left: 3px solid #4ade80;
}

.sl {
    border-left: 3px solid #fb7185;
}

.label {
    color: #718096;
    font-size: 9px;
    font-weight: 700;
}

.value {
    font-size: 14px;
    font-weight: 800;
    margin-top: 2px;
}

.info {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px;
    margin-top: 8px;
}

.info div {
    background: #101823;
    border-radius: 8px;
    padding: 7px;
}

.info small {
    color: #718096;
    font-size: 8px;
}

.info b {
    display: block;
    font-size: 11px;
    margin-top: 2px;
}

.reason {
    border-top: 1px solid #1b2735;
    margin-top: 10px;
    padding-top: 9px;
    color: #a8b4c5;
    font-size: 11px;
    line-height: 1.5;
}

.note {
    padding: 11px 14px;
    border-radius: 10px;
    margin-bottom: 14px;
    background: #211c0f;
    border: 1px solid #55451b;
    color: #d9c78b;
    font-size: 12px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# IDX DYNAMIC UNIVERSE
# =========================================================

IDX_URL = (
    "https://www.idx.co.id/"
    "primary/ListedCompany/GetCompanyProfiles"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Linux; Android 14) "
        "AppleWebKit/537.36 "
        "Chrome/128.0 Mobile Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.idx.co.id/",
    "Origin": "https://www.idx.co.id",
}


@st.cache_data(ttl=86400, show_spinner=False)
def get_idx_universe():

    rows = []

    start = 0
    length = 1000

    # curl_cffi dipakai kalau tersedia karena
    # website IDX kadang menolak request biasa.
    try:
        from curl_cffi import requests as curl_requests
        use_curl = True
    except Exception:
        curl_requests = None
        use_curl = False

    while True:

        params = {
            "start": start,
            "length": length,
            "code": ""
        }

        if use_curl:

            response = curl_requests.get(
                IDX_URL,
                params=params,
                headers=HEADERS,
                timeout=25,
                impersonate="chrome"
            )

        else:

            response = requests.get(
                IDX_URL,
                params=params,
                headers=HEADERS,
                timeout=25
            )

        response.raise_for_status()

        payload = response.json()

        batch = payload.get("data", [])

        if not batch:
            break

        rows.extend(batch)

        try:
            total = int(
                payload.get(
                    "recordsTotal",
                    len(rows)
                )
            )
        except Exception:
            total = len(rows)

        if len(rows) >= total:
            break

        if len(batch) < length:
            break

        start += length

        # pengaman
        if start > 10000:
            break

    tickers = []

    for row in rows:

        if not isinstance(row, dict):
            continue

        code = None

        for key in [
            "KodeEmiten",
            "Kode_Emiten",
            "code",
            "Code",
            "Kode"
        ]:

            if key in row:
                code = row[key]
                break

        if code is None:
            continue

        code = str(code).strip().upper()

        if (
            2 <= len(code) <= 6
            and code.replace(".", "").isalnum()
        ):
            tickers.append(code)

    tickers = list(dict.fromkeys(tickers))

    # PENTING:
    # kalau IDX cuma mengembalikan sebagian,
    # jangan scan dan mengaku semua IDX.
    if len(tickers) < 500:

        raise RuntimeError(
            f"IDX hanya mengembalikan "
            f"{len(tickers)} ticker. "
            f"Scanner dihentikan agar "
            f"tidak menggunakan universe yang tidak lengkap."
        )

    return tickers


# =========================================================
# TIMEFRAME
# =========================================================

TIMEFRAMES = {

    "Daily": (
        "1y",
        "1d"
    ),

    "1H": (
        "180d",
        "1h"
    ),

    "15M": (
        "60d",
        "15m"
    ),

    "5M": (
        "30d",
        "5m"
    )
}


# =========================================================
# DOWNLOAD DATA
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def download_batch(
    symbols,
    period,
    interval
):

    yahoo_symbols = [
        f"{symbol}.JK"
        for symbol in symbols
    ]

    try:

        data = yf.download(
            tickers=list(yahoo_symbols),
            period=period,
            interval=interval,
            auto_adjust=False,
            group_by="ticker",
            threads=False,
            progress=False
        )

        if data is None or data.empty:
            return None

        return data

    except Exception:

        return None


def extract_symbol(
    raw,
    symbol
):

    if raw is None or raw.empty:
        return None

    yahoo_symbol = (
        f"{symbol}.JK"
    )

    try:

        if isinstance(
            raw.columns,
            pd.MultiIndex
        ):

            level0 = list(
                raw.columns
                .get_level_values(0)
            )

            level1 = list(
                raw.columns
                .get_level_values(1)
            )

            if yahoo_symbol in level0:

                df = raw[
                    yahoo_symbol
                ].copy()

            elif yahoo_symbol in level1:

                df = raw.xs(
                    yahoo_symbol,
                    axis=1,
                    level=1
                ).copy()

            else:

                return None

        else:

            df = raw.copy()

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        if not all(
            x in df.columns
            for x in required
        ):
            return None

        df = df[required].copy()

        for col in required:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna()

        if len(df) < 60:
            return None

        return df

    except Exception:

        return None


# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze_stock(
    df,
    symbol,
    mode,
    min_price,
    max_price
):

    if df is None:
        return None

    if len(df) < 60:
        return None

    try:

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        open_ = df["Open"]
        volume = df["Volume"]

        # -----------------------------
        # MA
        # -----------------------------

        df["MA5"] = (
            close.rolling(5).mean()
        )

        df["MA10"] = (
            close.rolling(10).mean()
        )

        df["MA20"] = (
            close.rolling(20).mean()
        )

        df["MA50"] = (
            close.rolling(50).mean()
        )

        # -----------------------------
        # Volume
        # -----------------------------

        df["VolMA20"] = (
            volume.rolling(20).mean()
        )

        # -----------------------------
        # ATR
        # -----------------------------

        prev_close = close.shift(1)

        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs()
            ],
            axis=1
        ).max(axis=1)

        df["ATR14"] = (
            tr.rolling(14).mean()
        )

        # -----------------------------
        # Support / Resistance
        # -----------------------------

        df["PrevHigh10"] = (
            high.shift(1)
            .rolling(10)
            .max()
        )

        df["PrevLow10"] = (
            low.shift(1)
            .rolling(10)
            .min()
        )

        df["PrevHigh20"] = (
            high.shift(1)
            .rolling(20)
            .max()
        )

        df["PrevLow20"] = (
            low.shift(1)
            .rolling(20)
            .min()
        )

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        price = float(
            latest["Close"]
        )

        if not (
            min_price
            <= price
            <= max_price
        ):
            return None

        atr = float(
            latest["ATR14"]
        )

        vol_ma = float(
            latest["VolMA20"]
        )

        if (
            not np.isfinite(atr)
            or atr <= 0
            or vol_ma <= 0
        ):
            return None

        vol_ratio = (
            float(latest["Volume"])
            / vol_ma
        )

        change = (
            price
            / float(previous["Close"])
            - 1
        ) * 100

        ma5 = float(
            latest["MA5"]
        )

        ma10 = float(
            latest["MA10"]
        )

        ma20 = float(
            latest["MA20"]
        )

        ma50 = float(
            latest["MA50"]
        )

        support = float(
            latest["PrevLow10"]
        )

        resistance10 = float(
            latest["PrevHigh10"]
        )

        resistance20 = float(
            latest["PrevHigh20"]
        )

        # -----------------------------
        # Conditions
        # -----------------------------

        bullish_candle = (
            float(latest["Close"])
            >
            float(latest["Open"])
        )

        fast_trend = (
            ma5 > ma10
            and
            ma10 > ma20
        )

        main_trend = (
            price > ma20
            and
            ma20 > ma50
        )

        breakout = (
            price > resistance20
        )

        near_support = (
            price >= support
            and
            (
                (price - support)
                / price
            ) <= 0.03
        )

        structure_up = (
            float(latest["High"])
            >
            float(latest["PrevHigh10"])
            and
            float(latest["Low"])
            >
            float(latest["PrevLow10"])
        )

        # -----------------------------
        # SCORE
        # -----------------------------

        score = 0

        reasons = []

        if price > ma20:

            score += 15

            reasons.append(
                "Harga di atas MA20"
            )

        if ma20 > ma50:

            score += 15

            reasons.append(
                "MA20 di atas MA50"
            )

        if bullish_candle:

            score += 10

            reasons.append(
                "Candle terakhir bullish"
            )

        if vol_ratio > 1.0:

            score += 10

            reasons.append(
                f"Volume {vol_ratio:.2f}x rata-rata"
            )

        if vol_ratio > 1.5:

            score += 5

            reasons.append(
                "Volume spike > 1.5x"
            )

        if breakout:

            score += 15

            reasons.append(
                "Breakout high 20 periode"
            )

        if change > 1:

            score += 10

            reasons.append(
                f"Momentum +{change:.2f}%"
            )

        if structure_up:

            score += 10

            reasons.append(
                "Struktur high/low menguat"
            )

        if near_support:

            score += 10

            reasons.append(
                "Harga dekat support"
            )

        score = min(
            score,
            100
        )

        # =================================================
        # ENTRY
        # =================================================

        if breakout:

            entry_low = max(
                resistance20,
                price - (
                    0.5 * atr
                )
            )

        else:

            entry_low = max(
                support,
                price - (
                    0.5 * atr
                )
            )

        entry_high = price

        if entry_low >= entry_high:

            entry_low = (
                entry_high
                - 0.5 * atr
            )

        entry_low = max(
            1,
            entry_low
        )

        entry_mid = (
            entry_low
            + entry_high
        ) / 2

        # =================================================
        # STOP LOSS
        # =================================================

        sl = (
            support
            - 0.25 * atr
        )

        if sl >= entry_mid:

            sl = (
                entry_mid
                - atr
            )

        sl = max(
            1,
            sl
        )

        risk = (
            entry_mid
            - sl
        )

        if risk <= 0:
            return None

        # =================================================
        # TAKE PROFIT
        # =================================================

        resistances = sorted(
            [
                x
                for x in [
                    resistance10,
                    resistance20
                ]
                if x > entry_mid
            ]
        )

        # TP1 sekitar 1R
        tp1 = (
            entry_mid
            + risk
        )

        if resistances:

            nearest = resistances[0]

            if (
                nearest
                <
                entry_mid
                + 1.25 * risk
            ):

                tp1 = nearest

        # TP2 sekitar 2R
        tp2 = (
            entry_mid
            + 2 * risk
        )

        if resistances:

            farthest = resistances[-1]

            if (
                farthest > tp1
                and
                farthest
                <
                entry_mid
                + 3 * risk
            ):

                tp2 = farthest

        rr1 = (
            tp1
            - entry_mid
        ) / risk

        rr2 = (
            tp2
            - entry_mid
        ) / risk

        # =================================================
        # SETUP
        # =================================================

        if (
            breakout
            and
            vol_ratio >= 1.2
        ):

            setup = "BREAKOUT"

        elif near_support:

            setup = "NEAR SUPPORT"

        elif (
            main_trend
            and
            fast_trend
        ):

            setup = "MOMENTUM"

        else:

            setup = "WATCH"

        # =================================================
        # MODE FILTER
        # =================================================

        if mode == "⚡ Scalping Besok":

            qualifies = (
                score >= 55
                and
                (
                    vol_ratio >= 1
                    or breakout
                    or near_support
                )
            )

        else:

            qualifies = (
                score >= 60
                and
                main_trend
                and
                (
                    fast_trend
                    or structure_up
                )
            )

        if not qualifies:
            return None

        return {

            "ticker": symbol,

            "price": price,

            "change": change,

            "volume": float(
                latest["Volume"]
            ),

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

            "frame": df.copy()
        }

    except Exception:

        return None


# =========================================================
# FORMAT
# =========================================================

def rp(value):

    return (
        f"Rp {int(round(value)):,}"
        .replace(",", ".")
    )


def render_card(item):

    score = int(
        item["score"]
    )

    if score >= 80:

        color = "#4ade80"

    elif score >= 70:

        color = "#55c2ff"

    else:

        color = "#facc15"

    change = float(
        item["change"]
    )

    change_class = (
        "pos"
        if change >= 0
        else "neg"
    )

    sign = (
        "+"
        if change >= 0
        else ""
    )

    reasons = ""

    for reason in item["reasons"][:5]:

        reasons += (
            "<div>✓ "
            + html.escape(
                str(reason)
            )
            + "</div>"
        )

    st.markdown(
        f"""
        <div class="card">

            <div>

                <span class="ticker">
                    {html.escape(
                        item["ticker"]
                    )}
                </span>

                <span class="setup">
                    {html.escape(
                        item["setup"]
                    )}
                </span>

            </div>

            <div class="price">

                {rp(item["price"])}

                <span class="{change_class}">
                    {sign}{change:.2f}%
                </span>

            </div>

            <div class="score-row">

                <div
                    clas
