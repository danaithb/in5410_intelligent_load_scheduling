import pandas as pd
import matplotlib.pyplot as plt

# 1. Last inn dataene
# Antar at filene ikke har overskrifter (header=None) basert på snutten
df1 = pd.read_csv('PricesNP.xlsx', header=None, names=['Tid', 'Pris_NP'])
df2 = pd.read_csv('Rnd_prices.xlsx', header=None, names=['Tid', 'Pris_Rnd'])

# 2. Rydd opp i tidsformatet
# Vi henter bare start-tidspunktet (f.eks. "00:00") for å gjøre aksen lesbar
df1['Tid_start'] = df1['Tid'].str.split(' - ').str[0]

# 3. Lag plottet
plt.figure(figsize=(12, 6))

plt.plot(df1['Tid_start'], df1['Pris_NP'], label='Prices NP', color='blue', linewidth=1.5)
plt.plot(df1['Tid_start'], df2['Pris_Rnd'], label='Rnd Prices', color='orange', linewidth=1.5)

# 4. Formatering for å gjøre det pent
plt.title('Sammenligning av Priser over Tid', fontsize=14)
plt.xlabel('Tidspunkt', fontsize=12)
plt.ylabel('Pris', fontsize=12)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)

# Vis bare hver 8. merkelapp på X-aksen så det ikke blir kaos
plt.xticks(df1['Tid_start'][::8], rotation=45)

plt.tight_layout()
plt.show()