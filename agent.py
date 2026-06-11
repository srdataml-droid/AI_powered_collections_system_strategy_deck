# """
# agent.py — Geldium AI Collections System: The AI Agent
# =======================================================
# This is the brain of the autonomous system.
# It runs the full collections loop without any human triggering it:

#   1. Load customer data
#   2. Score every customer through the ML model
#   3. Route each customer to the right action lane
#   4. Send high-risk alerts to human agents
#   5. Log everything for audit trail
#   6. Send daily summary report

# HOW TO RUN MANUALLY (for testing):
#   python agent.py

# HOW IT RUNS AUTOMATICALLY:
#   scheduler.py calls agent.run() every 24 hours.
#   You never need to run this manually in production.

# WHAT "AGENTIC" MEANS HERE:
#   Traditional software: human triggers action → system responds
#   Agentic software:     system wakes up → assesses situation →
#                         decides action → executes → reports back

#   The agent makes decisions (which tier? which action?) and
#   executes them (send alert, log outcome) autonomously.
#   Human oversight is preserved — High risk always gets a human alert.
# """

# # ── IMPORTS ──────────────────────────────────────────────────────────────────

# import os
# from dotenv import load_dotenv
# load_dotenv()  # load .env before anything else reads os.getenv()
# import pickle
# import logging
# import numpy as np
# import pandas as pd
# from datetime import datetime
# from notifier import send_high_risk_alert, send_daily_summary

# # ── LOGGING ───────────────────────────────────────────────────────────────────
# # We log to BOTH the console (so you can watch it run)
# # AND a file (so you have a permanent audit trail).

# # Create logs/ folder if it doesn't exist
# os.makedirs("logs", exist_ok=True)

# # Set up logging to write to both terminal and a daily log file
# log_filename = f"logs/agent_{datetime.now().strftime('%Y%m%d')}.log"

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(message)s",  # timestamp | level | message
#     handlers=[
#         logging.FileHandler(log_filename),    # write to file
#         logging.StreamHandler()               # also print to terminal
#     ]
# )
# logger = logging.getLogger(__name__)


# # ── FILE PATHS ────────────────────────────────────────────────────────────────
# BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
# MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
# DATA_PATH  = os.path.join(BASE_DIR, "data.xlsx")


# # ── LOAD MODEL ────────────────────────────────────────────────────────────────
# # Load once at module level — not inside the run() function.
# # If scheduler.py calls run() every 24 hours, we don't want to
# # reload the model from disk 365 times a year unnecessarily.

# logger.info("Loading model bundle...")

# if not os.path.exists(MODEL_PATH):
#     raise FileNotFoundError(
#         f"model.pkl not found at {MODEL_PATH}. Run train.py first."
#     )

# with open(MODEL_PATH, "rb") as f:
#     bundle = pickle.load(f)

# model    = bundle["model"]
# scaler   = bundle["scaler"]
# encoder  = bundle["encoder"]
# FEATURES = bundle["features"]

# logger.info(f"✅ Model loaded. Ready to score customers.")


# # ── HELPER: LOAD DATA ─────────────────────────────────────────────────────────

# def load_customer_data() -> pd.DataFrame:
#     """
#     Load and clean the customer dataset.

#     In production: replace this function with a database query.
#     Example (PostgreSQL):
#         import psycopg2
#         conn = psycopg2.connect(os.getenv("DATABASE_URL"))
#         df = pd.read_sql("SELECT * FROM customers WHERE last_updated >= NOW() - INTERVAL '1 day'", conn)

#     For now: we load from the static Excel file and simulate
#     "fresh daily data" by using the full dataset each run.
#     """
#     logger.info(f"Loading customer data from {DATA_PATH}...")

#     if not os.path.exists(DATA_PATH):
#         raise FileNotFoundError(f"data.xlsx not found at {DATA_PATH}")

#     df = pd.read_excel(DATA_PATH)

#     # Fill missing values (same logic as train.py — must be consistent)
#     df["Income"]       = df["Income"].fillna(df["Income"].median())
#     df["Credit_Score"] = df["Credit_Score"].fillna(df["Credit_Score"].median())
#     df["Loan_Balance"] = df["Loan_Balance"].fillna(df["Loan_Balance"].median())

