import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def collect_prices():
    
    #Opens the NordPool Browser with prices for today

    #In a perfect world, the script would also collect the prices for tomorrow to simulate the actual prices then. This is excluded for now, as the prices for tomorrow are released at uncertain times around 13:00 every day


    today= time.strftime("%Y-%m-%d")

    driver = webdriver.Chrome()
    url = "https://data.nordpoolgroup.com/auction/day-ahead/prices?deliveryDate={today}&currency=EUR&aggregation=DeliveryPeriod&deliveryAreas=NO1"  # Sett inn den faktiske URL-en her
    driver.get(url)

    try:
        #Locates the table
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dx-datagrid-table")))
        

        #Finds the rows of the table
        rows = driver.find_elements(By.XPATH, "//tr[@role='row']")

        table_data = []
        for row in rows:
            #Collects all the cells
            cells = row.find_elements(By.TAG_NAME, "td")
            rad_tekst = [cell.text for cell in cells if cell.text.strip() != ""]

            if rad_tekst:
                table_data.append(rad_tekst)


        
        #Makes the data into a dataframe
        df = pd.DataFrame(table_data)

        #Removing first and last row to avoid average prices and headlines
        if len(df) > 2:
            df = df.iloc[1:-1]

        #Converting the price colum to numbers with . instead of , for decimals
        try:
            column_index = 1 
            df[column_index] = df[column_index].str.replace(',', '.', regex=False).astype(float)
            
        except Exception as e:
            print(f"Could not convert column {column_index} to a number: {e}")


        #Since we did not collect the prices for tomorrow, we repeat todays prices.
        two_day_df = pd.concat([df, df], ignore_index=True)

        # Saves the file to Excel
        prices_path = os.path.join("data", "PricesNP.xlsx")
        filename = "PricesNP.xlsx"
        two_day_df.to_excel(prices_path, index=False, header=False)

        print(f"Data saved to {prices_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()

collect_prices()