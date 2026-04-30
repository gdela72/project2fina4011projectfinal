# app.py — Elite Equity Valuation Platform (Final)

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from io import BytesIO
import time

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(page_title="Elite Equity Valuation", page_icon="📈", layout="wide")

st.title("📈 Elite Equity Valuation Platform")
st.caption("DCF + Relative Valuation + Sensitivity Analysis")

# ---------------------------
# SIDEBAR INPUT
# ---------------------------
st.sidebar.header("Inputs")

ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
load_btn = st.sidebar.button("Load Ticker")

if not load_btn:
    st.stop()

# ---------------------------
# DATA LOADER (ROBUST)
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
# LOADING SCREEN
# ---------------------------
with st.spinner(f"Loading data for {ticker}..."):
    time.sleep(0.6)
    data, hist = load_stock(ticker)

if not data["price"]:
    st.error("No price data found for this ticker.")
    st.stop()

# ---------------------------
# USER OVERRIDES
# ---------------------------
st.sidebar.subheader("Data Overrides")

current_price = st.sidebar.number_input("Current Price", value=float(data["price"] or 0))
shares = st.sidebar.number_input("Shares Outstanding (M)", value=float((data["shares"] or 1)/1_000_000))
market_cap = st.sidebar.number_input("Market Cap (M)", value=float((data["market_cap"] or 0)/1_000_000))
debt = st.sidebar.number_input("Debt (M)", value=float(data["debt"]/1_000_000))
cash = st.sidebar.number_input("Cash (M)", value=float(data["cash"]/1_000_000))
beta = st.sidebar.number_input("Beta", value=float(data["beta"] or 1.0))
eps = st.sidebar.number_input("Forward EPS", value=float(data["eps"] or 0))

# ---------------------------
# WARNINGS
# ---------------------------
missing = []
if not data["eps"]: missing.append("EPS")
if not data["beta"]: missing.append("Beta")
if not data["shares"]: missing.append("Shares")

if missing:
    st.warning(f"Missing data: {', '.join(missing)} — using manual inputs.")

# ---------------------------
# ASSUMPTIONS
# ---------------------------
growth = st.sidebar.slider("Growth %", 0, 25, 8)/100
terminal_growth = st.sidebar.slider("Terminal Growth %", 0, 8, 3)/100
years = st.sidebar.slider("Forecast Years", 3, 10, 5)

rf = st.sidebar.slider("Risk-Free %", 0, 10, 4)/100
erp = st.sidebar.slider("ERP %", 0, 10, 5)/100
tax = st.sidebar.slider("Tax Rate %", 0, 40, 21)/100
cod = st.sidebar.slider("Cost of Debt %", 0, 10, 5)/100

fcfe0 = st.sidebar.number_input("FCFE ($M)", value=50000.0)
fcff0 = st.sidebar.number_input("FCFF ($M)", value=60000.0)
pe = st.sidebar.slider("Target P/E", 5, 40, 20)

# ---------------------------
# VALUATION
# ---------------------------
cost_equity = rf + beta*erp
wacc = cost_equity if (market_cap+debt)==0 else (
    (market_cap/(market_cap+debt))*cost_equity +
    (debt/(market_cap+debt))*cod*(1-tax)
)

# FCFE
fcfe_vals = [fcfe0*(1+growth)**t for t in range(1, years+1)]
pv_fcfe = [cf/(1+cost_equity)**t for t,cf in enumerate(fcfe_vals,1)]
tv_fcfe = fcfe_vals[-1]*(1+terminal_growth)/(cost_equity-terminal_growth)
value_fcfe = (sum(pv_fcfe)+tv_fcfe/(1+cost_equity)**years)/shares

# FCFF
fcff_vals = [fcff0*(1+growth)**t for t in range(1, years+1)]
pv_fcff = [cf/(1+wacc)**t for t,cf in enumerate(fcff_vals,1)]
tv_fcff = fcff_vals[-1]*(1+terminal_growth)/(wacc-terminal_growth)
value_fcff = (sum(pv_fcff)+tv_fcff/(1+wacc)**years - debt + cash)/shares

# Relative
pe_value = eps * pe
avg = np.mean([value_fcfe, value_fcff, pe_value])

# ---------------------------
# DASHBOARD
# ---------------------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("Price", f"${current_price:,.2f}")
c2.metric("Intrinsic Value", f"${avg:,.2f}")
c3.metric("Upside", f"{(avg/current_price-1)*100:,.1f}%")
c4.metric("Signal", "BUY" if avg>current_price else "SELL")

st.subheader("Price Chart")
st.line_chart(hist["Close"])

# ---------------------------
# EXCEL MODEL (FORMULA-BASED)
# ---------------------------
def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book

        inputs = pd.DataFrame({
            "Variable":["Price","Shares","MarketCap","Debt","Cash","Beta","RF","ERP","COD","Tax","Growth","TG","Years","FCFE0","FCFF0","PE","EPS"],
            "Value":[current_price,shares,market_cap,debt,cash,beta,rf,erp,cod,tax,growth,terminal_growth,years,fcfe0,fcff0,pe,eps]
        })
        inputs.to_excel(writer, sheet_name="Inputs", index=False)

        ws = wb.add_worksheet("DCF")
        for i in range(1,years+1):
            ws.write(i,0,i)
            ws.write_formula(i,1,f"=Inputs!B14*(1+Inputs!B11)^{i}")

    return output.getvalue()

st.download_button(
    "📥 Download Excel Model",
    data=to_excel(),
    file_name=f"{ticker}_model.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)