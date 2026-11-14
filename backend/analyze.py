import json
import os
from round_trips import load_zerodha, build_round_trips
from detectors import disposition_effect, overtrading_after_loss, panic_selling
from costs import disposition_cost, overtrading_cost

PENALTY = {"High": 30, "Medium": 15, "Low": 0}


def analyze(path):
    """Run the full pipeline on one tradebook file and return a result dict."""
    rt = build_round_trips(load_zerodha(path))

    d = disposition_effect(rt)
    o = overtrading_after_loss(rt)
    p = panic_selling(rt)

    # only report a cost when the bias was actually detected
    d["cost"] = round(disposition_cost(rt)) if d["detected"] else 0
    if o["detected"]:
        cost, n = overtrading_cost(rt)
        o["cost"], o["trades_affected"] = round(cost), n
    else:
        o["cost"], o["trades_affected"] = 0, 0
    p["cost"] = None  # panic cost is future work

    biases = {"disposition_effect": d, "overtrading_after_loss": o, "panic_selling": p}

    # discipline score: start at 100, subtract points for each detected bias
    score = 100 - sum(PENALTY[b["severity"]] for b in biases.values() if b["detected"])
    score = max(score, 0)

    # personality label: based on the most severe detected bias
    labels = {
        "disposition_effect": "The Hopeful Holder",
        "overtrading_after_loss": "The Revenge Trader",
        "panic_selling": "The Nervous Seller",
    }
    detected = [(PENALTY[b["severity"]], k) for k, b in biases.items() if b["detected"]]
    label = labels[max(detected)[1]] if detected else "The Steady Hand"

    return {
        "file": os.path.basename(path),
        "total_trades": int(len(rt)),
        "total_pnl": round(float(rt["pnl"].sum())),
        "discipline_score": score,
        "personality": label,
        "total_estimated_cost": d["cost"] + o["cost"],
        "biases": biases,
    }


if __name__ == "__main__":
    folder = "data/synthetic"
    os.makedirs("data/results", exist_ok=True)
    for name in sorted(os.listdir(folder)):
        result = analyze(os.path.join(folder, name))
        out = "data/results/" + name.replace(".csv", ".json")
        with open(out, "w") as f:
            json.dump(result, f, indent=2, default=float)
        print(f"{name:26} score={result['discipline_score']:3}  "
              f"{result['personality']:20} cost=Rs {result['total_estimated_cost']}")