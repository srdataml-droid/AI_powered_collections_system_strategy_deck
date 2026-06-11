# # """
# # main.py — Geldium AI Collections System: FastAPI Backend
# # =========================================================
# # This is the API layer. It sits between the ML model and the dashboard.
# # It loads the trained model ONCE at startup, then serves predictions
# # on demand — without ever retraining.

# # HOW TO RUN LOCALLY:
# #   1. Make sure model.pkl is in the same folder as this file
# #   2. Install deps: pip install fastapi uvicorn scikit-learn pandas
# #   3. Run: uvicorn main:app --reload
# #   4. Visit: http://127.0.0.1:8000/docs  ← interactive API testing page (free!)

# # FOLDER STRUCTURE EXPECTED:
# #   ml/
# #   ├── main.py       ← this file
# #   ├── train.py      ← the training pipeline (already done)
# #   └── model.pkl     ← created when you ran train.py
# # """

# # # ── IMPORTS ──────────────────────────────────────────────────────────────────

# # # FastAPI   → the web framework. Lets us define API endpoints with simple functions
# # # HTTPException → lets us send proper error responses (like 404, 422, 500)
# # from fastapi import FastAPI, HTTPException

# # # BaseModel → from Pydantic. Lets us define exactly what shape the incoming
# # #             data must be. If the request is missing a field or has wrong type,
# # #             FastAPI automatically rejects it with a clear error message.
# # from pydantic import BaseModel, Field

# # # typing    → for type hints like Optional (field may or may not be present)
# # from typing import Optional

# # # numpy     → for array operations. The model expects numpy arrays as input.
# # import numpy as np

# # # pickle    → to load our saved model bundle from disk
# # import pickle

# # # os        → to build file paths that work on any operating system
# # import os

# # # logging   → to print structured logs (better than print() in production)
# # import logging

# # # ── LOGGING SETUP ────────────────────────────────────────────────────────────
# # # Why logging instead of print()?
# # # logging gives us timestamps, severity levels (INFO, WARNING, ERROR),
# # # and can be piped to files or monitoring tools in production.
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger(__name__)


# # # ── FILE PATHS ────────────────────────────────────────────────────────────────
# # # Always resolve paths relative to THIS file's location.
# # # This prevents "file not found" errors when running from a different directory.
# # BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
# # MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")


# # # ── LOAD MODEL AT STARTUP ────────────────────────────────────────────────────
# # # Why load here, outside any function?
# # # This code runs ONCE when the server starts — not on every request.
# # # Loading a model takes ~0.5 seconds. If we loaded it per request, every
# # # prediction would be slow. Load once, reuse thousands of times.
# # #
# # # The bundle contains:
# # #   bundle["model"]    → the trained RandomForestClassifier
# # #   bundle["scaler"]   → the fitted StandardScaler
# # #   bundle["encoder"]  → the fitted LabelEncoder (0/1/2 → High/Low/Medium)
# # #   bundle["features"] → the list of expected feature column names

# # logger.info("Loading model bundle from disk...")

# # # Case: model.pkl doesn't exist yet (train.py hasn't been run)
# # if not os.path.exists(MODEL_PATH):
# #     logger.error(f"model.pkl not found at {MODEL_PATH}")
# #     logger.error("Please run train.py first to generate the model.")
# #     raise FileNotFoundError(
# #         f"model.pkl not found. Run train.py first.\nExpected at: {MODEL_PATH}"
# #     )

# # # Load the bundle
# # try:
# #     with open(MODEL_PATH, "rb") as f:  # "rb" = read binary
# #         bundle = pickle.load(f)

# #     # Unpack the bundle into named variables for clarity
# #     model    = bundle["model"]
# #     scaler   = bundle["scaler"]
# #     encoder  = bundle["encoder"]
# #     FEATURES = bundle["features"]

# #     logger.info(f"✅ Model loaded. Features: {FEATURES}")

# # # Case: model.pkl exists but is corrupted or from an incompatible Python version
# # except Exception as e:
# #     logger.error(f"Failed to load model: {e}")
# #     raise RuntimeError(f"Could not load model.pkl: {e}")


# # # ── CREATE THE APP ────────────────────────────────────────────────────────────
# # # FastAPI() creates our application instance.
# # # Think of it as the restaurant itself — endpoints are the menu items.
# # app = FastAPI(
# #     title="Geldium AI Collections API",
# #     description="Predicts delinquency risk tier for customers and recommends interventions.",
# #     version="1.0.0"
# # )


# # # ── DATA MODELS (Request & Response Schemas) ──────────────────────────────────
# # # Pydantic BaseModel = a blueprint for what data must look like.
# # # FastAPI uses this to:
# # #   1. Validate incoming requests automatically
# # #   2. Generate documentation automatically (visible at /docs)
# # #   3. Return clear errors if required fields are missing
# # #
# # # Field(...) means the field is REQUIRED (no default).
# # # Field(default) means it's OPTIONAL with a fallback value.

