# app.py — Mode-Based Elite Valuation App

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from io import BytesIO
import time

st.set_page_config(page_title="Equity Valuation", layout="wide")

st.title("📈 Equity Valuation Platform")

# ---------------------------
# MODE SELECTOR
# ---------------------------
mode = st.sidebar.radio("Mode", ["Valuation", "Learn DCF"])

# ===========================
# TEACHING MODE
# ===========================
if mode == "Learn DCF":

    st.subheader("📘 How a DCF Model Works")

    st.markdown("""
### Step 1: Forecast Cash Flows
FCFFₜ = FCFF₀ × (1 + g)ᵗ  

### Step 2: Discounting
PV = CFₜ / (1 + WACC)ᵗ  

### Step 3: Terminal Value
TV = CFₙ × (1 + g) / (WACC - g)  

### Step 4: Enterprise Value
EV = Σ PV + PV(TV)  

### Step 5: Equity Value
Equity = EV - Debt + Cash  

### Step 6: Per Share Value
Value = Equity / Shares  

---

### 🔥 Key Insight
DCF is **extremely sensitive** to:
- WACC  
- Terminal Growth  

Even a 1% change can swing valuation massively.
""")

    st.stop()

# ===========================
# VALUATION MODE
# ===========================

st.sidebar.header("Inputs")

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
    st.error("No data found.")
    st.stop()

# ---------------------------
# OVERRIDES
# ---------------------------
st.sidebar.subheader("Override Data")

price = st.sidebar.number_input("Price", value=float(data["price"]))
shares = st.sidebar.number_input("Shares (M)", value=float((data["shares"] or 1)/1_000_000))
market_cap = st.sidebar.number_input("Market Cap (M)", value=float((data["market_cap"] or 0)/1_000_000))
debt = st.sidebar.number_input("Debt (M)", value=float(data["debt"]/1_000_000))
cash = st.sidebar.number_input("Cash (M)", value=float(data["cash"]/1_000_000))
beta = st.sidebar.number_input("Beta", value=float(data["beta"] or 1.0))
eps = st.sidebar.number_input("EPS", value=float(data["eps"] or 0))

# ---------------------------
# ASSUMPTIONS
# ---------------------------
g = st.sidebar.slider("Growth %", 0, 25, 8)/100
tg = st.sidebar.slider("Terminal Growth %", 0, 8, 3)/100
n = st.sidebar.slider("Years", 3, 10, 5)

rf = st.sidebar.slider("Risk-Free %", 0, 10, 4)/100
erp = st.sidebar.slider("ERP %", 0, 10, 5)/100
tax = st.sidebar.slider("Tax %", 0, 40, 21)/100
cod = st.sidebar.slider("Cost of Debt %", 0, 10, 5)/100

fcff0 = st.sidebar.number_input("FCFF ($M)", value=60000.0)
pe = st.sidebar.slider("Target P/E", 5, 40, 20)

# ---------------------------
# VALUATION
# ---------------------------
cost_equity = rf + beta*erp
wacc = (market_cap/(market_cap+debt))*cost_equity + (debt/(market_cap+debt))*cod*(1-tax)

fcff = [fcff0*(1+g)**t for t in range(1,n+1)]
pv = [cf/(1+wacc)**t for t,cf in enumerate(fcff,1)]

tv = fcff[-1]*(1+tg)/(wacc-tg)
value = (sum(pv)+tv/(1+wacc)**n - debt + cash)/shares

pe_val = eps * pe
final_val = np.mean([value, pe_val])

# ---------------------------
# OUTPUT
# ---------------------------
c1,c2,c3 = st.columns(3)

c1.metric("Price", f"${price:,.2f}")
c2.metric("Intrinsic Value", f"${final_val:,.2f}")
c3.metric("Upside", f"{(final_val/price-1)*100:,.1f}%")

st.line_chart(hist["Close"])

# ---------------------------
# EXCEL
# ---------------------------
def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame({"Value":[final_val]}).to_excel(writer, sheet_name="Summary")
    return output.getvalue()

st.download_button("📥 Download Excel", data=to_excel(), file_name="valuation.xlsx")