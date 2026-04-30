# app.py — Scrollable Teaching Valuation App (Equations Included)

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from io import BytesIO
import time

st.set_page_config(page_title="DCF Learning Platform", layout="wide")

st.title("📘 Equity Valuation — Step-by-Step with Equations")

# ---------------------------
# LOAD DATA
# ---------------------------
st.sidebar.header("Load Company")

ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
load_btn = st.sidebar.button("Load Data")

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

if load_btn:
    with st.spinner(f"Loading {ticker}..."):
        time.sleep(0.5)
        data, hist = load_stock(ticker)
else:
    st.stop()

if not data["price"]:
    st.error("No data found.")
    st.stop()

# =========================================================
# 1. MARKET INPUTS
# =========================================================
st.header("1️⃣ Market Inputs")

st.markdown("""
### Equations
- **Equity Value = Price × Shares**
- **Enterprise Value = Equity + Debt − Cash**

These are the starting building blocks of valuation.
""")

price = st.number_input("Stock Price", value=float(data["price"]))
shares = st.number_input("Shares Outstanding (M)", value=float((data["shares"] or 1)/1_000_000))
debt = st.number_input("Debt (M)", value=float(data["debt"]/1_000_000))
cash = st.number_input("Cash (M)", value=float(data["cash"]/1_000_000))

equity_value = price * shares
st.success(f"Equity Value = {equity_value:,.2f}M")

# =========================================================
# 2. COST OF EQUITY
# =========================================================
st.header("2️⃣ Cost of Equity (CAPM)")

st.markdown("""
### Equation
**Re = Risk-Free Rate + Beta × Equity Risk Premium**

- Risk-Free → baseline return  
- Beta → volatility vs market  
- ERP → extra return investors demand
""")

rf = st.slider("Risk-Free Rate %", 0, 10, 4)/100
beta = st.number_input("Beta", value=float(data["beta"] or 1.0))
erp = st.slider("Equity Risk Premium %", 0, 10, 5)/100

cost_equity = rf + beta * erp
st.success(f"Cost of Equity = {cost_equity:.2%}")

# =========================================================
# 3. WACC
# =========================================================
st.header("3️⃣ Weighted Average Cost of Capital (WACC)")

st.markdown("""
### Equation
**WACC = (E/(E+D))×Re + (D/(E+D))×Rd×(1−Tax)**

Blends cost of equity and debt based on capital structure.
""")

market_cap = equity_value
tax = st.slider("Tax Rate %", 0, 40, 21)/100
cod = st.slider("Cost of Debt %", 0, 10, 5)/100

wacc = (market_cap/(market_cap+debt))*cost_equity + \
       (debt/(market_cap+debt))*cod*(1-tax)

st.success(f"WACC = {wacc:.2%}")

# =========================================================
# 4. FCFF
# =========================================================
st.header("4️⃣ Forecast Free Cash Flow")

st.markdown("""
### Equation
**FCFFₜ = FCFF₀ × (1 + g)ᵗ**

Projects future operating cash flow.
""")

fcff0 = st.number_input("Current FCFF ($M)", value=60000.0)
g = st.slider("Growth Rate %", 0, 20, 5)/100
n = st.slider("Forecast Years", 3, 10, 5)

fcff = [fcff0*(1+g)**t for t in range(1, n+1)]
st.write("Projected FCFF:", [round(x,2) for x in fcff])

# =========================================================
# 5. DISCOUNTING
# =========================================================
st.header("5️⃣ Discount Cash Flows")

st.markdown("""
### Equation
**PV = CFₜ / (1 + WACC)ᵗ**

Converts future cash into today's value.
""")

pv = [cf/(1+wacc)**t for t,cf in enumerate(fcff,1)]
st.write("Present Values:", [round(x,2) for x in pv])

# =========================================================
# 6. TERMINAL VALUE
# =========================================================
st.header("6️⃣ Terminal Value")

st.markdown("""
### Equation
**TV = CFₙ × (1 + g) / (WACC − g)**

Captures value beyond forecast period.
""")

tg = st.slider("Terminal Growth %", 0, 5, 3)/100

tv = fcff[-1]*(1+tg)/(wacc-tg)
pv_tv = tv/(1+wacc)**n

st.success(f"Terminal Value = {tv:,.2f}")
st.success(f"PV Terminal Value = {pv_tv:,.2f}")

# =========================================================
# 7. ENTERPRISE VALUE
# =========================================================
st.header("7️⃣ Enterprise Value")

st.markdown("""
### Equation
**EV = Σ PV(FCFF) + PV(Terminal Value)**
""")

ev = sum(pv) + pv_tv
st.success(f"Enterprise Value = {ev:,.2f}")

# =========================================================
# 8. EQUITY VALUE
# =========================================================
st.header("8️⃣ Equity Value")

st.markdown("""
### Equation
**Equity Value = EV − Debt + Cash**
""")

equity = ev - debt + cash
value_per_share = equity / shares

st.success(f"Equity Value = {equity:,.2f}")
st.success(f"Value per Share = {value_per_share:,.2f}")

# =========================================================
# 9. RELATIVE VALUATION
# =========================================================
st.header("9️⃣ Relative Valuation (P/E)")