# # class CustomerInput(BaseModel):
# #     """
# #     The shape of data the /predict endpoint expects to receive.
# #     Every field maps to one of the 8 features our model was trained on.
# #     """
# #     Credit_Utilization:   float = Field(...,  description="Ratio of credit used (0.0 to 1.0+). E.g. 0.85 = 85%")
# #     Missed_Payments:      int   = Field(...,  description="Number of missed payments (0–6)")
# #     Credit_Score:         float = Field(...,  description="Credit bureau score (300–850)")
# #     Debt_to_Income_Ratio: float = Field(...,  description="Debt as proportion of income (0.0–1.0+)")
# #     Income:               float = Field(...,  description="Annual income in currency units")
# #     Loan_Balance:         float = Field(...,  description="Current outstanding loan balance")
# #     Age:                  int   = Field(...,  description="Customer age in years")
# #     Account_Tenure:       int   = Field(...,  description="Years as a customer")

# #     # Example values shown in the /docs interactive page
# #     class Config:
# #         json_schema_extra = {
# #             "example": {
# #                 "Credit_Utilization": 0.85,
# #                 "Missed_Payments": 2,
# #                 "Credit_Score": 480.0,
# #                 "Debt_to_Income_Ratio": 0.6,
# #                 "Income": 45000.0,
# #                 "Loan_Balance": 12000.0,
# #                 "Age": 34,
# #                 "Account_Tenure": 3
# #             }
# #         }


# # class PredictionResponse(BaseModel):
# #     """
# #     The shape of data the /predict endpoint sends BACK.
# #     """
# #     risk_tier:      str   # "High", "Medium", or "Low"
# #     intervention:   str   # what action to take
# #     confidence:     float # how confident the model is (0.0 – 1.0)
# #     risk_score:     float # probability of being in the predicted tier


# # # ── HELPER: MAP TIER TO INTERVENTION ─────────────────────────────────────────
# # # This function translates a model prediction into a human-readable
# # # business action. This is the "so what?" layer — pure business logic.

# # def get_intervention(tier: str) -> str:
# #     interventions = {
# #         "High":   "🔴 Escalate to human agent — offer personalised hardship plan or account review immediately.",
# #         "Medium": "🟡 Proactive outreach — send repayment plan offer and financial counselling invitation.",
# #         "Low":    "🟢 Automated reminder — send standard payment reminder via SMS or email."
# #     }
# #     # .get() with a fallback prevents a KeyError if tier is unexpected
# #     return interventions.get(tier, "⚪ Unknown tier — manual review recommended.")


# # # ── ENDPOINTS ─────────────────────────────────────────────────────────────────

# # # ENDPOINT 1: Health Check
# # # GET /  → just confirms the API is running
# # # Used by: monitoring tools, cloud platforms, your dashboard's startup check
# # @app.get("/", summary="Health Check")
# # def root():
# #     return {
# #         "status": "ok",
# #         "message": "Geldium AI Collections API is running.",
# #         "model_features": FEATURES
# #     }


# # # ENDPOINT 2: Predict Risk Tier
# # # POST /predict  → receives customer data, returns risk tier + intervention
# # #
# # # How it works step by step:
# # #   1. FastAPI receives the JSON body and validates it against CustomerInput
# # #   2. We convert the validated data into a numpy array (what the model needs)
# # #   3. We scale the array using the saved scaler
# # #   4. The model predicts the risk tier (as an integer: 0, 1, or 2)
# # #   5. We decode the integer back to "High"/"Low"/"Medium" using the encoder
# # #   6. We look up the intervention recommendation
# # #   7. We return a clean JSON response

# # @app.post("/predict", response_model=PredictionResponse, summary="Predict Customer Risk Tier")
# # def predict(customer: CustomerInput):
# #     """
# #     Send a single customer's data → receive their risk tier and recommended action.
# #     """

# #     try:
# #         # STEP 1: Build input array in the EXACT feature order the model expects
# #         # The order matters — scaler and model were fitted in this exact order
# #         input_data = np.array([[
# #             customer.Credit_Utilization,
# #             customer.Missed_Payments,
# #             customer.Credit_Score,
# #             customer.Debt_to_Income_Ratio,
# #             customer.Income,
# #             customer.Loan_Balance,
# #             customer.Age,
# #             customer.Account_Tenure
# #         ]])
# #         # Shape is now (1, 8) — one customer, eight features

# #         # STEP 2: Scale the input the same way training data was scaled
# #         # CRITICAL: Must use the SAME scaler that was fitted during training.
# #         #           Using a fresh scaler would produce wrong predictions.
# #         input_scaled = scaler.transform(input_data)

# #         # STEP 3: Get the model's prediction (returns an integer: 0, 1, or 2)
# #         prediction_encoded = model.predict(input_scaled)[0]
# #         # [0] because predict() returns an array — we take the first (only) element

# #         # STEP 4: Get probability scores for all three classes
# #         # predict_proba() returns [[prob_High, prob_Low, prob_Medium]]
# #         probabilities = model.predict_proba(input_scaled)[0]

# #         # Confidence = the probability of the predicted class
# #         confidence  = float(probabilities[prediction_encoded])

