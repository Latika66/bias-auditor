import os
import random
from datetime import datetime, timedelta
import pandas as pd

random.seed(42)  # makes results the same every run

# Stock name -> rough price
STOCKS = {
    "TCS": 3800, "INFY": 1600, "RELIANCE": 2400, "HDFCBANK": 1650,
    "ITC": 420, "SBIN": 620, "ICICIBANK": 1000, "WIPRO": 450,
    "AXISBANK": 1050, "LT": 3300, "MARUTI": 10500, "TITAN": 3400,
    "HCLTECH": 1450, "BAJFINANCE": 7200, "ASIANPAINT": 2900,
    "SUNPHARMA": 1250, "ONGC": 230, "NTPC": 280, "COALINDIA": 380,
    "POWERGRID": 260, "TATASTEEL": 130, "HINDUNILVR": 2500,
    "KOTAKBANK": 1750, "M&M": 1600, "ADANIPORTS": 800,
    "BHARTIARTL": 900, "ULTRACEMCO": 8500, "NESTLEIND": 2400,
    "TECHM": 1200, "DRREDDY": 5500,
}


def make_trader(trader_id, style, n_trades=120):
    """style = 'disciplined', 'biased', 'panic', or 'revenge'"""
    rows = []
    trade_counter = 1
    entry_date = datetime(2023, 1, 2, 10, 0)
    busy_until = {}  # remembers until when each stock is held
    after_loss = False  # did the previous trade end in a loss?

    for _ in range(n_trades):
        free = [s for s in STOCKS if busy_until.get(s, datetime.min) < entry_date]
        symbol = random.choice(free or list(STOCKS))
        buy_price = round(STOCKS[symbol] * random.uniform(0.9, 1.1), 2)
        qty = random.choice([10, 20, 25, 50])
        if style == "revenge" and after_loss:
            qty *= 2  # bigger bet right after a loss
        is_win = random.random() < (0.35 if style == "revenge" and after_loss else 0.5)

        if style == "biased":
            # sells winners fast, holds losers very long
            if is_win:
                hold_days = random.randint(1, 4)
                change = random.uniform(0.01, 0.04)
            else:
                hold_days = random.randint(30, 90)
                change = -random.uniform(0.05, 0.15)
        elif style == "panic":
            # exits losing trades within 1 day
            if is_win:
                hold_days = random.randint(3, 10)
                change = random.uniform(0.02, 0.06)
            else:
                hold_days = 1
                change = -random.uniform(0.03, 0.08)
        elif style == "revenge":
            hold_days = random.randint(2, 5)
            change = random.uniform(0.02, 0.05) if is_win else -random.uniform(0.02, 0.06)
        else:
            # disciplined: similar holding time for wins and losses
            hold_days = random.randint(3, 10)
            change = random.uniform(0.02, 0.06) if is_win else -random.uniform(0.02, 0.05)

        sell_price = round(buy_price * (1 + change), 2)
        exit_date = entry_date + timedelta(days=hold_days)
        busy_until[symbol] = exit_date

        # one BUY row and one SELL row, like a real tradebook
        for side, price, when in [("buy", buy_price, entry_date),
                                  ("sell", sell_price, exit_date)]:
            rows.append({
                "symbol": symbol,
                "isin": "",
                "trade_date": when.strftime("%Y-%m-%d"),
                "exchange": "NSE",
                "segment": "EQ",
                "series": "EQ",
                "trade_type": side,
                "auction": "FALSE",
                "quantity": qty,
                "price": price,
                "trade_id": f"{trader_id}{trade_counter:05d}",
                "order_id": f"{trader_id}{trade_counter:05d}",
                "order_execution_time": when.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            trade_counter += 1

        if style == "revenge":
            # after a loss: jump back in within 1 hour; after a win: wait 2-4 days
            if is_win:
                entry_date = exit_date + timedelta(days=random.randint(2, 4))
            else:
                entry_date = exit_date + timedelta(hours=1)
            after_loss = not is_win
        else:
            entry_date += timedelta(days=random.randint(1, 4))  # next trade

    df = pd.DataFrame(rows).sort_values("order_execution_time")
    return df


if __name__ == "__main__":
    os.makedirs("data/synthetic", exist_ok=True)

    traders = (
        [("disciplined", i) for i in range(1, 5)]
        + [("biased", i) for i in range(1, 5)]
        + [("panic", i) for i in range(1, 4)]
        + [("revenge", i) for i in range(1, 4)]
    )

    for style, i in traders:
        df = make_trader(f"{style[0].upper()}{i}", style)
        path = f"data/synthetic/trader_{style}_{i}.csv"
        df.to_csv(path, index=False)
        print("Created", path, "-", len(df), "rows")