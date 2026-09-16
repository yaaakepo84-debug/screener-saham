import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Auto-Screener IDX Saham Murah", layout="wide")

st.title("🤖 AI Auto-Screener - Saham Murah & Gorengan (Full IDX)")
st.caption("Scan otomatis 800+ saham Bursa Efek Indonesia untuk cari saham ramai & berpotensi scalping")

# --- DAFTAR SELURUH / HAMPIR SEMUA TICKER IDX ---
ALL_IDX_TICKERS = [
    "AALI.JK", "ABBA.JK", "ABDA.JK", "ABMM.JK", "ACES.JK", "ACST.JK", "ADEL.JK", "ADHI.JK", "ADCP.JK", "ADMR.JK",
    "ADRO.JK", "AGAR.JK", "AGII.JK", "AGRO.JK", "AGRS.JK", "AHAP.JK", "AIMS.JK", "AISA.JK", "AKRA.JK", "AKSI.JK",
    "ALDO.JK", "AMAG.JK", "AMAR.JK", "AMFG.JK", "AMIN.JK", "AMMN.JK", "AMRT.JK", "ANDI.JK", "ANTM.JK", "APEX.JK",
    "APIC.JK", "APLN.JK", "ARCI.JK", "ARNA.JK", "ARTA.JK", "ASGR.JK", "ASII.JK", "ASJT.JK", "ASRI.JK", "ASRM.JK",
    "AUTO.JK", "BABP.JK", "BACA.JK", "BAJA.JK", "BBCA.JK", "BBHI.JK", "BBKP.JK", "BBLD.JK", "BBMD.JK", "BBNI.JK",
    "BBRI.JK", "BBRM.JK", "BBTN.JK", "BCAT.JK", "BCIC.JK", "BDMN.JK", "BEBS.JK", "BEST.JK", "BFIN.JK", "BGTG.JK",
    "BHIT.JK", "BIPI.JK", "BIRD.JK", "BISI.JK", "BJBR.JK", "BJTM.JK", "BKSL.JK", "BKSW.JK", "BLTA.JK", "BLTZ.JK",
    "BMAS.JK", "BMRI.JK", "BMTR.JK", "BNBR.JK", "BNGA.JK", "BNII.JK", "BNLI.JK", "BOGA.JK", "BOLT.JK", "BOSS.JK",
    "BSDE.JK", "BSIM.JK", "BSBK.JK", "BTPS.JK", "BVIC.JK", "BUMI.JK", "BRMS.JK", "BRPT.JK", "BUKA.JK", "CASA.JK",
    "CAST.JK", "CEKA.JK", "CENT.JK", "CFIN.JK", "CINT.JK", "CITA.JK", "CITY.JK", "CLPI.JK", "CMNP.JK", "CMRY.JK",
    "CNTX.JK", "COAL.JK", "CPIN.JK", "CPRO.JK", "CSAP.JK", "CSIS.JK", "CSRA.JK", "CTRA.JK", "CUAN.JK", "DART.JK",
    "DEWA.JK", "DGGN.JK", "DILD.JK", "DIVA.JK", "DKFT.JK", "DLTA.JK", "DMAS.JK", "DNAR.JK", "DNET.JK", "DOOH.JK",
    "DOID.JK", "DRMA.JK", "DSFI.JK", "DSNG.JK", "DSSD.JK", "DUTI.JK", "DVLA.JK", "ECII.JK", "ELSA.JK", "EMTK.JK",
    "ENRG.JK", "EPMT.JK", "ERAA.JK", "ERTX.JK", "ESSA.JK", "ESTI.JK", "ETWA.JK", "EXCL.JK", "FAST.JK", "FASW.JK",
    "FIRE.JK", "FMII.JK", "FORU.JK", "FPNI.JK", "FREN.JK", "FWCT.JK", "GAAA.JK", "GDST.JK", "GEMS.JK", "GGRM.JK",
    "GIAA.JK", "GJTL.JK", "GLOB.JK", "GLVA.JK", "GOOD.JK", "GOTO.JK", "GPRA.JK", "GSMF.JK", "GTBO.JK", "GTRA.JK",
    "GWSA.JK", "GZCO.JK", "HATM.JK", "HDFA.JK", "HDTX.JK", "HEAL.JK", "HERO.JK", "HEXA.JK", "HITS.JK", "HMSP.JK",
    "HOKI.JK", "HOME.JK", "HOPE.JK", "HRTA.JK", "HRUM.JK", "HUMI.JK", "IATA.JK", "IBST.JK", "ICBP.JK", "ICON.JK",
    "IDPR.JK", "IGAR.JK", "IIKP.JK", "IKAI.JK", "IKBI.JK", "IMAS.JK", "INAF.JK", "INCF.JK", "INCI.JK", "INDF.JK",
    "INDY.JK", "INKP.JK", "INPC.JK", "INPP.JK", "INRU.JK", "INTD.JK", "INTP.JK", "IPCC.JK", "IPCM.JK", "IPOL.JK",
    "IPTV.JK", "IRRA.JK", "ISAT.JK", "ISSP.JK", "ITMG.JK", "JARR.JK", "JAST.JK", "JAST.JK", "JECC.JK", "JKSW.JK",
    "JPFA.JK", "JRPT.JK", "JSMR.JK", "JSPT.JK", "JTPE.JK", "KBLI.JK", "KBLM.JK", "KBAG.JK", "KARW.JK", "KAYU.JK",
    "KDSI.JK", "KIAS.JK", "KICI.JK", "KIJA.JK", "KKGI.JK", "KLBF.JK", "KMDS.JK", "KOBX.JK", "KOIN.JK", "KAEF.JK",
    "KPAL.JK", "KPIG.JK", "KRAS.JK", "KREN.JK", "LCGP.JK", "LEAD.JK", "LION.JK", "LMPI.JK", "LMSH.JK", "LPCK.JK",
    "LPGI.JK", "LPLI.JK", "LPKR.JK", "LPCR.JK", "LRNA.JK", "LSIP.JK", "LTLS.JK", "LUCK.JK", "MAIN.JK", "MAMI.JK",
    "MAPA.JK", "MAPI.JK", "MARI.JK", "MASA.JK", "MBAP.JK", "MBSS.JK", "MBTO.JK", "MCAS.JK", "MCOL.JK", "MDCCA.JK",
    "MDKA.JK", "MDKI.JK", "MDLN.JK", "MDRN.JK", "MEDC.JK", "MEGA.JK", "MERK.JK", "METR.JK", "MFIN.JK", "MIKA.JK",
    "MINA.JK", "MIRA.JK", "MITI.JK", "MKPI.JK", "MLBI.JK", "MLIA.JK", "MLPT.JK", "MNCN.JK", "MPMX.JK", "MPPA.JK",
    "MRAT.JK", "MSIN.JK", "MTDL.JK", "MTFN.JK", "MTLA.JK", "MTPS.JK", "MYOR.JK", "MYRX.JK", "MYTX.JK", "NELY.JK",
    "NFCX.JK", "NICK.JK", "NICL.JK", "NIKL.JK", "NINE.JK", "NIPS.JK", "NIRO.JK", "NISP.JK", "NOBU.JK", "NRCA.JK",
    "OASA.JK", "OBMD.JK", "OCEAN.JK", "OJPR.JK", "OMRE.JK", "PPRE.JK", "PADI.JK", "PALM.JK", "PANI.JK", "PANR.JK",
    "PANS.JK", "PBID.JK", "PBRX.JK", "PDES.JK", "PEHA.JK", "PGAS.JK", "PGJO.JK", "PGLI.JK", "PJAA.JK", "PKPK.JK",
    "PLIN.JK", "PMJS.JK", "PNBN.JK", "PNBS.JK", "PNIN.JK", "PNLF.JK", "POLI.JK", "POLL.JK", "POLY.JK", "POOL.JK",
    "PORT.JK", "POWR.JK", "PPGL.JK", "PPRO.JK", "PRDA.JK", "PRIM.JK", "PSAB.JK", "PSDN.JK", "PSGO.JK", "PTBA.JK",
    "PTDU.JK", "PTPP.JK", "PTRO.JK", "PTSN.JK", "PUDP.JK", "PWON.JK", "PYFA.JK", "RAAM.JK", "RAJA.JK", "RALS.JK",
    "RANC.JK", "RBMS.JK", "RDTX.JK", "REAL.JK", "RELI.JK", "RICY.JK", "RIGS.JK", "RIMO.JK", "ROTI.JK", "RODA.JK",
    "SAME.JK", "SAMF.JK", "SAPX.JK", "SBAT.JK", "SCCO.JK", "SCMA.JK", "SCNP.JK", "SDMU.JK", "SDPC.JK", "SFA.JK",
    "SGER.JK", "SGMW.JK", "SGRO.JK", "SHID.JK", "SILO.JK", "SIMP.JK", "SIPD.JK", "SKBM.JK", "SKLT.JK", "SKYB.JK",
    "SLIS.JK", "SMBR.JK", "SMCB.JK", "SMDM.JK", "SMDR.JK", "SMGR.JK", "SMKL.JK", "SMMA.JK", "SMRA.JK", "SMRU.JK",
    "SMSM.JK", "SOCR.JK", "SOCI.JK", "SOFA.JK", "SOHO.JK", "SONA.JK", "SOSI.JK", "SRIL.JK", "SRSN.JK", "SRTG.JK",
    "SSIA.JK", "SSMS.JK", "SSSS.JK", "SSTC.JK", "STAA.JK", "STAT.JK", "STTP.JK", "STRK.JK", "SUGI.JK", "SULI.JK",
    "SUPR.JK", "SURE.JK", "TALF.JK", "TARA.JK", "TAXI.JK", "TBIG.JK", "TBLA.JK", "TBMS.JK", "TCID.JK", "TCMM.JK",
    "TELE.JK", "TFCO.JK", "TGRA.JK", "TIFA.JK", "TINS.JK", "TIRA.JK", "TISPC.JK", "TKIM.JK", "TLKM.JK", "TMAS.JK",
    "TMPO.JK", "TNCA.JK", "TOBA.JK", "TOTL.JK", "TOWR.JK", "TPIA.JK", "TPMA.JK", "TRAM.JK", "TRIM.JK", "TRIN.JK",
    "TRIO.JK", "TRIS.JK", "TRST.JK", "TRUK.JK", "TSPC.JK", "TUGU.JK", "ULTJ.JK", "UNIC.JK", "UNIQ.JK", "UNVR.JK",
    "URBN.JK", "VRNA.JK", "VKTR.JK", "WIFI.JK", "WICC.JK", "WIIM.JK", "WIM.JK", "WINS.JK", "WMPP.JK", "WOOD.JK",
    "WOWS.JK", "WSBP.JK", "WSKT.JK", "WTON.JK", "YPAS.JK", "YULE.JK", "ZBRA.JK", "ZINC.JK", "ZONE.JK"
]