# #         # Risk score = probability of being High risk specifically
# #         # encoder.classes_ = ['High', 'Low', 'Medium'] → High is index 0
# #         high_index  = list(encoder.classes_).index("High")
# #         risk_score  = float(probabilities[high_index])

# #         # STEP 5: Decode integer back to string label
# #         risk_tier = encoder.inverse_transform([prediction_encoded])[0]

# #         # STEP 6: Look up the intervention recommendation
# #         intervention = get_intervention(risk_tier)

# #         # STEP 7: Log the prediction for monitoring/audit trail
# #         logger.info(
# #             f"Prediction: {risk_tier} | Confidence: {confidence:.2f} | "
# #             f"High-risk score: {risk_score:.2f}"
# #         )

# #         # STEP 8: Return the response
# #         return PredictionResponse(
# #             risk_tier=risk_tier,
# #             intervention=intervention,
# #             confidence=round(confidence, 4),
# #             risk_score=round(risk_score, 4)
# #         )

# #     # Case: input data has something unexpected (wrong shape, bad values)
# #     except ValueError as e:
# #         logger.warning(f"Invalid input data: {e}")
# #         raise HTTPException(
# #             status_code=422,  # 422 = Unprocessable Entity (standard for bad input)
# #             detail=f"Invalid input data: {str(e)}"
# #         )

# #     # Case: anything else goes wrong (model internals, numpy error, etc.)
# #     except Exception as e:
# #         logger.error(f"Prediction failed: {e}")
# #         raise HTTPException(
# #             status_code=500,  # 500 = Internal Server Error
# #             detail=f"Prediction failed unexpectedly. Check server logs. Error: {str(e)}"
# #         )


# # # ENDPOINT 3: Batch Predict (multiple customers at once)
# # # POST /predict/batch → receives a list of customers, returns a list of predictions
# # # Why: the dashboard will upload a CSV with hundreds of customers at once.
# # #      Calling /predict 500 times would be slow. Batch is one call for all.

# # class BatchInput(BaseModel):
# #     customers: list[CustomerInput]

# # class BatchResponse(BaseModel):
# #     total:       int
# #     predictions: list[dict]

# # @app.post("/predict/batch", response_model=BatchResponse, summary="Predict Risk for Multiple Customers")
# # def predict_batch(batch: BatchInput):
# #     """
# #     Send a list of customers → receive risk tiers for all of them at once.
# #     """

# #     # Case: empty list sent
# #     if not batch.customers:
# #         raise HTTPException(
# #             status_code=400,  # 400 = Bad Request
# #             detail="No customers provided. Send at least one customer in the list."
# #         )

# #     # Case: too many customers at once (protects the server from overload)
# #     if len(batch.customers) > 1000:
# #         raise HTTPException(
# #             status_code=400,
# #             detail="Batch size exceeds limit of 1000 customers per request."
# #         )

# #     try:
# #         # Build a 2D array: one row per customer, 8 columns (features)
# #         input_matrix = np.array([
# #             [
# #                 c.Credit_Utilization,
# #                 c.Missed_Payments,
# #                 c.Credit_Score,
# #                 c.Debt_to_Income_Ratio,
# #                 c.Income,
# #                 c.Loan_Balance,
# #                 c.Age,
# #                 c.Account_Tenure
# #             ]
# #             for c in batch.customers
# #         ])
# #         # Shape: (N, 8) where N = number of customers

# #         # Scale all rows at once (much faster than one by one)
# #         input_scaled = scaler.transform(input_matrix)

# #         # Predict all at once
# #         predictions_encoded = model.predict(input_scaled)
# #         probabilities_all   = model.predict_proba(input_scaled)

# #         high_index = list(encoder.classes_).index("High")

# #         # Build results list
# #         results = []
# #         for i, pred_enc in enumerate(predictions_encoded):
# #             tier         = encoder.inverse_transform([pred_enc])[0]
# #             confidence   = float(probabilities_all[i][pred_enc])
# #             risk_score   = float(probabilities_all[i][high_index])
# #             intervention = get_intervention(tier)

# #             results.append({
# #                 "customer_index": i,
# #                 "risk_tier":      tier,
# #                 "intervention":   intervention,
# #                 "confidence":     round(confidence, 4),
# #                 "risk_score":     round(risk_score, 4)
# #             })

# #         logger.info(f"Batch prediction: {len(results)} customers processed.")

# #         return BatchResponse(total=len(results), predictions=results)

# #     except ValueError as e:
# #         logger.warning(f"Batch input error: {e}")
# #         raise HTTPException(status_code=422, detail=f"Invalid batch input: {str(e)}")

# #     except Exception as e:
# #         logger.error(f"Batch prediction failed: {e}")
# #         raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

# """
# main.py — Geldium AI Collections System: FastAPI Backend
# =========================================================
# This is the API layer. It sits between the ML model and the dashboard.
# It loads the trained model ONCE at startup, then serves predictions
# on demand — without ever retraining.