#     logger.info(f"✅ Loaded {len(df)} customers.")
#     return df


# # ── HELPER: SCORE CUSTOMERS ───────────────────────────────────────────────────

# def score_customers(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Run every customer through the ML model and return the DataFrame
#     with three new columns added:
#         risk_tier   → "High", "Medium", or "Low"
#         risk_score  → probability of being High risk (0.0 – 1.0)
#         confidence  → probability of the predicted tier (0.0 – 1.0)

#     Why batch scoring instead of one at a time?
#       Passing all 500 rows to the model at once is ~100x faster than
#       looping and calling predict() on each row individually.
#       NumPy and scikit-learn are optimised for matrix operations.
#     """
#     logger.info("Scoring all customers...")

#     # Extract the feature columns in the exact order the model expects
#     X = df[FEATURES].values   # .values converts DataFrame to raw NumPy array

#     # Scale using the saved scaler (MUST match how training data was scaled)
#     X_scaled = scaler.transform(X)

#     # Predict risk tier for all customers at once
#     predictions_encoded = model.predict(X_scaled)          # shape: (N,)
#     probabilities       = model.predict_proba(X_scaled)    # shape: (N, 3)

#     # Get the index of "High" in the encoder's class list
#     high_index = list(encoder.classes_).index("High")

#     # Decode integer predictions back to string labels
#     risk_tiers = encoder.inverse_transform(predictions_encoded)

#     # Build confidence and risk score arrays
#     confidences  = probabilities[np.arange(len(predictions_encoded)), predictions_encoded]
#     risk_scores  = probabilities[:, high_index]

#     # Add results as new columns on the DataFrame
#     df = df.copy()   # avoid modifying the original
#     df["risk_tier"]  = risk_tiers
#     df["risk_score"] = risk_scores
#     df["confidence"] = confidences

#     # Log tier distribution
#     counts = df["risk_tier"].value_counts()
#     logger.info(
#         f"Scoring complete → "
#         f"High: {counts.get('High', 0)} | "
#         f"Medium: {counts.get('Medium', 0)} | "
#         f"Low: {counts.get('Low', 0)}"
#     )

#     return df


# # ── HELPER: GET INTERVENTION TEXT ─────────────────────────────────────────────

# def get_intervention(tier: str) -> str:
#     """Map risk tier to recommended business action."""
#     return {
#         "High":   "Escalate to human agent — offer personalised hardship plan immediately.",
#         "Medium": "Proactive outreach — send repayment plan offer and counselling invitation.",
#         "Low":    "Automated reminder — send standard payment reminder via SMS or email."
#     }.get(tier, "Manual review recommended.")


# # ── HELPER: LOG ACTIONS TO FILE ───────────────────────────────────────────────

# def log_actions(df: pd.DataFrame):
#     """
#     Save a CSV of all customer predictions to the logs/ folder.
#     This is the audit trail — a record of every decision the agent made.

#     Why an audit trail?
#       Responsible AI requires that automated decisions can be reviewed.
#       If a customer disputes their treatment, you can look up exactly
#       what the model scored them and why.
#     """
#     audit_path = f"logs/audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

#     audit_df = df[["risk_tier", "risk_score", "confidence"]].copy()
#     audit_df["intervention"] = audit_df["risk_tier"].map(get_intervention)
#     audit_df["timestamp"]    = datetime.now().isoformat()

#     # Include Customer_ID if it exists in the dataset
#     if "Customer_ID" in df.columns:
#         audit_df.insert(0, "Customer_ID", df["Customer_ID"])

#     audit_df.to_csv(audit_path, index=False)
#     logger.info(f"✅ Audit log saved: {audit_path}")


# # ── MAIN AGENT LOOP ───────────────────────────────────────────────────────────

# def run():
#     """
#     The full autonomous agent loop.
#     Called by scheduler.py on a schedule, or manually for testing.

#     Returns a summary dict with the run's statistics.
#     """

