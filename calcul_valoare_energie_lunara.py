import pandas as pd
import os

# ==========================================
# CONFIGURARE MARJE ȘI PRAGURI
# ==========================================
PRAG_PRET = 100.0 # Pragul de preț în lei/MWh

# Cazul 1: Cumpărare de la producător (se aplică pentru producție)
MARJA_CUMPARARE_FIXA = 15     # lei (se scade din preț când PZU < 100)
MARJA_CUMPARARE_PROC = 0.85   # % (se aplică 85% din preț când PZU >= 100)

# Cazul 2: Vânzare energie (se aplică pentru consum)
MARJA_VANZARE_FIXA = 15       # lei (se adaugă la preț când PZU < 100)
MARJA_VANZARE_PROC = 1.15     # % (se aplică 115% din preț când PZU >= 100)
# ==========================================

# Funcție pentru citirea sigură a datelor
def incarca_date(filepath):
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        try:
            df = pd.read_csv(filepath)
            if not df.empty:
                return df.iloc[:, 1].fillna(0)
        except Exception as e:
            print(f"Avertisment: Nu s-a putut citi {filepath}: {e}")
    return None

# 1. Încărcarea prețurilor PZU
price_df = pd.read_csv('2026-09/PZU_2026_09_15min.csv')
price_melt = price_df.melt(id_vars=['Data'], var_name='Interval', value_name='Price')
price_melt['Int_Num'] = price_melt['Interval'].str.extract(r'(\d+)').astype(int)
price_melt = price_melt.sort_values(['Data', 'Int_Num']).reset_index(drop=True)

# 2. Crearea DataFrame-ului principal cu prețurile PZU
analysis_df = pd.DataFrame({'Price_PZU': price_melt['Price']})

# 3. Încărcarea datelor de Producție și Consum
prod_series = incarca_date('2026-09/sample-productie-2026-sept.csv')
cons_series = incarca_date('2026-09/sample-consum-2026-sept.csv')

analysis_df['Production'] = prod_series if prod_series is not None else 0.0
analysis_df['Consumption'] = cons_series if cons_series is not None else 0.0

# 4. Aplicarea formulelor pentru noile prețuri
analysis_df['Price_Buy'] = analysis_df['Price_PZU'].apply(
    lambda pzu: (pzu - MARJA_CUMPARARE_FIXA) if pzu < PRAG_PRET else (pzu * MARJA_CUMPARARE_PROC)
)
analysis_df['Price_Sell'] = analysis_df['Price_PZU'].apply(
    lambda pzu: (pzu + MARJA_VANZARE_FIXA) if pzu < PRAG_PRET else (pzu * MARJA_VANZARE_PROC)
)

# 5. Calcularea valorilor finale
analysis_df['Value_Prod_Buy'] = analysis_df['Production'] * analysis_df['Price_Buy']
analysis_df['Value_Cons_Sell'] = analysis_df['Consumption'] * analysis_df['Price_Sell']

# 6. Măști pentru defalcarea pragurilor
low_mask = analysis_df['Price_PZU'] < PRAG_PRET
high_mask = analysis_df['Price_PZU'] >= PRAG_PRET

# 7. Agregarea rezultatelor finale
total_prod_mwh = analysis_df['Production'].sum()
total_val_prod = analysis_df['Value_Prod_Buy'].sum()
avg_price_buy = total_val_prod / total_prod_mwh if total_prod_mwh > 0 else 0

total_cons_mwh = analysis_df['Consumption'].sum()
total_val_cons = analysis_df['Value_Cons_Sell'].sum()
avg_price_sell = total_val_cons / total_cons_mwh if total_cons_mwh > 0 else 0

# 8. Afișarea rezultatelor pe categorii
print("=== DEFALCARE PRODUCȚIE (Achiziție de la Producător) ===")
if total_prod_mwh > 0:
    print(f"  [Intervale cu PZU < 100 lei]")
    print(f"  Cantitate generată:        {analysis_df.loc[low_mask, 'Production'].sum():.3f} MWh")
    print(f"  Valoare achitată (-15 lei):{analysis_df.loc[low_mask, 'Value_Prod_Buy'].sum():.2f} lei\n")
    
    print(f"  [Intervale cu PZU >= 100 lei]")
    print(f"  Cantitate generată:        {analysis_df.loc[high_mask, 'Production'].sum():.3f} MWh")
    print(f"  Valoare achitată (85%):    {analysis_df.loc[high_mask, 'Value_Prod_Buy'].sum():.2f} lei\n")
    
    print(f"  --------------------------------------------------")
    print(f"  TOTAL Cantitate Achiziție: {total_prod_mwh:.3f} MWh")
    print(f"  TOTAL Valoare Achiziție:   {total_val_prod:.2f} lei")
    print(f"  Preț Mediu Cumpărare:      {avg_price_buy:.2f} lei/MWh\n")
else:
    print("  Nu există date valide de producție.\n")


print("=== DEFALCARE CONSUM (Vânzare către Consumator) ===")
if total_cons_mwh > 0:
    print(f"  [Intervale cu PZU < 100 lei]")
    print(f"  Cantitate consumată:       {analysis_df.loc[low_mask, 'Consumption'].sum():.3f} MWh")
    print(f"  Valoare încasată (+15 lei):{analysis_df.loc[low_mask, 'Value_Cons_Sell'].sum():.2f} lei\n")
    
    print(f"  [Intervale cu PZU >= 100 lei]")
    print(f"  Cantitate consumată:       {analysis_df.loc[high_mask, 'Consumption'].sum():.3f} MWh")
    print(f"  Valoare încasată (115%):   {analysis_df.loc[high_mask, 'Value_Cons_Sell'].sum():.2f} lei\n")
    
    print(f"  --------------------------------------------------")
    print(f"  TOTAL Cantitate Vânzare:   {total_cons_mwh:.3f} MWh")
    print(f"  TOTAL Valoare Vânzare:     {total_val_cons:.2f} lei")
    print(f"  Preț Mediu Vânzare:        {avg_price_sell:.2f} lei/MWh\n")
else:
    print("  Nu există date valide de consum.\n")