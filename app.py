import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="IDX Signal Table", page_icon="📊", layout="wide")

st.title("📊 IDX Signal Table")
st.caption("Universe saham Indonesia dari Yahoo Finance • OHLCV Daily • model teknikal sederhana")


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


def analyze_one(symbol, data):
    if data is None or data.empty:
        return None

    df = data.copy().dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    if len(df) < 60:
        return None

    close = df["Close"]
    high = df["High"]
    volume = df["Volume"]

    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["VOL20"] = volume.rolling(20).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(last["Close"])
    ma20 = float(last["MA20"])
    ma50 = float(last["MA50"])
    vol20 = float(last["VOL20"])
    rsi = float(last["RSI14"])

    if not all(np.isfinite(x) for x in [price, ma20, ma50, vol20, rsi]):
        return None

    volume_ratio = float(last["Volume"]) / vol20 if vol20 > 0 else 0
    bullish = float(last["Close"]) > float(last["Open"])
    high20 = float(high.tail(20).max())
    prev_high20 = float(high.iloc[-21:-1].max())

    score = 0
    if price > ma20:
        score += 20
    if ma20 > ma50:
        score += 20
    if bullish:
        score += 10
    if volume_ratio >= 1.0:
        score += 10
    if volume_ratio >= 1.5:
        score += 10
    if price >= prev_high20:
        score += 20
    if price > float(prev["Close"]):
        score += 5
    if 45 <= rsi <= 70:
        score += 5

    near_ma20 = abs(price - ma20) / price <= 0.025
    breakout = price >= prev_high20 and volume_ratio >= 1.2
    pullback = price > ma50 and near_ma20 and bullish and 40 <= rsi <= 65

    if breakout or pullback:
        category = "PB"
    elif price < ma20 and ma20 < ma50:
        category = "DT"
    else:
        category = "PB" if price >= ma50 else "DT"

    if score >= 75:
        tier = "A"
    elif score >= 60:
        tier = "B"
    else:
        tier = "C"

    high_pct = ((high20 / price) - 1) * 100 if price > 0 else 0

    return {
        "Kode": symbol,
        "Tier": tier,
        "Kategori": category,
        "Entry Price": price,
        "High": high20,
        "High%": high_pct,
        "Score": score,
        "RSI": rsi,
        "Vol x": volume_ratio,
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
    st.header("Pengaturan")

    min_tier = st.selectbox("Tampilkan mulai Tier", ["A", "B", "C"], index=0)

    category_filter = st.multiselect(
        "Kategori",
        ["PB", "DT"],
        default=["PB", "DT"],
    )

    min_score = st.slider("Minimum Score", 0, 100, 55, 5)

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
    st.error("Tidak ada ticker Indonesia/JKT yang berhasil ditemukan.")
    st.stop()

st.info(f"Yahoo Finance menemukan {len(tickers)} saham di region Indonesia / exchange JKT.")

with st.spinner(f"Mengambil OHLCV Daily dan menganalisis {len(tickers)} saham..."):
    result_df = scan_market(tickers)

if result_df.empty:
    st.error("Belum ada data OHLCV yang berhasil dianalisis.")
    st.stop()

tier_order = {"A": 0, "B": 1, "C": 2}
result_df["_tier_order"] = result_df["Tier"].map(tier_order)
allowed_tiers = list(tier_order.keys())[list(tier_order.keys()).index(min_tier):]

filtered = result_df[
    result_df["Tier"].isin(allowed_tiers)
    & result_df["Kategori"].isin(category_filter)
    & (result_df["Score"] >= min_score)
].copy()

filtered = filtered.sort_values(
    ["_tier_order", "Score", "High%"],
    ascending=[True, False, False],
)

display_df = filtered[["Kode", "Tier", "Kategori", "Entry Price", "High", "High%"]].copy()
display_df["Entry Price"] = display_df["Entry Price"].round(2)
display_df["High"] = display_df["High"].round(2)
display_df["High%"] = display_df["High%"].map(lambda x: f"{x:+.1f}%")

st.subheader("INFORMASI SINYAL & MANAJEMEN RISIKO")

st.dataframe(display_df, use_container_width=True, hide_index=True)

c1, c2, c3 = st.columns(3)
c1.metric("Saham dianalisis", len(result_df))
c2.metric("Sinyal setelah filter", len(filtered))
c3.metric("Tier A", int((result_df["Tier"] == "A").sum()))

if not filtered.empty:
    csv = filtered.drop(columns=["_tier_order"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download hasil CSV",
        data=csv,
        file_name="idx_signal_table.csv",
        mime="text/csv",
    )

    with st.expander("Detail skor"):
        detail = filtered[["Kode", "Tier", "Kategori", "Score", "RSI", "Vol x"]].copy()
        detail["RSI"] = detail["RSI"].round(1)
        detail["Vol x"] = detail["Vol x"].round(2)
        st.dataframe(detail, use_container_width=True, hide_index=True)

st.caption(
    "Catatan: High = high tertinggi 20 sesi terakhir, bukan prediksi masa depan. "
    "High% = jarak High 20 hari terhadap Entry Price. OHLCV berasal dari Yahoo Finance."
)
