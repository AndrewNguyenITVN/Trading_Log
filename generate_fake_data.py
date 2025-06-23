import sqlite3
import random
from datetime import datetime, timedelta
import os

# --- Configuration ---
DB_FILE = os.path.join('instance', 'trading_journal.db')
NUM_TRADES = 100  # Number of fake trades to generate
START_DATE = datetime.now() - timedelta(days=180) # Trades over the last 6 months

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists('instance'):
        os.makedirs('instance')
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_profit(entry_price, exit_price, position_size, order_type, instrument):
    """Calculates net profit based on trade parameters."""
    pip_size = 0.01 if 'jpy' in instrument.lower() else 0.0001
    pip_value_per_lot = 10  # For USD quoted pairs

    if order_type.upper() == 'BUY':
        pips = (exit_price - entry_price) / pip_size
    else:  # SELL
        pips = (entry_price - exit_price) / pip_size
        
    profit = pips * pip_value_per_lot * position_size
    return round(profit, 2)

def create_fake_trade(trade_id):
    """Generates a single fake trade with realistic and consistent data."""
    instrument = random.choice(['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'XAU/USD'])
    order_type = random.choice(['BUY', 'SELL'])
    status = random.choice(['WIN', 'LOSS', 'BREAKEVEN'])
    
    entry_datetime = START_DATE + timedelta(
        days=random.randint(0, 179),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    exit_datetime = entry_datetime + timedelta(minutes=random.randint(5, 240))

    pip_size = 0.01 if 'jpy' in instrument.lower() else 0.0001
    price_decimals = 2 if 'jpy' in instrument.lower() else 4
    
    entry_price = round(random.uniform(1.05, 1.35) if 'jpy' not in instrument.lower() else random.uniform(100, 150), price_decimals)
    position_size = round(random.choice([0.01, 0.02, 0.05, 0.1, 0.5, 1.0]), 2)
    
    # Determine exit price based on status
    pips_moved = random.randint(5, 150) * pip_size
    
    if status == 'WIN':
        exit_price = entry_price + pips_moved if order_type == 'BUY' else entry_price - pips_moved
    elif status == 'LOSS':
        exit_price = entry_price - pips_moved if order_type == 'BUY' else entry_price + pips_moved
    else: # BREAKEVEN
        exit_price = entry_price

    exit_price = round(exit_price, price_decimals)
    
    # Set logical SL/TP
    sl_pips = random.randint(10, 50) * pip_size
    tp_pips = random.randint(20, 200) * pip_size
    
    stop_loss = entry_price - sl_pips if order_type == 'BUY' else entry_price + sl_pips
    take_profit = entry_price + tp_pips if order_type == 'BUY' else entry_price - tp_pips
    
    net_profit = calculate_profit(entry_price, exit_price, position_size, order_type, instrument)

    return (
        entry_datetime, exit_datetime, instrument, order_type,
        entry_price, exit_price, round(stop_loss, price_decimals), round(take_profit, price_decimals),
        position_size, status, net_profit,
        round(net_profit / (sl_pips / pip_size * 10 * position_size) if sl_pips > 0 and position_size > 0 else 0, 2), # R-value
        "This is a generated rationale for the trade setup.",
        "This is a generated review of the trade outcome.",
        random.choice(["Confident", "Anxious", "Neutral", "Greedy"]),
        random.choice(["Trend Following", "Breakout", "Scalping", "News Trade"])
    )

def main():
    """Main function to clear existing trades and populate the database."""
    print(f"Connecting to database: {DB_FILE}")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if sqlite_sequence table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        has_sequence_table = cursor.fetchone()

        print("Clearing existing data from 'trades' table...")
        cursor.execute("DELETE FROM trades")
        if has_sequence_table:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'trades'")
        
        # Check if trade_image table exists before trying to clear it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_image'")
        if cursor.fetchone():
            print("Clearing existing data from 'trade_image' table...")
            cursor.execute("DELETE FROM trade_image")
            if has_sequence_table:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'trade_image'")

        print("Existing data cleared.")

        print(f"Generating and inserting {NUM_TRADES} fake trades...")
        for i in range(NUM_TRADES):
            trade_data = create_fake_trade(i + 1)
            cursor.execute("""
                INSERT INTO trades (
                    entry_datetime, exit_datetime, instrument, order_type,
                    entry_price, exit_price, initial_stop_loss, initial_take_profit,
                    position_size, status, net_profit, r_value,
                    rationale, review, emotions, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, trade_data)
        
        conn.commit()
        print(f"Successfully inserted {NUM_TRADES} new fake trades.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == '__main__':
    main() 