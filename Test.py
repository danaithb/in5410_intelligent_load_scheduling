import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Oppsett av driver
driver = webdriver.Chrome()
url = "https://data.nordpoolgroup.com/auction/day-ahead/prices?deliveryDate=2026-02-27&currency=EUR&aggregation=DeliveryPeriod&deliveryAreas=NO1"  # Sett inn den faktiske URL-en her
driver.get(url)

try:
    # 2. Vent på at tabellen lastes inn
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dx-datagrid-table")))
    print("Tabell funnet, henter data...")

    # 3. Finn alle rader i tabellen
    rader = driver.find_elements(By.XPATH, "//tr[@role='row']")
    
    tabell_data = []
    for rad in rader:
        # Hent alle celler i raden
        celler = rad.find_elements(By.TAG_NAME, "td")
        rad_tekst = [celle.text for celle in celler if celle.text.strip() != ""]
        
        if rad_tekst:
            tabell_data.append(rad_tekst)

    # 4. Databehandling med Pandas
    df = pd.DataFrame(tabell_data)

    # Fjern første og siste rad
    if len(df) > 2:
        df = df.iloc[1:-1]

    # Konverter pris-kolonnen til tall (antar kolonne B / indeks 1)
    # Vi fjerner komma og setter inn punktum for at Python skal forstå det som float
    try:
        column_index = 1 
        df[column_index] = df[column_index].str.replace(',', '.', regex=False).astype(float)
        print("Priser konvertert til tall.")
    except Exception as e:
        print(f"Kunne ikke konvertere kolonne {column_index} til tall: {e}")

    # 5. Lagre til Excel (overskriver automatisk eksisterende fil)
    filnavn = "strompriser.xlsx"
    df.to_excel(filnavn, index=False, header=False)
    
    print(f"Ferdig! Data lagret til {filnavn}")

except Exception as e:
    print(f"En feil oppstod under kjøring: {e}")

finally:
    # Stopper og lar deg se resultatet i terminalen før vinduet lukkes
    input("Trykk Enter for å avslutte og lukke nettleseren...")
    driver.quit()