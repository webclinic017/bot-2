import sqlite3

conn = sqlite3.connect('bot.sqlite', check_same_thread=False, isolation_level=None)
conn.execute('pragma journal_mode=wal')
conn.commit()
print("Database Connected")

def user():
    create_table = """
    CREATE TABLE "user" (
        "id"	INTEGER NOT NULL,
        "usrename"	TEXT UNIQUE,
        "password"	TEXT,
        "api_key"	TEXT,
        "api_secret"	TEXT,
        "listen_key"	TEXT,
        "telegram_id"	NUMERIC,
        "telegram_user"	TEXT,
        "role"	TEXT DEFAULT 'user',
        "is_active"	INTEGER DEFAULT 1,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
    """
    conn.execute(create_table)
    conn.commit()

def user_strategy():
    create_table = """
    CREATE TABLE "user_strategy" (
        "id"	INTEGER NOT NULL,
        "user_id"	INTEGER,
        "strategy_id"	INTEGER,
        "is_active"	INTEGER DEFAULT 0,
        "in_position"	INTEGER DEFAULT 0,
        "is_compound"	INTEGER DEFAULT 0,
        "is_auto_symbol"	INTEGER DEFAULT 0,
        "is_time_limited"	INTEGER DEFAULT 0,
        "is_sl"	INTEGER DEFAULT 0,
        "is_overwrite_tp"	INTEGER DEFAULT 0,
        "is_overwrite_sl"	INTEGER DEFAULT 0,
        "overwrite_tp_percent"	INTEGER,
        "overwrite_sl_percent"	INTEGER,
        "symbol"	TEXT,
        "max_money"	NUMERIC,
        "current_money"	NUMERIC,
        "max_compound_money"	NUMERIC,
        "time_end"	DATETIME,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
    """
    conn.execute(create_table)
    conn.commit()

def strategy():
    create_table = """
    CREATE TABLE "strategy" (
        "id"	INTEGER NOT NULL,
        "file"	TEXT,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
    """
    conn.execute(create_table)
    conn.commit()

def stream_list():
    create_table = """
    CREATE TABLE "stream_list" (
        "id"	INTEGER NOT NULL,
        "stream_name"	TEXT UNIQUE,
        "status"	INTEGER,
        "belong_to"	TEXT,
        "created_at"	DATETIME DEFAULT CURRENT_TIMESTAMP,
        "updated_at"	DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
    """
    conn.execute(create_table)
    conn.commit()

def user_strategy_pnl():
    create_table = """
    CREATE TABLE "user_strategy_pnl" (
        "id"	INTEGER NOT NULL,
        "client_order_id"	TEXT,
        "pnl"	NUMERIC,
        "fee"	NUMERIC,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
    """
    conn.execute(create_table)
    conn.commit()
###########################
