"""
train.py — Geldium AI Collections System
=========================================
This script is the entire ML pipeline.
Run it once. It trains the model and saves it to disk.
The API will load the saved model — it never retrains.

PIPELINE STATIONS:
  1. Load & Clean
  2. Feature Engineering (create Risk_Tier labels)
  3. Preprocess (scale numbers, encode categories)
  4. Train Model
  5. Save Model + Preprocessor

HOW TO RUN:
  1. Place this file in your ml/ folder
  2. Place your dataset in the same folder as data.xlsx
  3. Run: python train.py
  4. You will see model.pkl appear in the same folder
"""

# ── IMPORTS ──────────────────────────────────────────────────────────────────
# pandas  → for loading and manipulating our Excel/CSV data like a spreadsheet
# numpy   → for number crunching under the hood (pandas uses it too)
# sklearn → scikit-learn, our ML toolkit. Has the model, scaler, encoder, splitter
# pickle  → for saving Python objects (like our trained model) to a file on disk

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pickle
import os

# ── FILE PATHS ────────────────────────────────────────────────────────────────
# These are the file names the script reads from and writes to.
# Keep data.xlsx in the same folder as this script.

# DATA_PATH   = "data.xlsx"   # your Geldium dataset
# MODEL_PATH  = "model.pkl"   # where we save the trained model bundle
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.xlsx")
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
# =============================================================================
# STATION 1: LOAD & CLEAN
# =============================================================================
# Why clean?
#   Some cells in the dataset are empty (NaN = Not a Number).
#   A machine learning model cannot handle empty values — it will crash.
#   So we fill gaps with the MEDIAN of each column.
#
#   Why median and not average (mean)?
#   Median is the middle value when sorted. It ignores extreme outliers.
#   Example: incomes of [20k, 30k, 25k, 500k] → mean=143k (misleading),
#   median=27.5k (much more representative of the typical customer).
# =============================================================================

print("📂 Station 1: Loading and cleaning data...")

# Load the Excel file into a DataFrame (think: Python's version of a spreadsheet)
df = pd.read_excel(DATA_PATH)

# Fill missing values in each column with that column's median value
# .fillna()  → replaces NaN with whatever you put inside
# .median()  → calculates the middle value of the column
df["Income"]       = df["Income"].fillna(df["Income"].median())
df["Credit_Score"] = df["Credit_Score"].fillna(df["Credit_Score"].median())
df["Loan_Balance"] = df["Loan_Balance"].fillna(df["Loan_Balance"].median())

print(f"   ✅ Loaded {len(df)} customers. Missing values filled.")


# =============================================================================
# STATION 2: FEATURE ENGINEERING — Create the Risk_Tier label
# =============================================================================
# Why engineer a label?
#   Our dataset has a column called "Delinquent_Account" (0 or 1).
#   But we need THREE tiers: High, Medium, Low — not just yes/no.
#   So we CREATE a new column called "Risk_Tier" using business rules
#   directly from your report's recommendations.
#
# This technique is called "rule-based labelling" — very common in industry
# when you have domain knowledge but no pre-labelled target column.
#
# The rules (from your SMART goal report):
#   HIGH   = credit utilization > 80% AND at least 1 missed payment
#   MEDIUM = high utilization OR missed payments with low credit score
#             OR high debt-to-income ratio with missed payments
#   LOW    = everything else (safe customers)
# =============================================================================

print("🏗️  Station 2: Engineering Risk_Tier labels...")

# This function runs once per customer row and returns their risk tier
def assign_risk_tier(row):
    # Check each risk condition as a True/False flag
    high_utilization = row["Credit_Utilization"] > 0.80   # above 80%
    has_missed       = row["Missed_Payments"] >= 1         # at least 1 missed payment
    low_score        = row["Credit_Score"] < 500           # credit score below 500
    high_dti         = row["Debt_to_Income_Ratio"] > 0.5   # debt > 50% of income

    # Apply the rules in order of severity
    if high_utilization and has_missed:
        return "High"
    elif high_utilization or (has_missed and low_score) or (high_dti and has_missed):
        return "Medium"
    else:
        return "Low"

# Apply the function to every row in the dataframe
# axis=1 means "go row by row" (axis=0 would go column by column)
df["Risk_Tier"] = df.apply(assign_risk_tier, axis=1)

print("   Distribution of Risk Tiers:")
print(df["Risk_Tier"].value_counts().to_string())


# =============================================================================
# STATION 3: PREPROCESS
# =============================================================================
# Why preprocess?
#   Machine learning models only understand NUMBERS.
#   But even with all-numeric data, there's a problem:
#
#   Income can be 165,000. Credit_Utilization is 0.85.
#   The model sees Income as WAY more important just because it's a bigger number.
#   That's not fair — it's just a units problem (dollars vs. percentage).
#
#   StandardScaler fixes this by converting every column to the same scale:
#   mean of 0, standard deviation of 1. Now all features are equally "sized".
#
#   Think of it like converting everyone's height to the same unit before
#   comparing — you wouldn't mix feet and centimetres in one analysis.
#
# We also need to ENCODE the target label (Risk_Tier):
#   Models need numbers as output too. So:
#   "High" → 0, "Low" → 1, "Medium" → 2  (alphabetical order by default)
#   LabelEncoder does this automatically and remembers the mapping.
#
# CRITICAL: We save the scaler.
#   When the API gets a new customer, it must scale that customer's data
#   the SAME WAY we scaled training data. Otherwise predictions are wrong.
# =============================================================================

