import pulp

#Paramtre
Timer = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
#Må gå over logikken for om timen 00:00 til 01:00 ska heitte 0 eller 1.

Priser = {t: 1 if 17 <= t <= 20 else 0.5 for t in Timer} # Priser er





#Definere adle oppgåvene, her har eg tatt ca gjennomsnitt for ulike forbruk
#p er effekt og d er varighet
Applience = {
"Dishwasher": {"p": 1.44/3, "d": 3},
"Laundry": {"p": 1.94/2, "d": 2},
"Electric Vehicle": {"p": 9.9/3, "d": 3}
}
#Dette  kan garantert automatiseres ved å legge det i en csv eller excel


Oppgave_1 = pulp.LpProblem("Oppgave_1", pulp.LpMinimize)

x = pulp.LpVariable.dicts("starttid_applience", (Applience.keys(), Timer), cat='Binary')


#Objektfunksjonen
kostnad = []
for a, info in Applience.items():
    p = info['p']
    d = info['d']
    for t in Timer:
        if t + d <= 23:  # Her e ei grensa for å ikkje gå utforbi dagen, men det trenge vel ikkje ver tilfelle



            sum_pris_syklus = sum(Priser[t + i] for i in range(d))
            kostnad_for_start_t = x[a][t] * sum_pris_syklus * p
            kostnad.append(kostnad_for_start_t)

Oppgave_1 += pulp.lpSum(kostnad)


# Constraints

#Alle apperater kan kun starte ein gong
#I teorien kan eksempelvis elbilen lade 2 av timane etter hverandre, ta ein pause og så lade siste timen feks


for a, info in Applience.items():
    Oppgave_1 += pulp.lpSum([x[a][t] for t in Timer if t + info['d'] <= 24]) == 1





#Tidsrom for appliences
Oppgave_1 += pulp.lpSum([x["Laundry"][t] for t in range(17, 21) if t + 2 <= 24]) == 1
Oppgave_1 += pulp.lpSum([x["Dishwasher"][t] for t in range(1, 19) if t + 3 <= 24]) == 1
Oppgave_1 += pulp.lpSum([x["Electric Vehicle"][t] for t in range(17, 24) if t + 3 <= 24]) == 1
#Må oppdatera koden for å tillata wraparound på døgnet.

#Notere meg her at navnene, rangesene og t + d bør konne automatiseres visst alt legges i excel eller ein csv


# Maks begrensning på effekt
#Ska me sjå vekk for dette?


for k in Timer:
    last_i_time_k = []
    for a, info in Applience.items():
        p = info['p']
        d = info['d']
        # Finn alle starttidspunkter som gjør at apparatet er "PÅ" i time k
        aktive_starter = [x[a][t] for t in Timer if k - d + 1 <= t <= k]
        last_i_time_k.append(pulp.lpSum(aktive_starter) * p)
    
    Oppgave_1 += pulp.lpSum(last_i_time_k) <= 9.0


Oppgave_1.solve(pulp.PULP_CBC_CMD(msg=0)) # msg=0 skjuler teknisk logg

print(f"Status: {pulp.LpStatus[Oppgave_1.status]}")
print("-" * 30)
for a in Applience.keys():
    for t in Timer:

        if pulp.value(x[a][t]) == 1:
            print(f"{a:15} starter kl {t:02d}:00 (Varighet: {Applience[a]['d']}t)")
print("-" * 30)
print(f"Total kostnad for perioden: {pulp.value(Oppgave_1.objective):.2f} kr")