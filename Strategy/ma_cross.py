import pandas as pd
import pandas_ta as ta

# last = iloc[-1]  [-2]  [-3] ...

def strategy(df):
    # print(df)
    time = df[0]
    open = df[1]
    high = df[2]
    low = df[3]
    close = df[4]
    volume = df[5]

    rsi = ta.rsi(close)
    ema_5 = ta.ema(close,length=5)
    ema_8 = ta.ema(close,length=8)
    ema_18 = ta.ema(close,length=18)
    atr    = ta.atr(high,low,close)
    cat = pd.concat([df, rsi, ema_5, ema_8, ema_18, atr], axis=1)
    
    print(cat)

    last_close = cat[4].iloc[-1]
    tp = last_close * 1.003
    sl = last_close * 0.997

    return ["buy", last_close, sl, tp]
    

def tp(df, side):
    rsi = ta.rsi(df[4]).iloc[-1]

    if side == "BUY":
        if rsi == 30:
            return True
    
    if side == "SELL":
        if rsi == 70:
            return True

def test():
    print("TEST HERE")
