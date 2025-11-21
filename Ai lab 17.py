import re
import pandas as pd

# GitHub Copilot
# File: C:/Users/SAI THRUSHNA/Downloads/Ai lab 17.py
# Lab Question 3: Financial Transactions Dataset
# Task 1: Remove duplicate transactions and convert all amounts into USD using a conversion dictionary.
# Task 2: Normalize timestamps into UTC and create a new column transaction_hour.


# --- Configuration: update as needed ---
INPUT_CSV = "transactions.csv"   # path to your raw data file
OUTPUT_CSV = "transactions_cleaned.csv"
# Example conversion rates: 1 unit of currency -> USD
CONVERSION_RATES = {
    "USD": 1.0,
    "EUR": 1.10,
    "GBP": 1.25,
    "JPY": 0.0073,
    "AUD": 0.67,
    "CAD": 0.74,
    # add more currencies as needed
}

# --- Helper functions ---
def parse_amount(value):
    """
    Turn amount strings like "$1,234.56" or "1.234,56" into a float.
    If value is already numeric, return it as float.
    Returns NaN on failure.
    """
    if pd.isna(value):
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    # Remove common grouping separators and currency symbols, keep digits, dot, minus
    # First replace comma used as thousands separator (e.g. "1,234.56") => remove commas
    s = s.replace(",", "")
    # Remove currency symbols and letters (we expect currency in a separate column)
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s) if s != "" else float("nan")
    except ValueError:
        return float("nan")

def convert_to_usd(amount, currency, rates):
    """
    Convert numeric amount in given currency into USD using rates dict.
    If currency missing or rate unknown, returns NaN.
    """
    if pd.isna(amount):
        return float("nan")
    if pd.isna(currency):
        return float("nan")
    currency = str(currency).upper().strip()
    rate = rates.get(currency)
    if rate is None:
        return float("nan")
    return amount * rate

# --- Load data ---
# Adjust read method if your file format or column names differ.
df = pd.read_csv(INPUT_CSV, dtype=str)  # read as strings to clean explicitly

# If your dataset already has numeric amount or specific dtypes, you can read with infer dtypes:
# df = pd.read_csv(INPUT_CSV)

# --- Step 1: Remove duplicates ---
# If there's a transaction id column, use it; otherwise drop exact duplicate rows.
if "transaction_id" in df.columns:
    df = df.drop_duplicates(subset=["transaction_id"]).reset_index(drop=True)
else:
    df = df.drop_duplicates().reset_index(drop=True)

# --- Step 1b: Clean and convert amounts ---
# Expecting columns: 'amount' and 'currency'. Adjust names if your file uses different ones.
amount_col = "amount"       # change if needed
currency_col = "currency"   # change if needed

# Parse amounts into numeric column
df["amount_clean"] = df.get(amount_col, pd.Series([None]*len(df))).apply(parse_amount)

# Convert to USD using conversion dict
df["amount_usd"] = df.apply(
    lambda r: convert_to_usd(r["amount_clean"], r.get(currency_col, None), CONVERSION_RATES),
    axis=1
)

# If some rates were missing, you may want to inspect them:
missing_rates = df[df["amount_usd"].isna() & df["amount_clean"].notna()]
if not missing_rates.empty:
    # Print a small sample to help debugging (remove or comment out in non-interactive scripts)
    print("Warning: some amounts could not be converted to USD due to missing/unknown currency or bad amounts.")
    print(missing_rates[[amount_col, currency_col]].drop_duplicates().head())

# --- Step 2: Normalize timestamps into UTC and create transaction_hour ---
# Expecting a column 'timestamp' and optionally a 'timezone' column with IANA tz names per row.
timestamp_col = "timestamp"   # change if needed
timezone_col = "timezone"     # optional: e.g., "Europe/Berlin", "America/New_York"

if timestamp_col not in df.columns:
    raise ValueError(f"Expected a timestamp column named '{timestamp_col}' in the input data.")

# Case A: If there's a per-row timezone column, localize per-row and convert to UTC
if timezone_col in df.columns:
    def to_utc_row(row):
        raw = row[timestamp_col]
        tz = row[timezone_col]
        try:
            ts = pd.to_datetime(raw, errors="coerce")
            if pd.isna(ts):
                return pd.NaT
            # if ts has no tz, localize to provided tz first
            if ts.tzinfo is None:
                return ts.tz_localize(tz).tz_convert("UTC")
            else:
                return ts.tz_convert("UTC")
        except Exception:
            return pd.NaT

    df["timestamp_utc"] = df.apply(to_utc_row, axis=1)

else:
    # Case B: No per-row timezone. We use pandas to_datetime with utc=True.
    # This will:
    # - parse tz-aware timestamps and convert to UTC
    # - treat naive timestamps as UTC (if they are actually in a different zone, specify/convert accordingly)
    df["timestamp_utc"] = pd.to_datetime(df[timestamp_col], errors="coerce", utc=True)

# Create transaction_hour (UTC hour 0-23). If timestamp_utc is NaT, hour will be NaN.
df["transaction_hour"] = df["timestamp_utc"].dt.hour

# --- Optional: reorder/drop helper columns and save ---
# Keep original columns + amount_usd + timestamp_utc + transaction_hour
keep_cols = list(df.columns)  # modify if you want to drop helper columns like 'amount_clean'
# Example to drop helper columns:
# df = df.drop(columns=["amount_clean"])

# Save cleaned dataset
df.to_csv(OUTPUT_CSV, index=False)

# Print summary
print(f"Processed {len(df)} rows. Cleaned data written to: {OUTPUT_CSV}")