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


###################
# Generate random prices once per program run
###################
prices_hourly = generate_hourly_prices() + generate_hourly_prices()

generated_prices = []
for p in prices_hourly:
    generated_prices.extend([p] * 4)


while True:
    TASK = choose_task()

    if TASK == "q":
        print("Exiting program.. have a nice day :)")
        break

    quarters = list(range(192))

    if TASK == 1:
        prices_path = os.path.join("data", "Prices_task1.xlsx")
        appliances_path = os.path.join("data", "appliances_1.xlsx")

        df_prices = pd.read_excel(prices_path, header=None)
        prices = df_prices.iloc[:, 1].tolist()

    else:
        prices = generated_prices[:]  # copy of same generated prices for task 2, 3 and 4

        if TASK == 3:
            appliances_path = os.path.join("data", "appliances_3.xlsx")
        else: #task 2 and 4
            appliances_path = os.path.join("data", "appliances_2_4.xlsx")

    ###################
    #Provide a reasonable capacity here
    ###################
    L = 10/4 #Provides the maximum possible capacity for a single quarter
    #This should be expanded to "nettleige" and introduced as part of the objective function

    df_appliances = pd.read_excel(appliances_path)

    appliances = {}

    # Build dictionary of appliances and their constraints
    for _, row in df_appliances.iterrows():
        window_string = str(row["window_slots"])
        intervals = []

        for part in window_string.split(","):
            s, e = part.strip().split("-")
            intervals.append((int(s), int(e)))

        appliances[row["appliances"]] = {
            "p": float(row["energy_kwh"]) / float(row["duration_slots"]),
            "d": int(row["duration_slots"]),
            "windows": intervals,
            "Pausable": bool(row["can_pause"]),
            "Adjustable": bool(row["can_adjust"]),
        }

    problem = pulp.LpProblem("Smart_Electricity_usage", pulp.LpMinimize)

    active = pulp.LpVariable.dicts("active", (appliances.keys(), quarters), cat="Binary")
    start = pulp.LpVariable.dicts("start", (appliances.keys(), quarters), cat="Binary")
    effect = pulp.LpVariable.dicts("effect", (appliances.keys(), quarters), lowBound=0)

    #Objective function
    total_cost = []
    for a, info in appliances.items():
        for t in quarters:
            if info["Adjustable"]:
                total_cost.append(effect[a][t] * prices[t]) #uses the current effect
            else:
                total_cost.append(active[a][t] * info["p"] * prices[t])

    problem += pulp.lpSum(total_cost)

    #Constraints
    for a, info in appliances.items():

        #limiting time slots
        for t in quarters:
            legal = False
            for (v_start, v_end) in info["windows"]:
                if v_start <= t < v_end:
                    legal = True
                    break
            #if the hour is not legal for the applience its use is set to 0
            if not legal:
                problem += active[a][t] == 0
                problem += effect[a][t] == 0

        #adjustable effect
        if info["Adjustable"]:
            total_energy_requirement = info["p"] * info["d"]#this simply returs the original p as it was divided by d in the making of the list
            problem += pulp.lpSum([effect[a][t] for t in quarters]) == total_energy_requirement

            for t in quarters:
                problem += effect[a][t] <= info["p"] * active[a][t] #Limits the use to the meximum capacity, given by p in excel

        elif info["Pausable"]:
            problem += pulp.lpSum([active[a][t] for t in quarters]) == info["d"]

        #Cannot be paused or adjusted
        else:
            problem += pulp.lpSum([start[a][t] for t in quarters]) == 1
            for k in quarters:
                is_active = pulp.lpSum(
                    [start[a][t] for t in quarters if k - info["d"] + 1 <= t <= k]
                )
                problem += active[a][k] == is_active

    # Constraint for maximum usage at any given time - only active for task 4
    if TASK == 4:
        for t in quarters:
            time_last = []
            for a, info in appliances.items():
                if info["Adjustable"]:
                    time_last.append(effect[a][t])
                else:
                    time_last.append(active[a][t] * info["p"])
            problem += pulp.lpSum(time_last) <= L

    problem.solve(pulp.PULP_CBC_CMD(msg=0))

    print(f"Status: {pulp.LpStatus[problem.status]}")
    print("=" * 50)
    print(f"{'Time':<17} {'Appliance consumption (kW)':<40}")
    print("-" * 50)

    for t in quarters:
        hour = (t // 4) % 24
        minute = (t % 4) * 15
        line = f"At {hour:02d}:{minute:02d}:   "

        for a in appliances:
            if appliances[a]["Adjustable"]:
                value_print = pulp.value(effect[a][t])
            else:
                value_print = pulp.value(active[a][t]) * appliances[a]["p"]

            if value_print > 0.01: #Only prints the appliances that are active
                line += f"[{a}: {value_print:.1f} kW] "
        print(line)

    print("=" * 50)
    print(f"Electricity bill comes to: {pulp.value(problem.objective) / 100:.4f} NOK")
    print("=" * 50)
    print()