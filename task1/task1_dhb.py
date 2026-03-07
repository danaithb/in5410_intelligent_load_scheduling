import numpy as np
from scipy.optimize import linprog

# -----------------------------
# problem setup (q1 - tou pricing)
# -----------------------------

# hours are 1..24 (1 = 00:00-01:00, ..., 24 = 23:00-24:00)
H = 24
hours = np.arange(1, H + 1)

# tou pricing: peak 17:00-20:00 (i model as hours 17,18,19,20), off-peak otherwise
p = np.full(H, 0.5)
peak_hours = [17, 18, 19, 20]
for h in peak_hours:
    p[h - 1] = 1.0

# appliances
A = ["wm", "dw", "ev"]

# total energy requirements (kwh per day)
E = {
    "wm": 1.94,
    "dw": 1.44,
    "ev": 9.9,
}

# per-hour power/energy limits (kwh per hour-slot)
gamma_max = {
    "wm": 0.9,
    "dw": 0.7,
    "ev": 3.6,
}

# SLETT????????????? VISS ME Kun bruke intervals
# allowed operation windows (setup time alpha, deadline beta)
# note: wrap-around windows are represented by a set of allowed hours
def allowed_hours(alpha, beta):
    # returns set of allowed hours in [alpha, beta] if alpha <= beta
    # if alpha > beta it wraps over midnight: [alpha..24] U [1..beta]
    if alpha <= beta:
        return set(range(alpha, beta + 1))
    return set(range(alpha, 25)) | set(range(1, beta + 1))


# helper for a plain inclusive interval
def interval(a, b):
    return set(range(a, b + 1))

allowed = {
    "wm": interval(17, 22),  # 22 so they can hang up clothes before bedtime       
    "dw": interval(6, 7) | interval(19, 23),# morning + evening, avoid dinnertime 17-19
    "ev": interval(17, 24) | interval(1,2)  # max 2 so the charging doesnt start after bedtime      
}

# -----------------------------
# build lp in vector form
# variable order: [wm_1..wm_24, dw_1..dw_24, ev_1..ev_24]
# -----------------------------
n_vars = len(A) * H

def idx(a, h):
    # a in A, h in 1..24
    a_pos = A.index(a)
    return a_pos * H + (h - 1)

# objective: min sum_h p_h * (wm_h + dw_h + ev_h)
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

# optional: add a household cap to avoid "everything at 02:00"
# set to None to disable
max_total_per_hour = 4.0  # kwh per hour-slot (can tune)
A_ub = []
b_ub = []
if max_total_per_hour is not None:
    for h in hours:
        row = np.zeros(n_vars)
        for a in A:
            row[idx(a, h)] = 1.0
        A_ub.append(row)
        b_ub.append(max_total_per_hour)
A_ub = np.array(A_ub) if A_ub else None
b_ub = np.array(b_ub) if b_ub else None

# bounds: 0 <= x[a,h] <= gamma_max[a] inside allowed window, else x[a,h] = 0
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

x = res.x

# -----------------------------
# pretty print schedule
# -----------------------------
wm = x[0:H]
dw = x[H:2*H]
ev = x[2*H:3*H]
total = wm + dw + ev

def hour_label(h):
    start = (h - 1) % 24
    end = h % 24
    return f"{start:02d}:00-{end:02d}:00"

print("tou price (nok/kwh): peak hours =", peak_hours)
print("total cost (nok):", round(res.fun, 4))
print()

print("hour        price   wm     dw     ev     total")
print("------------------------------------------------")
for h in hours:
    print(
        f"{hour_label(h):<11} "
        f"{p[h-1]:>4.1f}   "
        f"{wm[h-1]:>4.2f}   "
        f"{dw[h-1]:>4.2f}   "
        f"{ev[h-1]:>4.2f}   "
        f"{total[h-1]:>5.2f}"
    )

print()
print("checks (kwh):")
print("wm sum:", round(wm.sum(), 4), "target:", E["wm"])
print("dw sum:", round(dw.sum(), 4), "target:", E["dw"])
print("ev sum:", round(ev.sum(), 4), "target:", E["ev"])
print("max total per hour:", max_total_per_hour)