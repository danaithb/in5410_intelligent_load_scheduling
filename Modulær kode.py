import pulp
import pandas as pd

# 1. OPPSETT AV DATA
timer = list(range(24))
# Eksempel på strømpriser (dyrt kl 08-20)
priser = [101.2575,
100.88,
100.455,
100.2,
100.9925,
103.2525,
129.195,
218.3675,
352.6125,
226.025,
165.2725,
134.2075,
119.54,
110.51,
109,
116.5925,
122.525,
151.2225,
129.1175,
119.545,
119.5425,
110.8525,
101.3875,
95.085]


MAKS_HUS_EFFEKT = 6.0 # Maks kW totalt i huset per time

# Apparater med ulike egenskaper
# p = Effekt (kW), d = Varighet (timer), vindu = (start, slutt)
# kan_pauses: True/False, kan_justeres: True/False (hvis True er 'p' maks-effekt)

df = pd.read_excel("Apperater.xlsx")
    
# Konverter dataframe til en dictionary som passer til modellen
apparater = {}

for _, row in df.iterrows():
    apparater[row['navn']] = {
        "p": float(row['p']),
        "d": int(row['d']),
        "vindu": (int(row['vindu_start']), int(row['vindu_slutt'])),
        "kan_pauses": bool(row['kan_pauses']),
        "kan_justeres": bool(row['kan_justeres'])
    }


# 2. INITIALISERING
prob = pulp.LpProblem("Avansert_Energistyring", pulp.LpMinimize)

# 3. VARIABLER
# Binær: Er apparatet på (1) eller av (0)
aktiv = pulp.LpVariable.dicts("aktiv", (apparater.keys(), timer), cat='Binary')
# Binær: Starter sekvensen i time t (kun for de som ikke kan pauses)
start = pulp.LpVariable.dicts("start", (apparater.keys(), timer), cat='Binary')
# Kontinuerlig: Faktisk effektbruk (kun for de som kan justeres)
effekt = pulp.LpVariable.dicts("effekt", (apparater.keys(), timer), lowBound=0)

# 4. OBJEKTFUNKSJON (Minimere kr)
total_kostnad = []
for a, info in apparater.items():
    for t in timer:
        if info['kan_justeres']:
            total_kostnad.append(effekt[a][t] * priser[t])
        else:
            total_kostnad.append(aktiv[a][t] * info['p'] * priser[t])
prob += pulp.lpSum(total_kostnad)

# 5. CONSTRAINTS
for a, info in apparater.items():
    t_start, t_slutt = info['vindu']
    
    # Begrensning til tidsrom (vindu)
    for t in timer:
        if t < t_start or t >= t_slutt:
            prob += aktiv[a][t] == 0
            prob += effekt[a][t] == 0


    # LOGIKK 1: JUSTERBAR EFFEKT (F.eks. Elbil)
    if info['kan_justeres']:
        # Total energi (kWh) må stemme: Effekt * Varighet
        total_energi_behov = info['p'] * info['d']
        prob += pulp.lpSum([effekt[a][t] for t in timer]) == total_energi_behov
        # Effekten i hver time kan ikke overstige maks 'p'
        for t in timer:
            prob += effekt[a][t] <= info['p'] * aktiv[a][t]


    # LOGIKK 2: KAN PAUSES, MEN FAST EFFEKT (F.eks. Varmekabler)
    elif info['kan_pauses']:
        prob += pulp.lpSum([aktiv[a][t] for t in timer]) == info['d']

    # LOGIKK 3: FAST SEKVENS (F.eks. Vaskemaskin)
    else:
        prob += pulp.lpSum([start[a][t] for t in timer]) == 1
        for k in timer:
            # Koble start-tid til aktiv-status for hele varigheten d
            er_aktiv = pulp.lpSum([start[a][t] for t in timer if k - info['d'] + 1 <= t <= k])
            prob += aktiv[a][k] == er_aktiv

# REGEL: MAKS TOTAL EFFEKT I HUSET PER TIME
for t in timer:
    time_last = []
    for a, info in apparater.items():
        if info['kan_justeres']:
            time_last.append(effekt[a][t])
        else:
            time_last.append(aktiv[a][t] * info['p'])
    prob += pulp.lpSum(time_last) <= MAKS_HUS_EFFEKT

# 6. LØSNING OG RESULTAT
prob.solve(pulp.PULP_CBC_CMD(msg=0))

print(f"Status: {pulp.LpStatus[prob.status]}")
print("=" * 50)
print(f"{'Time':<10} {'Apparat Forbruk (kW)':<40}")
print("-" * 50)

for t in timer:
    linje = f"Kl {t:02d}:00:   "
    for a in apparater:
        # Hent verdien basert på om apparatet er justerbart eller ikke
        if apparater[a]['kan_justeres']:
            verdi = pulp.value(effekt[a][t])
        else:
            verdi = pulp.value(aktiv[a][t]) * apparater[a]['p']
            
        if verdi > 0.01: # Vis bare apparater som er på
            linje += f"[{a}: {verdi:.1f}kW] "
    print(linje)

print("=" * 50)
# Her henter vi ut totalprisen fra objektfunksjonen
print(f"TOTALPRIS FOR DØGNET: {pulp.value(prob.objective):.2f} øre")
print("=" * 50)