import pandas as pd
import re

# ---------- 1. Ask user for file paths (no hardcoding) ----------
input_file  = input("Enter INPUT csv file path  (e.g. Demo_Data.csv): ").strip().strip('"').strip("'")
output_file = input("Enter OUTPUT csv file path (e.g. Transformed_Trades.csv): ").strip().strip('"').strip("'")

# ---------- Load ----------
df = pd.read_csv(input_file)

# ---------- 2. Parse symbol & direction from 'futures' column ----------
df['Raw Symbol'] = df['futures'].apply(lambda x: x.split(' ')[0])
df['Direction']  = df['futures'].apply(lambda x: x.split(' ')[1].split('·')[0])   # Long / Short

# ---------- 3. Strip USDT / USDT.P suffix from symbol ----------
df['Symbol'] = df['Raw Symbol'].apply(lambda s: re.sub(r'USDT(\.P)?$', '', s))

# ---------- Clean quantity (remove coin name, keep number) ----------
df['Quantity'] = df['closed amount'].apply(lambda x: float(str(x).split(' ')[0]))

# ---------- 4. Build Buy/Sell rows (Fee merged, no Value, no PnL) ----------
rows = []
for _, r in df.iterrows():
    is_long = r['Direction'] == 'Long'
    fee     = (r['position fee'] - (r['funding fees']))      # merged into single Fee

    # ENTRY row
    rows.append({'Symbol': r['Symbol'],
                 'Side': 'Buy' if is_long else 'Sell',
                 'Quantity': r['Quantity'],
                 'Price': r['average entry price'],
                 'Timestamp': r['opening time'],
                 'Fee': 0.0,
                 'Status': 'Entry'})

    # EXIT row
    rows.append({'Symbol': r['Symbol'],
                 'Side': 'Sell' if is_long else 'Buy',
                 'Quantity': r['Quantity'],
                 'Price': r['average closing price'],
                 'Timestamp': r['closed time'],
                 'Fee': fee,
                 'Status': 'Exit'})

# ---------- Save ----------
out = pd.DataFrame(rows, columns=['Symbol', 'Side', 'Quantity', 'Price', 'Timestamp', 'Fee', 'Status'])
out.to_csv(output_file, index=False)
print(f"Done - {len(df)} trades converted into {len(out)} rows, saved to '{output_file}'")