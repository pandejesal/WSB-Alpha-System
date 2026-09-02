import pandas as pd
import numpy as np
import ta
from src.alpha.base_strategy import BaseStrategy
from src.alpha.indicators import compute_indicators

class H3AlphaEnsemble(BaseStrategy):
    """
    H3-Alpha: Multi-Indicator Voting Ensemble Strategy
    Combines RSI(14), RSI(21), EMA(10/30) crossover, and WSB Alpha signals.
    Dynamic weights via 20-day rolling Sharpe of each voter's recent signals.
    """
    
    def __init__(self, name="H3AlphaEnsemble", rsi_period1=14, rsi_period2=21,
                 ema_short=10, ema_long=30, lookback_sharpe=20):
        self.name = name
        self.rsi_period1 = rsi_period1
        self.rsi_period2 = rsi_period2
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.lookback_sharpe = lookback_sharpe
        # Voter names for weight tracking
        self.voter_names = ["rsi14", "rsi21", "ema_cross", "wsb_alpha"]
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate ensemble signals using voting with dynamic weights.
        Returns df with 'signal' column (1=long, -1=short, 0=flat).
        """
        df = df.copy()
        
        # Compute base indicators using existing compute_indicators
        df = compute_indicators(df)
        
        # Add additional indicators
        # RSI 21
        df['RSI_21'] = ta.momentum.RSIIndicator(close=df['Close'], window=self.rsi_period2).rsi()
        
        # EMA 10 and 30
        df['EMA_10'] = ta.trend.EMAIndicator(close=df['Close'], window=self.ema_short).ema_indicator()
        df['EMA_30'] = ta.trend.EMAIndicator(close=df['Close'], window=self.ema_long).ema_indicator()
        
        # Initialize voter signals
        df['vote_rsi14'] = 0
        df['vote_rsi21'] = 0
        df['vote_ema_cross'] = 0
        df['vote_wsb_alpha'] = 0
        
        # 1. RSI 14 voter: oversold <30 → long, overbought >70 → short
        df.loc[df['RSI_14'] < 30, 'vote_rsi14'] = 1
        df.loc[df['RSI_14'] > 70, 'vote_rsi14'] = -1
        
        # 2. RSI 21 voter: oversold <35 → long, overbought >65 → short
        df.loc[df['RSI_21'] < 35, 'vote_rsi21'] = 1
        df.loc[df['RSI_21'] > 65, 'vote_rsi21'] = -1
        
        # 3. EMA crossover voter: EMA10 > EMA30 → long, else short
        df.loc[df['EMA_10'] > df['EMA_30'], 'vote_ema_cross'] = 1
        df.loc[df['EMA_10'] <= df['EMA_30'], 'vote_ema_cross'] = -1
        
        # 4. WSB Alpha voter: use existing signal column from compute_indicators
        # WSB Alpha uses EMA20+RSI14+MACD+sentiment veto
        # We'll recreate a simple version here for voting
        # Actually, we can use the signals from compute_indicators if available
        # For now, use a simplified WSB Alpha signal based on EMA20 and RSI14
        df['wsb_signal'] = 0
        # Long if price > EMA20 and RSI14 < 70 (not overbought)
        df.loc[(df['Close'] > df['EMA_20']) & (df['RSI_14'] < 70), 'wsb_signal'] = 1
        # Short if price < EMA20 and RSI14 > 30 (not oversold)
        df.loc[(df['Close'] < df['EMA_20']) & (df['RSI_14'] > 30), 'wsb_signal'] = -1
        df['vote_wsb_alpha'] = df['wsb_signal']
        
        # Calculate rolling Sharpe for each voter (20-day lookback)
        # For each voter, compute Sharpe of its signal returns
        # We'll use a simplified approach: compute rolling correlation with forward returns
        # and use that as a weight proxy
        
        # First, compute forward returns (1-day ahead)
        df['forward_return'] = df['Close'].pct_change().shift(-1)
        
        # Initialize weight columns
        for voter in self.voter_names:
            df[f'weight_{voter}'] = 1.0 / len(self.voter_names)  # equal weights initially
        
        # Compute dynamic weights based on rolling Sharpe proxy
        # For each voter, compute rolling correlation between its signal and forward returns
        # Then normalize to sum to 1
        for i in range(self.lookback_sharpe, len(df)):
            window_slice = df.iloc[i-self.lookback_sharpe:i]
            
            sharpes = {}
            for voter in self.voter_names:
                signal_col = f'vote_{voter}'
                # Compute correlation between signal and forward returns
                corr = window_slice[signal_col].corr(window_slice['forward_return'])
                # Convert to Sharpe-like metric (using mean/std)
                if not np.isnan(corr):
                    # Use correlation as a proxy for signal quality
                    sharpes[voter] = max(corr, 0)  # floor at 0
                else:
                    sharpes[voter] = 1.0 / len(self.voter_names)
            
            # Normalize weights to sum to 1
            total = sum(sharpes.values())
            if total > 0:
                for voter in self.voter_names:
                    df.iloc[i, df.columns.get_loc(f'weight_{voter}')] = sharpes[voter] / total
            else:
                # Equal weights if all correlations are zero
                for voter in self.voter_names:
                    df.iloc[i, df.columns.get_loc(f'weight_{voter}')] = 1.0 / len(self.voter_names)
        
        # Compute ensemble signal: weighted sum of votes
        df['ensemble_raw'] = 0.0
        for voter in self.voter_names:
            df['ensemble_raw'] += df[f'weight_{voter}'] * df[f'vote_{voter}']
        
        # Convert to discrete signal: >0 → long (1), <0 → short (-1), else flat (0)
        df['signal'] = 0
        df.loc[df['ensemble_raw'] > 0.1, 'signal'] = 1   # threshold to avoid noise
        df.loc[df['ensemble_raw'] < -0.1, 'signal'] = -1
        
        # Clean up temporary columns
        df.drop(['forward_return', 'wsb_signal'] + [f'weight_{voter}' for voter in self.voter_names] + 
                [f'vote_{voter}' for voter in self.voter_names] + ['ensemble_raw'], 
                axis=1, inplace=True, errors='ignore')
        
        return df