# HOW TO RUN LOCALLY:
#   1. Make sure model.pkl is in the same folder as this file
#   2. Install deps: pip install fastapi uvicorn scikit-learn pandas
#   3. Run: uvicorn main:app --reload
#   4. Visit: http://127.0.0.1:8000/docs  ← interactive API testing page (free!)

# FOLDER STRUCTURE EXPECTED:
#   ml/
#   ├── main.py       ← this file
#   ├── train.py      ← the training pipeline (already done)
#   └── model.pkl     ← created when you ran train.py
# """

# # ── IMPORTS ──────────────────────────────────────────────────────────────────

# # FastAPI   → the web framework. Lets us define API endpoints with simple functions
# # HTTPException → lets us send proper error responses (like 404, 422, 500)
# import google.generativeai as genai
# import os

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# gemini = genai.GenerativeModel("gemini-pro")

# from fastapi import FastAPI, HTTPException

# # BaseModel → from Pydantic. Lets us define exactly what shape the incoming
# #             data must be. If the request is missing a field or has wrong type,
# #             FastAPI automatically rejects it with a clear error message.
# from pydantic import BaseModel, Field

# # typing    → for type hints like Optional (field may or may not be present)
# from typing import Optional

# # numpy     → for array operations. The model expects numpy arrays as input.
# import numpy as np

# # pickle    → to load our saved model bundle from disk
# import pickle

# # os        → to build file paths that work on any operating system
# import os

# # logging   → to print structured logs (better than print() in production)
# import logging
# import pandas as pd
# df = pd.read_excel("data.xlsx")
# @app.get("/customer/{customer_id}")
# def get_customer_prediction(customer_id: str):
#     # Look up customer in dataset
#     customer_row = df[df["Customer_ID"] == customer_id]
    
#     if customer_row.empty:
#         raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    
#     row = customer_row.iloc[0]
    
#     # Build input and predict
#     customer = CustomerInput(
#         Customer_ID=customer_id,
#         Credit_Utilization=row["Credit_Utilization"],
#         Missed_Payments=row["Missed_Payments"],
#         Credit_Score=row["Credit_Score"],
#         Debt_to_Income_Ratio=row["Debt_to_Income_Ratio"],
#         Income=row["Income"],
#         Loan_Balance=row["Loan_Balance"],
#         Age=row["Age"],
#         Account_Tenure=row["Account_Tenure"]
#     )
    
#     return predict(customer)
# # ── LOGGING SETUP ────────────────────────────────────────────────────────────
# # Why logging instead of print()?
# # logging gives us timestamps, severity levels (INFO, WARNING, ERROR),
# # and can be piped to files or monitoring tools in production.
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# # ── FILE PATHS ────────────────────────────────────────────────────────────────
# # Always resolve paths relative to THIS file's location.
# # This prevents "file not found" errors when running from a different directory.
# BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
# MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")


# # ── LOAD MODEL AT STARTUP ────────────────────────────────────────────────────
# # Why load here, outside any function?
# # This code runs ONCE when the server starts — not on every request.
# # Loading a model takes ~0.5 seconds. If we loaded it per request, every
# # prediction would be slow. Load once, reuse thousands of times.
# #
# # The bundle contains:
# #   bundle["model"]    → the trained RandomForestClassifier
# #   bundle["scaler"]   → the fitted StandardScaler
# #   bundle["encoder"]  → the fitted LabelEncoder (0/1/2 → High/Low/Medium)
# #   bundle["features"] → the list of expected feature column names

# logger.info("Loading model bundle from disk...")

# # Case: model.pkl doesn't exist yet (train.py hasn't been run)
# if not os.path.exists(MODEL_PATH):
#     logger.error(f"model.pkl not found at {MODEL_PATH}")
#     logger.error("Please run train.py first to generate the model.")
#     raise FileNotFoundError(
#         f"model.pkl not found. Run train.py first.\nExpected at: {MODEL_PATH}"
#     )

# # Load the bundle
# try:
#     with open(MODEL_PATH, "rb") as f:  # "rb" = read binary
#         bundle = pickle.load(f)

#     # Unpack the bundle into named variables for clarity
#     model    = bundle["model"]
#     scaler   = bundle["scaler"]
#     encoder  = bundle["encoder"]
#     FEATURES = bundle["features"]

#     logger.info(f"✅ Model loaded. Features: {FEATURES}")

# # Case: model.pkl exists but is corrupted or from an incompatible Python version
# except Exception as e:
#     logger.error(f"Failed to load model: {e}")
#     raise RuntimeError(f"Could not load model.pkl: {e}")


# # ── CREATE THE APP ────────────────────────────────────────────────────────────
# # FastAPI() creates our application instance.
# # Think of it as the restaurant itself — endpoints are the menu items.
# app = FastAPI(
#     title="Geldium AI Collections API",
#     description="Predicts delinquency risk tier for customers and recommends interventions.",
#     version="1.0.0"
# )


# # ── DATA MODELS (Request & Response Schemas) ──────────────────────────────────
# # Pydantic BaseModel = a blueprint for what data must look like.
# # FastAPI uses this to:
# #   1. Validate incoming requests automatically
# #   2. Generate documentation automatically (visible at /docs)
# #   3. Return clear errors if required fields are missing
# #
# # Field(...) means the field is REQUIRED (no default).
# # Field(default) means it's OPTIONAL with a fallback value.

