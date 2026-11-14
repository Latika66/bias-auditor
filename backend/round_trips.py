import os
from collections import deque
import pandas as pd


def load_zerodha(path):
    """Read a Zerodha-style tradebook into our common format."""
    df = pd.read_csv(path)
    df = df.rename(columns={
        "trade_type": "side",
        "order_execution_time": "timestamp",
    })
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df[["symbol", "side", "quantity", "price", "timestamp"]]


def build_round_trips(trades):
    """Match buys with sells (FIFO = first bought, first sold)."""
    trades = trades.sort_values("timestamp")
    results = []

    for symbol, group in trades.groupby("symbol"):
        buys = deque()  # waiting list of unsold buys, oldest first

        for _, t in group.iterrows():
            if t["side"] == "buy":
                buys.append({"qty": t["quantity"], "price": t["price"],
                             "time": t["timestamp"]})
            else:
                sell_qty = t["quantity"]
                while sell_qty > 0 and buys:
                    lot = buys[0]  # the oldest buy
                    matched = min(lot["qty"], sell_qty)
                    results.append({
                        "symbol": symbol,
                        "entry_date": lot["time"],
                        "exit_date": t["timestamp"],
                        "entry_price": lot["price"],
                        "exit_price": t["price"],
                        "quantity": matched,
                    })
                    lot["qty"] -= matched
                    sell_qty -= matched
                    if lot["qty"] == 0:
                        buys.popleft()

    rt = pd.DataFrame(results).sort_values("exit_date").reset_index(drop=True)
    rt["days_held"] = (rt["exit_date"] - rt["entry_date"]).dt.days
    rt["pnl"] = (rt["exit_price"] - rt["entry_price"]) * rt["quantity"]
    rt["return_pct"] = (rt["exit_price"] / rt["entry_price"] - 1) * 100
    return rt


if __name__ == "__main__":
    folder = "data/synthetic"
    for name in sorted(os.listdir(folder)):
        rt = build_round_trips(load_zerodha(os.path.join(folder, name)))
        win = rt[rt["pnl"] > 0]["days_held"].mean()
        loss = rt[rt["pnl"] < 0]["days_held"].mean()
        print(f"{name:32} trips={len(rt):3}  winners_held={win:5.1f}d  losers_held={loss:5.1f}d")