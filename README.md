# IN5410 - Intelligent Load Scheduling

## Running the program

Run the program with:

python main.py

You will be prompted to choose which task to run (1–4) or exit the program.

## Using Nord Pool prices (optional)

If you want to run the model with Nord Pool prices:

1. Run the script that collects prices:

python Collect_prices.py

2. This will save the prices to:

data/PricesNP.xlsx

3. Modify `main.py` so that tasks 2–4 read prices from this file instead of using generated prices.

## Files per task

| Task | Price source                         | Appliance file           |
| ---- | ------------------------------------ | ------------------------ |
| 1    | data/Prices_task1.xlsx               | data/appliances_1.xlsx   |
| 2    | Generated price curve                | data/appliances_2_4.xlsx |
| 3    | Generated price curve                | data/appliances_3.xlsx   |
| 4    | Same generated price curve as Task 2 | data/appliances_2_4.xlsx |

Task 1 uses prices from an Excel file.  
Tasks 2–4 use a generated electricity price curve.

## Dependencies

Install required packages:

pip install pulp pandas openpyxl