# class CustomerInput(BaseModel):
#     """
#     The shape of data the /predict endpoint expects to receive.
#     Every field maps to one of the 8 features our model was trained on.
#     """
#     Credit_Utilization:   float = Field(...,  description="Ratio of credit used (0.0 to 1.0+). E.g. 0.85 = 85%")
#     Missed_Payments:      int   = Field(...,  description="Number of missed payments (0–6)")
#     Credit_Score:         float = Field(...,  description="Credit bureau score (300–850)")
#     Debt_to_Income_Ratio: float = Field(...,  description="Debt as proportion of income (0.0–1.0+)")
#     Income:               float = Field(...,  description="Annual income in currency units")
#     Loan_Balance:         float = Field(...,  description="Current outstanding loan balance")
#     Age:                  int   = Field(...,  description="Customer age in years")
#     Account_Tenure:       int   = Field(...,  description="Years as a customer")

#     # Example values shown in the /docs interactive page
#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "Credit_Utilization": 0.85,
#                 "Missed_Payments": 2,
#                 "Credit_Score": 480.0,
#                 "Debt_to_Income_Ratio": 0.6,
#                 "Income": 45000.0,
#                 "Loan_Balance": 12000.0,
#                 "Age": 34,
#                 "Account_Tenure": 3
#             }
#         }


# class PredictionResponse(BaseModel):
#     """
#     The shape of data the /predict endpoint sends BACK.
#     """
#     risk_tier:      str   # "High", "Medium", or "Low"
#     intervention:   str   # what action to take
#     confidence:     float # how confident the model is (0.0 – 1.0)
#     risk_score:     float # probability of being in the predicted tier
#     explanation:    str = ""


# # ── HELPER: MAP TIER TO INTERVENTION ─────────────────────────────────────────
# # This function translates a model prediction into a human-readable
# # business action. This is the "so what?" layer — pure business logic.

# def get_intervention(tier: str) -> str:
#     interventions = {
#         "High":   "🔴 Escalate to human agent — offer personalised hardship plan or account review immediately.",
#         "Medium": "🟡 Proactive outreach — send repayment plan offer and financial counselling invitation.",
#         "Low":    "🟢 Automated reminder — send standard payment reminder via SMS or email."
#     }
#     # .get() with a fallback prevents a KeyError if tier is unexpected
#     return interventions.get(tier, "⚪ Unknown tier — manual review recommended.")


# # ── ENDPOINTS ─────────────────────────────────────────────────────────────────

# # ENDPOINT 1: Health Check
# # GET /  → just confirms the API is running
# # Used by: monitoring tools, cloud platforms, your dashboard's startup check
# @app.get("/", summary="Health Check")
# def root():
#     return {
#         "status": "ok",
#         "message": "Geldium AI Collections API is running.",
#         "model_features": FEATURES
#     }


# # ENDPOINT 2: Predict Risk Tier
# # POST /predict  → receives customer data, returns risk tier + intervention
# #
# # How it works step by step:
# #   1. FastAPI receives the JSON body and validates it against CustomerInput
# #   2. We convert the validated data into a numpy array (what the model needs)
# #   3. We scale the array using the saved scaler
# #   4. The model predicts the risk tier (as an integer: 0, 1, or 2)
# #   5. We decode the integer back to "High"/"Low"/"Medium" using the encoder
# #   6. We look up the intervention recommendation
# #   7. We return a clean JSON response

# @app.post("/predict", response_model=PredictionResponse, summary="Predict Customer Risk Tier")
# def get_gemini_explanation(customer, risk_tier, risk_score):
#     prompt = f"""
#     A customer has been assessed by our credit risk model.
    
#     Customer Data:
#     - Credit Utilization: {customer.Credit_Utilization}
#     - Missed Payments: {customer.Missed_Payments}
#     - Credit Score: {customer.Credit_Score}
#     - Debt to Income Ratio: {customer.Debt_to_Income_Ratio}
#     - Income: {customer.Income}
#     - Loan Balance: {customer.Loan_Balance}
#     - Age: {customer.Age}
#     - Account Tenure: {customer.Account_Tenure}
    
#     Risk Tier: {risk_tier}
#     Risk Score: {risk_score}
    
#     In 2 sentences explain why this customer is {risk_tier} risk
#     and what action should be taken.
#     """
#     try:
#         response = gemini.generate_content(prompt)
#         return response.text
#     except Exception as e:
#         logger.warning(f"Gemini explanation failed: {e}")
#         return "AI explanation unavailable."
# def predict(customer: CustomerInput):
#     """
#     Send a single customer's data → receive their risk tier and recommended action.
#     """

