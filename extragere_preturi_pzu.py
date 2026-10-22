import requests
import pandas as pd
from datetime import datetime
import calendar
import time
import io

def extrage_preturi_pzu(an, luna, rezolutie="15min", fisier_export="preturi_pzu"):
    """
    Parametrul `rezolutie` acceptă:
    - "15min": va exporta 96 de coloane pentru fiecare zi.
    - "1h": va calcula media a 4 intervale și va exporta 24 de coloane pentru fiecare zi.
    """
    _, numar_zile = calendar.monthrange(an, luna)
    toate_datele = []
    
    url_template = "https://www.opcom.ro/rapoarte-pzu-raportPIP-export-csv/{day:02d}/{month:02d}/{year}/ro"
    headers = {'User-Agent': 'Mozilla/5.0'}

    print(f"Se extrag prețurile pentru luna {luna:02d}/{an} (Rezoluție cerută: {rezolutie})...")

    for zi in range(1, numar_zile + 1):
        url = url_template.format(day=zi, month=luna, year=an)
        print(f"Se procesează ziua: {zi:02d}-{luna:02d}-{an}")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Căutăm rândul unde începe tabelul
            linii = response.text.splitlines()
            index_antet = 0
            for i, linie in enumerate(linii):
                if "Zona de tranzactionare" in linie or "Interval" in linie:
                    index_antet = i
                    break
                    
            csv_content = io.StringIO(response.text)
            df_zi = pd.read_csv(csv_content, skiprows=index_antet)
            
            # Identificăm dinamic coloanele
            col_pret = [col for col in df_zi.columns if 'pre' in str(col).lower() and 'inchidere' in str(col).lower()]
            if not col_pret:
                col_pret = [col for col in df_zi.columns if 'pre' in str(col).lower()] # Fallback
            
            col_interval = [col for col in df_zi.columns if 'interval' in str(col).lower()]
            
            if not col_pret or not col_interval:
                print(f"  -> Avertisment: Coloane lipsă pentru ziua {zi}.")
                continue
                
            # Extragem doar cele două coloane esențiale și le redenumim standard
            df_zi = df_zi[[col_interval[0], col_pret[0]]].copy()
            df_zi.columns = ['Interval', 'Pret']
            
            # Curățare date: ne asigurăm că prețul este convertit corect în număr (float)
            if df_zi['Pret'].dtype == object:
                df_zi['Pret'] = df_zi['Pret'].astype(str).str.replace(',', '.').astype(float)
                
            df_zi['Data'] = f"{an}-{luna:02d}-{zi:02d}"
            
            toate_datele.append(df_zi)
            time.sleep(1)
            
        except Exception as e:
            print(f" Eroare la procesarea zilei {zi}: {e}")

    if toate_datele:
        # Combinăm toate zilele într-un singur tabel "lung"
        df_brut = pd.concat(toate_datele, ignore_index=True)
        df_brut['Interval'] = df_brut['Interval'].astype(int)

        # Aplicăm transformarea în funcție de rezoluția dorită
        if rezolutie == "1h":
            # Calculăm cărei ore îi aparține fiecare interval de 15 min
            # Ex: intervalele 1,2,3,4 -> Ora 1 | 5,6,7,8 -> Ora 2
            df_brut['Ora'] = (df_brut['Interval'] - 1) // 4 + 1
            
            # Calculăm media prețului pe fiecare oră din fiecare zi
            df_agregat = df_brut.groupby(['Data', 'Ora'])['Pret'].mean().reset_index()
            
            # Pivotăm tabelul: Data devine rând, Orele devin coloane
            df_pivot = df_agregat.pivot(index='Data', columns='Ora', values='Pret').reset_index()
            
            # Redenumim coloanele pentru a fi clare (Data, Ora_1, Ora_2 ... Ora_24)
            df_pivot.columns = ['Data'] + [f"Ora_{h}" for h in df_pivot.columns if str(h).isdigit()]
            
        else:
            # Pivotăm direct la 15 minute
            df_pivot = df_brut.pivot(index='Data', columns='Interval', values='Pret').reset_index()
            # Redenumim (Data, Int_1, Int_2 ... Int_96)
            df_pivot.columns = ['Data'] + [f"Int_{i}" for i in df_pivot.columns if str(i).isdigit()]

        # Construim un nume sugestiv pentru fișiere
        sufix = "1h" if rezolutie == "1h" else "15min"
        nume_csv = f"{fisier_export}_{an}_{luna:02d}_{sufix}.csv"
        nume_excel = f"{fisier_export}_{an}_{luna:02d}_{sufix}.xlsx"
        
        # Salvăm
        df_pivot.to_csv(nume_csv, index=False, encoding='utf-8-sig')
        df_pivot.to_excel(nume_excel, index=False)
        
        print(f"\n Succes! Datele au fost transformate și salvate în:")
        print(f" -> {nume_csv}")
        print(f" -> {nume_excel}")
    else:
        print("\n Nu s-au putut extrage date.")

# ==========================================
# SECȚIUNEA DE RULARE
# ==========================================
if __name__ == "__main__":
    ANUL = 2026
    LUNA = 9
    REZOLUTIE = "15min"  # Poți schimba la "15min" dacă vrei toate cele 96 de coloane
    
    extrage_preturi_pzu(ANUL, LUNA, rezolutie=REZOLUTIE, fisier_export="PZU")