st.markdown("""
### Equation
**Value = EPS × P/E Multiple**

Uses market comparables instead of cash flows.
""")

eps = st.number_input("EPS", value=float(data["eps"] or 0))
pe = st.slider("Target P/E", 5, 40, 20)

pe_value = eps * pe
st.success(f"P/E Value = {pe_value:,.2f}")

# =========================================================
# 10. FINAL VALUE
# =========================================================
st.header("🔟 Final Valuation")

st.markdown("""
### Equation
**Intrinsic Value = Average(DCF Value, Relative Value)**

Combines multiple valuation approaches.
""")

final_value = np.mean([value_per_share, pe_value])

st.metric("Intrinsic Value", f"${final_value:,.2f}")
st.metric("Upside", f"{(final_value/price-1)*100:,.1f}%")

# =========================================================
# CHART
# =========================================================
st.subheader("Price Chart")
st.line_chart(hist["Close"])

def to_excel():
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book

        # =========================
        # INPUTS SHEET
        # =========================
        inputs = [
            ["Price", price],
            ["Shares (M)", shares],
            ["Debt (M)", debt],
            ["Cash (M)", cash],
            ["Beta", beta],
            ["Risk-Free", rf],
            ["ERP", erp],
            ["Cost of Debt", cod],
            ["Tax Rate", tax],
            ["Growth", g],
            ["Terminal Growth", tg],
            ["Years", n],
            ["FCFF0", fcff0],
            ["EPS", eps],
            ["Target P/E", pe],
        ]

        df_inputs = pd.DataFrame(inputs, columns=["Variable", "Value"])
        df_inputs.to_excel(writer, sheet_name="Inputs", index=False)

        ws_inputs = writer.sheets["Inputs"]

        # Helper function for clean references
        def ref(row):
            return f"Inputs!B{row}"

        PRICE = ref(2)
        SHARES = ref(3)
        DEBT = ref(4)
        CASH = ref(5)
        BETA = ref(6)
        RF = ref(7)
        ERP = ref(8)
        COD = ref(9)
        TAX = ref(10)
        G = ref(11)
        TG = ref(12)
        YEARS = int(n)
        FCFF0 = ref(14)
        EPS = ref(15)
        PE = ref(16)

        # =========================
        # MODEL SHEET
        # =========================
        ws = wb.add_worksheet("DCF Model")

        headers = ["Year", "FCFF", "Discount Factor", "PV FCFF"]
        for col, h in enumerate(headers):
            ws.write(0, col, h)

        for t in range(1, YEARS + 1):
            row = t

            # Year
            ws.write(row, 0, t)

            # FCFF forecast
            ws.write_formula(row, 1, f"={FCFF0}*(1+{G})^{t}")

            # WACC formula inline
            wacc = f"(({PRICE}*{SHARES})/(({PRICE}*{SHARES})+{DEBT}))*({RF}+{BETA}*{ERP}) + ({DEBT}/(({PRICE}*{SHARES})+{DEBT}))*{COD}*(1-{TAX})"

            # Discount factor
            ws.write_formula(row, 2, f"=1/(1+({wacc}))^{t}")

            # PV
            ws.write_formula(row, 3, f"=B{row+1}*C{row+1}")

        last = YEARS + 1

        # =========================
        # TERMINAL VALUE
        # =========================
        ws.write("A10", "Terminal Value")
        ws.write_formula(
            "B10",
            f"=B{last}*(1+{TG})/(({wacc})-{TG})"
        )

        ws.write("A11", "PV Terminal")
        ws.write_formula(
            "B11",
            f"=B10/(1+({wacc}))^{YEARS}"
        )

        # =========================
        # ENTERPRISE VALUE
        # =========================
        ws.write("A13", "Enterprise Value")
        ws.write_formula(
            "B13",
            f"=SUM(D2:D{last})+B11"
        )

        # =========================
        # EQUITY VALUE
        # =========================
        ws.write("A14", "Equity Value")
        ws.write_formula(
            "B14",
            f"=B13-{DEBT}+{CASH}"
        )

        ws.write("A15", "Value per Share")
        ws.write_formula(
            "B15",
            f"=B14/{SHARES}"
        )

        # =========================
        # RELATIVE VALUATION
        # =========================
        ws.write("A17", "P/E Value")
        ws.write_formula(
            "B17",
            f"={EPS}*{PE}"
        )

        # =========================
        # FINAL VALUE
        # =========================
        ws.write("A19", "Final Value")
        ws.write_formula(
            "B19",
            "=AVERAGE(B15,B17)"
        )

        # =========================
        # SUMMARY SHEET
        # =========================
        summary = wb.add_worksheet("Summary")

        summary.write("A1", "Intrinsic Value")
        summary.write_formula("B1", "= 'DCF Model'!B19")

        summary.write("A2", "Current Price")
        summary.write_formula("B2", f"={PRICE}")

        summary.write("A3", "Upside")
        summary.write_formula("B3", "=B1/B2-1")

    return output.getvalue()
# ---------------------------
# EXCEL DOWNLOAD BUTTON
# ---------------------------
excel_data = to_excel()

st.markdown("---")

st.download_button(
    label="📥 Download Full DCF Excel Model",
    data=excel_data,
    file_name=f"{ticker}_DCF_Model.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)