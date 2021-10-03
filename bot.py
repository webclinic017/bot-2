import threading as tr
import pandas_ta as ta
import pandas as pd
import time, websocket, json,numpy, sqlite3,ccxt

from cryptofeed import FeedHandler
from cryptofeed.exchanges import Binance

global_klines = []

######################################## [S] CCXT
API_KEY= "API_KEY"
API_SECRET= "API_SECRET"

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    # 'enableRateLimit': False,  # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
    'options': {
        'defaultType': 'future',
    }
})

def exchange_symbols():
    exchange_info = exchange.fetch_markets()

    symbols_array = []
    for s in exchange_info:
        symbol = s['id']
        contractType = s['info']['contractType']
        quoteAsset = s['info']['quoteAsset']
        if contractType == 'PERPETUAL' and quoteAsset == 'USDT':
            symbols_array.append(symbol)
    
    print("Fetch Exchange Symbols Completed")
    return symbols_array


def ohlcv(symbol,interval,limit):
    klines = exchange.fetch_ohlcv(symbol,interval,limit=limit) # "BTCUSDT", "1m", 199
    print(symbol,"- Fetched OHLC")
    
    last_kline = klines[-1]
    is_closed = True
    for kline in klines:
        if kline == last_kline:
            is_closed = False
        obj = {}
        obj['s'] = symbol
        obj['t'] = kline[0] # open_time
        obj['o'] = kline[1] # open
        obj['c'] = kline[2] # close
        obj['h'] = kline[3] # high
        obj['l'] = kline[4] # low
        obj['v'] = kline[5] # volume
        obj['T'] = kline[6] # close_time
        obj['x'] = is_closed
        global_klines.append(obj)
    return global_klines

######################################## [E] CCXT
def dif_time_in_minutes(asked_time):
    asked_time = int(asked_time) / 1000
    now = time.time()
    dif_time = (now - asked_time)
    dif_minutes = dif_time / 60
    return dif_minutes

def user_ws():
    print("USER DATA STREAM")

def on_message(ws,message):
    data = json.loads(message)['k']
    new_data = {
        "t": data['t'],
        "T": data['T'],
        "s": data['s'],
        "o": data['o'],
        "c": data['c'],
        "h": data['h'],
        "l": data['l'],
        "v": data['v'],
        "x": data['x']
    }
    empty_template = {"t": 0,"T": 0,"s": data['s'],"o": "","c": "","h": "","l": "","v": "","x": False}
    for kline in global_klines:
        if kline: # not empty {}
            if kline['x'] == False and data['s'] == kline['s']:
                kline.update(new_data)
            
            # Delete older than 202 candles
            if kline['x'] == True and dif_time_in_minutes(kline['t']) > 201:
                kline.clear()
            
    if data['x'] == True:
        global_klines.append(empty_template)
    

def on_open(ws):
    print("open connection")

def on_close(ws):
    print("close connection")

def ws(stream_name):
    SOCKET = "wss://fstream.binance.com/ws/" + stream_name
    ws = websocket.WebSocketApp(SOCKET,on_open=on_open,on_close=on_close,on_message=on_message)
    ws.run_forever()

#############################################################################################
def market_ws_multi(symbols,interval="1m",limit=199):

    for symbol in symbols:
        while True:
            time_now = time.localtime()
            seconds_time = int(time.strftime("%S", time_now))
            print(seconds_time)
            if (seconds_time >= 2 and seconds_time <= 50):
                # Fetch,Insert OHLCV
                ohlcv(symbol,interval,limit)

                # Run WS
                symbol_lower = symbol.lower()
                symbol_lower += "@kline_" + interval
                t = tr.Thread(target=ws, args=[symbol_lower])
                t.start()
                break
            time.sleep(1)
        time.sleep(1)
    

#############################################################################################
if __name__ == '__main__':
    exchange_symbols_data = exchange_symbols()
    
    market_ws_multi(exchange_symbols_data,limit=199)

    print("ENDED BLOCK")
