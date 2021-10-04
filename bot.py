import threading as tr
import pandas_ta as ta
import pandas as pd
import time, websocket, json,numpy, sqlite3,ccxt

# CryptoFeed
from cryptofeed import FeedHandler
from cryptofeed.exchanges import Binance

conn = sqlite3.connect(':memory:', check_same_thread=False, isolation_level=None) # multi.sqlite
conn.execute('pragma journal_mode=wal')
create_table = """
    CREATE TABLE "kline" (
    "id"	INTEGER NOT NULL,
    "t_open" NUMERIC,
    "t_close" NUMERIC,
    "s"	TEXT,
    "o"	NUMERIC,
    "c"	NUMERIC,
    "h"	NUMERIC,
    "l"	NUMERIC,
    "v"	NUMERIC,
    "x"	INTEGER,
    PRIMARY KEY("id" AUTOINCREMENT)
    )
"""
conn.execute(create_table)
conn.commit()
print("Database Connected")

######################################## [S] CCXT
API_KEY= ""
API_SECRET= ""

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
        conn.execute(f"INSERT INTO kline (s,t_open,o,c,h,l,v,t_close,x) VALUES ('{symbol}', {kline[0]}, {kline[1]}, {kline[2]}, {kline[3]}, {kline[4]}, {kline[5]}, {kline[6]}, {is_closed})")
        conn.commit()

######################################## [E] CCXT

######################################## [S] DB
def update_db(data):
    # Extract data
    t_open = data['t']
    t_close = data['T']
    s = data['s']
    o = data['o']
    c = data['c']
    h = data['h']
    l = data['l']
    v = data['v']
    x = data['x']
    
    conn.execute(f"UPDATE kline SET t_open={t_open}, t_close={t_close}, s='{s}', o={o}, c={c}, h={h}, l={l}, v={v}, x={x} WHERE s='{s}' AND x=False")
    conn.commit()

def insert_db(symbol):
    conn.execute(f"INSERT INTO kline (s,x) VALUES ('{symbol}', False)")
    conn.commit()

def delete_db():
    conn.execute(f"DELETE FROM kline WHERE x=True AND t_close <= (strftime('%s','now', '-202 minutes')) * 1000")
    conn.commit()

def fetch_db():
    return conn.execute("SELECT * FROM kline WHERE s='BTCUSDT'").fetchall()
######################################## [E] DB

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

    update_db(data)

    if data['x'] == True:
        insert_db(data['s'])
    
    time.sleep(0.1)
    

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

    market_ws_multi(exchange_symbols_data,limit=199) # ["BTCUSDT","ETCUSDT"]
    # user_ws()

    print("ENDED BLOCK")

    while True:
        time_now = time.localtime()
        seconds_time = int(time.strftime("%S", time_now))
        if (seconds_time == 59):
            delete_db()
            print(fetch_db(), "\n")
        time.sleep(1)
