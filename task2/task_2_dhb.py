import numpy as np
from scipy.optimize import linprog

# -----------------------------
# q2 - rtp scheduling (lp)
# -----------------------------

# hours are 1..24 (1 = 00:00-01:00, ..., 24 = 23:00-24:00)
# note: a clock interval [start,end) maps to hour indices (start+1) .. end
H = 24
hours = np.arange(1, H + 1)

def hour_label(h: int) -> str:
    start = (h - 1) % 24
    end = h % 24
    return f"{start:02d}:00-{end:02d}:00"

def hours_for_clock_range(start_hour: int, end_hour: int):
    # returns hour indices for clock interval [start_hour, end_hour)
    # so [18,23) -> h in {19,20,21,22,23}
    if not (0 <= start_hour <= 24 and 0 <= end_hour <= 24 and start_hour <= end_hour):
        raise ValueError("use 0<=start<=end<=24 for non-wrapping ranges")
    return set(range(start_hour + 1, end_hour + 1))

def normalize_to_total(weights: np.ndarray, total_kwh: float) -> np.ndarray:
    w = np.clip(weights.astype(float), 0.0, None)
    s = w.sum()
    if s <= 0:
        return np.full(H, total_kwh / H)
    return total_kwh * (w / s)

# -----------------------------
# rtp price generation (save for q4)
# -----------------------------

rng = np.random.default_rng(42)

# base shape: low at night, higher in evening peak, medium elsewhere
base = np.full(H, 0.8)
for h in hours:
    start = h - 1  # clock start hour
    if 0 <= start < 6:
        base[h - 1] = 0.5
    elif 6 <= start < 8:
        base[h - 1] = 0.7
    elif 8 <= start < 16:
        base[h - 1] = 0.85
    elif 16 <= start < 23:
        base[h - 1] = 1.2
    else:
        base[h - 1] = 0.6

noise = rng.normal(loc=0.0, scale=0.08, size=H)
p = np.clip(base + noise, 0.2, None)  # nok/kwh, keep positive

# save pricing curve for q4 reuse
np.savetxt("rtp_prices_q2.csv", np.column_stack([hours, p]), delimiter=",", header="hour,price_nok_per_kwh", comments="")

# -----------------------------
# non-shiftable fixed load profile l_ns[h]
# -----------------------------

# pick concrete values within the given ranges
E_ns = {
    "fridge": 1.32,     # kwh/day
    "router": 0.24,     # kwh/day
    "heating": 8.0,     # kwh/day (choose within 6.4-9.6)
    "lighting": 1.5,    # kwh/day (choose within 1.0-2.0)
    "stove": 3.9,       # kwh/day
    "tv": 0.4,          # kwh/day (choose within 0.15-0.6)
    "pc2": 1.2,         # kwh/day (2 pcs * 0.6)
}

l_ns = np.zeros(H)

# fridge, router: uniform baseline
l_ns += E_ns["fridge"] / H
l_ns += E_ns["router"] / H

# heating: low night, boost morning, medium day, high evening
w_heat = np.zeros(H)
for h in hours:
    start = h - 1
    if 23 <= start or start < 6:
        w_heat[h - 1] = 0.6
    elif 6 <= start < 7:
        w_heat[h - 1] = 1.2
    elif 8 <= start < 16:
        w_heat[h - 1] = 0.8
    elif 17 <= start < 23:
        w_heat[h - 1] = 1.3
    else:
        w_heat[h - 1] = 0.7
l_ns += normalize_to_total(w_heat, E_ns["heating"])

# lighting: occupancy-based (morning low, evening high)
w_light = np.zeros(H)
for h in hours:
    start = h - 1
    if 6 <= start < 7:
        w_light[h - 1] = 0.4
    elif 17 <= start < 23:
        w_light[h - 1] = 1.0
    else:
        w_light[h - 1] = 0.05
l_ns += normalize_to_total(w_light, E_ns["lighting"])

# stove: fixed dinner block once between 17-19 (2 hours) -> [17,19)
stove_hours = hours_for_clock_range(17, 19)
for h in stove_hours:
    l_ns[h - 1] += E_ns["stove"] / len(stove_hours)

# tv: fixed 5h -> [18,23)
tv_hours = hours_for_clock_range(18, 23)
for h in tv_hours:
    l_ns[h - 1] += E_ns["tv"] / len(tv_hours)

# computers (2): fixed evening -> [17,23)
pc_hours = hours_for_clock_range(17, 23)
for h in pc_hours:
    l_ns[h - 1] += E_ns["pc2"] / len(pc_hours)