#     try:
#         # STEP 1: Build input array in the EXACT feature order the model expects
#         # The order matters — scaler and model were fitted in this exact order
#         input_data = np.array([[
#             customer.Credit_Utilization,
#             customer.Missed_Payments,
#             customer.Credit_Score,
#             customer.Debt_to_Income_Ratio,
#             customer.Income,
#             customer.Loan_Balance,
#             customer.Age,
#             customer.Account_Tenure
#         ]])
#         # Shape is now (1, 8) — one customer, eight features

#         # STEP 2: Scale the input the same way training data was scaled
#         # CRITICAL: Must use the SAME scaler that was fitted during training.
#         #           Using a fresh scaler would produce wrong predictions.
#         input_scaled = scaler.transform(input_data)

#         # STEP 3: Get the model's prediction (returns an integer: 0, 1, or 2)
#         prediction_encoded = model.predict(input_scaled)[0]
#         # [0] because predict() returns an array — we take the first (only) element

#         # STEP 4: Get probability scores for all three classes
#         # predict_proba() returns [[prob_High, prob_Low, prob_Medium]]
#         probabilities = model.predict_proba(input_scaled)[0]

#         # Confidence = the probability of the predicted class
#         confidence  = float(probabilities[prediction_encoded])

#         # Risk score = probability of being High risk specifically
#         # encoder.classes_ = ['High', 'Low', 'Medium'] → High is index 0
#         high_index  = list(encoder.classes_).index("High")
#         risk_score  = float(probabilities[high_index])

#         # STEP 5: Decode integer back to string label
#         risk_tier = encoder.inverse_transform([prediction_encoded])[0]

#         # STEP 6: Look up the intervention recommendation
#         intervention = get_intervention(risk_tier)

#         # STEP 7: Log the prediction for monitoring/audit trail
#         logger.info(
#             f"Prediction: {risk_tier} | Confidence: {confidence:.2f} | "
#             f"High-risk score: {risk_score:.2f}"
#         )

#         # STEP 8: Return the response
#         # return PredictionResponse(
#         #     risk_tier=risk_tier,
#         #     intervention=intervention,
#         #     confidence=round(confidence, 4),
#         #     risk_score=round(risk_score, 4)
#         # )

#         # STEP 8: Get Gemini explanation
#         explanation = get_gemini_explanation(customer, risk_tier, risk_score)

#         # STEP 9: Return the response
#         return PredictionResponse(
#             risk_tier=risk_tier,
#             intervention=intervention,
#             confidence=round(confidence, 4),
#             risk_score=round(risk_score, 4),
#             explanation=explanation
#         )

#     # Case: input data has something unexpected (wrong shape, bad values)
#     except ValueError as e:
#         logger.warning(f"Invalid input data: {e}")
#         raise HTTPException(
#             status_code=422,  # 422 = Unprocessable Entity (standard for bad input)
#             detail=f"Invalid input data: {str(e)}"
#         )

#     # Case: anything else goes wrong (model internals, numpy error, etc.)
#     except Exception as e:
#         logger.error(f"Prediction failed: {e}")
#         raise HTTPException(
#             status_code=500,  # 500 = Internal Server Error
#             detail=f"Prediction failed unexpectedly. Check server logs. Error: {str(e)}"
#         )


# # ENDPOINT 3: Batch Predict (multiple customers at once)
# # POST /predict/batch → receives a list of customers, returns a list of predictions
# # Why: the dashboard will upload a CSV with hundreds of customers at once.
# #      Calling /predict 500 times would be slow. Batch is one call for all.

# class BatchInput(BaseModel):
#     customers: list[CustomerInput]

# class BatchResponse(BaseModel):
#     total:       int
#     predictions: list[dict]

# @app.post("/predict/batch", response_model=BatchResponse, summary="Predict Risk for Multiple Customers")
# def predict_batch(batch: BatchInput):
#     """
#     Send a list of customers → receive risk tiers for all of them at once.
#     """

#     # Case: empty list sent
#     if not batch.customers:
#         raise HTTPException(
#             status_code=400,  # 400 = Bad Request
#             detail="No customers provided. Send at least one customer in the list."
#         )

#     # Case: too many customers at once (protects the server from overload)
#     if len(batch.customers) > 1000:
#         raise HTTPException(
#             status_code=400,
#             detail="Batch size exceeds limit of 1000 customers per request."
#         )

#     try:
#         # Build a 2D array: one row per customer, 8 columns (features)
#         input_matrix = np.array([
#             [
#                 c.Credit_Utilization,
#                 c.Missed_Payments,
#                 c.Credit_Score,
#                 c.Debt_to_Income_Ratio,
#                 c.Income,
#                 c.Loan_Balance,
#                 c.Age,
#                 c.Account_Tenure
#             ]
#             for c in batch.customers
#         ])
#         # Shape: (N, 8) where N = number of customers

#         # Scale all rows at once (much faster than one by one)
#         input_scaled = scaler.transform(input_matrix)

#         # Predict all at once
#         predictions_encoded = model.predict(input_scaled)
#         probabilities_all   = model.predict_proba(input_scaled)

#         high_index = list(encoder.classes_).index("High")

