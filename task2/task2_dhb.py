import pulp
import pandas as pd
import random
import json

# -----------------------------
# rtp generation (random but structured)
# -----------------------------

def generate_rtp(hours, seed=42, offpeak_range=(0.2, 0.7), peak_range=(0.8, 1.5), peak_hours=None):
    # generates hourly rtp prices in nok/kwh
    # peak_hours is a set of hours where price tends to be higher
    random.seed(seed)
    if peak_hours is None:
        peak_hours = set(range(17, 21))  # 17-20 as typical peak window

    prices = []
    for h in hours:
        if h in peak_hours:
            prices.append(random.uniform(*peak_range))
        else:
            prices.append(random.uniform(*offpeak_range))
    return prices

def save_prices(prices, path="rtp_prices_task2.json"):
    # saves prices so you can reuse the exact same curve in task 4
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prices, f, indent=2)

# -----------------------------
# baseline (non-shiftable + random small appliances)
# -----------------------------

def build_baseline_kw():
    # baseline in kw per hour (0..23)
    # keep it simple but realistic, you can tune numbers later
    b = [0.25] * 24  # fridge/router/standby baseline

    # lighting 10-20 (example: 1.5 kwh over 10 hours -> 0.15 kw)
    for t in range(10, 20):
        b[t] += 0.15

    # heating: higher in morning/evening (example pattern)
    for t in range(6, 9):
        b[t] += 0.8
    for t in range(17, 23):
        b[t] += 1.0

    # stove: lunch + dinner peaks (example)
    b[12] += 1.2
    b[18] += 1.5
    b[19] += 1.0

    # tv/computer mostly evening (example)
    for t in range(19, 23):
        b[t] += 0.25

    # random small appliances (microwave/toaster/charger etc.)
    b[7] += 0.10
    b[8] += 0.05
    b[21] += 0.10

    return b

# -----------------------------
# time sets for comfort constraints
# -----------------------------

hours = list(range(24))

away_hours = set(range(8, 16))          # 08:00-16:00 (away)
awake_home_hours = set(range(17, 23))   # 17:00-23:00 (home&awake)
peak_hours = set(range(17, 21))         # typical peak for rtp shaping (not tou)

# -----------------------------
# read appliances from excel
# -----------------------------

df = pd.read_excel("task2\Apperater.xlsx")

appliances = {}
for _, row in df.iterrows():
    name = str(row["navn"])
    appliances[name] = {
        "p": float(row["p"]),                      # kw
        "d": int(row["d"]),                        # hours
        "vindu_start": int(row["vindu_start"]),    # hour index 0..23
        "vindu_slutt": int(row["vindu_slutt"]),    # exclusive, 1..24 (or 0..24)
        "kan_pauses": bool(row["kan_pauses"]),
        "kan_justeres": bool(row["kan_justeres"]),
    }

# -----------------------------
# choose comfort rules (edit this list to match your narrative)
# -----------------------------

# note: this is where we make it "realistic" according to your text
# wm: do not start while away (08-16), and do not start after 23
# dw: allowed morning before work and evening after dinner, but avoid 17-19
# ev: user plugs in before sleep, charging can happen overnight, but should not "start" after 23

comfort = {
    "wm_requires_user_present": set(range(16, 23)),        # start window for wm (16-22)
    "dw_allowed_hours": (set(range(6, 8)) | set(range(19, 23))),  # run hours for dw
    "dw_blocked_hours": set(range(17, 19)),                # avoid 17-18
    "ev_allowed_hours": (set(range(17, 24)) | set(range(0, 7))),  # charging hours
}

# -----------------------------
# rtp prices + baseline
# -----------------------------

prices = generate_rtp(hours, seed=7, peak_hours=peak_hours)
save_prices(prices, "rtp_prices_task2.json")

baseline_kw = build_baseline_kw()
max_house_kw = 6.0  # household cap (realism)

# -----------------------------
# model
# -----------------------------

prob = pulp.LpProblem("task2_rtp_home_energy_management", pulp.LpMinimize)

# variables
active = pulp.LpVariable.dicts("active", (appliances.keys(), hours), cat="Binary")
start = pulp.LpVariable.dicts("start", (appliances.keys(), hours), cat="Binary")
power = pulp.LpVariable.dicts("power", (appliances.keys(), hours), lowBound=0)

# objective: minimize total cost (baseline + scheduled)
cost_terms = []
for t in hours:
    cost_terms.append(prices[t] * baseline_kw[t])

for a, info in appliances.items():
    for t in hours:
        if info["kan_justeres"]:
            cost_terms.append(prices[t] * power[a][t])
        else:
            cost_terms.append(prices[t] * info["p"] * active[a][t])