#     start_time = datetime.now()
#     logger.info("=" * 60)
#     logger.info("🤖 GELDIUM AI AGENT — Starting daily run")
#     logger.info(f"   Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
#     logger.info("=" * 60)

#     # Track errors so we can include them in the summary email
#     errors = []

#     # Initialise counters
#     high_count   = 0
#     medium_count = 0
#     low_count    = 0

#     try:
#         # ── STEP 1: LOAD DATA ─────────────────────────────────────────────
#         df = load_customer_data()

#         # ── STEP 2: SCORE CUSTOMERS ───────────────────────────────────────
#         df = score_customers(df)

#         # ── STEP 3: ROUTE EACH CUSTOMER TO THE RIGHT ACTION LANE ─────────
#         logger.info("Processing action lanes...")

#         high_risk_customers   = df[df["risk_tier"] == "High"]
#         medium_risk_customers = df[df["risk_tier"] == "Medium"]
#         low_risk_customers    = df[df["risk_tier"] == "Low"]

#         high_count   = len(high_risk_customers)
#         medium_count = len(medium_risk_customers)
#         low_count    = len(low_risk_customers)

#         # ── STEP 4: HANDLE HIGH RISK — send alert per customer ────────────
#         # Why one email per customer (not one bulk email)?
#         # Each high-risk case needs individual human attention.
#         # A bulk list gets skimmed. An individual alert gets acted on.
#         logger.info(f"🔴 Processing {high_count} High-risk customers...")

#         for idx, row in high_risk_customers.iterrows():
#             logger.info(
#                 f"   → Alerting for customer #{idx} | "
#                 f"Risk score: {row['risk_score']:.2f} | "
#                 f"Confidence: {row['confidence']:.2f}"
#             )
#             send_high_risk_alert(
#                 customer_index=idx,
#                 risk_score=row["risk_score"],
#                 confidence=row["confidence"],
#                 intervention=get_intervention("High")
#             )

#         # ── STEP 5: HANDLE MEDIUM RISK — log for outreach system ──────────
#         # In a full production system, this would trigger your CRM
#         # (Customer Relationship Management) tool to schedule calls.
#         # For now we log them — easy to extend later.
#         logger.info(f"🟡 Logging {medium_count} Medium-risk customers for outreach...")
#         for idx, row in medium_risk_customers.iterrows():
#             logger.info(
#                 f"   → Outreach queued: customer #{idx} | "
#                 f"Risk score: {row['risk_score']:.2f}"
#             )

#         # ── STEP 6: HANDLE LOW RISK — log only ────────────────────────────
#         logger.info(f"🟢 Logging {low_count} Low-risk customers (automated reminders)...")

#         # ── STEP 7: SAVE AUDIT LOG ────────────────────────────────────────
#         log_actions(df)

#     # Case: data file missing or unreadable
#     except FileNotFoundError as e:
#         error_msg = f"Data loading failed: {e}"
#         logger.error(error_msg)
#         errors.append(error_msg)

#     # Case: model scoring fails (wrong feature shape, etc.)
#     except ValueError as e:
#         error_msg = f"Scoring failed: {e}"
#         logger.error(error_msg)
#         errors.append(error_msg)

#     # Case: anything else unexpected
#     except Exception as e:
#         error_msg = f"Unexpected error: {e}"
#         logger.error(error_msg)
#         errors.append(error_msg)

#     # ── STEP 8: SEND DAILY SUMMARY ────────────────────────────────────────
#     # This runs whether or not there were errors — always send the report.
#     end_time = datetime.now()
#     run_duration = str(end_time - start_time).split(".")[0]  # e.g. "0:00:03"

#     summary = {
#         "total":    high_count + medium_count + low_count,
#         "high":     high_count,
#         "medium":   medium_count,
#         "low":      low_count,
#         "run_time": run_duration,
#         "errors":   "; ".join(errors) if errors else None
#     }

#     logger.info("📊 Sending daily summary report...")
#     send_daily_summary(summary)

#     logger.info("=" * 60)
#     logger.info(f"✅ Agent run complete in {run_duration}")
#     logger.info("=" * 60)

#     return summary


