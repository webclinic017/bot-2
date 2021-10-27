import multiprocessing as mp
import threading as tr
import pandas_ta as ta
import pandas as pd
import math
import time
import websocket
import json
import sqlite3
import hmac
import hashlib
import requests
import importlib
from urllib.parse import urlencode

ws_list = []
df_list = []
################################################################################### Helper (Utils)
def time_condition():
    while True:
        time_now = time.localtime()
        seconds_time = int(time.strftime("%S", time_now))
        print(seconds_time)
        if (2 <= seconds_time <= 50):
            break
        time.sleep(1)
    return True

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

def perc(number, max_float):
    if isinstance(number, float) or isinstance(number, int):
        return math.floor(number * (10**max_float)) / (10**max_float)

def wait_for_exchange_info():
    while True:
        exchange_info = fetch_exchange_info_all()
        last_data = exchange_info[-1]
        if last_data[5]:
            break
        time.sleep(1)

def prevent(thread):
    memory_db.execute("INSERT INTO thread (thread_id) VALUES (?)", [thread])
    memory_db.commit()
    
    time.sleep(1)
    max_thread = memory_db.execute("SELECT MAX(thread_id) FROM thread").fetchone()
    return max_thread[0]

################################################################################### Database
memory_db = sqlite3.connect(':memory:', check_same_thread=False, isolation_level=None)

memory_db.execute('pragma journal_mode=wal')
kline_table = """
    CREATE TABLE "kline" (
        "id"	INTEGER NOT NULL,
        "t_open" NUMERIC,
        "o"	NUMERIC,
        "h"	NUMERIC,
        "l"	NUMERIC,
        "c"	NUMERIC,
        "v"	NUMERIC,
        "t_close" NUMERIC,
        "x"	INTEGER,
        "s"	TEXT,
        PRIMARY KEY("id" AUTOINCREMENT)
    )
"""
memory_db.execute(kline_table)
memory_db.commit()

exchange_info_table = """
    CREATE TABLE "exchange_info" (
        "id"	INTEGER NOT NULL,
        "symbol"	TEXT,
        "pricePrecision"	NUMERIC,
        "quantityPrecision"	NUMERIC,
        "minQty"	NUMERIC,
        "percent"	NUMERIC,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
"""
memory_db.execute(exchange_info_table)
memory_db.commit()

user_settings_leverage_table = """
    CREATE TABLE "user_settings_leverage" (
        "id"	INTEGER NOT NULL,
        "user_id"	INTEGER,
        "symbol"	TEXT,
        "leverage"	NUMERIC,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
"""
memory_db.execute(user_settings_leverage_table)
memory_db.commit()

thread_table = """
    CREATE TABLE "thread" (
        "id"	INTEGER NOT NULL,
        "thread_id"	INTEGER,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
    """
memory_db.execute(thread_table)
memory_db.commit()
print("Memory: Database Connected")

#########
db = sqlite3.connect('bot.sqlite', check_same_thread=False, isolation_level=None)
db.execute('pragma journal_mode=wal')
print("File: Database Connected")

def fetch_kline_df(symbol):
    return memory_db.execute("SELECT t_open,o,h,l,c,v FROM kline WHERE s=?", [symbol]).fetchall()

def insert_empty_kline(symbol):
    memory_db.execute("INSERT INTO kline (s,x) VALUES (?, False)", [symbol])
    memory_db.commit()