# --- SIDEBAR PARAMETERS ---
st.sidebar.header("⚙️ Auto-Scan Configuration")

# Limit Jumlah Scan (Supaya tidak lelet di HP)
scan_limit = st.sidebar.slider("Jumlah Saham Yang Di-scan:", min_value=50, max_value=len(ALL_IDX_TICKERS), value=150, step=50)

# Filter Rentang Harga (Min & Max Price)
st.sidebar.subheader("💰 Filter Harga Saham (Gorengan)")
min_price = st.sidebar.number_input("Harga Minimum (Rp):", min_value=50, max_value=5000, value=50, step=10)
max_price = st.sidebar.number_input("Harga Maksimum (Rp):", min_value=50, max_value=10000, value=500, step=50)

# Timeframe & Strategy
timeframe = st.sidebar.selectbox("Timeframe:", ["1d", "1h", "15m"], index=0)
period_map = {"1d": "6mo", "1h": "1mo", "15m": "5d"}

st.sidebar.subheader("🎯 Kondisi AI Screener")
strategy = st.sidebar.radio(
    "Pilih Target Sinyal Scalping:",
    [
        "Volume Spike + Naik (Meledak Transaksinya)",
        "Top Gainers Saham Murah (Kenaikan High %)",
        "Breakout High 5 Hari (Potensi Lanjut Arah)",
        "Semua Saham Murah Di Rentang Harga"
    ]
)