# # ── ENTRY POINT ───────────────────────────────────────────────────────────────
# # This block only runs if you execute agent.py directly:
# #   python agent.py
# # It does NOT run when scheduler.py imports agent and calls agent.run()
# # That's what "if __name__ == '__main__'" means.

# if __name__ == "__main__":
#     result = run()
#     print("\n📋 Run Summary:")
#     for key, value in result.items():
#         print(f"   {key}: {value}")

"""
agent.py — Geldium AI Collections System: The AI Agent
=======================================================
Updated version with:
  1. Gemini AI — generates plain-English explanation for each High-risk customer
  2. Dynamic receiver — reads receiver email/name from settings.json
  3. load_dotenv() — reads .env credentials before anything runs

HOW TO RUN MANUALLY (for testing):
  python agent.py

HOW IT RUNS AUTOMATICALLY:
  scheduler.py calls agent.run() every 24 hours.
"""

# ── IMPORTS ──────────────────────────────────────────────────────────────────
from urllib import response

from dotenv import load_dotenv
load_dotenv()   # MUST be first — loads .env before any os.getenv() calls
import requests
import os
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime

# Gemini AI — for generating risk explanations

from google import genai

# client = genai.Client(api_key=GEMINI_API_KEY)

# Our modules
from notifier import send_high_risk_alert, send_daily_summary
from settings import load_settings, sender_configured

# ── LOGGING ───────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

log_filename = f"logs/agent_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ── FILE PATHS ────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
DATA_PATH  = os.path.join(BASE_DIR, "data.xlsx")


# ── GROQ SETUP ──────────────────────────────────────────────────────────────
# Configure Groq with the API key from .env
# genai.configure() must be called once before any model calls

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # <-- Make sure this matches your .env variable name

if GROQ_API_KEY:
    # genai.configure(api_key=GROQ_API_KEY)
    # client = genai.Client(api_key=GROQ_API_KEY)
    # gemini_model = client("gemini-1.5-flash")
    
    # gemini-1.5-flash = free tier, fast, good at explanation tasks
    logger.info("✅ Groq AI configured.")
else:
    gemini_model = None
    logger.warning(
        "GROQ_API_KEY not set in .env. "
        "Agent will run without AI explanations."
    )


# ── LOAD ML MODEL ─────────────────────────────────────────────────────────────
logger.info("Loading ML model bundle...")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"model.pkl not found at {MODEL_PATH}. Run train.py first."
    )

with open(MODEL_PATH, "rb") as f:
    bundle = pickle.load(f)

model    = bundle["model"]
scaler   = bundle["scaler"]
encoder  = bundle["encoder"]
FEATURES = bundle["features"]

logger.info("✅ ML model loaded.")


# ── HELPER: GENERATE AI EXPLANATION ──────────────────────────────────────────