def insert_kline(symbol, klines): # ohlcv
    last_kline = klines[-1]
    is_closed = True
    for kline in klines:
        if kline == last_kline:
            is_closed = False
        params = [kline[0], kline[1], kline[2], kline[3], kline[4], kline[5], kline[6], is_closed, symbol]
        memory_db.execute("INSERT INTO kline (t_open,o,h,l,c,v,t_close, x, s) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
        memory_db.commit()

def update_kline(data):
    # Extract data
    t_open = data['t']
    o = data['o']
    h = data['h']
    l = data['l']
    c = data['c']
    v = data['v']
    t_close = data['T']
    x = data['x']
    s = data['s']

    params = [t_open, o, h, l, c, v, t_close, x, s, s] # first s=? => symbol  | second s=? => WHERE 
    memory_db.execute("""UPDATE kline SET t_open=?, o=?, h=?, l=?, c=?, v=?, t_close=?, x=?, s=? WHERE s=? AND x=False""", params)
    memory_db.commit()

def delete_kline():
    while True:
        memory_db.execute("""DELETE FROM kline WHERE x=True AND t_close <= (strftime('%s','now', '-202 minutes')) * 1000""")
        memory_db.commit()
        print("Database Cleaned")
        time.sleep(60)

def fetch_user(user_id):
    return db.execute("SELECT * FROM user WHERE id=?",[user_id]).fetchone()

def fetch_all_user():
    return db.execute("SELECT * FROM user WHERE is_active=True").fetchall()

def fetch_all_user_strategy():
    return db.execute("SELECT * FROM user_strategy INNER JOIN strategy").fetchall()

def fetch_all_user_strategy_id(id):
    return db.execute("SELECT * FROM user_strategy INNER JOIN strategy WHERE user_strategy.id=?", [id]).fetchone()

def fetch_stream_list(id):
    return db.execute("SELECT id FROM stream_list WHERE id=?",[id]).fetchone()

def fetch_stream_list_symbol(symbol):
    stream_name = symbol.lower() + "@kline_1m"
    return db.execute("SELECT * FROM stream_list WHERE stream_name=? AND status=1", [stream_name]).fetchone()

def fetch_all_stream_list():
    return db.execute("SELECT * FROM stream_list").fetchall()

def fetch_stream_list_kline():
    return db.execute("SELECT * FROM stream_list WHERE belong_to='market_kline'").fetchall()

def delete_stream(id):
    print("Examples: ")
    on_close(id)       # close ws by id (ws_object needed)
    ws_list.remove(id) # remove ws_list by id
    db.execute("DELETE FROM stream_list WHERE id=?",[id]) # Delete it from database 

def insert_exchange_info(symbol_array):
    symbol = symbol_array[0]
    pricePrecision = symbol_array[1]
    quantityPrecision = symbol_array[2]
    minQty = symbol_array[3]

    params = [symbol, pricePrecision, quantityPrecision, minQty]
    memory_db.execute("INSERT INTO exchange_info (symbol,pricePrecision,quantityPrecision,minQty) VALUES (?, ?, ?, ?)", params)
    memory_db.commit()

def fetch_exchange_info_all():
    return memory_db.execute("SELECT * FROM exchange_info").fetchall()

def fetch_exchange_info_one(symbol):
    """
    return => id, symbol, pricePrecision, quantityPrecision, minQty, percent
    """
    return memory_db.execute("SELECT * FROM exchange_info WHERE symbol=?", [symbol]).fetchone()

def fetch_exchange_info_max_percent():
    return memory_db.execute("SELECT symbol,MAX(percent) FROM exchange_info").fetchone()

def update_exchange_info_percent(percent, symbol):
    memory_db.execute("""UPDATE exchange_info SET percent=? WHERE symbol=?""", [percent, symbol])
    memory_db.commit()

def fetch_user_strategy_id(id):
    return db.execute("SELECT * FROM user_strategy WHERE id=?", [id]).fetchone()

def update_user_strategy_in_position(position_status, id):
    db.execute("""UPDATE user_strategy SET in_position=? WHERE id=?""", [position_status, id])
    db.commit()

def update_user_strategy_current_money(current_money, id):
    db.execute("""UPDATE user_strategy SET current_money=? WHERE id=?""", [current_money, id])
    db.commit()

def update_user_strategy_is_sl(boolean, id):
    db.execute("""UPDATE user_strategy SET is_sl=? WHERE id=?""", [boolean, id])
    db.commit()

def insert_user_strategy_pnl(data):
    client_order_id = data[0]
    pnl = data[1] 
    fee = data[2]
    params = [client_order_id, pnl, fee]
    db.execute("INSERT INTO user_strategy_pnl (client_order_id, pnl, fee) VALUES (?, ?, ?)", params)
    db.commit()

def insert_user_settings_leverage(api_key, api_secret, user_id):
    account_info = get_account_info(api_key, api_secret)
    positions = account_info['positions']
    for position in positions:
        positionSide = position["positionSide"]
        symbol = position["symbol"]
        leverage = position["leverage"]
        if positionSide == "LONG":
            params = [user_id, symbol, leverage]
            memory_db.execute("INSERT INTO user_settings_leverage (user_id, symbol, leverage) VALUES (?, ?, ?)", params)
            memory_db.commit()

def fetch_user_settings_leverage(user_id, symbol):
    params = [user_id, symbol]
    return memory_db.execute("SELECT leverage FROM user_settings_leverage WHERE user_id=? AND symbol=?", params).fetchone()

def update_user_settings_leverage(symbol, leverage, user_id):
    params = [symbol, leverage, user_id]
    return memory_db.execute("UPDATE user_settings_leverage SET symbol=?, leverage=? WHERE user_id=?", params)
################################################################################### CONFIG
CONFIG_MONEY_MARGIN = 0.94 # 94% - you can not submit order with 100% of your money

################################################################################### HTTP Request
# ======  begin of functions ======
def base_url_finder(url_path: str):
    base_url = ""
    if url_path.startswith("/fapi"):
        base_url = "https://fapi.binance.com"
    elif url_path.startswith("/api"):
        base_url = "https://api.binance.com"
    elif url_path.startswith("/dapi"):
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

def exchange_info(new_symbol = None):
    exchange_info = send_public_request("/fapi/v1/exchangeInfo")
    single_symbol = ()
    for s in exchange_info['symbols']:
        symbol = s['symbol']
        contractType = s['contractType']
        quoteAsset = s['quoteAsset']
        pricePrecision = s["pricePrecision"]
        quantityPrecision = s["quantityPrecision"]
        minQty = float(s["filters"][1]["minQty"])
        if contractType == 'PERPETUAL' and quoteAsset == 'USDT':

            data = (symbol, pricePrecision, quantityPrecision, minQty)
            
            if new_symbol == None:
                insert_exchange_info(data) # add all

            if new_symbol and new_symbol == symbol:
                insert_exchange_info(data) # add just one
                single_symbol = (None, symbol, pricePrecision, quantityPrecision, minQty) # act like database fetch
     
    print("Fetch Exchange Symbols Completed")
    if new_symbol:
        print(single_symbol)
        return single_symbol


def ohlcv(symbol, interval, limit):
    params = {"symbol":symbol, "interval":interval, "limit":limit}
    klines = send_public_request("/fapi/v1/klines", params) # "BTCUSDT", "1m", 199
    print(symbol,"- Fetched OHLC")
    # print(klines)
    return klines

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

def new_order(api_key,api_secret,symbol,side,type,quantity,newClientOrderId, stopPrice="", positionSide=""):
    params = {"symbol":symbol, "side":side, "type":type, "quantity":quantity, "newClientOrderId":newClientOrderId}
    if stopPrice:
        params['stopPrice'] = stopPrice
    if positionSide:
        params['positionSide'] = positionSide

    order = send_signed_request("POST",api_key,api_secret,"/fapi/v1/order",params)
    print(order,"\n")
    return order

def order_cancel_batch(api_key, api_secret, symbol, ids):
    params = {"symbol": symbol, "origClientOrderIdList": ids}
    orders = send_signed_request("DELETE", api_key, api_secret,"/fapi/v1/batchOrders", params)
    print(orders)

def change_margin_type(api_key, api_secret, symbol, marginType):
    """
    ISOLATED, CROSSED
    """
    params = {"symbol": symbol, "marginType": marginType}
    margin = send_signed_request("POST", api_key, api_secret,"/fapi/v1/marginType", params)
    print(margin)

def change_margin_type_all(api_key, api_secret, marginType):
    """
    ISOLATED, CROSSED
    """
    exchange = fetch_exchange_info_all()
    for data in exchange:
        symbol = data[1]
        change_margin_type(api_key, api_secret, symbol, marginType)
        time.sleep(0.5)

def change_leverage(api_key, api_secret, symbol, leverage):
    params = {"symbol": symbol, "leverage": leverage}
    leverage = send_signed_request("POST", api_key, api_secret, "/fapi/v1/leverage", params)
    print(leverage)

def change_leverage_all(api_key, api_secret, leverage):
    exchange = fetch_exchange_info_all()
    for data in exchange:
        symbol = data[1]
        change_leverage(api_key, api_secret, symbol, leverage)
        time.sleep(0.5)

def change_multiAssetsMargin(api_key, api_secret, multiAssetsMargin):
    """
    "true": Multi-Assets Mode; "false": Single-Asset Mode
    """
    params = {"multiAssetsMargin": multiAssetsMargin}
    multi = send_signed_request("POST", api_key, api_secret, "/fapi/v1/multiAssetsMargin", params)
    print(multi)

def change_positionSide(api_key, api_secret, dualSidePosition):
    """
    "true": Hedge Mode; "false": One-way Mode
    """
    params = {"dualSidePosition": dualSidePosition}
    positionSide = send_signed_request("POST", api_key, api_secret, "/fapi/v1/positionSide/dual", params)
    print(positionSide)

def get_account_info(api_key, api_secret):
    return send_signed_request("GET", api_key, api_secret, "/fapi/v2/account")

################################################################################### Websockets & Callbacks
def on_open(ws):
    print("open connection")

def on_close(ws):
    ws.close()
    print("close connection")

def market_kline_on_message(ws, message):
    data = json.loads(message)['k']

    update_kline(data)

    if data['x'] == True:
        insert_empty_kline(data['s'])

    time.sleep(0.1)
    # print(data)

def user_data_on_message(ws,message):
    data = json.loads(message)
    e = data['e']
    
    if e == "ORDER_TRADE_UPDATE":
        o = data['o']
        symbol = o["s"]
        status = o["X"]
        pnl = float(o["rp"])
        clientID:str = o["c"]
        
        complete_strategy_id = extract_string(clientID, "i")
        row_id = extract_string(clientID, "i", "u")
        user_id = extract_string(clientID, "u", "q")
        leverage = extract_string(clientID, "q")
        
        if clientID.startswith("tp0") or clientID.startswith("sl0") or clientID.startswith("o0"):
            if status == "FILLED":
                # Update PNL user_strategy
                fee = float(o["n"])
                strategy_user = fetch_user_strategy_id(row_id)
                current_money = strategy_user[10]
                new_current_money = current_money + pnl - fee
                update_user_strategy_current_money(new_current_money, row_id)

                # Update TP
                if clientID.startswith("tp0"):
                    update_user_strategy_is_sl(False, row_id)
                elif clientID.startswith("sl0"):
                    update_user_strategy_is_sl(True, row_id)
                
                # Cancel Other TP / SL
                if clientID.startswith("tp0") or clientID.startswith("sl0"):
                    # Cancel TP/SL
                    user = fetch_user(user_id)
                    api_key = user[3]
                    api_secret = user[4]
                    ids = ["sl0i"+complete_strategy_id, "tp0i"+complete_strategy_id]
                    order_cancel_batch(api_key, api_secret, symbol, ids)
                
                # Insert PNL in user_strategy_pnl table (for history)
                insert_user_strategy_pnl([clientID, pnl, fee])
                
        print(data)


def ws(stream_name, callback, extra):
    # Extract extra
    extra_belong_to = extra[0]
    extra_header = None
    if len(extra) > 1 :
        extra_header = extra[1]

    SOCKET = "wss://fstream.binance.com/ws/" + stream_name
    ws = websocket.WebSocketApp(SOCKET,header=extra_header,on_open=on_open,on_close=on_close,on_message=callback)
    # Insert WS to DB for when server is dead
    d = db.execute("INSERT INTO stream_list (stream_name, status, belong_to) VALUES (?, True, ?)", [stream_name, extra_belong_to])
    db.commit()
    print(f"{stream_name} - Inserted Into Database")
    last_row = d.lastrowid
    stream_list_id = fetch_stream_list(last_row)
    stream_list = {"id":stream_list_id, "ws_object": ws}
    ws_list.append(stream_list)
    print(f"{stream_name} - Inserted Into Websocket LIST")
    ws.run_forever()

################################################################################### Spiders
# Spiders are independed, they are going and collecting data for us and saving them into database
# - Symbol Finder
def spider_symbol_percent():
    while True:
        exchange = fetch_exchange_info_all()
        # exchange = [ # TEST
        #     (0,"ADAUSDT"),
        #     (1,"BNBUSDT"),
        #     (2,"XRPUSDT"),
        #     (3,"TRXUSDT"),
        # ]
        for data in exchange:
            symbol = data[1]
            klines = ohlcv(symbol, "1m", 99)
            
            symbol_closes = []
            for kline in klines:
                close = float(kline[4])
                symbol_closes.append(close)
            
            min_close = min(symbol_closes)
            max_close = max(symbol_closes)
            percent = 100 - ((min_close * 100) / max_close)
            update_exchange_info_percent(percent, symbol)
            time.sleep(0.5)
        time.sleep(60 * 30)

def spider_create_df():
    while True:
        streams = fetch_stream_list_kline()
        for stream in streams:
            stream_name = stream[1]
            symbol = extract_string(stream_name, end="@").upper()
            klines = fetch_kline_df(symbol)
            kdf = ta.DataFrame(klines)
            if len(df_list) == 0:
                df_list.append({"symbol": symbol, "df": kdf})
            
            for i in df_list:
                i_symbol = i["symbol"]
                if i_symbol == symbol:
                    i["df"] = kdf
        time.sleep(2)

################################################################################### Strategy
def symbol_info(symbol):
    data = fetch_exchange_info_one(symbol)
    if data == None:
        new_data = exchange_info(new_symbol=symbol)
        if new_data:
            return new_data
        else:
            print("There is no coin")
            return False
    return data
    
def strategy(symbol, file_to_load):
    klines = fetch_kline_df(symbol)
    df = ta.DataFrame(klines)
    return importlib.import_module("Strategy." + file_to_load).strategy(df)

def strategy_order(data, signal):
    api_key = data[0]
    api_secret = data[1]
    symbol = data[2]
    quantity = data[3]
    uuid = data[4]

    ione = fetch_exchange_info_one(symbol)
    pricePrecision = ione[2]

    side = signal[0].upper()
    swap_side = ""
    positionSide = ""
    if side == "BUY":
        positionSide = "LONG"
        swap_side = "SELL"
    if side == "SELL":
        positionSide = "SHORT"
        swap_side = "BUY"
    
    order = new_order(api_key, api_secret, symbol, side, "MARKET", quantity, "o0" + uuid, positionSide=positionSide)
    if hasattr(order,'code') == False:
        if order["status"] == "NEW":
            # Stop Loss
            stoploss = signal[2]
            stoploss = perc(stoploss, pricePrecision)
            new_order(api_key, api_secret, symbol, swap_side, "STOP_MARKET", quantity, "sl0" + uuid, stoploss, positionSide)

            # if Take Profit Comes, Submit Take Profit
            if len(signal) == 4:
                takeprofit = signal[3]
                takeprofit = perc(takeprofit, pricePrecision)
                new_order(api_key, api_secret, symbol, swap_side, "TAKE_PROFIT_MARKET", quantity, "tp0" + uuid, takeprofit, positionSide)

def user_strategy(_id):
    while True:
        data = fetch_all_user_strategy_id(_id)
        id = data[0]
        user_id = data[1]
        strategy_id = data[2]
        is_active = data[3]
        in_position = data[4]
        is_compound = data[5]
        is_auto_symbol = data[6]
        is_time_limited = data[7]
        is_sl = data[8] # will not use here
        is_overwrite_tp = data[9]
        is_overwrite_sl = data[10]
        overwrite_tp_percent = data[11]
        overwrite_sl_percent = data[12]
        symbol = data[13]
        max_money = data[14]
        current_money = data[15]
        max_compound_money = data[16]
        time_end = data[17]
        file = data[19]

        uuid = f"i{id}u{user_id}"
        current_thread_id = tr.get_ident()

        pass_time = True
        if is_time_limited:
            if time.time() >= time_end:
                pass_time = False
                print("time pass: False, its over")

        # test = False
        if in_position == 0 and is_active and pass_time:

            order_symbol: str
            if is_auto_symbol == False:
                order_symbol = symbol
            else: 
                order_symbol = fetch_exchange_info_max_percent()[0]

            # Now check if the order_symbol is available in websockets,
            # otherwise create ws for this order_symbol
            symbol_in_ws = fetch_stream_list_symbol(order_symbol)
            if symbol_in_ws == None:
                max_thread = prevent(current_thread_id)
                if current_thread_id == max_thread:
                    market_kline_ws_multi(order_symbol)
                    # flush thread
                    memory_db.execute("DELETE FROM thread")
                    memory_db.commit()
                else: 
                    # its smaller thread, so it should wait for the next round
                    print(current_thread_id, "Waiting for the next round...")
            else:
                signal = strategy(order_symbol, file)
                print(signal)

                user = fetch_user(user_id)
                api_key = user[3]
                api_secret = user[4]

                if signal:
                    si = symbol_info(order_symbol)
                    minQty = si[4]
                    quantity_perc_symbol = si[3]

                    last_close_price = signal[1]
                    leverage = fetch_user_settings_leverage(user_id, order_symbol)[0]
                    
                    money: float = 0
                    if current_money <= max_compound_money:
                        if is_compound == True and current_money:
                            money = current_money * CONFIG_MONEY_MARGIN
                        else:
                            if max_money <= current_money:
                                money = max_money * CONFIG_MONEY_MARGIN
                            else: 
                                money = 0 # you dont have enough money
                    else:
                        money = 0

                    total_money = leverage * money
                    quantity = total_money / last_close_price
                    quantity = perc(quantity, quantity_perc_symbol)

                    new_uuid = uuid + "q" + str(leverage)
                    order_params = [api_key, api_secret, order_symbol, quantity, new_uuid]

                    if quantity >= minQty:
                        update_user_strategy_in_position(True, id)
                        strategy_order(order_params, signal)
                    
                        # ["buy", close, SL] # TP is on fly
                        if len(signal) == 3:
                            side = signal[0]
                            strategy_tp_multi(order_params, side, file)
                    else:
                        print("You dont have enough money")
                        update_user_strategy_in_position(True, id)
        time.sleep(2)    

def strategy_test():
    # test strategies with /History/Symbol.csv Data
    # and /Strategy/*.py Logic
    print("Dynamic import test() from /Strategy/*.py")

def strategy_tp(params, side, file):
    # For Order
    api_key = params[0]
    api_secret = params[1]
    symbol = params[2]
    quantity = params[3]
    uuid = params[4]
    row_id = extract_string(uuid, "i", "u")
    
    # Signal
    tp_signal: bool
    sl: bool
    while True:
        klines = fetch_kline_df(symbol)
        df = ta.DataFrame(klines)
        signal = importlib.import_module("Strategy." + file).tp(df, side)
        
        user_strategy = fetch_user_strategy_id(row_id)
        is_sl = user_strategy[8]
        if is_sl:
            sl = is_sl
            break
        elif signal:
            tp_signal = signal
            break
        time.sleep(2)

    # Order
    if tp_signal and sl == False:
        side = signal[0].upper()
        swap_side = ""
        positionSide = ""
        if side == "BUY":
            positionSide = "LONG"
            swap_side = "SELL"
        if side == "SELL":
            positionSide = "SHORT"
            swap_side = "BUY"
        new_order(api_key, api_secret, symbol, swap_side, "MARKET", quantity, "o0" + uuid, positionSide=positionSide)
    
    # change SL to false again
    update_user_strategy_is_sl(False, row_id)
    

################################################################################### Multi Processing - Threading
def spider_symbol_percent_multi():
    t = tr.Thread(target=spider_symbol_percent)
    t.start()

def strategy_multi():
    user_strategies = fetch_all_user_strategy()
    for strategy in user_strategies:
        id = strategy[0]
        t = tr.Thread(target=user_strategy, args=[id])
        t.start()

def strategy_tp_multi(params, side, file):
    t = tr.Thread(target=strategy_tp, args=[params, side, file])
    t.start()
 
def market_kline_ws_multi(symbol: str,interval="1m",limit=199):
    
    can_i_go = time_condition()

    if can_i_go:
        # Fetch,Insert OHLCV
        klines = ohlcv(symbol,interval,limit)
        insert_kline(symbol, klines)
        
         # Run WS
        symbol_lower = symbol.lower()
        symbol_lower += "@kline_" + interval
        extra = ["market_kline"]
        t = tr.Thread(target=ws, args=[symbol_lower,market_kline_on_message,extra])
        t.start()
    time.sleep(1)


def user_data_ws_multi(user_id):
    user = fetch_user(user_id)
    
    id = user[0]
    api_key = user[3]
    api_secert = user[4]
    listen_key = generate_listenKey(api_key)
    db.execute("""UPDATE user SET listen_key=? WHERE id=?""", [listen_key, id])
    db.commit()

    # User Account Info
    insert_user_settings_leverage(api_key, api_secert, id)
    
    # Listen Key
    header = {"X-MBX-APIKEY": api_key}
    extra = [f"user_data", header]
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
    db.execute("DELETE FROM stream_list WHERE belong_to='user_data'")
    db.commit()

    users = fetch_all_user()
    for user in users:
        id = user[0]
        user_data_ws_multi(id)
    
def reboot_market_kline(interval="1m"):
    streams = fetch_stream_list_kline()
    if len(ws_list) == 0:
        for stream in streams:
            id = stream[0]
            stream_name:str = stream[1]
            status = stream[2]
            
            db.execute("DELETE FROM stream_list WHERE id=?", [id])
            db.commit()

            if status:
                symbol = stream_name.replace("@kline_" + interval, "").upper()
                market_kline_ws_multi(symbol)

def reboot():
    # check if internet connection died for 3minutes, then call this function one more time
    reboot_market_kline()
    reboot_user_data()
################################################################################### Sanic Framework
# Sanic|Flask here

################################################################################### Run On Startup - Forever
if __name__ == '__main__':
    # # reboot()
    exchange_info()
    spider_symbol_percent_multi()
    wait_for_exchange_info()
    
    # Kline Stream
    clean_kline_db_multi()

    # # # User Stream
    time.sleep(1)
    user_data_ws_multi(1)

    time.sleep(5)
    strategy_multi()
