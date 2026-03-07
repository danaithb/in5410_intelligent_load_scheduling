import pulp
import pandas as pd
#import Collect_prices #Saves electricity prices from Nordpool to an Excel file
import os #Will be used to ensure compatibility across different operating systems when loading files
from Price_curve_generator import generate_hourly_prices


###################
# Prompt the user to choose a task (1-4) or exit
###################
def choose_task():
    while True:
        choice = input("Which task do you want to run? Choose between 1-4, or write q to exit: ").strip().lower()
        if choice in {"1", "2", "3", "4"}:
            return int(choice)
        if choice == "q":
            return "q"
        print("Invalid choice. Please enter 1, 2, 3, 4, or q")

TASK = choose_task()
if TASK == "q":
    print("Exiting program..")
    quit()

quarters = list(range(192))

if TASK == 1:
    prices_path = os.path.join("data", "Prices_task1.xlsx")
    appliences_path = os.path.join("data", "appliances_1.xlsx")
elif TASK == 3:
  #  prices_path = os.path.join("data", "PricesNP.xlsx")
    appliences_path = os.path.join("data", "appliances_3.xlsx")
else:  # Task 2 and 4
   # prices_path = os.path.join("data", "PricesNP.xlsx")
    appliences_path = os.path.join("data", "appliances_2_4.xlsx")

df_prices = pd.read_excel(prices_path, header=None)

prices = df_prices.iloc[:, 1].tolist()

###################
#Provide a reasonable capacity here
###################
L = 10/4 #Provides the maximum possible capacity for a single quarter
#This should be expanded to "nettleige" and introduced as part of the objective function

df_appliences = pd.read_excel(appliences_path)
    

appliences = {}

#The following logic builds the dictionary of appliences and their constraints

for _, row in df_appliences.iterrows():

    window_string = str(row['window_slots']) 
    intervals = []
    for part in window_string.split(','):
        s, e = part.split('-')
        intervals.append((int(s), int(e)))

###################
#Må oppdatera desse te engelsk når excel e klart, hugså å oppdatere gjennom heile koden
###################

    appliences[row['appliances']] = {
        "p": float(row['energy_kwh'])/int(row['duration_slots']),
        "d": int(row['duration_slots']),
        "windows": intervals, 
        "Pausable": bool(row['can_pause']),
        "Adjustable": bool(row['can_adjust'])
    }



problem = pulp.LpProblem("Smart_Electricity_usage", pulp.LpMinimize)


active = pulp.LpVariable.dicts("active", (appliences.keys(), quarters), cat='Binary')

#To be used for appliances that cannot be paused
start = pulp.LpVariable.dicts("start", (appliences.keys(), quarters), cat='Binary')


#To be used for appliences that can adust their effect
effect = pulp.LpVariable.dicts("effect", (appliences.keys(), quarters), lowBound=0)



#Objective function
total_cost = []
for a, info in appliences.items():
    for t in quarters:
        if info['Adjustable']:
            total_cost.append(effect[a][t] * prices[t]) #uses the current effect
        else:
            total_cost.append(active[a][t] * info['p'] * prices[t])
problem += pulp.lpSum(total_cost)

#Constraints
for a, info in appliences.items():
    
    #limiting time slots
    for t in quarters:
        
        legal = False
        for (v_start, v_slutt) in info['windows']:
            if v_start <= t < v_slutt:
                legal = True
                break
        
        #if the hour is not legal for the applience its use is set to 0
        if not legal:
            problem += active[a][t] == 0
            problem += effect[a][t] == 0



    #adjustable effect
    if info['Adjustable']:
        
        total_energy_requirement = info['p'] * info['d'] #this simply returs the original p as it was divided by d in the making of the list
        problem += pulp.lpSum([effect[a][t] for t in quarters]) == total_energy_requirement
        
        for t in quarters:
            problem += effect[a][t] <= info['p'] * active[a][t] #Limits the use to the meximum capacity, given by p in excel


    
    elif info['Pausable']:
        problem += pulp.lpSum([active[a][t] for t in quarters]) == info['d']

    #Cannot be paused or adjusted
    else:
        problem += pulp.lpSum([start[a][t] for t in quarters]) == 1
        for k in quarters:
            
            is_active = pulp.lpSum([start[a][t] for t in quarters if k - info['d'] + 1 <= t <= k])
            problem += active[a][k] == is_active



#Contraint for maximum usage at any given time - only active for task 4
if TASK == 4:
    for t in quarters:
        time_last = []
        for a, info in appliences.items():
            if info['Adjustable']:
                time_last.append(effect[a][t])
            else:
                time_last.append(active[a][t] * info['p'])
        problem += pulp.lpSum(time_last) <= L




problem.solve(pulp.PULP_CBC_CMD(msg=0))


print(f"Status: {pulp.LpStatus[problem.status]}")
print("=" * 50)
print(f"{'Time':<17} {'Apparat Forbruk (kW)':<40}")
print("-" * 50)

for t in quarters:
    line = f"Kl {df_prices.iloc[t, 0]}:   "

    for a in appliences:
        
        if appliences[a]['Adjustable']:
            value_print = pulp.value(effect[a][t])
        else:
            value_print = pulp.value(active[a][t]) * appliences[a]['p']
            
        if value_print > 0.01: #Only prints the appliances that are active
            line += f"[{a}: {value_print:.1f}kW] "
    print(line)

print("=" * 50)
print(f"Electricitybill comes to: {pulp.value(problem.objective)/100:.4f} NOK") #Adjusts prices normally given in øre to Nok
print("=" * 50)