def generate_explanation(customer_row: pd.Series, risk_score: float) -> str:
    """
    Ask Gemini to explain WHY a customer is high risk in plain English.

    We build a prompt with the customer's actual numbers and ask Gemini
    to write a 2-3 sentence explanation a collections agent can act on.

    Why this matters:
      The ML model gives a number (87% risk). That's not enough for a
      human agent to understand the situation or explain it to a customer.
      Gemini turns the numbers into a readable, actionable explanation.

    If Gemini is not configured or the call fails, we return a
    fallback explanation built from the numbers directly — so the
    agent never crashes just because AI explanation failed.
    """
    
    # Build a fallback explanation using raw numbers
    # This runs if Gemini fails or isn't configured
    fallback = (
        f"This customer has a credit utilization of "
        f"{customer_row['Credit_Utilization']*100:.0f}%, "
        f"{int(customer_row['Missed_Payments'])} missed payment(s), "
        f"a credit score of {customer_row['Credit_Score']:.0f}, "
        f"and a debt-to-income ratio of {customer_row['Debt_to_Income_Ratio']:.2f}. "
        f"These combined factors place them at {risk_score*100:.0f}% delinquency risk."
    )

    if not GROQ_API_KEY:
        return fallback

    # Build the prompt — specific, short, business-focused
    prompt = f"""
You are a financial risk analyst at Geldium Finance.
A customer has been flagged as HIGH RISK for credit delinquency.

Their financial data:
- Credit Utilization: {customer_row['Credit_Utilization']*100:.0f}% (above 80% is high risk)
- Missed Payments: {int(customer_row['Missed_Payments'])} in last 6 months
- Credit Score: {customer_row['Credit_Score']:.0f}
- Debt-to-Income Ratio: {customer_row['Debt_to_Income_Ratio']:.2f}
- Annual Income: £{customer_row['Income']:,.0f}
- Loan Balance: £{customer_row['Loan_Balance']:,.0f}
- Age: {int(customer_row['Age'])}
- Account Tenure: {int(customer_row['Account_Tenure'])} years
- Overall Delinquency Risk Score: {risk_score*100:.0f}%

Write a 2-3 sentence plain-English explanation of why this customer 
is high risk. Focus on which specific factors are most concerning 
and what they suggest about the customer's financial situation.
Write it for a collections agent who will contact the customer.
Do not use bullet points. Do not start with "This customer".
"""

    try:
        # response = gemini_model.generate_content(prompt)
        # explanation = response.text.strip()
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
        response.raise_for_status()
        explanation = response.json()["choices"][0]["message"]["content"].strip()
        logger.info("✅ Groq explanation generated.")
        return explanation

    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            logger.warning("Groq rate limit hit")
            return fallback + " (AI explanation: rate limit reached)"
        logger.error(f"Groq API error: {e}")
        return fallback
    # Case: Groq API rate limit hit (free tier has limits)
    except Exception as e:
        logger.warning(f"Groq explanation failed: {e}. Using fallback.")
        return fallback


# ── HELPER: LOAD DATA ─────────────────────────────────────────────────────────

def load_customer_data() -> pd.DataFrame:
    """
    Load and clean customer data.
    Swap this function's internals for a database query in production.
    """
    logger.info(f"Loading customer data...")

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"data.xlsx not found at {DATA_PATH}")

    df = pd.read_excel(DATA_PATH)

    # Fill missing values — must match train.py exactly
    df["Income"]       = df["Income"].fillna(df["Income"].median())
    df["Credit_Score"] = df["Credit_Score"].fillna(df["Credit_Score"].median())
    df["Loan_Balance"] = df["Loan_Balance"].fillna(df["Loan_Balance"].median())

    logger.info(f"✅ Loaded {len(df)} customers.")
    return df


# ── HELPER: SCORE CUSTOMERS ───────────────────────────────────────────────────