#         # Build results list
#         results = []
#         for i, pred_enc in enumerate(predictions_encoded):
#             tier         = encoder.inverse_transform([pred_enc])[0]
#             confidence   = float(probabilities_all[i][pred_enc])
#             risk_score   = float(probabilities_all[i][high_index])
#             intervention = get_intervention(tier)

#             results.append({
#                 "customer_index": i,
#                 "risk_tier":      tier,
#                 "intervention":   intervention,
#                 "confidence":     round(confidence, 4),
#                 "risk_score":     round(risk_score, 4)
#             })

#         logger.info(f"Batch prediction: {len(results)} customers processed.")

#         return BatchResponse(total=len(results), predictions=results)

#     except ValueError as e:
#         logger.warning(f"Batch input error: {e}")
#         raise HTTPException(status_code=422, detail=f"Invalid batch input: {str(e)}")

#     except Exception as e:
#         logger.error(f"Batch prediction failed: {e}")
#         raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


# # ── SETTINGS ENDPOINTS ────────────────────────────────────────────────────────
# # These are used by the HTML frontend settings page.
# # GET /settings  → load current receiver settings
# # POST /settings → save new receiver settings

# from settings import load_settings, save_settings, sender_configured
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse

# class SettingsInput(BaseModel):
#     receiver_name:  str = ""
#     receiver_email: str = ""

# @app.get("/settings", summary="Load user settings")
# def get_settings():
#     """Return current settings plus sender configured status."""
#     data = load_settings()
#     data["sender_configured"] = sender_configured()
#     return data

# @app.post("/settings", summary="Save user settings")
# def post_settings(body: SettingsInput):
#     """Save receiver email and name to settings.json."""
#     settings = {
#         "receiver_name":  body.receiver_name,
#         "receiver_email": body.receiver_email
#     }
#     success = save_settings(settings)
#     if not success:
#         raise HTTPException(status_code=500, detail="Could not save settings.")
#     return {"status": "saved", **settings}

# # Serve the HTML frontend at root
# # Place index.html in the same folder as main.py
# @app.get("/app", summary="Serve frontend dashboard")
# def serve_frontend():
#     """Serve the HTML dashboard."""
#     html_path = os.path.join(BASE_DIR, "index.html")
#     if not os.path.exists(html_path):
#         raise HTTPException(status_code=404, detail="index.html not found.")
#     return FileResponse(html_path)
"""
main.py — Geldium AI Collections System: FastAPI Backend
=========================================================
Loads the trained model once at startup, serves predictions on demand.

HOW TO RUN LOCALLY:
  uvicorn main:app --reload
  Visit: http://127.0.0.1:8000/docs
"""

# ── IMPORTS ──────────────────────────────────────────────────────────────────
# All imports go at the very top — nothing else runs before this

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from google import genai          # NEW Gemini package — replaces google.generativeai
import numpy as np
import pickle
import os
import logging
import pandas as pd


# ── LOGGING SETUP ─────────────────────────────────────────────────────────────
# Timestamps + severity levels on every log line
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── FILE PATHS ────────────────────────────────────────────────────────────────
# Resolve paths relative to this file so it works on any machine/cloud
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
DATA_PATH  = os.path.join(BASE_DIR, "data.xlsx")

# ── GEMINI SETUP ──────────────────────────────────────────────────────────────
# Initialise Gemini client once at startup — not on every request
# API key comes from Railway environment variables (never hardcoded)
# gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# ── GEMINI SETUP ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# TEMPORARY DEBUG — remove after fixing
logger.info(f"GEMINI_API_KEY loaded: {'YES' if GEMINI_API_KEY else 'NO — KEY IS MISSING'}")

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ── LOAD MODEL AT STARTUP ─────────────────────────────────────────────────────
# Runs once when server starts — not on every request
# bundle contains: model, scaler, encoder, features
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

# ── LOAD DATASET ──────────────────────────────────────────────────────────────
# Used by /customer/{customer_id} endpoint to look up customers by ID
# Loaded once at startup for speed
try:
    df = pd.read_excel(DATA_PATH)
    logger.info(f"✅ Dataset loaded. {len(df)} customers.")
except Exception as e:
    logger.warning(f"Could not load data.xlsx: {e}")
    df = None

# ── CREATE THE APP ────────────────────────────────────────────────────────────
# app = FastAPI() MUST come before any @app.get / @app.post decorators
app = FastAPI(
    title="Geldium AI Collections API",
    description="Predicts delinquency risk tier and recommends interventions.",
    version="1.0.0"
)

# ── DATA MODELS ───────────────────────────────────────────────────────────────