prob += pulp.lpSum(cost_terms)

# helper: check if hour is inside [start, end) without wraparound
def in_simple_window(t, w_start, w_end):
    return w_start <= t < w_end

# constraints per appliance
for a, info in appliances.items():
    w_start = info["vindu_start"]
    w_end = info["vindu_slutt"]

    # base time window from excel (simple window only)
    for t in hours:
        if not in_simple_window(t, w_start, w_end):
            prob += active[a][t] == 0
            prob += power[a][t] == 0
            prob += start[a][t] == 0

    # appliance-specific comfort overrides (based on names)
    a_lower = a.lower()

    # dishwasher comfort: only allow dw hours in morning/evening and block 17-19
    if "dish" in a_lower:
        for t in hours:
            if (t not in comfort["dw_allowed_hours"]) or (t in comfort["dw_blocked_hours"]):
                prob += active[a][t] == 0

    # washing machine comfort: do not start while away, and do not start after 23
    if "wash" in a_lower or "laundry" in a_lower:
        for t in hours:
            if t not in comfort["wm_requires_user_present"]:
                prob += start[a][t] == 0

    # ev comfort: only allow charging in ev_allowed_hours
    if "ev" in a_lower or "vehicle" in a_lower:
        for t in hours:
            if t not in comfort["ev_allowed_hours"]:
                prob += active[a][t] == 0
                prob += power[a][t] == 0

        # if charging happens after midnight, require that charging was already active before sleep
        # this avoids "charging starts at 03:00" in the interpretation
        night_hours = set(range(0, 7))
        for t in night_hours:
            prob += active[a][t] <= active[a][22] + active[a][23]

    # logic types
    if info["kan_justeres"]:
        # adjustable power: total energy = sum(power) because slot length is 1 hour
        total_energy_kwh = info["p"] * info["d"]
        prob += pulp.lpSum([power[a][t] for t in hours]) == total_energy_kwh

        # power only when active, capped by max power p
        for t in hours:
            prob += power[a][t] <= info["p"] * active[a][t]

        # start var unused for adjustable devices
        for t in hours:
            prob += start[a][t] == 0

    elif info["kan_pauses"]:
        # pausable fixed power: must be active exactly d hours total
        prob += pulp.lpSum([active[a][t] for t in hours]) == info["d"]

        # no start needed
        for t in hours:
            prob += start[a][t] == 0
            prob += power[a][t] == 0

    else:
        # non-pausable cycle: start once, run d consecutive hours
        # only allow start times where the full cycle fits in the excel window
        valid_starts = []
        for t in hours:
            if in_simple_window(t, w_start, w_end) and (t + info["d"] <= w_end):
                valid_starts.append(t)
            else:
                prob += start[a][t] == 0

        prob += pulp.lpSum([start[a][t] for t in valid_starts]) == 1

        # link start -> active for consecutive run
        for k in hours:
            prob += active[a][k] == pulp.lpSum(
                [start[a][t] for t in valid_starts if t <= k <= (t + info["d"] - 1)]
            )

        # power var unused
        for t in hours:
            prob += power[a][t] == 0

# household cap per hour
for t in hours:
    load_terms = [baseline_kw[t]]
    for a, info in appliances.items():
        if info["kan_justeres"]:
            load_terms.append(power[a][t])
        else:
            load_terms.append(info["p"] * active[a][t])
    prob += pulp.lpSum(load_terms) <= max_house_kw

# solve
prob.solve(pulp.PULP_CBC_CMD(msg=0))

# -----------------------------
# output
# -----------------------------

print("status:", pulp.LpStatus[prob.status])
print("total cost (nok):", round(pulp.value(prob.objective), 4))
print("saved rtp curve to: rtp_prices_task2.json")
print()

print("hour  price  baseline  scheduled  total")
print("----------------------------------------")
for t in hours:
    scheduled = 0.0
    for a, info in appliances.items():
        if info["kan_justeres"]:
            scheduled += pulp.value(power[a][t]) or 0.0
        else:
            scheduled += (pulp.value(active[a][t]) or 0.0) * info["p"]
    total = baseline_kw[t] + scheduled
    print(f"{t:02d}    {prices[t]:>4.2f}    {baseline_kw[t]:>6.2f}    {scheduled:>7.2f}   {total:>6.2f}")

print()
print("schedule (only non-zero loads):")
for t in hours:
    line = f"{t:02d}:00  "
    for a, info in appliances.items():
        if info["kan_justeres"]:
            val = pulp.value(power[a][t]) or 0.0
        else:
            val = (pulp.value(active[a][t]) or 0.0) * info["p"]
        if val > 0.01:
            line += f"[{a}: {val:.2f}kw] "
    print(line)