print("⚙️  Station 3: Preprocessing features...")

# These are the 8 columns we feed into the model
# We drop Customer_ID (just a name), Employment_Status (text), etc.
FEATURES = [
    "Credit_Utilization",   # % of credit limit used
    "Missed_Payments",      # number of missed payments
    "Credit_Score",         # credit bureau score
    "Debt_to_Income_Ratio", # how much debt vs. income
    "Income",               # annual income
    "Loan_Balance",         # current loan balance
    "Age",                  # customer age
    "Account_Tenure"        # how long they've been a customer
]

# X = input features (what the model learns FROM)
# y = target label   (what the model learns TO PREDICT)
X = df[FEATURES]
y = df["Risk_Tier"]

# Fit the scaler on X and immediately transform X
# fit()       → calculates the mean and std of each column
# transform() → applies the scaling using those values
# fit_transform() → does both in one step (only use on training data!)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Convert "High/Low/Medium" string labels into integers 0/1/2
le = LabelEncoder()
y_encoded = le.fit_transform(y)

print(f"   ✅ Features scaled. Label classes: {list(le.classes_)}")


# =============================================================================
# STATION 4: TRAIN MODEL
# =============================================================================
# Why Random Forest?
#   Random Forest = many decision trees averaged together.
#   One decision tree is like a flowchart: "Is utilization > 80%? If yes → ..."
#   One tree can overfit (memorise training data). Many trees averaged = robust.
#
#   It works well here because:
#   - Our features are numeric (no complex transformations needed)
#   - We have a mix of scales (RF handles this well post-scaling)
#   - It gives us feature importance (explainability for stakeholders)
#
# Train/Test Split:
#   We hold back 20% of customers (test_size=0.2) that the model NEVER sees
#   during training. After training, we test on this hidden 20%.
#   This simulates real-world performance on new customers.
#
#   stratify=y_encoded → ensures each Risk Tier is proportionally represented
#   in both train and test sets. Without this, all High-risk customers might
#   accidentally end up in training, leaving none to test on.
# =============================================================================

print("🤖 Station 4: Training Random Forest model...")

# Split data: 80% for training, 20% for testing
# random_state=42 → sets a seed so results are reproducible every run
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_encoded,
    test_size=0.2,
    random_state=42,
    stratify=y_encoded   # maintain class balance in both splits
)

# Create and train the Random Forest model
model = RandomForestClassifier(
    n_estimators=100,  # 100 decision trees — averaged together for final prediction
    max_depth=10,      # each tree can be at most 10 levels deep (prevents overfitting)
    random_state=42    # seed for reproducibility
)

# .fit() is where actual learning happens
# The model finds patterns linking features → risk tiers
model.fit(X_train, y_train)

# Predict on the held-out test set
y_pred = model.predict(X_test)

# Print performance report
# Precision = of predicted Highs, how many were actually High?
# Recall    = of actual Highs, how many did we correctly catch?
# F1-score  = harmonic mean of precision and recall (overall quality)
print("\n   📊 Model Performance on Held-Out Test Set:")
print(classification_report(y_test, y_pred, target_names=le.classes_))


# =============================================================================
# STATION 5: SAVE MODEL + SCALER + METADATA
# =============================================================================
# Why save everything together in one bundle?
#   The API needs to:
#     1. Know which features to expect       → features list
#     2. Scale incoming data the same way    → scaler
#     3. Make a prediction                   → model
#     4. Convert 0/1/2 back to High/Low/Med  → encoder
#
#   If we only saved the model, the API would have no scaler → broken predictions.
#   We bundle all 4 into one dictionary and save with pickle.
#
# pickle = Python's built-in way to serialise (freeze) any Python object to disk.
# "wb" = write binary (pickle files are binary, not plain text)
# =============================================================================

print("💾 Station 5: Saving model bundle to disk...")

# Bundle everything the API will need at prediction time
bundle = {
    "model":    model,    # the trained Random Forest
    "scaler":   scaler,   # the fitted StandardScaler
    "encoder":  le,       # the fitted LabelEncoder
    "features": FEATURES  # the exact list of columns to expect
}


# Save the bundle to model.pkl
with open(MODEL_PATH, "wb") as f:
    pickle.dump(bundle, f)

print(f"   ✅ model.pkl saved successfully!")
print()
print("🎉 Pipeline complete!")
print("   Your model is trained and ready.")
print("   Next step: build the FastAPI backend (Phase 2).")