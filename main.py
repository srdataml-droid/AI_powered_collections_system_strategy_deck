"""
main.py — Geldium AI Collections System: FastAPI Backend
=========================================================
"""

# ── IMPORTS ──────────────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware  # ← CORS
from pydantic import BaseModel, Field
from typing import Optional
import numpy as np
import pickle
import os
import logging
import pandas as pd
import requests

# ── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── FILE PATHS ───────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
DATA_PATH  = os.path.join(BASE_DIR, "data.xlsx")

# ── GROQ SETUP ───────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── LOAD MODEL ───────────────────────────────────────────────────────────────
logger.info("Loading model bundle from disk...")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"model.pkl not found. Run train.py first.")

try:
    with open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
    model    = bundle["model"]
    scaler   = bundle["scaler"]
    encoder  = bundle["encoder"]
    FEATURES = bundle["features"]
    logger.info(f"✅ Model loaded. Features: {FEATURES}")
except Exception as e:
    raise RuntimeError(f"Could not load model.pkl: {e}")

# ── LOAD DATASET ─────────────────────────────────────────────────────────────
try:
    df = pd.read_excel(DATA_PATH)
    logger.info(f"✅ Dataset loaded. {len(df)} customers.")
except Exception as e:
    logger.warning(f"Could not load data.xlsx: {e}")
    df = None

# ═════════════════════════════════════════════════════════════════════════════
# CREATE APP — ONLY ONCE! With CORS attached.
# ═════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Geldium AI Collections API",
    description="Predicts delinquency risk tier and recommends interventions.",
    version="1.0.0"
)

# ── CORS CONFIGURATION ───────────────────────────────────────────────────────
# MUST come right after app creation, BEFORE any endpoints

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # ← Allows all domains (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("✅ CORS middleware configured")

# ── DATA MODELS ───────────────────────────────────────────────────────────────
class CustomerInput(BaseModel):
    Customer_ID:          str   = Field(..., description="e.g. CUST0001")
    Credit_Utilization:   float = Field(..., description="0.0–1.0+")
    Missed_Payments:      int   = Field(..., description="0–6")
    Credit_Score:         float = Field(..., description="300–850")
    Debt_to_Income_Ratio: float = Field(..., description="0.0–1.0+")
    Income:               float = Field(..., description="Annual income")
    Loan_Balance:         float = Field(..., description="Outstanding balance")
    Age:                  int   = Field(..., description="Years")
    Account_Tenure:       int   = Field(..., description="Years as customer")

    class Config:
        json_schema_extra = {
            "example": {
                "Customer_ID": "CUST0001",
                "Credit_Utilization": 0.85,
                "Missed_Payments": 2,
                "Credit_Score": 480.0,
                "Debt_to_Income_Ratio": 0.6,
                "Income": 45000.0,
                "Loan_Balance": 12000.0,
                "Age": 34,
                "Account_Tenure": 3
            }
        }

class PredictionResponse(BaseModel):
    Customer_ID:  str
    risk_tier:    str
    intervention: str
    confidence:   float
    risk_score:   float
    explanation:  str

class BatchInput(BaseModel):
    customers: list[CustomerInput]

class BatchResponse(BaseModel):
    total:       int
    predictions: list[dict]

class SettingsInput(BaseModel):
    receiver_name:  str = ""
    receiver_email: str = ""

# ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

def get_intervention(tier: str) -> str:
    interventions = {
        "High":   "🔴 Escalate to human agent — offer personalised hardship plan immediately.",
        "Medium": "🟡 Proactive outreach — send repayment plan offer and counselling invitation.",
        "Low":    "🟢 Automated reminder — send standard payment reminder via SMS or email."
    }
    return interventions.get(tier, "⚪ Unknown tier — manual review recommended.")