class CustomerInput(BaseModel):
    """What /predict expects to RECEIVE — 8 financial features."""
    Customer_ID:          str   = Field(...,  description="Customer ID e.g. CUST0001")
    Credit_Utilization:   float = Field(...,  description="Ratio of credit used (0.0–1.0+)")
    Missed_Payments:      int   = Field(...,  description="Number of missed payments (0–6)")
    Credit_Score:         float = Field(...,  description="Credit bureau score (300–850)")
    Debt_to_Income_Ratio: float = Field(...,  description="Debt as proportion of income")
    Income:               float = Field(...,  description="Annual income in currency units")
    Loan_Balance:         float = Field(...,  description="Current outstanding loan balance")
    Age:                  int   = Field(...,  description="Customer age in years")
    Account_Tenure:       int   = Field(...,  description="Years as a customer")

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
    """What /predict sends BACK — model outputs only."""
    Customer_ID:  str
    risk_tier:    str    # "High", "Medium", or "Low"
    intervention: str    # recommended business action
    confidence:   float  # how confident the model is (0.0–1.0)
    risk_score:   float  # probability of being High risk
    explanation:  str    # Gemini AI explanation

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
    """Translate risk tier into a human-readable business action."""
    interventions = {
        "High":   "🔴 Escalate to human agent — offer personalised hardship plan immediately.",
        "Medium": "🟡 Proactive outreach — send repayment plan offer and counselling invitation.",
        "Low":    "🟢 Automated reminder — send standard payment reminder via SMS or email."
    }
    return interventions.get(tier, "⚪ Unknown tier — manual review recommended.")


def get_gemini_explanation(customer: CustomerInput, risk_tier: str, risk_score: float) -> str:
    # """
    # Ask Gemini to explain in plain English why this customer got this risk tier.
    # Falls back to a safe message if Gemini is unavailable.
    # """
    if gemini_client is None:
        return "AI explanation unavailable — Gemini key not configured."
    prompt = f"""
    A customer has been assessed by our credit risk model.

    Customer Data:
    - Credit Utilization:   {customer.Credit_Utilization}
    - Missed Payments:      {customer.Missed_Payments}
    - Credit Score:         {customer.Credit_Score}
    - Debt to Income Ratio: {customer.Debt_to_Income_Ratio}
    - Income:               {customer.Income}
    - Loan Balance:         {customer.Loan_Balance}
    - Age:                  {customer.Age}
    - Account Tenure:       {customer.Account_Tenure}

    Risk Tier: {risk_tier}
    Risk Score: {risk_score}

    In 2 sentences, explain why this customer is {risk_tier} risk
    and what action the collections team should take.
    """
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.warning(f"Gemini explanation failed: {e}")
        return "AI explanation unavailable."


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

# ENDPOINT 1: Health Check
@app.get("/", summary="Health Check")
def root():
    return {
        "status": "ok",
        "message": "Geldium AI Collections API is running.",
        "model_features": FEATURES
    }


# ENDPOINT 2: Single Predict
# Receives customer data → returns risk tier + Gemini explanation
@app.post("/predict", response_model=PredictionResponse, summary="Predict Customer Risk Tier")
def predict(customer: CustomerInput):
    """Send one customer's data → get risk tier and recommended action."""
    try:
        # Build input array in exact feature order model was trained on
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

        # Scale using the same scaler fitted during training
        input_scaled = scaler.transform(input_data)

        # Get prediction (returns integer: 0, 1, or 2)
        prediction_encoded = model.predict(input_scaled)[0]

        # Get probability scores for all three classes
        probabilities = model.predict_proba(input_scaled)[0]

        # Confidence = probability of the predicted class
        confidence = float(probabilities[prediction_encoded])

        # Risk score = probability of being High risk specifically
        high_index = list(encoder.classes_).index("High")
        risk_score = float(probabilities[high_index])

        # Decode integer back to string label (High/Medium/Low)
        risk_tier = encoder.inverse_transform([prediction_encoded])[0]

        # Get business action recommendation
        intervention = get_intervention(risk_tier)

        # Get Gemini AI explanation
        explanation = get_gemini_explanation(customer, risk_tier, risk_score)

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


# ENDPOINT 3: Customer Lookup by ID
# GET /customer/CUST0001 → looks up customer in data.xlsx → runs prediction
# No manual data entry needed — just the customer ID
@app.get("/customer/{customer_id}", summary="Predict by Customer ID")
def get_customer_prediction(customer_id: str):
    """Look up a customer by ID and run prediction automatically."""
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset not loaded.")

    customer_row = df[df["Customer_ID"] == customer_id]

    if customer_row.empty:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")

    row = customer_row.iloc[0]

    # Build CustomerInput from the dataset row
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

    # Reuse the predict function — no code duplication
    return predict(customer)


# ENDPOINT 4: Batch Predict
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

        input_scaled        = scaler.transform(input_matrix)
        predictions_encoded = model.predict(input_scaled)
        probabilities_all   = model.predict_proba(input_scaled)
        high_index          = list(encoder.classes_).index("High")

        results = []
        for i, pred_enc in enumerate(predictions_encoded):
            tier         = encoder.inverse_transform([pred_enc])[0]
            confidence   = float(probabilities_all[i][pred_enc])
            risk_score   = float(probabilities_all[i][high_index])
            intervention = get_intervention(tier)

            results.append({
                "Customer_ID":    batch.customers[i].Customer_ID,
                "customer_index": i,
                "risk_tier":      tier,
                "intervention":   intervention,
                "confidence":     round(confidence, 4),
                "risk_score":     round(risk_score, 4)
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
        "receiver_name":  body.receiver_name,
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