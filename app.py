import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="IDX Watchlist Besok", page_icon="🎯", layout="wide")

st.title("🎯 IDX Watchlist Besok")
st.caption("Yahoo Finance • Daily OHLCV • penyaring kandidat untuk dicek manual besok")

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_idx_tickers():
    query = yf.EquityQuery("and", [
        yf.EquityQuery("eq", ["region", "id"]),
        yf.EquityQuery("eq", ["exchange", "JKT"]),
    ])

    tickers = []
    offset = 0

    for _ in range(10):
        result = yf.screen(
            query,
            offset=offset,
            size=250,
            sortField="ticker",
            sortAsc=True,
        )
        quotes = result.get("quotes", [])
        if not quotes:
            break

        for item in quotes:
            symbol = item.get("symbol")
            if symbol:
                symbol = str(symbol).upper().replace(".JK", "")
                if symbol not in tickers:
                    tickers.append(symbol)

        if len(quotes) < 250:
            break
        offset += 250

    return sorted(tickers)


def atr(df, period=14):
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def analyze_one(symbol, data):
    if data is None or data.empty:
        return None

    df = data.copy().dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    if len(df) < 70:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["VOL20"] = volume.rolling(20).mean()
    df["ATR14"] = atr(df, 14)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(last["Close"])
    open_price = float(last["Open"])
    high_price = float(last["High"])
    low_price = float(last["Low"])
    ma20 = float(last["MA20"])
    ma50 = float(last["MA50"])
    vol20 = float(last["VOL20"])
    atr14 = float(last["ATR14"])
    rsi = float(last["RSI14"])

    vals = [price, open_price, high_price, low_price, ma20, ma50, vol20, atr14, rsi]
    if not all(np.isfinite(x) for x in vals):
        return None
    if price <= 0 or atr14 <= 0 or vol20 <= 0:
        return None

    volume_ratio = float(last["Volume"]) / vol20
    bullish = price > open_price
    body_pct = abs(price - open_price) / price * 100

    high10 = float(high.tail(10).max())
    low10 = float(low.tail(10).min())
    high20_prev = float(high.iloc[-21:-1].max())
    low20_prev = float(low.iloc[-21:-1].min())

    # Trend
    trend_up = price > ma20 > ma50
    trend_ok = price > ma50 and ma20 >= ma50 * 0.995

    # Pullback: harga dekat MA20, tetapi belum rusak trend.
    dist_ma20_pct = abs(price - ma20) / price * 100
    near_ma20 = dist_ma20_pct <= 3.0
    pullback = trend_ok and near_ma20 and bullish and 42 <= rsi <= 68

    # Breakout: close melewati high 20 hari sebelumnya + volume.
    breakout = price >= high20_prev and volume_ratio >= 1.15

    # Rebound: menyentuh area low 10 hari / MA20 lalu tutup menguat.
    near_support = (
        trend_ok
        and price <= ma20 * 1.025
        and price >= ma20 * 0.965
        and bullish
        and rsi <= 65
    )

    if breakout:
        category = "BO"
    elif pullback:
        category = "PB"
    elif near_support:
        category = "REB"
    else:
        category = ""

    # Hindari saham yang sudah terlalu panas untuk watchlist besok.
    one_day_change = (price / float(prev["Close"]) - 1) * 100
    hot = rsi > 75 or one_day_change > 12

    # Skor 100.
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

    if volume_ratio >= 1.0:
        score += 10
        reasons.append(f"vol {volume_ratio:.1f}x")
    if volume_ratio >= 1.5:
        score += 5

    if breakout:
        score += 20
        reasons.append("breakout")
    elif pullback:
        score += 15
        reasons.append("pullback MA20")
    elif near_support:
        score += 12
        reasons.append("rebound area support")

    if 45 <= rsi <= 68:
        score += 10
    elif 40 <= rsi < 45:
        score += 5

    # Risk filter.
    if hot:
        score -= 20

    # Jangan masukkan trend rusak / setup kosong.
    if not category or not trend_ok or hot:
        return None

    # Entry zone berbasis ATR, bukan satu harga.
    if category == "BO":
        entry_low = max(price, high20_prev)
        entry_high = entry_low + 0.35 * atr14
        support = max(low10, high20_prev - 0.8 * atr14)
    else:
        center = max(ma20, price - 0.15 * atr14)
        entry_low = max(ma20 - 0.25 * atr14, low10 * 0.995)
        entry_high = center + 0.20 * atr14
        entry_low = min(entry_low, entry_high)

        # Jangan membuat zona terlalu jauh dari harga sekarang.
        if entry_low < price * 0.94:
            entry_low = price * 0.96
        if entry_high < entry_low:
            entry_high = entry_low + 0.20 * atr14

        support = min(low10, ma20 - 0.5 * atr14)

    # SL di bawah support/ATR.
    sl = support - 0.30 * atr14

    # Batasi SL agar tidak terlalu dekat atau terlalu jauh.
    if sl >= entry_low:
        sl = entry_low - 0.75 * atr14
    if sl <= entry_low * 0.90:
        sl = entry_low * 0.90

    # Target memakai risk dari entry zone bawah.
    risk = entry_low - sl
    if risk <= 0:
        return None

    tp1 = entry_low + 1.25 * risk
    tp2 = entry_low + 2.0 * risk

    # Resistance sebagai target tambahan.
    resistance = float(high.tail(30).max())
    if resistance > tp1 and resistance < tp2:
        tp1 = resistance

    rr_tp1 = (tp1 - entry_low) / risk
    rr_tp2 = (tp2 - entry_low) / risk

    tier = "A" if score >= 75 else ("B" if score >= 60 else "C")

    return {
        "Kode": symbol,
        "Tier": tier,
        "Kategori": category,
        "Entry Low": entry_low,
        "Entry High": entry_high,
        "TP1": tp1,
        "TP2": tp2,
        "SL": sl,
        "RR_TP1": rr_tp1,
        "RR_TP2": rr_tp2,
        "Score": score,
        "Close": price,
        "Change%": one_day_change,
        "RSI": rsi,
        "Vol x": volume_ratio,
        "Alasan": ", ".join(reasons),
    }