def score_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Score all customers through the ML model in one batch."""
    logger.info("Scoring all customers...")

    X           = df[FEATURES].values
    X_scaled    = scaler.transform(X)
    preds_enc   = model.predict(X_scaled)
    probs       = model.predict_proba(X_scaled)
    high_index  = list(encoder.classes_).index("High")

    df = df.copy()
    df["risk_tier"]  = encoder.inverse_transform(preds_enc)
    df["risk_score"] = probs[:, high_index]
    df["confidence"] = probs[np.arange(len(preds_enc)), preds_enc]

    counts = df["risk_tier"].value_counts()
    logger.info(
        f"Scoring complete → "
        f"High: {counts.get('High', 0)} | "
        f"Medium: {counts.get('Medium', 0)} | "
        f"Low: {counts.get('Low', 0)}"
    )
    return df


# ── HELPER: INTERVENTION TEXT ─────────────────────────────────────────────────

def get_intervention(tier: str) -> str:
    return {
        "High":   "Escalate to human agent — offer personalised hardship plan immediately.",
        "Medium": "Proactive outreach — send repayment plan offer and counselling invitation.",
        "Low":    "Automated reminder — send standard payment reminder via SMS or email."
    }.get(tier, "Manual review recommended.")


# ── HELPER: AUDIT LOG ─────────────────────────────────────────────────────────

def log_actions(df: pd.DataFrame):
    """Save a full CSV audit trail of every decision the agent made."""
    audit_path = f"logs/audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    audit_df = df[["risk_tier", "risk_score", "confidence"]].copy()
    audit_df["intervention"] = audit_df["risk_tier"].map(get_intervention)
    audit_df["timestamp"]    = datetime.now().isoformat()

    if "Customer_ID" in df.columns:
        audit_df.insert(0, "Customer_ID", df["Customer_ID"])

    audit_df.to_csv(audit_path, index=False)
    logger.info(f"✅ Audit log saved: {audit_path}")


# ── MAIN AGENT LOOP ───────────────────────────────────────────────────────────

def run():
    """
    The full autonomous agent loop.
    Called by scheduler.py every 24 hours or manually for testing.
    """

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🤖 GELDIUM AI AGENT — Starting daily run")
    logger.info(f"   {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    errors = []
    high_count = medium_count = low_count = 0

    # ── LOAD USER SETTINGS ────────────────────────────────────────────────
    # Get receiver email and name from settings.json
    # This is what the user configured in the dashboard
    settings      = load_settings()
    receiver_email = settings.get("receiver_email", "")
    receiver_name  = settings.get("receiver_name", "Collections Agent")

    # Warn if receiver not configured — agent still runs, just skips emails
    if not receiver_email:
        logger.warning(
            "No receiver email configured. "
            "Emails will be skipped. "
            "User must set their email in the dashboard settings."
        )

    # Warn if sender not configured
    if not sender_configured():
        logger.warning(
            "Sender credentials not set in .env. "
            "Emails will be skipped."
        )

    try:
        # STEP 1: Load data
        df = load_customer_data()

        # STEP 2: Score all customers
        df = score_customers(df)

        # STEP 3: Split into tiers
        high_risk   = df[df["risk_tier"] == "High"]
        medium_risk = df[df["risk_tier"] == "Medium"]
        low_risk    = df[df["risk_tier"] == "Low"]

        high_count   = len(high_risk)
        medium_count = len(medium_risk)
        low_count    = len(low_risk)

        # STEP 4: Handle HIGH risk — alert per customer with AI explanation
        logger.info(f"🔴 Processing {high_count} High-risk customers...")

        for idx, row in high_risk.iterrows():

            # Generate AI explanation for this specific customer
            explanation = generate_explanation(row, row["risk_score"])

            logger.info(
                f"   → Customer #{idx} | "
                f"Risk: {row['risk_score']:.2f} | "
                f"Confidence: {row['confidence']:.2f}"
            )

            # Send alert email if receiver is configured
            if receiver_email:
                send_high_risk_alert(
                    customer_index=idx,
                    risk_score=row["risk_score"],
                    confidence=row["confidence"],
                    intervention=get_intervention("High"),
                    explanation=explanation,
                    receiver_email=receiver_email,
                    receiver_name=receiver_name
                )

        # STEP 5: Handle MEDIUM risk — log for outreach
        logger.info(f"🟡 Logging {medium_count} Medium-risk customers for outreach...")
        for idx, row in medium_risk.iterrows():
            logger.info(
                f"   → Outreach queued: #{idx} | "
                f"Risk: {row['risk_score']:.2f}"
            )

        # STEP 6: Handle LOW risk — log only
        logger.info(f"🟢 {low_count} Low-risk customers logged.")

        # STEP 7: Save audit trail
        log_actions(df)

    except FileNotFoundError as e:
        error_msg = f"Data loading failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    except ValueError as e:
        error_msg = f"Scoring failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    # STEP 8: Send daily summary — always runs even if errors occurred
    end_time     = datetime.now()
    run_duration = str(end_time - start_time).split(".")[0]

    summary = {
        "total":    high_count + medium_count + low_count,
        "high":     high_count,
        "medium":   medium_count,
        "low":      low_count,
        "run_time": run_duration,
        "errors":   "; ".join(errors) if errors else None
    }

    if receiver_email:
        logger.info("📊 Sending daily summary report...")
        send_daily_summary(
            summary=summary,
            receiver_email=receiver_email,
            receiver_name=receiver_name
        )

    logger.info("=" * 60)
    logger.info(f"✅ Agent run complete in {run_duration}")
    logger.info("=" * 60)

    return summary


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run()
    print("\n📋 Run Summary:")
    for key, value in result.items():
        print(f"   {key}: {value}")