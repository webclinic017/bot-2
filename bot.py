import threading as tr
import pandas_ta as ta
import pandas as pd
import time
import websocket
import json
import sqlite3
import hmac
import hashlib
import requests
from urllib.parse import urlencode

ws_list = []
################################################################################### Helper (Utils)
def extract_string(string:str,start="",end=""):
    _start = string.find(start) + 1
    _end   = string.find(end, _start)
    if start == "":
        _start = None
    if end == "":
        _end = None
    return string[_start:_end]

def dif_time_in_minutes(asked_time):
    asked_time = int(asked_time) / 1000
    now = time.time()
    dif_time = (now - asked_time)
    dif_minutes = dif_time / 60
    return dif_minutes

def split_array(array,parts,index):
    length = len(array)
    split_list = [array[i*length // parts: (i+1)*length // parts]
                  for i in range(parts)]
    split_index = split_list[index]
    print(split_index)
    return split_index

################################################################################### Database
memory_db = sqlite3.connect(':memory:', check_same_thread=False, isolation_level=None) # multi.sqlite
memory_db.execute('pragma journal_mode=wal')
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
memory_db.execute(create_table)
memory_db.commit()
print("Memory: Database Connected")

db = sqlite3.connect('bot.sqlite', check_same_thread=False, isolation_level=None)
db.execute('pragma journal_mode=wal')
print("File: Database Connected")

def fetch_kline(symbol):
    return memory_db.execute(f"SELECT * FROM kline WHERE s='{symbol}'").fetchall()

def insert_kline(symbol):
    memory_db.execute(f"INSERT INTO kline (s,x) VALUES ('{symbol}', False)")
    memory_db.commit()

def update_kline(data):
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
    
    memory_db.execute(f"UPDATE kline SET t_open={t_open}, t_close={t_close}, s='{s}', o={o}, c={c}, h={h}, l={l}, v={v}, x={x} WHERE s='{s}' AND x=False")
    memory_db.commit()

def delete_kline():
    while True:
        memory_db.execute(f"DELETE FROM kline WHERE x=True AND t_close <= (strftime('%s','now', '-202 minutes')) * 1000")
        memory_db.commit()
        print("Database Cleaned")
        time.sleep(60)


def fetch_user(user_id):
    return db.execute(f"SELECT * FROM user WHERE id={user_id}").fetchone()

def fetch_all_user():
    return db.execute(f"SELECT * FROM user WHERE is_active=True").fetchall()

def fetch_stream_list(id):
    return db.execute(f"SELECT id FROM stream_list WHERE id={id}").fetchone()

def fetch_all_stream_list():
    return db.execute(f"SELECT * FROM stream_list").fetchall()

def delete_stream(id):
    print("Examples: ")
    on_close(id)       # close ws by id (ws_object needed)
    ws_list.remove(id) # remove ws_list by id
    db.execute(f"DELETE FROM stream_list WHERE id={id}") # Delete it from database 

################################################################################### CONFIG
CONFIG_TEST = "TEST"

################################################################################### HTTP Request
# ======  begin of functions, you don't need to touch ======
def base_url_finder(url_path):
    base_url = ""
    if url_path.find("/fapi") != -1:
        base_url = "https://fapi.binance.com"
    elif url_path.find("/api") != -1:
        base_url = "https://api.binance.com"
    elif url_path.find("/dapi") != -1:
        base_url = "https://dapi.binance.com"
    else:
        base_url = "https://testnet.binancefuture.com"
    return base_url

def hashing(query_string,api_secret):
    return hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_timestamp():
    return int(time.time() * 1000)

def dispatch_request(http_method,api_key):
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json;charset=utf-8',
        'X-MBX-APIKEY': api_key
    })
    return {
        'GET': session.get,
        'DELETE': session.delete,
        'PUT': session.put,
        'POST': session.post,
    }.get(http_method, 'GET')

# used for sending request requires the signature
def send_signed_request(http_method,api_key,api_secret, url_path, payload={}):
    query_string = urlencode(payload)
    # replace single quote to double quote
    query_string = query_string.replace('%27', '%22')
    if query_string:
        query_string = "{}&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = 'timestamp={}'.format(get_timestamp())

    BASE_URL = base_url_finder(url_path)

    url = BASE_URL + url_path + '?' + query_string + '&signature=' + hashing(query_string,api_secret)
    print("{} {}".format(http_method, url))
    params = {'url': url, 'params': {}}
    response = dispatch_request(http_method,api_key)(**params)
    return response.json()

# used for sending public data request
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload, True)
    
    BASE_URL = base_url_finder(url_path)

    url = BASE_URL + url_path
    if query_string:
        url = url + '?' + query_string
    print("{}".format(url))
    response = dispatch_request('GET', api_key="")(url=url)
    return response.json()
#  ======  end of functions ======

def exchange_symbols():
    exchange_info = send_public_request("/fapi/v1/exchangeInfo")
    symbols_array = []
    for s in exchange_info['symbols']:
        symbol = s['symbol']
        contractType = s['contractType']
        quoteAsset = s['quoteAsset']
        if contractType == 'PERPETUAL' and quoteAsset == 'USDT':
            symbols_array.append(symbol)
    
    print("Fetch Exchange Symbols Completed")
    print(symbols_array)
    return symbols_array