@st.cache_data(ttl=900, show_spinner=False)
def scan_market(tickers, batch_size=80):
    rows = []

    for start in range(0, len(tickers), batch_size):
        batch = tickers[start:start + batch_size]

        try:
            raw = yf.download(
                [f"{x}.JK" for x in batch],
                period="6mo",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=True,
                group_by="ticker",
            )
        except Exception:
            continue

        if raw is None or raw.empty:
            continue

        for symbol in batch:
            yf_symbol = f"{symbol}.JK"
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if yf_symbol not in raw.columns.get_level_values(0):
                        continue
                    df = raw[yf_symbol].copy()
                else:
                    df = raw.copy()

                result = analyze_one(symbol, df)
                if result is not None:
                    rows.append(result)
            except Exception:
                continue

    return pd.DataFrame(rows)


with st.sidebar:
    st.header("⚙️ Filter Watchlist")

    min_tier = st.selectbox(
        "Minimal Tier",
        ["A", "B", "C"],
        index=0,
    )

    categories = st.multiselect(
        "Setup",
        ["BO", "PB", "REB"],
        default=["BO", "PB", "REB"],
    )

    min_score = st.slider(
        "Minimal Score",
        0, 100, 60, 5,
    )

    max_results = st.slider(
        "Jumlah saham",
        5, 50, 20, 5,
    )

    if st.button("🔄 Scan ulang", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


try:
    tickers = get_yahoo_idx_tickers()
except Exception as e:
    st.error("Universe saham Yahoo Finance gagal diambil.")
    st.code(str(e))
    st.stop()

if not tickers:
    st.error("Tidak ada ticker Indonesia/JKT yang ditemukan.")
    st.stop()

st.info(
    f"Universe: **{len(tickers)} saham** dari Yahoo Finance "
    "(region Indonesia / exchange JKT)."
)

with st.spinner(f"Menganalisis {len(tickers)} saham..."):
    result_df = scan_market(tickers)

if result_df.empty:
    st.warning("Belum ada kandidat yang memenuhi setup.")
    st.stop()

tier_order = {"A": 0, "B": 1, "C": 2}
result_df["_tier_order"] = result_df["Tier"].map(tier_order)

allowed_tiers = list(tier_order.keys())[list(tier_order.keys()).index(min_tier):]

filtered = result_df[
    result_df["Tier"].isin(allowed_tiers)
    & result_df["Kategori"].isin(categories)
    & (result_df["Score"] >= min_score)
].copy()

# Pastikan kolom sorting benar-benar ada sebelum sort.
sort_cols = [c for c in ["_tier_order", "Score", "RR_TP2"] if c in filtered.columns]
sort_ascending = [True, False, False][:len(sort_cols)]

if sort_cols:
    filtered = filtered.sort_values(
        sort_cols,
        ascending=sort_ascending,
    )

filtered = filtered.head(max_results)

st.subheader("🎯 Kandidat Untuk Dicek Besok")

if filtered.empty:
    st.warning(
        "Tidak ada kandidat yang memenuhi filter. "
        "Coba turunkan Minimal Score atau pilih Tier B/C."
    )
else:
    table = filtered[
        [
            "Kode", "Tier", "Kategori",
            "Entry Low", "Entry High",
            "TP1", "TP2", "SL",
            "RR_TP1", "RR_TP2",
            "Score", "RSI", "Vol x",
        ]
    ].copy()

    for col in ["Entry Low", "Entry High", "TP1", "TP2", "SL"]:
        table[col] = table[col].round(2)

    for col in ["RR_TP1", "RR_TP2"]:
        table[col] = table[col].map(lambda x: f"{x:.2f}R")

    table = table.rename(columns={
        "RR_TP1": "R/R TP1",
        "RR_TP2": "R/R TP2",
    })

    table["RSI"] = table["RSI"].round(1)
    table["Vol x"] = table["Vol x"].map(lambda x: f"{x:.2f}x")

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Entry adalah zona, bukan harga wajib. Kandidat tetap perlu "
        "dikonfirmasi manual saat market buka, terutama TF 15M/5M."
    )

    with st.expander("📌 Alasan tiap kandidat"):
        reason_table = filtered[
            ["Kode", "Tier", "Kategori", "Close", "Change%", "Alasan"]
        ].copy()
        reason_table["Close"] = reason_table["Close"].round(2)
        reason_table["Change%"] = reason_table["Change%"].map(lambda x: f"{x:+.2f}%")
        st.dataframe(reason_table, use_container_width=True, hide_index=True)

    csv = filtered.drop(columns=["_tier_order"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Watchlist CSV",
        data=csv,
        file_name="watchlist_besok.csv",
        mime="text/csv",
    )

c1, c2, c3 = st.columns(3)
c1.metric("Universe", len(tickers))
c2.metric("Lolos scan", len(result_df))
c3.metric("Watchlist", len(filtered))

st.caption(
    "⚠️ Ini screening teknikal, bukan jaminan harga naik besok. "
    "OHLCV berasal dari Yahoo Finance melalui yfinance."
    )
    
