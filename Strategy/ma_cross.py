import pandas_ta as ta
# last = iloc[-1]  [-2]  [-3] ...

def strategy(df):
    time = df[1]
    open = df[4]
    high = df[5]
    low = df[6]
    close = df[7]
    volume = df[8]
    
    rsi = ta.rsi(close)
    ema = ta.ema(close)

    if rsi.iloc[-1] >= 70:
        print("Its time to sell")
    
    if rsi.iloc[-1] <= 30:
        print("Its time to buy")

def tpsl():
    print("Take Profit/Stop Loss")

def test():
    print("Strategy TESTER Here")
