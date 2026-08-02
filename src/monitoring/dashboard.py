import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="WSB-Alpha Dashboard", layout="wide")

def main():
    st.title("WSB-Alpha-System Real-Time Dashboard")

    st.sidebar.header("Navigation")
    page = st.sidebar.radio("Go to", ["Performance Analytics", "Darwinian Leaderboard", "Risk & Positions"])

    if page == "Performance Analytics":
        st.header("Equity Curve & Performance Analytics")
        # Mock Data
        dates = pd.date_range('2023-01-01', periods=100)
        equity = np.cumsum(np.random.normal(10, 50, 100)) + 10000
        df = pd.DataFrame({'Date': dates, 'Equity': equity})

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Equity'], mode='lines', name='Equity'))
        fig.update_layout(title="Portfolio Equity", xaxis_title="Date", yaxis_title="USD")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Sharpe Ratio", "2.1")
        col2.metric("Sortino Ratio", "3.2")
        col3.metric("Win Rate", "65%")
        col4.metric("Profit Factor", "1.8")

        st.subheader("Interactive TradingView Style Chart (Plotly)")
        # Mock candle data
        candle_df = pd.DataFrame({
            'Date': dates,
            'Open': equity - 10,
            'High': equity + 20,
            'Low': equity - 20,
            'Close': equity + 10
        })
        fig_candle = go.Figure(data=[go.Candlestick(x=candle_df['Date'],
                open=candle_df['Open'],
                high=candle_df['High'],
                low=candle_df['Low'],
                close=candle_df['Close'])])

        # Add mock trade markers
        fig_candle.add_trace(go.Scatter(
            x=[dates[10], dates[30]],
            y=[candle_df['Low'].iloc[10]-5, candle_df['Low'].iloc[30]-5],
            mode='markers',
            marker=dict(symbol='triangle-up', size=15, color='green'),
            name='Buy'
        ))
        st.plotly_chart(fig_candle, use_container_width=True)

    elif page == "Darwinian Leaderboard":
        st.header("Darwinian Strategy Leaderboard")
        data = {
            "Strategy ID": ["STRAT_A", "STRAT_B", "STRAT_C", "STRAT_D"],
            "Fitness Score": [0.85, 0.72, 0.45, 0.12],
            "Regime State": ["Bull", "Bull", "Neutral", "Bear"],
            "Survival Status": ["Promoted", "Active", "Active", "Discarded"]
        }
        st.dataframe(pd.DataFrame(data), use_container_width=True)

    elif page == "Risk & Positions":
        st.header("Risk & Position Monitor")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Open Positions")
            pos_data = {
                "Asset": ["AAPL", "MSFT", "NVDA"],
                "Weight": ["15%", "10%", "20%"],
                "CVaR Contrib": ["2.1%", "1.5%", "4.0%"]
            }
            st.table(pd.DataFrame(pos_data))

        with col2:
            st.subheader("Circuit Breaker Status")
            st.success("Daily Limit: 1.2% / 5.0% (SAFE)")
            st.success("Weekly Limit: 3.0% / 10.0% (SAFE)")
            st.success("Total Drawdown: 4.5% / 15.0% (SAFE)")

if __name__ == '__main__':
    main()
