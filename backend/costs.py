import os
import pandas as pd
from round_trips import load_zerodha, build_round_trips


def disposition_cost(rt, stop_loss_pct=5.0):
    """What if every loss had been cut at -stop_loss_pct% instead?"""
    losers = rt[rt["return_pct"] < -stop_loss_pct]
    # loss at the stop-loss level
    capped_loss = -(stop_loss_pct / 100) * losers["entry_price"] * losers["quantity"]
    actual_loss = losers["pnl"]
    saved = capped_loss - actual_loss  # positive number = money saved
    return float(saved.sum())


def overtrading_cost(rt):
    """What if trades taken within 1 day after a loss had been skipped?"""
    by_exit = rt.sort_values("exit_date").reset_index(drop=True)
    skipped_pnl = 0.0
    count = 0
    for _, t in rt.iterrows():
        # was there a losing trade that closed within 1 day before this entry?
        recent = by_exit[
            (by_exit["pnl"] < 0)
            & (by_exit["exit_date"] <= t["entry_date"])
            & (by_exit["exit_date"] >= t["entry_date"] - pd.Timedelta(days=1))
        ]
        if len(recent) > 0:
            skipped_pnl += t["pnl"]
            count += 1
    # cost = money lost on those trades (if they made money overall, cost is 0)
    return float(max(-skipped_pnl, 0)), count


if __name__ == "__main__":
    folder = "data/synthetic"
    for name in sorted(os.listdir(folder)):
        rt = build_round_trips(load_zerodha(os.path.join(folder, name)))
        total = rt["pnl"].sum()
        d_cost = disposition_cost(rt)
        o_cost, n = overtrading_cost(rt)
        print(f"{name:26} total_pnl={total:10.0f}  "
              f"disposition_cost={d_cost:9.0f}  "
              f"overtrading_cost={o_cost:8.0f} ({n} trades)")