# -----------------------------
# shiftable + small random appliances (decision variables)
# -----------------------------

A = ["wm", "dryer", "dw", "ev", "phone", "coffee", "hair"]

E = {
    "wm": 1.94,
    "dryer": 2.50,
    "dw": 1.44,
    "ev": 9.9,
    "phone": 0.05,
    "coffee": 0.10,
    "hair": 0.20,
}

# per-hour caps (kwh per hour-slot), choose reasonable values
gamma_max = {
    "wm": 0.9,
    "dryer": 1.2,
    "dw": 0.7,
    "ev": 3.6,
    "phone": 0.05,   # tiny, can be equal to total
    "coffee": 0.10,
    "hair": 0.20,
}

# allowed time windows (clock-based)
allowed = {
    "wm": hours_for_clock_range(17, 23),                         # [17,23)
    "dryer": hours_for_clock_range(18, 23),                      # [18,23)
    "dw": hours_for_clock_range(6, 7) | hours_for_clock_range(19, 23),  # [6,7) and [19,23)
    "ev": hours_for_clock_range(17, 24) | hours_for_clock_range(1, 2),  # [17,24) and [1,2)
    "phone": hours_for_clock_range(17, 23) | hours_for_clock_range(22, 24),  # [17,23) or [22,24)
    "coffee": hours_for_clock_range(6, 7),                       # [6,7)
    "hair": hours_for_clock_range(6, 7) | hours_for_clock_range(17, 23),     # [6,7) or [17,23)
}

# -----------------------------
# build lp
# variable order: [a1_1..a1_24, a2_1..a2_24, ...]
# -----------------------------

n_vars = len(A) * H

def idx(a: str, h: int) -> int:
    a_pos = A.index(a)
    return a_pos * H + (h - 1)

# objective: min sum_h p_h * (l_ns_h + sum_a x[a,h])
# l_ns is constant, so we only need prices on decision variables
c = np.zeros(n_vars)
for a in A:
    for h in hours:
        c[idx(a, h)] = p[h - 1]

# equality constraints: total energy per appliance
A_eq = []
b_eq = []
for a in A:
    row = np.zeros(n_vars)
    for h in hours:
        row[idx(a, h)] = 1.0
    A_eq.append(row)
    b_eq.append(E[a])
A_eq = np.array(A_eq)
b_eq = np.array(b_eq)

# optional realism cap: avoid all flexible loads stacking on one hour
max_total_shiftable_per_hour = 5.0  # kwh per hour-slot, tune as needed
A_ub = []
b_ub = []
for h in hours:
    row = np.zeros(n_vars)
    for a in A:
        row[idx(a, h)] = 1.0
    A_ub.append(row)
    b_ub.append(max_total_shiftable_per_hour)
A_ub = np.array(A_ub)
b_ub = np.array(b_ub)

# bounds: 0 <= x[a,h] <= gamma_max[a] if allowed, else 0
bounds = []
for a in A:
    for h in hours:
        if h in allowed[a]:
            bounds.append((0.0, gamma_max[a]))
        else:
            bounds.append((0.0, 0.0))

# -----------------------------
# solve
# -----------------------------

res = linprog(
    c=c,
    A_ub=A_ub, b_ub=b_ub,
    A_eq=A_eq, b_eq=b_eq,
    bounds=bounds,
    method="highs"
)

if not res.success:
    raise RuntimeError(res.message)

x = res.x.reshape(len(A), H)

# -----------------------------
# reporting
# -----------------------------

x_by_a = {a: x[i, :] for i, a in enumerate(A)}
shiftable_total = x.sum(axis=0)
total_load = l_ns + shiftable_total

cost_shiftable = float(np.dot(p, shiftable_total))
cost_total = float(np.dot(p, total_load))

print("saved rtp curve to rtp_prices_q2.csv")
print("total cost (nok) including non-shiftable:", round(cost_total, 4))
print("flexible cost (nok) only:", round(cost_shiftable, 4))
print()

print("hour        price   l_ns   flex   total")
print("--------------------------------------------")
for h in hours:
    print(
        f"{hour_label(h):<11} "
        f"{p[h-1]:>5.2f}  "
        f"{l_ns[h-1]:>5.2f}  "
        f"{shiftable_total[h-1]:>5.2f}  "
        f"{total_load[h-1]:>5.2f}"
    )

print()
print("energy checks (kwh):")
for a in A:
    print(f"{a:<6} sum:", round(x_by_a[a].sum(), 4), "target:", E[a])

print()
print("peak total load (kwh per hour-slot):", round(total_load.max(), 4))
print("cap on flexible per hour-slot:", max_total_shiftable_per_hour)