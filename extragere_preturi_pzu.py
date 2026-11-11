import requests
import pandas as pd
import calendar
import time
import io

def extrage_preturi_pzu(an, luna, rezolutie="15min", fisier_export="preturi_pzu"):
    # 1. Determinăm zilele (ultima zi din luna anterioară + toate din luna curentă)
    data_start = pd.Timestamp(year=an, month=luna, day=1)
    _, numar_zile = calendar.monthrange(an, luna)
    
    ziua_anterioara = data_start - pd.Timedelta(days=1)
    zile_de_procesat = [(ziua_anterioara.year, ziua_anterioara.month, ziua_anterioara.day)]
    
    for zi in range(1, numar_zile + 1):
        zile_de_procesat.append((an, luna, zi))
        
    toate_datele = []
    url_template = "https://www.opcom.ro/rapoarte-pzu-raportPIP-export-csv/{day:02d}/{month:02d}/{year}/ro"
    headers = {'User-Agent': 'Mozilla/5.0'}

    print(f"Se extrag prețurile PZU pentru {luna:02d}/{an} pe fusul EET (Rezoluție: {rezolutie})...")

    for a, l, z in zile_de_procesat:
        url = url_template.format(day=z, month=l, year=a)
        print(f"  -> Se extrage ziua CET: {z:02d}-{l:02d}-{a}")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            linii = response.text.splitlines()
            index_antet = 0
            for i, linie in enumerate(linii):
                if "Zona de tranzactionare" in linie or "Interval" in linie:
                    index_antet = i
                    break
                    
            csv_content = io.StringIO(response.text)
            df_zi = pd.read_csv(csv_content, skiprows=index_antet)
            
            col_pret = [col for col in df_zi.columns if 'pre' in str(col).lower() and 'inchidere' in str(col).lower()]
            if not col_pret:
                col_pret = [col for col in df_zi.columns if 'pre' in str(col).lower()]
            col_interval = [col for col in df_zi.columns if 'interval' in str(col).lower()]
            
            if not col_pret or not col_interval:
                print(f"     Avertisment: Coloane lipsă pentru {z:02d}-{l:02d}-{a}.")
                continue
                
            df_zi = df_zi[[col_interval[0], col_pret[0]]].copy()
            df_zi.columns = ['Interval', 'Pret']
            
            if df_zi['Pret'].dtype == object:
                df_zi['Pret'] = df_zi['Pret'].astype(str).str.replace(',', '.').astype(float)
                
            df_zi['Data'] = f"{a}-{l:02d}-{z:02d}"
            toate_datele.append(df_zi)
            time.sleep(1)
            
        except Exception as e:
            print(f"     Eroare la procesarea zilei {z:02d}-{l:02d}-{a}: {e}")

    if toate_datele:
        # Concatenăm fluxul continuu CET 
        df_brut = pd.concat(toate_datele, ignore_index=True)
        df_brut['Interval'] = df_brut['Interval'].astype(int)

        # 2. SHIFT VECTORIAL PENTRU FUSUL ORAR: 
        # Mutăm coloana de prețuri în jos cu 4 rânduri (1 oră). 
        # Astfel, prețul de la CET 23:00 aterizează perfect pe rândul cu etichetele EET 00:00 (Data curentă, Intervalul 1)
        df_brut['Pret'] = df_brut['Pret'].shift(4)

        # 3. Filtrăm array-ul pentru a păstra strict luna vizată
        df_brut = df_brut[df_brut['Data'].str.startswith(f"{an}-{luna:02d}")].copy()
        
        # Eliminăm primele 4 rânduri goale rezultate din shiftare (în caz că luna anterioară nu s-a descărcat corect)
        df_brut = df_brut.dropna(subset=['Pret'])

        # 4. Agregăm și pivotăm datele curate
        if rezolutie == "1h":
            df_brut['Ora'] = (df_brut['Interval'] - 1) // 4 + 1
            df_agregat = df_brut.groupby(['Data', 'Ora'])['Pret'].mean().reset_index()
            df_pivot = df_agregat.pivot(index='Data', columns='Ora', values='Pret').reset_index()
            df_pivot.columns = ['Data'] + [f"Ora_{h}" for h in df_pivot.columns if str(h).isdigit()]
        else:
            df_pivot = df_brut.pivot(index='Data', columns='Interval', values='Pret').reset_index()
            df_pivot.columns = ['Data'] + [f"Int_{i}" for i in df_pivot.columns if str(i).isdigit()]

        sufix = "1h" if rezolutie == "1h" else "15min"
        nume_csv = f"{fisier_export}_{an}_{luna:02d}_{sufix}.csv"
        nume_excel = f"{fisier_export}_{an}_{luna:02d}_{sufix}.xlsx"
        
        df_pivot.to_csv(nume_csv, index=False, encoding='utf-8-sig')
        df_pivot.to_excel(nume_excel, index=False)
        
        print(f"\nSucces! Datele OPCOM au fost pivotate pe EET și salvate în:")
        print(f" -> {nume_csv}")
        print(f" -> {nume_excel}")
    else:
        print("\nNu s-au putut extrage date.")

if __name__ == "__main__":
    ANUL = 2026
    LUNA = 10
    REZOLUTIE = "15min" 
    
    extrage_preturi_pzu(ANUL, LUNA, rezolutie=REZOLUTIE, fisier_export="PZU_EET")