vol_mult = st.sidebar.slider("Lonjakan Volume (x Rata-rata):", min_value=1.1, max_value=5.0, value=1.5, step=0.1)

# --- FUNCTION FETCH DATA ---
@st.cache_data(ttl=300)
def fetch_ohlcv_data(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty or len(df) < 10:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        
        df['Vol_MA'] = df['Volume'].rolling(window=10).mean()
        df['Prev_High_5'] = df['High'].shift(1).rolling(window=5).max()
        df['Change_%'] = df['Close'].pct_change() * 100
        
        return df
    except Exception:
        return None

# --- RUN AUTO SCANNER ---
if st.button(f"🚀 Mulai Scan ({scan_limit} Saham IDX)", use_container_width=True):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    selected_tickers = ALL_IDX_TICKERS[:scan_limit]
    total_tickers = len(selected_tickers)
    
    for i, symbol in enumerate(selected_tickers):
        # Update UI progress bar
        status_text.text(f"Scanning ({i+1}/{total_tickers}): {symbol}")
        progress_bar.progress((i + 1) / total_tickers)
        
        df = fetch_ohlcv_data(symbol, period_map[timeframe], timeframe)
        if df is None:
            continue
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        close_price = float(latest['Close'])
        change_pct = float(latest['Change_%'])
        volume = int(latest['Volume'])
        vol_ma = float(latest['Vol_MA']) if latest['Vol_MA'] > 0 else 1
        vol_ratio = volume / vol_ma
        
        # 1. Filter Rentang Harga
        if not (min_price <= close_price <= max_price):
            continue
        
        # 2. Filter Strategi AI
        is_match = False
        if strategy == "Volume Spike + Naik (Meledak Transaksinya)":
            is_match = (volume > vol_ma * vol_mult) and (change_pct > 0)
        elif strategy == "Top Gainers Saham Murah (Kenaikan High %)":
            is_match = change_pct >= 3.0
        elif strategy == "Breakout High 5 Hari (Potensi Lanjut Arah)":
            is_match = close_price > float(prev['Prev_High_5'])
        elif strategy == "Semua Saham Murah Di Rentang Harga":
            is_match = True

        if is_match:
            results.append({
                "Ticker": symbol.replace(".JK", ""),
                "Harga Close": int(close_price),
                "Kenaikan (%)": round(change_pct, 2),
                "Volume": volume,
                "Lonjakan Vol (x Avg)": round(vol_ratio, 2)
            })

    status_text.success("✅ Auto-scan selesai!")
    progress_bar.empty()
    st.session_state['results_df'] = pd.DataFrame(results)

# --- SHOW RESULTS ---
if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
    res_df = st.session_state['results_df'].sort_values(by="Kenaikan (%)", ascending=False)
    st.subheader(f"🔥 Ditemukan {len(res_df)} Saham Murah yang Memenuhi Kriteria:")
    st.dataframe(res_df, use_container_width=True)
    
    # Detail Chart
    st.divider()
    st.subheader("🔍 Detail Chart Saham Terpilih")
    selected_ticker = st.selectbox("Pilih Saham untuk Analisis Chart:", res_df["Ticker"].tolist())
    
    if selected_ticker:
        chart_df = fetch_ohlcv_data(f"{selected_ticker}.JK", period_map[timeframe], timeframe)
        if chart_df is not None:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=chart_df.index,
                open=chart_df['Open'],
                high=chart_df['High'],
                low=chart_df['Low'],
                close=chart_df['Close'],
                name="OHLC"
            ))
            fig.update_layout(
                title=f"Chart OHLCV - {selected_ticker}",
                xaxis_rangeslider_visible=False,
                height=450,
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)

elif 'results_df' in st.session_state and st.session_state['results_df'].empty:
    st.warning("Tidak ditemukan saham murah yang memenuhi syarat sinyal saat ini.")
               
