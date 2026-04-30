# app.py
# Elite Equity Valuation App (Streamlit)
# Features:
# - Live ticker data via yfinance
# - DCF (FCFE + FCFF/WACC)
# - Relative valuation (P/E)
# - Sensitivity analysis
# - Buy / Hold / Sell signal
# - Downloadable Excel model
# - Clean professional UI

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from io import BytesIO

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Elite Equity Valuation",
    page_icon="📈",
    layout="wide"
)

# ---------------------------
# STYLING
# ---------------------------
st.markdown("""
<style>
.main {background-color:#0E1117;}
h1,h2,h3 {color:white;}
div[data-testid="metric-container"]{
    background:#1c1f26;
    padding:15px;
    border-radius:12px;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 Elite Equity Valuation Platform")
st.caption("DCF + Relative Valuation + Sensitivity Analysis")

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.header("Inputs")

ticker = st.sidebar.text_input("Ticker", "AAPL").upper()

# ---------------------------
# LOAD STOCK DATA
# ---------------------------
@st.cache_data
def load_stock(tkr):
    stock = yf.Ticker(tkr)
    info = stock.info
    hist = stock.history(period="1y")
    return info, hist

try:
    info, hist = load_stock(ticker)

    current_price = info.get("currentPrice", 0)
    shares = info.get("sharesOutstanding", 1) / 1_000_000
    market_cap = info.get("marketCap", 0) / 1_000_000
    debt = info.get("totalDebt", 0) / 1_000_000
    cash = info.get("totalCash", 0) / 1_000_000
    beta = info.get("beta", 1.0)
    eps = info.get("forwardEps", 0)

except:
    st.error("Ticker not found or no data available.")
    st.stop()

# ---------------------------
# USER ASSUMPTIONS
# ---------------------------
growth = st.sidebar.slider("Short-Term Growth %", 0, 25, 8) / 100
terminal_growth = st.sidebar.slider("Terminal Growth %", 0, 8, 3) / 100
forecast_years = st.sidebar.slider("Forecast Years", 3, 10, 5)

risk_free = st.sidebar.slider("Risk-Free Rate %", 0, 10, 4) / 100
erp = st.sidebar.slider("Equity Risk Premium %", 0, 10, 5) / 100
tax_rate = st.sidebar.slider("Tax Rate %", 0, 40, 21) / 100
cost_debt = st.sidebar.slider("Cost of Debt %", 0, 10, 5) / 100

fcfe0 = st.sidebar.number_input("Current FCFE ($M)", value=50000.0)
fcff0 = st.sidebar.number_input("Current FCFF ($M)", value=60000.0)

target_pe = st.sidebar.slider("Target P/E", 5, 40, 20)

# ---------------------------
# COST OF EQUITY / WACC
# ---------------------------
cost_equity = risk_free + beta * erp

E = market_cap
D = debt

if E + D == 0:
    wacc = cost_equity
else:
    wacc = (E/(E+D))*cost_equity + (D/(E+D))*cost_debt*(1-tax_rate)

# ---------------------------
# DCF FCFE
# ---------------------------
fcfe_vals = []
pv_fcfe = []

for t in range(1, forecast_years+1):
    cf = fcfe0 * (1+growth)**t
    pv = cf / (1+cost_equity)**t
    fcfe_vals.append(cf)
    pv_fcfe.append(pv)

tv_fcfe = fcfe_vals[-1]*(1+terminal_growth)/(cost_equity-terminal_growth)
pv_tv_fcfe = tv_fcfe/(1+cost_equity)**forecast_years

equity_fcfe = sum(pv_fcfe)+pv_tv_fcfe
value_fcfe = equity_fcfe/shares

# ---------------------------
# DCF FCFF
# ---------------------------
fcff_vals = []
pv_fcff = []

for t in range(1, forecast_years+1):
    cf = fcff0*(1+growth)**t
    pv = cf/(1+wacc)**t
    fcff_vals.append(cf)
    pv_fcff.append(pv)

tv_fcff = fcff_vals[-1]*(1+terminal_growth)/(wacc-terminal_growth)
pv_tv_fcff = tv_fcff/(1+wacc)**forecast_years

enterprise = sum(pv_fcff)+pv_tv_fcff
equity_fcff = enterprise - debt + cash
value_fcff = equity_fcff/shares

# ---------------------------
# RELATIVE VALUATION
# ---------------------------
pe_value = eps * target_pe

# ---------------------------
# SIGNAL
# ---------------------------
avg_value = np.mean([value_fcfe, value_fcff, pe_value])

if avg_value > current_price * 1.15:
    signal = "🟢 BUY"
elif avg_value < current_price * 0.85:
    signal = "🔴 SELL"
else:
    signal = "🟡 HOLD"

# ---------------------------
# TOP DASHBOARD
# ---------------------------
c1,c2,c3,c4 = st.columns(4)

c1.metric("Current Price", f"${current_price:,.2f}")
c2.metric("Intrinsic Value", f"${avg_value:,.2f}")
c3.metric("Upside / Downside", f"{(avg_value/current_price-1)*100:,.1f}%")
c4.metric("Signal", signal)

# ---------------------------
# COMPANY SNAPSHOT
# ---------------------------
st.subheader(f"{ticker} Snapshot")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Market Cap", f"${market_cap:,.0f}M")
c2.metric("Cash", f"${cash:,.0f}M")
c3.metric("Debt", f"${debt:,.0f}M")
c4.metric("Beta", f"{beta:.2f}")

# ---------------------------
# PRICE CHART
# ---------------------------
st.subheader("1-Year Price Chart")
st.line_chart(hist["Close"])

# ---------------------------
# VALUATION TABLE
# ---------------------------
st.subheader("Valuation Models")

vals = pd.DataFrame({
    "Method":["DCF FCFE","DCF FCFF","P/E Multiple"],
    "Value Per Share":[value_fcfe,value_fcff,pe_value]
})

st.dataframe(vals, use_container_width=True)

# ---------------------------
# FORECAST TABLE
# ---------------------------
st.subheader("DCF Forecast")

forecast = pd.DataFrame({
    "Year":range(1,forecast_years+1),
    "FCFE":fcfe_vals,
    "PV FCFE":pv_fcfe,
    "FCFF":fcff_vals,
    "PV FCFF":pv_fcff
})

st.dataframe(forecast, use_container_width=True)

# ---------------------------
# SENSITIVITY ANALYSIS
# ---------------------------
st.subheader("Sensitivity Analysis (WACC vs Growth)")

grid = []

for g in [0.02,0.03,0.04]:
    row = {}
    for r in [wacc-0.01,wacc,wacc+0.01]:
        tv = fcff_vals[-1]*(1+g)/(r-g)
        ev = sum(pv_fcff)+tv/(1+r)**forecast_years
        eq = ev-debt+cash
        val = eq/shares
        row[f"{r*100:.1f}%"] = round(val,2)
    grid.append(pd.Series(row,name=f"g={g*100:.1f}%"))

sens = pd.DataFrame(grid)
st.dataframe(sens)

# ---------------------------
# EDUCATION SECTION
# ---------------------------
with st.expander("How the DCF Model Works"):
    st.markdown("""
### Step 1: Forecast Cash Flows

FCFE = Cash flow available to shareholders  
FCFF = Cash flow available to debt + equity holders

### Step 2: Discount Cash Flows

PV = CF / (1+r)^t

### Step 3: Calculate Terminal Value

TV = CFₙ₊₁ / (r-g)

### Step 4: Total Value

Enterprise Value = PV Forecast + PV TV

Equity Value = EV - Debt + Cash

### Step 5: Per Share Value

Intrinsic Value = Equity Value / Shares Outstanding
""")

# ---------------------------
# EXCEL DOWNLOAD
# ---------------------------
def to_excel():
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book

        # ---------------------------
        # INPUTS SHEET
        # ---------------------------
        inputs = pd.DataFrame({
            "Variable": [
                "Current Price",
                "Shares Outstanding (M)",
                "Market Cap (M)",
                "Debt (M)",
                "Cash (M)",
                "Beta",
                "Risk-Free Rate",
                "Equity Risk Premium",
                "Cost of Debt",
                "Tax Rate",
                "Growth Rate",
                "Terminal Growth",
                "Forecast Years",
                "FCFE0",
                "FCFF0",
                "Target P/E",
                "EPS"
            ],
            "Value": [
                current_price,
                shares,
                market_cap,
                debt,
                cash,
                beta,
                risk_free,
                erp,
                cost_debt,
                tax_rate,
                growth,
                terminal_growth,
                forecast_years,
                fcfe0,
                fcff0,
                target_pe,
                eps
            ]
        })

        inputs.to_excel(writer, sheet_name="Inputs", index=False)
        ws_inputs = writer.sheets["Inputs"]

        # ---------------------------
        # DEFINE CELL REFERENCES
        # ---------------------------
        # Excel row numbers (1-based + header)
        def cell(row): return f"Inputs!B{row}"

        PRICE = cell(2)
        SHARES = cell(3)
        MCAP = cell(4)
        DEBT = cell(5)
        CASH = cell(6)
        BETA = cell(7)
        RF = cell(8)
        ERP = cell(9)
        COD = cell(10)
        TAX = cell(11)
        G = cell(12)
        TG = cell(13)
        N = int(forecast_years)
        FCFE0 = cell(14)
        FCFF0 = cell(15)
        PE = cell(16)
        EPS = cell(17)

        # ---------------------------
        # CALC SHEET (DCF MODEL)
        # ---------------------------
        ws = wb.add_worksheet("DCF")

        headers = ["Year", "FCFE", "PV FCFE", "FCFF", "PV FCFF"]
        for col, h in enumerate(headers):
            ws.write(0, col, h)

        for t in range(1, N + 1):
            row = t

            # Year
            ws.write(row, 0, t)

            # FCFE = FCFE0 * (1+g)^t
            ws.write_formula(row, 1,
                f"={FCFE0}*(1+{G})^{t}"
            )

            # Cost of Equity = RF + Beta*ERP
            cost_eq = f"({RF}+{BETA}*{ERP})"

            # PV FCFE
            ws.write_formula(row, 2,
                f"=B{row+1}/(1+{cost_eq})^{t}"
            )

            # FCFF
            ws.write_formula(row, 3,
                f"={FCFF0}*(1+{G})^{t}"
            )

            # WACC
            wacc = f"(({MCAP}/({MCAP}+{DEBT}))*({cost_eq}) + ({DEBT}/({MCAP}+{DEBT}))*{COD}*(1-{TAX}))"

            # PV FCFF
            ws.write_formula(row, 4,
                f"=D{row+1}/(1+{wacc})^{t}"
            )

        last_row = N + 1

        # ---------------------------
        # TERMINAL VALUE (FORMULA)
        # ---------------------------
        ws.write("A10", "Terminal Value FCFE")
        ws.write_formula("B10",
            f"=B{last_row}*(1+{TG})/(({RF}+{BETA}*{ERP})-{TG})"
        )

        ws.write("A11", "PV Terminal FCFE")
        ws.write_formula("B11",
            f"=B10/(1+({RF}+{BETA}*{ERP}))^{N}"
        )

        ws.write("A13", "Equity Value FCFE")
        ws.write_formula("B13",
            f"=SUM(C2:C{last_row})+B11"
        )

        ws.write("A14", "Value per Share FCFE")
        ws.write_formula("B14",
            f"=B13/{SHARES}"
        )

        # ---------------------------
        # FCFF SIDE
        # ---------------------------
        ws.write("D10", "Terminal Value FCFF")
        ws.write_formula("E10",
            f"=D{last_row}*(1+{TG})/({wacc}-{TG})"
        )

        ws.write("D11", "PV Terminal FCFF")
        ws.write_formula("E11",
            f"=E10/(1+{wacc})^{N}"
        )

        ws.write("D13", "Enterprise Value")
        ws.write_formula("E13",
            f"=SUM(E2:E{last_row})+E11"
        )

        ws.write("D14", "Equity Value")
        ws.write_formula("E14",
            f"=E13-{DEBT}+{CASH}"
        )

        ws.write("D15", "Value per Share FCFF")
        ws.write_formula("E15",
            f"=E14/{SHARES}"
        )

        # ---------------------------
        # RELATIVE VALUATION
        # ---------------------------
        ws.write("A16", "P/E Value")
        ws.write_formula("B16", f"={EPS}*{PE}")

        # ---------------------------
        # FINAL OUTPUT
        # ---------------------------
        ws.write("A18", "Average Value")
        ws.write_formula("B18", "=AVERAGE(B14,E15,B16)")

    return output.getvalue()