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

def to_excel():
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book

        # =========================
        # INPUTS SHEET
        # =========================
        inputs = pd.DataFrame({
            "Variable": [
                "Current Price","Shares (M)","Market Cap (M)",
                "Debt (M)","Cash (M)",
                "Beta","Risk Free","ERP","Cost of Debt","Tax Rate",
                "Growth","Terminal Growth","Forecast Years",
                "FCFF0","Target P/E","EPS"
            ],
            "Value": [
                current_price,shares,market_cap,
                debt,cash,
                beta,rf,erp,cod,tax,
                growth,terminal_growth,years,
                fcff0,pe,eps
            ]
        })

        inputs.to_excel(writer, sheet_name="Inputs", index=False)

        # Helper references
        def ref(r): return f"Inputs!B{r}"

        PRICE = ref(2)
        SHARES = ref(3)
        MCAP = ref(4)
        DEBT = ref(5)
        CASH = ref(6)
        BETA = ref(7)
        RF = ref(8)
        ERP = ref(9)
        COD = ref(10)
        TAX = ref(11)
        G = ref(12)
        TG = ref(13)
        N = int(years)
        FCFF0 = ref(14)

        # =========================
        # WACC SHEET
        # =========================
        wacc_ws = wb.add_worksheet("WACC")

        wacc_ws.write("A1","Cost of Equity")
        wacc_ws.write_formula("B1", f"={RF}+{BETA}*{ERP}")

        wacc_ws.write("A2","Weight Equity")
        wacc_ws.write_formula("B2", f"={MCAP}/({MCAP}+{DEBT})")

        wacc_ws.write("A3","Weight Debt")
        wacc_ws.write_formula("B3", f"={DEBT}/({MCAP}+{DEBT})")

        wacc_ws.write("A4","WACC")
        wacc_ws.write_formula("B4",
            f"=B2*B1 + B3*{COD}*(1-{TAX})"
        )

        # =========================
        # MODEL SHEET (DCF)
        # =========================
        ws = wb.add_worksheet("DCF")

        headers = ["Year","FCFF","Discount Factor","PV FCFF"]
        for i,h in enumerate(headers):
            ws.write(0,i,h)

        for t in range(1, N+1):
            row = t

            ws.write(row,0,t)

            # FCFF forecast
            ws.write_formula(row,1,
                f"={FCFF0}*(1+{G})^{t}"
            )

            # Discount factor
            ws.write_formula(row,2,
                f"=1/(1+WACC!B4)^{t}"
            )

            # PV
            ws.write_formula(row,3,
                f"=B{row+1}*C{row+1}"
            )

        last = N + 1

        # Terminal Value
        ws.write("A10","Terminal Value")
        ws.write_formula("B10",
            f"=B{last}*(1+{TG})/(WACC!B4-{TG})"
        )

        ws.write("A11","PV Terminal")
        ws.write_formula("B11",
            f"=B10/(1+WACC!B4)^{N}"
        )

        ws.write("A13","Enterprise Value")
        ws.write_formula("B13",
            f"=SUM(D2:D{last})+B11"
        )

        ws.write("A14","Equity Value")
        ws.write_formula("B14",
            f"=B13-{DEBT}+{CASH}"
        )

        ws.write("A15","Value per Share")
        ws.write_formula("B15",
            f"=B14/{SHARES}"
        )

        # =========================
        # SUMMARY SHEET
        # =========================
        summary = wb.add_worksheet("Summary")

        summary.write("A1","Intrinsic Value")
        summary.write_formula("B1","=DCF!B15")

        summary.write("A2","Current Price")
        summary.write_formula("B2", f"={PRICE}")

        summary.write("A3","Upside %")
        summary.write_formula("B3","=B1/B2-1")

        # =========================
        # SENSITIVITY TABLE
        # =========================
        sens = wb.add_worksheet("Sensitivity")

        sens.write("A1","WACC \\ g")

        g_vals = [0.02,0.03,0.04]
        wacc_vals = ["WACC!B4-0.01","WACC!B4","WACC!B4+0.01"]

        for i,gv in enumerate(g_vals):
            sens.write(0,i+1,gv)

        for j,wv in enumerate(wacc_vals):
            sens.write(j+1,0,wv)

            for i,gv in enumerate(g_vals):
                sens.write_formula(j+1,i+1,
                    f"=(DCF!B{last}*(1+{gv})/({wv}-{gv}))"
                )

    return output.getvalue()