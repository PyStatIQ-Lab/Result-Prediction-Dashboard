import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Load main data from JSON
with open('backup_20250328_203836.json') as f:
    data = json.load(f)

# Helper function to analyze a single stock (by symbol)
def analyze_stock(symbol):
    stock_data = data.get(symbol)
    if not stock_data:
        return None
    try:
        return {
            'Symbol': symbol,
            'Last Close': stock_data['technical']['last_close'],
            'Volume': stock_data['technical']['last_volume'],
            'RSI': stock_data['technical']['rsi'],
            'Trend': stock_data['technical']['trend'],
            'Next Earnings': stock_data['earnings']['next_earnings_prediction'],
            'Confidence Score': stock_data['earnings']['prediction_metadata']['confidence_score']
        }
    except Exception:
        return None

# Dashboard layout
st.set_page_config(layout="wide")
st.title("📈 Stock Market Analysis Dashboard")

# Load all symbols into overview dataframe
stocks = []
for symbol, stock_data in data.items():
    result = analyze_stock(symbol)
    if result:
        stocks.append(result)

df = pd.DataFrame(stocks)

# === USER UPLOADS EXCEL TO ANALYZE MULTIPLE SYMBOLS ===
st.sidebar.title("Navigation")

st.sidebar.subheader("📄 Analyze Custom Stock List")
if os.path.exists("stocklist.xlsx"):
    xl = pd.ExcelFile("stocklist.xlsx")
    stock_sheets = xl.sheet_names

    selected_sheet = st.sidebar.selectbox("Select Sheet", stock_sheets)
    analyze_button = st.sidebar.button("Analyze Stocks")

    if analyze_button:
        try:
            stock_df = pd.read_excel("stocklist.xlsx", sheet_name=selected_sheet)
            if "Symbol" not in stock_df.columns:
                st.error("❌ The selected sheet doesn't have a 'Symbol' column.")
            else:
                symbols = stock_df["Symbol"].dropna().unique().tolist()
                st.success(f"📊 Analyzing {len(symbols)} stocks...")

                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, symbol in enumerate(symbols):
                    status_text.text(f"Analyzing {symbol} ({i+1}/{len(symbols)})...")
                    result = analyze_stock(symbol)
                    if result:
                        results.append(result)
                    progress_bar.progress((i + 1) / len(symbols))

                if results:
                    df = pd.DataFrame(results)
                    st.success("✅ Analysis complete!")
                else:
                    st.warning("⚠️ No valid stock data found.")
        except Exception as e:
            st.error(f"Error loading sheet: {e}")
else:
    st.sidebar.warning("Please upload a file named `stocklist.xlsx` to use this feature.")

# === MAIN DASHBOARD ===
selected_symbol = st.sidebar.selectbox("Select Stock", df["Symbol"].unique())

# Overview section
st.header("📊 Market Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Stocks", len(df))
col2.metric("Average RSI", round(df["RSI"].mean(), 2))
col3.metric("Most Common Trend", df["Trend"].mode()[0])

st.dataframe(df.sort_values("Last Close", ascending=False), use_container_width=True)

