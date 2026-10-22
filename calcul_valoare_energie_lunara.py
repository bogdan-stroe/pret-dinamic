import pandas as pd

# ==========================================
# CONFIGURARE MARJE ȘI PRAGURI
# ==========================================
PRAG_PRET = -100.0 # Pragul de preț în lei/MWh

# Cazul 1: Cumpărare de la producător
MARJA_CUMPARARE_FIXA = 15     # lei (se scade din preț când PZU < 100)
MARJA_CUMPARARE_PROC = 0.85   # % (se aplică 85% din preț când PZU >= 100)

# Cazul 2: Vânzare energie
MARJA_VANZARE_FIXA = 15       # lei (se adaugă la preț când PZU < 100)
MARJA_VANZARE_PROC = 1.15     # % (se aplică 115% din preț când PZU >= 100)
# ==========================================

# 1. Încărcarea datelor
prod_df = pd.read_csv('2026-sept/iordache-consum-2026-sept.csv')
price_df = pd.read_csv('2026-sept/PZU_2026_09_15min.csv')

# 2. Prelucrarea și alinierea prețurilor
price_melt = price_df.melt(id_vars=['Data'], var_name='Interval', value_name='Price')
price_melt['Int_Num'] = price_melt['Interval'].str.extract(r'(\d+)').astype(int)
price_melt = price_melt.sort_values(['Data', 'Int_Num']).reset_index(drop=True)

analysis_df = pd.DataFrame({
    'Production': prod_df.iloc[:, 1], 
    'Price_PZU': price_melt['Price']
})

# 3. Aplicarea formulelor pentru noile prețuri
analysis_df['Price_Buy'] = analysis_df['Price_PZU'].apply(
    lambda pzu: (pzu - MARJA_CUMPARARE_FIXA) if pzu < PRAG_PRET else (pzu * MARJA_CUMPARARE_PROC)
)
analysis_df['Price_Sell'] = analysis_df['Price_PZU'].apply(
    lambda pzu: (pzu + MARJA_VANZARE_FIXA) if pzu < PRAG_PRET else (pzu * MARJA_VANZARE_PROC)
)

# 4. Calcularea valorilor (PZU Original, Cumpărare, Vânzare)
analysis_df['Value_PZU'] = analysis_df['Production'] * analysis_df['Price_PZU']
analysis_df['Value_Buy'] = analysis_df['Production'] * analysis_df['Price_Buy']
analysis_df['Value_Sell'] = analysis_df['Production'] * analysis_df['Price_Sell']

# 5. Crearea măștilor de filtrare pe baza prețului PZU original
low_mask = analysis_df['Price_PZU'] < PRAG_PRET
high_mask = analysis_df['Price_PZU'] >= PRAG_PRET

# 6. Calcularea totalurilor și a mediilor
total_energie = analysis_df['Production'].sum()

total_valoare_pzu = analysis_df['Value_PZU'].sum()
total_valoare_cump = analysis_df['Value_Buy'].sum()
total_valoare_vanz = analysis_df['Value_Sell'].sum()

pret_mediu_pzu = total_valoare_pzu / total_energie if total_energie > 0 else 0
pret_mediu_cump = total_valoare_cump / total_energie if total_energie > 0 else 0
pret_mediu_vanz = total_valoare_vanz / total_energie if total_energie > 0 else 0

# 7. Afișarea rezultatelor comparative
print("=== ANALIZĂ INTERVALE CU PZU < 100 LEI ===")
print(f"Cantitate produsă:          {analysis_df.loc[low_mask, 'Production'].sum():.3f} MWh")
print(f"Valoare Cumpărare (-15 lei): {analysis_df.loc[low_mask, 'Value_Buy'].sum():.2f} lei")
print(f"Valoare Vânzare (+15 lei):  {analysis_df.loc[low_mask, 'Value_Sell'].sum():.2f} lei\n")

print("=== ANALIZĂ INTERVALE CU PZU >= 100 LEI ===")
print(f"Cantitate produsă:          {analysis_df.loc[high_mask, 'Production'].sum():.3f} MWh")
print(f"Valoare Cumpărare (85%):    {analysis_df.loc[high_mask, 'Value_Buy'].sum():.2f} lei")
print(f"Valoare Vânzare (115%):     {analysis_df.loc[high_mask, 'Value_Sell'].sum():.2f} lei\n")

print("=== TOTAL LUNAR (TOATE INTERVALELE) ===")
print(f"Total Energie Produsă:      {total_energie:.3f} MWh")
print(f"Total Valoare PZU Pur:      {total_valoare_pzu:.2f} lei")
print(f"Total Valoare Cumpărare:    {total_valoare_cump:.2f} lei")
print(f"Total Valoare Vânzare:      {total_valoare_vanz:.2f} lei\n")

print("=== PREȚURI MEDII PONDERATE ===")
print(f"Preț Mediu PZU:             {pret_mediu_pzu:.2f} lei/MWh")
print(f"Preț Mediu Cumpărare:       {pret_mediu_cump:.2f} lei/MWh")
print(f"Preț Mediu Vânzare:         {pret_mediu_vanz:.2f} lei/MWh")