def ohlcv(symbol,interval,limit):
    params = {"symbol":symbol, "interval":interval, "limit":limit}
    klines = send_public_request("/fapi/v1/klines", params) # "BTCUSDT", "1m", 199
    print(symbol,"- Fetched OHLC")
    print(klines)

    last_kline = klines[-1]
    is_closed = True
    for kline in klines:
        if kline == last_kline:
            is_closed = False
        memory_db.execute(f"INSERT INTO kline (s,t_open,o,c,h,l,v,t_close,x) VALUES ('{symbol}', {kline[0]}, {kline[1]}, {kline[2]}, {kline[3]}, {kline[4]}, {kline[5]}, {kline[6]}, {is_closed})")
        memory_db.commit()

def generate_listenKey(api_key):    
    res = send_signed_request("POST",api_key,"", "/fapi/v1/listenKey")
    listenKey = res['listenKey']
    return listenKey

def refresh_listenKey(listen_key,api_key):
    while True:
        time.sleep(60 * 29) # 29min
        print("Going to refresh token ...")
        payload = urlencode({'listenKey': listen_key})
        send_signed_request("PUT",api_key,"",f"/fapi/v1/listenKey?{payload}")
        print("Refresh Done")

def new_order(api_key,api_secret,symbol,side,type,quantity,newClientOrderId, stopPrice=""):
    params = {"symbol":symbol, "side":side, "type":type, "quantity":quantity, "newClientOrderId":newClientOrderId}
    if stopPrice:
        params['stopPrice'] = stopPrice
    order = send_signed_request("POST",api_key,api_secret,"/fapi/v1/order",params)
    print(order,"\n")
################################################################################### Websockets & Callbacks
def on_open(ws):
    print("open connection")

def on_close(ws):
    ws.close()
    print("close connection")

def market_kline_on_message(ws,message):
    data = json.loads(message)['k']

    update_kline(data)

    if data['x'] == True:
        insert_kline(data['s'])
    
    time.sleep(0.1)

def user_data_on_message(ws,message):
    data = json.loads(message)
    e = data['e']
    if e == "ORDER_TRADE_UPDATE":
        print(data)

def ws(stream_name,callback,extra):
    # Extract extra
    extra_belong_to = extra[0]
    extra_header = None
    if len(extra) > 1 :
        extra_header = extra[1]

    SOCKET = "wss://fstream.binance.com/ws/" + stream_name
    ws = websocket.WebSocketApp(SOCKET,header=extra_header,on_open=on_open,on_close=on_close,on_message=callback)
    
    # Insert WS to DB for when server is dead
    d = db.execute(f"INSERT INTO stream_list (stream_name,status, belong_to) VALUES ('{stream_name}', True, '{extra_belong_to}')")
    db.commit()
    print(f"{stream_name} - Inserted Into Database")
    last_row = d.lastrowid
    stream_list_id = fetch_stream_list(last_row)
    stream_list = {"id":stream_list_id, "ws_object": ws}
    ws_list.append(stream_list)
    print(f"{stream_name} - Inserted Into Websocket LIST")
    ws.run_forever()

################################################################################### Strategy
def strategy(symbol):
    # if there is user_strategy active
        # Fetch kline from database
        # Use pandas
    print("in progress...")

################################################################################### Multi Processing - Threading
def strategy_multi():
    print("in progress...")

def market_kline_ws_multi(symbol,interval="1m",limit=199):

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
            extra = ["market_kline"]
            t = tr.Thread(target=ws, args=[symbol_lower,market_kline_on_message,extra])
            t.start()
            break
        time.sleep(1)
    time.sleep(1)

def user_data_ws_multi(user_id):
    user = fetch_user(user_id)
    
    id = user[0]
    api_key = user[3]
    listen_key = generate_listenKey(api_key)
    db.execute("""UPDATE user SET listen_key=? WHERE id=?""", [listen_key,id])
    db.commit()
    
    # Listen Key
    header = {"X-MBX-APIKEY": api_key}
    extra = ["user_data", header ]
    thread_listen_key = tr.Thread(target=ws, args=[listen_key,user_data_on_message, extra])
    thread_listen_key.start()

    # Refresh Listen Key
    thread_refresh = tr.Thread(target=refresh_listenKey, args=[listen_key,api_key])
    thread_refresh.start()

def clean_kline_db_multi():
    t = tr.Thread(target=delete_kline)
    t.start()

################################################################################### IF SERVER Reboot
def reboot_user_data():
    db.execute(f"DELETE FROM stream_list WHERE belong_to='user_data'")
    db.commit()

    users = fetch_all_user()
    for user in users:
        id = user[0]
        user_data_ws_multi(id)
    

def reboot_market_kline(interval="1m"):
    streams = db.execute(f"SELECT * FROM stream_list WHERE belong_to='market_kline'").fetchall()
    if len(ws_list) == 0:
        for stream in streams:
            id = stream[0]
            stream_name:str = stream[1]
            status = stream[2]
            
            db.execute(f"DELETE FROM stream_list WHERE id={id}")
            db.commit()

            if status:
                symbol = stream_name.replace("@kline_" + interval, "").upper()
                market_kline_ws_multi(symbol)

################################################################################### Sanic Framework

################################################################################### TEST

################################################################################### Run On Startup - Forever
if __name__ == '__main__':
    # reboot_market_kline()
    # reboot_user_data()
    
    # Kline Stream
    # market_kline_ws_multi("ETCUSDT",limit=20)
    # clean_kline_db_multi()
    # strategy("ETCUSDT")

    # User Stream
    # user_data_ws_multi(1)

    print("TEST")
