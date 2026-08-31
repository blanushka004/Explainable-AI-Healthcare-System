import pandas as pd
from pathlib import Path


# ==========================================
# 1. Define project paths
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed.cleveland.data"
OUTPUT_FILE = BASE_DIR / "data" / "heart_disease.csv"


# ==========================================
# 2. Define column names
# ==========================================

columns = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
    "target"
]


# ==========================================
# 3. Load the Cleveland Heart Disease Dataset
# ==========================================

df = pd.read_csv(
    INPUT_FILE,
    names=columns,
    na_values="?"
)


print("=" * 50)
print("HEART DISEASE DATASET LOADED")
print("=" * 50)

print("Original dataset shape:", df.shape)

print("\nFirst 5 rows:")
print(df.head())


# ==========================================
# 4. Convert all columns to numeric
# ==========================================

for column in columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")


# ==========================================
# 5. Check missing values
# ==========================================

print("\nMissing values before cleaning:")

print(df.isnull().sum())


# ==========================================
# 6. Remove rows containing missing values
# ==========================================

df = df.dropna().reset_index(drop=True)


print("\nDataset shape after removing missing values:")
print(df.shape)


# ==========================================
# 7. Convert target into binary classification
# ==========================================

# Original target:
# 0 = No Heart Disease
# 1 = Heart Disease
# 2 = Heart Disease
# 3 = Heart Disease
# 4 = Heart Disease

# New target:
# 0 = No Heart Disease
# 1 = Heart Disease Present

df["target"] = (df["target"] > 0).astype(int)


# ==========================================
# 8. Display target distribution
# ==========================================

print("\nTarget distribution:")

print(df["target"].value_counts())

print("\nTarget meaning:")
print("0 = No Heart Disease")
print("1 = Heart Disease Present")


# ==========================================
# 9. Save cleaned dataset
# ==========================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ==========================================
# 10. Final confirmation
# ==========================================

print("\n" + "=" * 50)
print("PREPROCESSING COMPLETED SUCCESSFULLY")
print("=" * 50)

print("Cleaned dataset saved at:")
print(OUTPUT_FILE)

print("\nFinal dataset shape:")
print(df.shape)

print("\nFinal dataset:")
print(df.head())