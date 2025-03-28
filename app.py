import streamlit as st
import pandas as pd
import json
from datetime import datetime

# Load the data
@st.cache_data
def load_data():
    with open('backup_20250328_203836.json', 'r') as f:
        data = json.load(f)
    
    # Convert to DataFrame
    records = []
    for symbol, details in data.items():
        record = {
            'Symbol': symbol,
            'Status': details.get('status', ''),
            'Next Earnings Prediction': details.get('earnings', {}).get('next_earnings_prediction', ''),
            'Confidence Score': details.get('earnings', {}).get('prediction_metadata', {}).get('confidence_score', ''),
            'Last Close': details.get('technical', {}).get('last_close', ''),
            'RSI': details.get('technical', {}).get('rsi', ''),
            'Trend': details.get('technical', {}).get('trend', ''),
            'MA_20': details.get('technical', {}).get('ma_20', ''),
            'MA_50': details.get('technical', {}).get('ma_50', ''),
            'MA_200': details.get('technical', {}).get('ma_200', ''),
            'Predicted Revenue': details.get('fundamental', {}).get('predictions', {}).get('Total Revenue', ''),
            'Predicted Net Income': details.get('fundamental', {}).get('predictions', {}).get('Net Income', ''),
            'Predicted EPS': details.get('fundamental', {}).get('predictions', {}).get('Basic EPS', ''),
            'Error': details.get('error', '')
        }
        records.append(record)
    
    df = pd.DataFrame(records)
    
    # Convert date strings to datetime objects for filtering
    df['Next Earnings Prediction'] = pd.to_datetime(df['Next Earnings Prediction'], errors='coerce')
    df['Days Until Earnings'] = (df['Next Earnings Prediction'] - datetime.now()).dt.days
    
    # Convert numeric columns
    numeric_cols = ['Last Close', 'RSI', 'MA_20', 'MA_50', 'MA_200', 
                   'Predicted Revenue', 'Predicted Net Income', 'Confidence Score']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

df = load_data()

# Dashboard layout
st.title('Stock Data Analysis Dashboard')
st.write("Analyze stock data with filters for earnings predictions and technical indicators")

# Sidebar filters
st.sidebar.header('Filters')

# Date range filter for earnings
min_date = df['Next Earnings Prediction'].min()
max_date = df['Next Earnings Prediction'].max()

date_range = st.sidebar.date_input(
    "Next Earnings Date Range",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date, end_date = date_range
    df = df[(df['Next Earnings Prediction'] >= pd.to_datetime(start_date)) & 
            (df['Next Earnings Prediction'] <= pd.to_datetime(end_date))]

# Confidence score filter
confidence_min, confidence_max = st.sidebar.slider(
    'Confidence Score Range',
    min_value=0, 
    max_value=100,
    value=(0, 100)
df = df[(df['Confidence Score'] >= confidence_min) & 
        (df['Confidence Score'] <= confidence_max)]

# RSI filter
rsi_min, rsi_max = st.sidebar.slider(
    'RSI Range',
    min_value=0, 
    max_value=100,
    value=(0, 100))
df = df[(df['RSI'] >= rsi_min) & (df['RSI'] <= rsi_max)]

# Trend filter
trend_options = ['All'] + sorted(df['Trend'].unique().tolist())
selected_trend = st.sidebar.selectbox('Trend', trend_options)
if selected_trend != 'All':
    df = df[df['Trend'] == selected_trend]

# Days until earnings filter
days_min = int(df['Days Until Earnings'].min())
days_max = int(df['Days Until Earnings'].max())
days_range = st.sidebar.slider(
    'Days Until Earnings',
    min_value=days_min,
    max_value=days_max,
    value=(days_min, days_max)
)
df = df[(df['Days Until Earnings'] >= days_range[0]) & 
        (df['Days Until Earnings'] <= days_range[1])]

# Main display
st.header('Filtered Stock Data')
st.write(f"Showing {len(df)} stocks")

# Display data table
st.dataframe(df.sort_values(by='Next Earnings Prediction'))

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Average Confidence Score", f"{df['Confidence Score'].mean():.1f}")
col2.metric("Average RSI", f"{df['RSI'].mean():.1f}")
col3.metric("Stocks in Bullish Trend", len(df[df['Trend'].str.contains('Bullish', case=False)]))

# Visualization
st.header('Visualizations')

# Earnings distribution
st.subheader('Earnings Date Distribution')
earnings_count = df['Next Earnings Prediction'].dt.date.value_counts().sort_index()
st.bar_chart(earnings_count)

# RSI vs Confidence Score
st.subheader('RSI vs Confidence Score')
st.scatter_chart(df, x='RSI', y='Confidence Score', color='Trend')

# Technical indicators
st.subheader('Moving Averages Comparison')
ma_df = df[['Symbol', 'Last Close', 'MA_20', 'MA_50', 'MA_200']].set_index('Symbol')
st.line_chart(ma_df)

# Show raw data if needed
if st.checkbox('Show raw data'):
    st.subheader('Raw Data')
    st.write(df)
