import os
import numpy as np
from scipy.stats import mannwhitneyu
from round_trips import load_zerodha, build_round_trips


def disposition_effect(rt):
    """Bias 1: does the trader hold losers longer than winners?"""
    winners = rt[rt["pnl"] > 0]["days_held"]
    losers = rt[rt["pnl"] < 0]["days_held"]

    if len(winners) < 5 or len(losers) < 5:
        return {"detected": False, "severity": "Low", "note": "Not enough data"}

    avg_win = winners.mean()
    avg_loss = losers.mean()
    ratio = avg_loss / max(avg_win, 0.5)

    _, p_value = mannwhitneyu(losers, winners, alternative="greater")

    significant = p_value < 0.05
    if significant and ratio >= 3:
        severity = "High"
    elif significant and ratio >= 1.5:
        severity = "Medium"
    else:
        severity = "Low"

    return {
        "detected": bool(significant and ratio >= 1.5),
        "avg_days_winners": round(avg_win, 1),
        "avg_days_losers": round(avg_loss, 1),
        "ratio": round(ratio, 1),
        "p_value": float(p_value),
        "severity": severity,
    }


def overtrading_after_loss(rt):
    """Bias 2: after a loss, does the trader jump back in faster / bigger?"""
    by_entry = rt.sort_values("entry_date").reset_index(drop=True)
    entry_times = by_entry["entry_date"].values

    rows = []
    for _, t in rt.iterrows():
        # find the very next trade the trader entered after this one closed
        i = entry_times.searchsorted(t["exit_date"].to_datetime64(), side="right")
        if i >= len(by_entry):
            continue
        nxt = by_entry.loc[i]
        gap_days = (nxt["entry_date"] - t["exit_date"]).total_seconds() / 86400
        rows.append({
            "was_loss": t["pnl"] < 0,
            "gap_days": gap_days,
            "next_qty": nxt["quantity"],
        })

    import pandas as pd
    df = pd.DataFrame(rows)
    after_loss = df[df["was_loss"]]
    after_win = df[~df["was_loss"]]

    if len(after_loss) < 5 or len(after_win) < 5:
        return {"detected": False, "severity": "Low", "note": "Not enough data"}

    gap_loss = after_loss["gap_days"].mean()
    gap_win = after_win["gap_days"].mean()
    speedup = gap_win / max(gap_loss, 0.1)  # how many times faster after a loss
    size_ratio = after_loss["next_qty"].mean() / after_win["next_qty"].mean()

    # is the wait after a loss significantly SHORTER than after a win?
    _, p_value = mannwhitneyu(after_loss["gap_days"], after_win["gap_days"],
                              alternative="less")

    significant = p_value < 0.05
    strength = max(speedup, size_ratio)
    if significant and strength >= 3:
        severity = "High"
    elif significant and strength >= 1.5:
        severity = "Medium"
    else:
        severity = "Low"

    return {
        "detected": bool(significant and strength >= 1.5),
        "gap_after_loss_days": round(gap_loss, 2),
        "gap_after_win_days": round(gap_win, 2),
        "size_ratio": round(size_ratio, 2),
        "p_value": float(p_value),
        "severity": severity,
    }


def panic_selling(rt):
    """Bias 3: quick exits at a loss, much shorter than the trader's normal hold."""
    losers = rt[rt["pnl"] < 0]
    if len(losers) < 5:
        return {"detected": False, "severity": "Low", "note": "Not enough data"}

    median_hold = rt["days_held"].median()
    limit = max(1, 0.25 * median_hold)
    panic = losers[losers["days_held"] <= limit]
    rate = len(panic) / len(losers)

    if rate >= 0.6:
        severity = "High"
    elif rate >= 0.3:
        severity = "Medium"
    else:
        severity = "Low"

    return {
        "detected": bool(rate >= 0.3),
        "panic_trades": int(len(panic)),
        "panic_rate": round(rate, 2),
        "severity": severity,
    }


if __name__ == "__main__":
    folder = "data/synthetic"
    for name in sorted(os.listdir(folder)):
        rt = build_round_trips(load_zerodha(os.path.join(folder, name)))
        d = disposition_effect(rt)
        o = overtrading_after_loss(rt)
        p = panic_selling(rt)
        print(f"{name:26} disposition={d['severity']:7} "
              f"overtrading={o['severity']:7} panic={p['severity']:7}")