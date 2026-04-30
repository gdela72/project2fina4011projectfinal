# app.py — Teaching Dashboard Version

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from io import BytesIO
import time

st.set_page_config(page_title="Equity Valuation Teaching Dashboard", layout="wide")

st.title("📈 Equity Valuation Teaching Dashboard")

# ---------------------------
# MODE TOGGLE
# ---------------------------
mode = st.radio(
    "Select Mode",
    ["📊 Analyst Mode", "🎓 Teaching Mode"],
    horizontal=True
)

# ---------------------------
# SIDEBAR INPUTS (EDUCATIONAL)
# ---------------------------
st.sidebar.header("📘 Model Inputs")

ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
load_btn = st.sidebar.button("Load Ticker")

if not load_btn:
    st.stop()

# ---------------------------
# DATA LOADER
# ---------------------------
@st.cache_data
def load_stock(tkr):
    stock = yf.Ticker(tkr)
    hist = stock.history(period="1y")
    fast = stock.fast_info

    data = {
        "price": fast.get("lastPrice"),
        "market_cap": fast.get("marketCap"),
        "shares": fast.get("shares"),
    }

    try:
        info = stock.info
    except:
        info = {}

    data["debt"] = info.get("totalDebt", 0)
    data["cash"] = info.get("totalCash", 0)
    data["beta"] = info.get("beta", 1.0)
    data["eps"] = info.get("forwardEps", 0)

    return data, hist

# ---------------------------
# LOADING
# ---------------------------
with st.spinner(f"Loading {ticker}..."):
    time.sleep(0.5)
    data, hist = load_stock(ticker)

if not data["price"]:
    st.error("No price data available.")
    st.stop()

# ---------------------------
# INPUTS
# ---------------------------
st.sidebar.subheader("🏢 Company Data")

current_price = st.sidebar.number_input("Stock Price", value=float(data["price"]))
shares = st.sidebar.number_input("Shares (M)", value=float((data["shares"] or 1)/1e6))
market_cap = st.sidebar.number_input("Market Cap (M)", value=float((data["market_cap"] or 0)/1e6))
debt = st.sidebar.number_input("Debt (M)", value=float(data["debt"]/1e6))
cash = st.sidebar.number_input("Cash (M)", value=float(data["cash"]/1e6))

st.sidebar.subheader("📊 Risk Inputs")

beta = st.sidebar.number_input("Beta", value=float(data["beta"]))
rf = st.sidebar.slider("Risk-Free Rate (%)", 0, 10, 4)/100
erp = st.sidebar.slider("Equity Risk Premium (%)", 0, 10, 5)/100
cod = st.sidebar.slider("Cost of Debt (%)", 0, 10, 5)/100
tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 21)/100

st.sidebar.subheader("📈 Growth")

growth = st.sidebar.slider("Growth (%)", 0, 25, 8)/100
terminal_growth = st.sidebar.slider("Terminal Growth (%)", 0, 8, 3)/100
years = st.sidebar.slider("Forecast Years", 3, 10, 5)

st.sidebar.subheader("💵 Cash Flow")

fcff0 = st.sidebar.number_input("FCFF ($M)", value=60000.0)

st.sidebar.subheader("📊 Relative")

eps = st.sidebar.number_input("EPS", value=float(data["eps"] or 0))
pe = st.sidebar.slider("Target P/E", 5, 40, 20)

# ---------------------------
# VALUATION
# ---------------------------
cost_equity = rf + beta*erp
wacc = (market_cap/(market_cap+debt))*cost_equity + (debt/(market_cap+debt))*cod*(1-tax)

fcff_vals = [fcff0*(1+growth)**t for t in range(1, years+1)]
pv_fcff = [cf/(1+wacc)**t for t,cf in enumerate(fcff_vals,1)]

tv = fcff_vals[-1]*(1+terminal_growth)/(wacc-terminal_growth)
ev = sum(pv_fcff) + tv/(1+wacc)**years
equity = ev - debt + cash
value = equity / shares

pe_value = eps * pe
avg = np.mean([value, pe_value])

# ---------------------------
# DASHBOARD
# ---------------------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("Price", f"${current_price:,.2f}")
c2.metric("DCF Value", f"${value:,.2f}")
c3.metric("Blended Value", f"${avg:,.2f}")
c4.metric("Signal", "BUY" if avg > current_price else "SELL")

st.line_chart(hist["Close"])

# ---------------------------
# TEACHING MODE
# ---------------------------
if mode == "🎓 Teaching Mode":

    st.markdown("---")
    st.header("🎓 Step-by-Step Valuation")

    step = st.selectbox("Select Step", [
        "Cost of Equity",
        "WACC",
        "Forecast",
        "Discounting",
        "Terminal Value",
        "Equity Value",
        "Final Price"
    ])

    if step == "Cost of Equity":
        st.latex(r"r_e = R_f + \beta \cdot ERP")
        st.write(f"{rf:.2%} + {beta:.2f}×{erp:.2%} = {cost_equity:.2%}")

    elif step == "WACC":
        st.latex(r"WACC = \frac{E}{E+D}r_e + \frac{D}{E+D}r_d(1-T)")
        st.write(f"WACC = {wacc:.2%}")

    elif step == "Forecast":
        st.dataframe(pd.DataFrame({
            "Year": range(1,years+1),
            "FCFF": fcff_vals
        }))

    elif step == "Discounting":
        st.dataframe(pd.DataFrame({
            "Year": range(1,years+1),
            "PV": pv_fcff
        }))

    elif step == "Terminal Value":
        st.latex(r"TV = \frac{FCFF_{n+1}}{r-g}")
        st.write(f"{tv:,.0f}")

    elif step == "Equity Value":
        st.metric("Equity Value", f"${equity:,.0f}M")

    elif step == "Final Price":
        st.metric("Intrinsic Price", f"${value:,.2f}")

# ---------------------------
# VALUE DRIVERS
# ---------------------------
st.subheader("📊 Value Drivers")

driver_df = pd.DataFrame({
    "Component": ["DCF Value", "P/E Value"],
    "Value": [value, pe_value]
})

st.bar_chart(driver_df.set_index("Component"))

# ---------------------------
# INSIGHTS
# ---------------------------
st.subheader("🧠 Insights")

if wacc > 0.12:
    st.warning("High WACC reduces valuation")

if growth > 0.12:
    st.info("High growth assumption driving value")

if terminal_growth > 0.04:
    st.warning("Terminal growth may be aggressive")

# ---------------------------
# EXCEL EXPORT
# ---------------------------
def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame({"Value":[value]}).to_excel(writer, sheet_name="Summary")
    return output.getvalue()

st.markdown("---")
st.download_button(
    "📥 Download Excel Model",
    data=to_excel(),
    file_name=f"{ticker}_model.xlsx"
)