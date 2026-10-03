import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Futures Journal Converter", page_icon="", layout="wide")

# ---------- extra styling ----------
st.markdown("""
<style>
  .block-container { padding-top: 2.2rem; }
  h1 {
    background: linear-gradient(90deg, #00c2ff 0%, #7b2ff7 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  div[data-testid="stMetric"] {
    background: rgba(128,128,128,.10);
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 14px;
    padding: 14px 18px;
  }
</style>
""", unsafe_allow_html=True)

REQUIRED_COLS = ["futures", "opening time", "average entry price", "average closing price",
                 "closed amount", "closed value", "position pnl", "realized pnl",
                 "funding fees", "position fee", "closed time"]

st.title("⚡ Futures Journal Converter")
st.caption("Long / Short positions → Buy / Sell execution rows  •  USDT suffix stripped  •  Fee = position fee − funding fees")

# ---------- sidebar ----------
uploaded   = st.sidebar.file_uploader("Upload journal CSV", type=["csv"])
drop_dups  = st.sidebar.checkbox("Remove exact duplicate rows", value=True)
sort_time  = st.sidebar.checkbox("Sort output chronologically", value=True)

if uploaded is None:
    st.info("👆 Upload your futures trading journal CSV to get started.")
    st.stop()

raw = pd.read_csv(uploaded)

missing = [c for c in REQUIRED_COLS if c not in raw.columns]
if missing:
    st.error(f"Input is missing required columns: {', '.join(missing)}")
    st.stop()

if drop_dups:
    before = len(raw)
    raw = raw.drop_duplicates()
    if before - len(raw):
        st.sidebar.warning(f"Removed {before - len(raw)} duplicate row(s).")

if raw.empty:
    st.warning("The file contains no data rows.")
    st.stop()

# ---------- transformation (finalized logic) ----------
df = raw.copy()
df["Direction"] = df["futures"].str.split(" ").str[1].str.split("·").str[0]          # Long / Short
df["Symbol"]    = df["futures"].str.split(" ").str[0].str.replace(r"USDT(\.P)?$", "", regex=True)
df["Quantity"]  = df["closed amount"].str.split(" ").str[0].astype(float)
df["Fee"]       = df["position fee"] - df["funding fees"]                            # your corrected math
df["close_ts"]  = pd.to_datetime(df["closed time"])

entries = pd.DataFrame({
    "Symbol": df["Symbol"].values,
    "Side": df["Direction"].map({"Long": "Buy",  "Short": "Sell"}).values,
    "Quantity": df["Quantity"].values,
    "Price": df["average entry price"].values,
    "Timestamp": df["opening time"].values,
    "Fee": 0.0,
    "Status": "Entry",
})
exits = pd.DataFrame({
    "Symbol": df["Symbol"].values,
    "Side": df["Direction"].map({"Long": "Sell", "Short": "Buy"}).values,
    "Quantity": df["Quantity"].values,
    "Price": df["average closing price"].values,
    "Timestamp": df["closed time"].values,
    "Fee": df["Fee"].values,
    "Status": "Exit",
})
out = pd.concat([entries, exits], ignore_index=True)

if sort_time:
    out["_t"] = pd.to_datetime(out["Timestamp"])
    out = out.sort_values("_t", kind="stable").drop(columns="_t").reset_index(drop=True)

# ---------- headline metrics ----------
st.success(f"✅ Converted {len(df)} trades into {len(out)} Buy/Sell rows.")
wins = int((df["realized pnl"] > 0).sum())
m1, m2, m3, m4 = st.columns(4)
m1.metric("Trades", len(df))
m2.metric("Win rate", f"{wins / len(df) * 100:.1f}%", delta=f"{wins}W / {len(df) - wins}L")
m3.metric("Realized PnL", f"{df['realized pnl'].sum():,.2f}")
m4.metric("Total fees", f"{df['Fee'].sum():,.4f}")

# ---------- tabs ----------
tab_trades, tab_charts, tab_raw = st.tabs(["📑 Converted trades", "📊 Analytics", "🧾 Raw input"])

with tab_trades:
    st.dataframe(out, use_container_width=True, height=430)
    csv = out.to_csv(index=False).encode("utf-8-sig")     # utf-8-sig = Excel-friendly
    st.download_button("⬇️ Download converted CSV", data=csv,
                       file_name="converted_buy_sell.csv",
                       mime="text/csv", type="primary")

with tab_charts:
    perf = df.sort_values("close_ts").copy()
    perf["cum_pnl"] = perf["realized pnl"].cumsum()
    perf["result"]  = perf["realized pnl"].apply(lambda v: "Win" if v > 0 else "Loss")

    c1, c2 = st.columns([2, 1])
    with c1:
        fig1 = px.area(perf, x="close_ts", y="cum_pnl",
                       title="Equity curve (cumulative realized PnL)")
        fig1.update_layout(height=380, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.pie(perf, names="result", hole=0.55, title="Win / Loss",
                      color="result", color_discrete_map={"Win": "#2cc985", "Loss": "#e5484d"})
        fig2.update_layout(height=380, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

    by_sym = df.groupby("Symbol", as_index=False)["realized pnl"].sum().sort_values("realized pnl")
    by_sym["win"] = by_sym["realized pnl"] > 0
    fig3 = px.bar(by_sym, x="Symbol", y="realized pnl", color="win",
                  color_discrete_map={True: "#2cc985", False: "#e5484d"},
                  title="PnL by symbol")
    fig3.update_layout(height=380, showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
    st.plotly_chart(fig3, use_container_width=True)

with tab_raw:
    st.dataframe(raw, use_container_width=True, height=430)