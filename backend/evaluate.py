import os
from analyze import analyze

EXPECTED = {"biased": "disposition_effect", "panic": "panic_selling",
            "revenge": "overtrading_after_loss", "disciplined": None}
BIASES = ["disposition_effect", "overtrading_after_loss", "panic_selling"]

folder = "data/synthetic"
rows = []
for name in sorted(os.listdir(folder)):
    style = name.split("_")[1]
    r = analyze(os.path.join(folder, name))
    found = {b for b in BIASES if r["biases"][b]["detected"]}
    want = {EXPECTED[style]} - {None}
    rows.append((name, want, found))
    print(f"{name:26} expected={sorted(want) or 'none'}  found={sorted(found) or 'none'}  {'OK' if want == found else 'WRONG'}")

print()
for b in BIASES:
    tp = sum(1 for _, w, f in rows if b in w and b in f)
    fp = sum(1 for _, w, f in rows if b not in w and b in f)
    fn = sum(1 for _, w, f in rows if b in w and b not in f)
    print(f"{b:24} caught={tp}  missed={fn}  false alarms={fp}")

ok = sum(1 for _, w, f in rows if w == f)
print(f"\nOverall: {ok}/{len(rows)} traders classified correctly")