def generate_explanation(customer, risk_score: float) -> str:
    """Generate AI explanation. Works with Pydantic models, dicts, or pandas Series."""
    
    def read(field: str):
        if hasattr(customer, field):
            return getattr(customer, field)
        return customer[field]
    
    credit_util = read('Credit_Utilization')
    missed = int(read('Missed_Payments'))
    score = read('Credit_Score')
    dti = read('Debt_to_Income_Ratio')
    income = read('Income')
    balance = read('Loan_Balance')
    age = int(read('Age'))
    tenure = int(read('Account_Tenure'))
    
    fallback = (
        f"This customer has a credit utilization of {credit_util*100:.0f}%, "
        f"{missed} missed payment(s), a credit score of {score:.0f}, "
        f"and a debt-to-income ratio of {dti:.2f}. "
        f"These combined factors place them at {risk_score*100:.0f}% delinquency risk."
    )
    
    if not GROQ_API_KEY:
        return fallback

    prompt = f"""You are a financial risk analyst at Geldium Finance.

Customer financial data:
- Credit Utilization: {credit_util*100:.0f}%
- Missed Payments: {missed} in last 6 months
- Credit Score: {score:.0f}
- Debt-to-Income Ratio: {dti:.2f}
- Annual Income: £{income:,.0f}
- Loan Balance: £{balance:,.0f}
- Age: {age}
- Account Tenure: {tenure} years
- Overall Delinquency Risk Score: {risk_score*100:.0f}%

Write a 2-3 sentence plain-English explanation of why this customer is at risk.
Focus on the most concerning factors. Write for a collections agent.
Do not use bullet points. Do not start with "This customer"."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 150
            },
            timeout=8
        )
        
        response_json = response.json()
        
        if "error" in response_json:
            logger.error(f"Groq API error: {response_json['error']}")
            return fallback
        
        if "choices" not in response_json:
            logger.error(f"Groq unexpected response: {response_json}")
            return fallback
        
        explanation = response_json["choices"][0]["message"]["content"].strip()
        logger.info("✅ Groq explanation generated.")
        return explanation

    except Exception as e:
        logger.warning(f"Groq failed: {e}")
        return fallback

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/", summary="Health Check")
def root():
    return {
        "status": "ok",
        "message": "Geldium AI Collections API is running.",
        "model_features": FEATURES,
        "ai_provider": "groq" if GROQ_API_KEY else "none"
    }

@app.post("/predict", response_model=PredictionResponse, summary="Predict Customer Risk Tier")
def predict(customer: CustomerInput):
    """Send one customer's data → get risk tier and recommended action."""
    try:
        input_data = np.array([[
            customer.Credit_Utilization,
            customer.Missed_Payments,
            customer.Credit_Score,
            customer.Debt_to_Income_Ratio,
            customer.Income,
            customer.Loan_Balance,
            customer.Age,
            customer.Account_Tenure
        ]])

        input_scaled = scaler.transform(input_data)
        prediction_encoded = model.predict(input_scaled)[0]
        probabilities = model.predict_proba(input_scaled)[0]

        confidence = float(probabilities[prediction_encoded])
        high_index = list(encoder.classes_).index("High")
        risk_score = float(probabilities[high_index])
        risk_tier = encoder.inverse_transform([prediction_encoded])[0]
        intervention = get_intervention(risk_tier)
        explanation = generate_explanation(customer, risk_score)

        logger.info(
            f"Prediction: {customer.Customer_ID} → {risk_tier} | "
            f"Confidence: {confidence:.2f} | Risk score: {risk_score:.2f}"
        )

        return PredictionResponse(
            Customer_ID=customer.Customer_ID,
            risk_tier=risk_tier,
            intervention=intervention,
            confidence=round(confidence, 4),
            risk_score=round(risk_score, 4),
            explanation=explanation
        )

    except ValueError as e:
        logger.warning(f"Invalid input: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid input data: {str(e)}")

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/customer/{customer_id}", summary="Predict by Customer ID")
def get_customer_prediction(customer_id: str):
    """Look up a customer by ID and run prediction automatically."""
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset not loaded.")

    customer_row = df[df["Customer_ID"] == customer_id]

    if customer_row.empty:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")

    row = customer_row.iloc[0]

    customer = CustomerInput(
        Customer_ID=customer_id,
        Credit_Utilization=float(row["Credit_Utilization"]),
        Missed_Payments=int(row["Missed_Payments"]),
        Credit_Score=float(row["Credit_Score"]),
        Debt_to_Income_Ratio=float(row["Debt_to_Income_Ratio"]),
        Income=float(row["Income"]),
        Loan_Balance=float(row["Loan_Balance"]),
        Age=int(row["Age"]),
        Account_Tenure=int(row["Account_Tenure"])
    )

    return predict(customer)

@app.post("/predict/batch", response_model=BatchResponse, summary="Batch Predict")
def predict_batch(batch: BatchInput):
    """Send multiple customers → get risk tiers for all at once."""
    if not batch.customers:
        raise HTTPException(status_code=400, detail="No customers provided.")

    if len(batch.customers) > 1000:
        raise HTTPException(status_code=400, detail="Batch limit is 1000 customers.")

    try:
        input_matrix = np.array([
            [c.Credit_Utilization, c.Missed_Payments, c.Credit_Score,
             c.Debt_to_Income_Ratio, c.Income, c.Loan_Balance, c.Age, c.Account_Tenure]
            for c in batch.customers
        ])

        input_scaled = scaler.transform(input_matrix)
        predictions_encoded = model.predict(input_scaled)
        probabilities_all = model.predict_proba(input_scaled)
        high_index = list(encoder.classes_).index("High")

        results = []
        for i, pred_enc in enumerate(predictions_encoded):
            tier = encoder.inverse_transform([pred_enc])[0]
            confidence = float(probabilities_all[i][pred_enc])
            risk_score = float(probabilities_all[i][high_index])
            intervention = get_intervention(tier)

            results.append({
                "Customer_ID": batch.customers[i].Customer_ID,
                "customer_index": i,
                "risk_tier": tier,
                "intervention": intervention,
                "confidence": round(confidence, 4),
                "risk_score": round(risk_score, 4)
            })

        logger.info(f"Batch: {len(results)} customers processed.")
        return BatchResponse(total=len(results), predictions=results)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid batch input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch failed: {str(e)}")

# ── SETTINGS ENDPOINTS ────────────────────────────────────────────────────────

from settings import load_settings, save_settings, sender_configured

@app.get("/settings", summary="Load settings")
def get_settings():
    data = load_settings()
    data["sender_configured"] = sender_configured()
    return data

@app.post("/settings", summary="Save settings")
def post_settings(body: SettingsInput):
    settings = {
        "receiver_name": body.receiver_name,
        "receiver_email": body.receiver_email
    }
    success = save_settings(settings)
    if not success:
        raise HTTPException(status_code=500, detail="Could not save settings.")
    return {"status": "saved", **settings}

@app.get("/app", summary="Serve frontend dashboard")
def serve_frontend():
    html_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="index.html not found.")
    return FileResponse(html_path)