# Stock details
selected_stock = data.get(selected_symbol)
if selected_stock:
    st.header(f"🔍 Detailed Analysis: {selected_symbol}")

    # Basic Info
    st.subheader("Basic Information")
    col1, col2, col3 = st.columns(3)
    col1.metric("Last Close", selected_stock["technical"]["last_close"])
    col2.metric("Volume", f"{selected_stock['technical']['last_volume']:,}")
    col3.metric("Trend", selected_stock["technical"]["trend"])

    # Earnings Prediction
    st.subheader("Earnings Prediction")
    next_earnings = selected_stock["earnings"]["next_earnings_prediction"]
    confidence = selected_stock["earnings"]["prediction_metadata"]["confidence_score"]

    col1, col2 = st.columns(2)
    col1.metric("Next Earnings Date", next_earnings)
    col2.metric("Confidence Score", f"{confidence}%")

    # Earnings History Chart
    try:
        st.subheader("Earnings Dates History")
        earnings_dates = pd.to_datetime(selected_stock["earnings"]["historical_dates"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=earnings_dates,
            y=[1] * len(earnings_dates),
            mode="markers+lines",
            name="Historical Earnings",
            marker=dict(size=10)
        ))
        if next_earnings:
            fig.add_vline(x=pd.to_datetime(next_earnings), line_dash="dash", line_color="red")
        fig.update_layout(
            xaxis_title="Date",
            yaxis=dict(showticklabels=False),
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning("Couldn't render earnings history chart.")

    # Technical indicators
    st.subheader("Technical Indicators")
    col1, col2, col3 = st.columns(3)
    col1.metric("RSI", round(selected_stock["technical"]["rsi"], 2))
    col2.metric("20-day MA", round(selected_stock["technical"]["ma_20"], 2))
    col3.metric("50-day MA", round(selected_stock["technical"]["ma_50"], 2))

    # MACD Chart
    st.subheader("MACD Indicator")
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(
        y=[selected_stock["technical"]["macd_line"]],
        name="MACD Line",
        mode="lines"
    ))
    macd_fig.add_trace(go.Scatter(
        y=[selected_stock["technical"]["macd_signal"]],
        name="Signal Line",
        mode="lines"
    ))
    macd_fig.update_layout(height=300)
    st.plotly_chart(macd_fig, use_container_width=True)

    # Fundamental Analysis
    st.subheader("Fundamental Analysis")
    if "fundamental" in selected_stock and "historical" in selected_stock["fundamental"]:
        fundamental = selected_stock["fundamental"]["historical"]
        metrics = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
        fundamental_df = pd.DataFrame()
        for metric in metrics:
            if metric in fundamental:
                temp_df = pd.DataFrame.from_dict(fundamental[metric], orient="index", columns=[metric])
                temp_df.index = pd.to_datetime(temp_df.index)
                fundamental_df = pd.concat([fundamental_df, temp_df], axis=1)

        if not fundamental_df.empty:
            fig = px.line(fundamental_df, x=fundamental_df.index, y=fundamental_df.columns,
                          title="Revenue and Profit Trends")
            st.plotly_chart(fig, use_container_width=True)
            latest_date = fundamental_df.index.max()
            latest_values = fundamental_df.loc[latest_date]
            st.write(f"Latest Values (as of {latest_date.date()})")
            cols = st.columns(len(latest_values))
            for i, (metric, value) in enumerate(latest_values.items()):
                cols[i].metric(metric, f"{value:,.2f}")

    # Predictions
    if "fundamental" in selected_stock and "predictions" in selected_stock["fundamental"]:
        st.subheader("Financial Predictions")
        predictions = selected_stock["fundamental"]["predictions"]
        valid_predictions = {k: v for k, v in predictions.items() if v is not None}
        if valid_predictions:
            cols = st.columns(3)
            for i, (metric, value) in enumerate(valid_predictions.items()):
                with cols[i % 3]:
                    st.metric(metric, f"{value:,.2f}" if isinstance(value, (int, float)) else value)

            # Prediction vs Last
            st.subheader("Prediction vs Last Historical Value")
            comparison_data = []
            for metric in valid_predictions:
                if metric in selected_stock["fundamental"]["historical"]:
                    historical = selected_stock["fundamental"]["historical"][metric]
                    if historical:
                        last_historical = list(historical.values())[-1]
                        predicted = valid_predictions[metric]
                        change_pct = ((predicted - last_historical) / last_historical * 100
                                      if last_historical != 0 else 0)
                        comparison_data.append({
                            "Metric": metric,
                            "Last Historical": last_historical,
                            "Predicted": predicted,
                            "Change (%)": change_pct
                        })

            if comparison_data:
                comp_df = pd.DataFrame(comparison_data)
                fig = go.Figure()
                for _, row in comp_df.iterrows():
                    fig.add_trace(go.Bar(
                        name=row["Metric"],
                        x=["Last Historical", "Predicted"],
                        y=[row["Last Historical"], row["Predicted"]],
                        text=[f"{row['Last Historical']:,.2f}", f"{row['Predicted']:,.2f}"],
                        textposition="auto"
                    ))
                fig.update_layout(
                    barmode="group",
                    title="Comparison of Last Historical and Predicted Values",
                    yaxis_title="Value",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)

# Optional: styling
st.markdown("""
<style>
    .stMetric {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
    .stDataFrame {
        border: 1px solid #ccc;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)
