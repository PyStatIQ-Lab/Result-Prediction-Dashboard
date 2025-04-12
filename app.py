import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Load the data
with open('backup_20250328_203836.json') as f:
    data = json.load(f)

# Convert to DataFrame for overview
stocks = []
for symbol, stock_data in data.items():
    try:
        stocks.append({
            'Symbol': symbol,
            'Last Close': stock_data['technical']['last_close'],
            'Volume': stock_data['technical']['last_volume'],
            'RSI': stock_data['technical']['rsi'],
            'Trend': stock_data['technical']['trend'],
            'Next Earnings': stock_data['earnings']['next_earnings_prediction'],
            'Confidence Score': stock_data['earnings']['prediction_metadata']['confidence_score']
        })
    except Exception as e:
        continue

df = pd.DataFrame(stocks)

# Dashboard layout
st.set_page_config(layout="wide")
st.title("Stock Market Analysis Dashboard")

# Sidebar for stock selection
st.sidebar.title("Navigation")
selected_symbol = st.sidebar.selectbox("Select Stock", df['Symbol'].unique())

# Get selected stock data
selected_stock = data.get(selected_symbol, {})

# Overview section
st.header("Market Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Stocks", len(df))
col2.metric("Average RSI", round(df['RSI'].mean(), 2))
col3.metric("Most Common Trend", df['Trend'].mode()[0])

st.dataframe(df.sort_values('Last Close', ascending=False), use_container_width=True)

# Stock details section
if selected_stock:
    st.header(f"Detailed Analysis: {selected_symbol}")
    
    # Basic info
    st.subheader("Basic Information")
    col1, col2, col3 = st.columns(3)
    col1.metric("Last Close", selected_stock['technical']['last_close'])
    col2.metric("Volume", f"{selected_stock['technical']['last_volume']:,}")
    col3.metric("Trend", selected_stock['technical']['trend'])
    
    # Earnings prediction
    st.subheader("Earnings Prediction")
    next_earnings = selected_stock['earnings']['next_earnings_prediction']
    confidence = selected_stock['earnings']['prediction_metadata']['confidence_score']
    
    col1, col2 = st.columns(2)
    col1.metric("Next Earnings Date", next_earnings)
    col2.metric("Confidence Score", f"{confidence}%")
    
    # Earnings history chart
    st.subheader("Earnings Dates History")
    try:
        earnings_dates = pd.to_datetime(selected_stock['earnings']['historical_dates'])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=earnings_dates,
            y=[1] * len(earnings_dates),
            mode='markers+lines',
            name='Historical Earnings',
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
        st.warning("Unable to display earnings history chart.")
    
    # Technical indicators
    st.subheader("Technical Indicators")
    col1, col2, col3 = st.columns(3)
    col1.metric("RSI", round(selected_stock['technical']['rsi'], 2))
    col2.metric("20-day MA", round(selected_stock['technical']['ma_20'], 2))
    col3.metric("50-day MA", round(selected_stock['technical']['ma_50'], 2))

    # MACD chart
    st.subheader("MACD Indicator")
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(
        y=[selected_stock['technical']['macd_line']],
        name='MACD Line',
        mode='lines'
    ))
    macd_fig.add_trace(go.Scatter(
        y=[selected_stock['technical']['macd_signal']],
        name='Signal Line',
        mode='lines'
    ))
    macd_fig.update_layout(height=300)
    st.plotly_chart(macd_fig, use_container_width=True)

    # Fundamental analysis
    st.subheader("Fundamental Analysis")
    if 'fundamental' in selected_stock and 'historical' in selected_stock['fundamental']:
        fundamental = selected_stock['fundamental']['historical']
        metrics = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']
        fundamental_df = pd.DataFrame()
        
        for metric in metrics:
            if metric in fundamental:
                temp_df = pd.DataFrame.from_dict(fundamental[metric], orient='index', columns=[metric])
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
    if 'fundamental' in selected_stock and 'predictions' in selected_stock['fundamental']:
        st.subheader("Financial Predictions")
        predictions = selected_stock['fundamental']['predictions']
        valid_predictions = {k: v for k, v in predictions.items() if v is not None}

        if valid_predictions:
            cols = st.columns(3)
            for i, (metric, value) in enumerate(valid_predictions.items()):
                with cols[i % 3]:
                    st.metric(
                        label=metric,
                        value=f"{value:,.2f}" if isinstance(value, (int, float)) else value
                    )

            # Comparison with last historical
            st.subheader("Prediction vs Last Historical Value")
            comparison_data = []
            for metric in valid_predictions:
                if metric in selected_stock['fundamental']['historical']:
                    historical_values = selected_stock['fundamental']['historical'][metric]
                    if historical_values:
                        last_historical = list(historical_values.values())[-1]
                        predicted = valid_predictions[metric]
                        change_pct = ((predicted - last_historical) / last_historical * 100
                                      if last_historical != 0 else 0)
                        comparison_data.append({
                            'Metric': metric,
                            'Last Historical': last_historical,
                            'Predicted': predicted,
                            'Change (%)': change_pct
                        })

            if comparison_data:
                comparison_df = pd.DataFrame(comparison_data)
                fig = go.Figure()
                for i, row in comparison_df.iterrows():
                    fig.add_trace(go.Bar(
                        name=row['Metric'],
                        x=['Last Historical', 'Predicted'],
                        y=[row['Last Historical'], row['Predicted']],
                        text=[f"{row['Last Historical']:,.2f}", f"{row['Predicted']:,.2f}"],
                        textposition='auto'
                    ))
                fig.update_layout(
                    barmode='group',
                    title="Comparison of Last Historical and Predicted Values",
                    yaxis_title="Value",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)

    if 'error' in selected_stock and selected_stock['error']:
        st.error(f"Error in data processing: {selected_stock['error']}")
else:
    st.warning("No data available for selected stock.")

# Add custom styling
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
