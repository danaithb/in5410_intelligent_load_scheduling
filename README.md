# IN5410 - Intelligent Load Scheduling

## Running the tasks

All tasks are run by setting the `TASK` variable at the top of `main.py` to the desired task number, then running the file:

```python
TASK = 4  # Change to 1, 2, 3 or 4
```

The correct price file, appliance file, and constraints are selected automatically based on `TASK`.

### Files per task

| Task | Price file                 | Appliance file               |
|------|----------------------------|------------------------------|
| 1    | `data/Prices_task1.xlsx`   | `data/appliances_1.xlsx`     |
| 2    | `data/PricesNP.xlsx`       | `data/appliances_2_4.xlsx`   |
| 3    | `data/PricesNP.xlsx`       | `data/appliances_3.xlsx`     |
| 4    | `data/PricesNP.xlsx`       | `data/appliances_2_4.xlsx`   |


## Live electricity prices (tasks 2-4)

For tasks 2-4, electricity prices are fetched live from Nordpool.

## Dependencies

```
pip install pulp pandas openpyxl
```