"""
app.py — Geldium AI Collections System: Streamlit Dashboard
============================================================
This is the frontend. It talks to the FastAPI backend (main.py)
and displays results in a clean web interface.

HOW TO RUN:
  1. Make sure your FastAPI server is running:
       python -m uvicorn main:app --reload
  2. In a SEPARATE terminal, run this dashboard:
       streamlit run app.py
  3. Your browser opens automatically at http://localhost:8501

FOLDER STRUCTURE:
  ml/
  ├── train.py     ✅ done
  ├── main.py      ✅ done (FastAPI)
  ├── model.pkl    ✅ done
  └── app.py       ← this file
"""

# ── IMPORTS ──────────────────────────────────────────────────────────────────

# streamlit → the web framework. Every st.something() call renders something
#             on the page: titles, buttons, inputs, tables, charts, etc.
import streamlit as st

# requests  → lets Python send HTTP requests (like a browser would)
#             We use it to call our FastAPI endpoints
import requests

# pandas    → for reading uploaded CSV files and displaying tables
import pandas as pd

# io        → for converting data to downloadable files in memory
#             (so users can download results without saving to disk)
import io

# json      → for formatting error messages nicely
import json


# ── CONFIG ───────────────────────────────────────────────────────────────────
# The URL of your running FastAPI server.
# Locally this is always http://localhost:8000
# When deployed to cloud, you'll change this to your Render/Railway URL.
# API_URL = "https://geldium-api-3nnf.onrender.com"
API_URL = "https://geldium-api-production.up.railway.app"

# Streamlit page config — must be the FIRST streamlit call in the script
st.set_page_config(
    page_title="Geldium AI Collections",
    page_icon="🏦",
    layout="wide"           # "wide" uses the full browser width
)


# ── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def check_api_health() -> bool:
    """
    Ping the API's health check endpoint.
    Returns True if the API is reachable, False if not.
    Used on every page load so we can warn the user early
    instead of letting them fill a form and then get a confusing error.
    """
    try:
        # GET request to the root endpoint — should return {"status": "ok"}
        response = requests.get(f"{API_URL}/", timeout=3)
        # status_code 200 means "OK" — the server responded successfully
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        # API server isn't running at all
        return False
    except requests.exceptions.Timeout:
        # API is too slow to respond (maybe overloaded or crashed)
        return False


def predict_single(data: dict) -> dict:
    """
    Send one customer's data to POST /predict.
    Returns the full prediction response as a Python dict.
    Raises an exception with a clear message if anything goes wrong.
    """
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=data,      # automatically serialises dict to JSON
            timeout=10      # wait up to 10 seconds for a response
        )

        # If status code is not 2xx, raise an exception
        response.raise_for_status()

        # Parse the JSON response body into a Python dict
        return response.json()

    except requests.exceptions.HTTPError as e:
        # The API returned an error (422 bad input, 500 server error, etc.)
        # Try to extract the detail message the API sent back
        try:
            detail = response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        raise ValueError(f"API Error: {detail}")

    except requests.exceptions.ConnectionError:
        raise ConnectionError("Cannot reach the API. Is FastAPI running? (python -m uvicorn main:app --reload)")

    except requests.exceptions.Timeout:
        raise TimeoutError("API took too long to respond. Try again.")


def predict_batch(customers: list) -> dict:
    """
    Send a list of customers to POST /predict/batch.
    Returns the full batch response as a Python dict.
    """
    try:
        response = requests.post(
            f"{API_URL}/predict/batch",
            json={"customers": customers},
            timeout=30      # batch can take longer — give it 30 seconds
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        try:
            detail = response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        raise ValueError(f"API Error: {detail}")

    except requests.exceptions.ConnectionError:
        raise ConnectionError("Cannot reach the API. Is FastAPI running?")

    except requests.exceptions.Timeout:
        raise TimeoutError("Batch prediction timed out. Try a smaller file.")


def tier_colour(tier: str) -> str:
    """Return an emoji colour indicator for the risk tier."""
    return {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(tier, "⚪")


# def display_prediction_card(result: dict):
#     customer_id = result.get("Customer_ID", "Unknown")
#     st.markdown(f"### Customer: `{customer_id}`")
    
#     tier       = result["risk_tier"]
#     """
#     Render a styled prediction result card.
#     Takes the dict returned by the API and displays it nicely.
#     """
#     tier       = result["risk_tier"]
#     confidence = result["confidence"]
#     risk_score = result["risk_score"]
#     action     = result["intervention"]
#     colour     = tier_colour(tier)

#     # st.metric() displays a big bold number with a label — good for KPIs
#     col1, col2, col3 = st.columns(3)
#     col1.metric("Risk Tier",   f"{colour} {tier}")
#     col2.metric("Confidence",  f"{confidence * 100:.1f}%")
#     col3.metric("High-Risk Score", f"{risk_score * 100:.1f}%")

#     # st.info / st.warning / st.error → coloured alert boxes
#     if tier == "High":
#         st.error(f"**Recommended Action:** {action}")
#     elif tier == "Medium":
#         st.warning(f"**Recommended Action:** {action}")
#     else:
#         st.success(f"**Recommended Action:** {action}")

def display_prediction_card(result: dict):
    """
    Render a styled prediction result card.
    Docstring always goes FIRST — before any code.
    """
    # Pull all values from the API response dict
    customer_id = result.get("Customer_ID", "Unknown")
    tier        = result["risk_tier"]
    confidence  = result["confidence"]
    risk_score  = result["risk_score"]
    action      = result["intervention"]
    explanation = result.get("explanation", "")  # Gemini explanation
    colour      = tier_colour(tier)

    # Show customer ID header
    st.markdown(f"### Customer: `{customer_id}`")

    # Three KPI metrics side by side
    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Tier",        f"{colour} {tier}")
    col2.metric("Confidence",       f"{confidence * 100:.1f}%")
    col3.metric("High-Risk Score",  f"{risk_score * 100:.1f}%")

    # Colour coded action box based on tier
    if tier == "High":
        st.error(f"**Recommended Action:** {action}")
    elif tier == "Medium":
        st.warning(f"**Recommended Action:** {action}")
    else:
        st.success(f"**Recommended Action:** {action}")

    # Show Gemini AI explanation if available
    if explanation and explanation != "AI explanation unavailable.":
        st.info(f"🤖 **AI Explanation:** {explanation}")
# ── SIDEBAR ───────────────────────────────────────────────────────────────────
# The sidebar stays visible on every page.
# We use it for navigation and the API status indicator.

with st.sidebar:
    st.title("🏦 Geldium AI")
    st.caption("Collections Risk System")

    st.divider()

    # Navigation — st.radio() creates a set of radio buttons
    page = st.radio(
        "Navigate",
        ["🏠 Home", "🔍 Single Predict", "📂 Batch Predict"],
        label_visibility="collapsed"   # hide the "Navigate" label
    )

    st.divider()

    # API health indicator — checked every time the page loads
    st.markdown("**API Status**")
    if check_api_health():
        st.success("✅ Connected")
    else:
        st.error("❌ Offline — start backend server first")
        st.code("backend server connecting ...", language="bash")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1: HOME
# ═════════════════════════════════════════════════════════════════════════════

if page == "🏠 Home":

    st.title("🏦 Geldium AI Collections System")
    st.markdown(
        "An autonomous, responsible AI system for predicting customer delinquency risk "
        "and recommending targeted interventions — at scale."
    )

    st.divider()

    # System overview in three columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🤖 How it works")
        st.markdown(
            "- Trained on 500 real Geldium customers\n"
            "- Uses 8 financial features\n"
            "- Random Forest model (98% accuracy)\n"
            "- 3 risk tiers: High / Medium / Low"
        )

    with col2:
        st.markdown("### ⚡ What it does")
        st.markdown(
            "- Scores each customer's delinquency risk\n"
            "- Recommends the right intervention\n"
            "- Handles single or batch predictions\n"
            "- Results downloadable as CSV"
        )

    with col3:
        st.markdown("### 🛡️ Responsible AI")
        st.markdown(
            "- Explainable predictions\n"
            "- Human oversight for High-risk cases\n"
            "- Fairness-aware design\n"
            "- ECOA / GDPR aligned"
        )

    st.divider()

    # Risk tier legend
    st.markdown("### Risk Tier Guide")

    t1, t2, t3 = st.columns(3)
    with t1:
        st.error("🔴 **HIGH RISK**\nCredit utilization > 80% + missed payments\n→ Human agent escalation")
    with t2:
        st.warning("🟡 **MEDIUM RISK**\nElevated utilization or debt burden\n→ Proactive outreach")
    with t3:
        st.success("🟢 **LOW RISK**\nStable repayment behaviour\n→ Automated reminder")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2: SINGLE CUSTOMER PREDICTION
# ═════════════════════════════════════════════════════════════════════════════

elif page == "🔍 Single Predict":

    st.title("🔍 Single Customer Risk Prediction")
    st.markdown("Enter a customer's financial details to get their risk tier and recommended action.")

    st.divider()

    # Input form — st.form() groups inputs together so the API is only
    # called when the user clicks Submit, not on every keystroke
    with st.form("single_predict_form"):

        st.markdown("#### Customer Financial Details")
        # Customer ID input
        # This links the prediction back to a real customer in your database
        # Format must match your data e.g. CUST0001
        customer_id = st.text_input(
            "Customer ID",
            value="CUST0001",
            help="Enter the customer ID exactly as it appears in your records e.g. CUST0001"
        )

        # Two columns for a cleaner layout
        col1, col2 = st.columns(2)

        with col1:
            credit_util = st.slider(
                "Credit Utilization",
                min_value=0.0, max_value=1.5, value=0.5, step=0.01,
                help="Proportion of credit limit used. 0.85 = 85% utilised."
            )
            missed_payments = st.number_input(
                "Missed Payments",
                min_value=0, max_value=10, value=0, step=1,
                help="Total number of missed payments on record."
            )
            credit_score = st.number_input(
                "Credit Score",
                min_value=300.0, max_value=850.0, value=600.0, step=1.0,
                help="Credit bureau score (300 = poor, 850 = excellent)."
            )
            debt_to_income = st.slider(
                "Debt-to-Income Ratio",
                min_value=0.0, max_value=2.0, value=0.3, step=0.01,
                help="Total debt divided by annual income. 0.5 = debt is 50% of income."
            )

        with col2:
            income = st.number_input(
                "Annual Income (£)",
                min_value=0.0, max_value=1_000_000.0, value=45000.0, step=500.0,
                help="Customer's annual income."
            )
            loan_balance = st.number_input(
                "Loan Balance (£)",
                min_value=0.0, max_value=500_000.0, value=10000.0, step=100.0,
                help="Current outstanding loan balance."
            )
            age = st.number_input(
                "Age",
                min_value=18, max_value=100, value=35, step=1
            )
            account_tenure = st.number_input(
                "Account Tenure (years)",
                min_value=0, max_value=50, value=3, step=1,
                help="How many years the customer has held their account."
            )

        # Submit button — triggers the API call
        submitted = st.form_submit_button("🔮 Predict Risk Tier", use_container_width=True)

    # Only run prediction after form is submitted
    if submitted:
        # Build the dict matching the CustomerInput schema in main.py
        customer_data = {
            "Customer_ID":          customer_id,
            "Credit_Utilization":   credit_util,
            "Missed_Payments":      int(missed_payments),
            "Credit_Score":         credit_score,
            "Debt_to_Income_Ratio": debt_to_income,
            "Income":               income,
            "Loan_Balance":         loan_balance,
            "Age":                  int(age),
            "Account_Tenure":       int(account_tenure)
        }

        # Show a spinner while the API call is in progress
        with st.spinner("Analysing customer risk..."):
            try:
                result = predict_single(customer_data)
                st.divider()
                st.markdown("### 📊 Prediction Result")
                display_prediction_card(result)

                # Show the raw JSON too — useful for developers/debugging
                with st.expander("🔧 Raw API Response (for developers)"):
                    st.json(result)

            # Display errors clearly instead of crashing
            except (ValueError, ConnectionError, TimeoutError) as e:
                st.error(f"**Prediction failed:** {e}")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3: BATCH PREDICTION (CSV UPLOAD)
# ═════════════════════════════════════════════════════════════════════════════

elif page == "📂 Batch Predict":

    st.title("📂 Batch Customer Risk Prediction")
    st.markdown("Upload a CSV file of customers and download their risk predictions.")

    st.divider()

    # Show the expected CSV format so users know exactly what to upload
    st.markdown("#### 📋 Required CSV Format")
    st.markdown("Your CSV must have these exact column names:")

    example_df = pd.DataFrame([{
        "Customer_ID":          "CUST0001",
        "Credit_Utilization":   0.85,
        "Missed_Payments":      2,
        "Credit_Score":         480.0,
        "Debt_to_Income_Ratio": 0.6,
        "Income":               45000.0,
        "Loan_Balance":         12000.0,
        "Age":                  34,
        "Account_Tenure":       3
    }])
    st.dataframe(example_df, use_container_width=True)

    # Download a template CSV so users don't have to guess the format
    template_csv = example_df.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Template CSV",
        data=template_csv,
        file_name="geldium_template.csv",
        mime="text/csv"
    )

    st.divider()

    # File uploader — accepts CSV only
    uploaded_file = st.file_uploader(
        "Upload your customer CSV",
        type=["csv"],
        help="Must match the column format shown above."
    )

    if uploaded_file is not None:

        # Read the uploaded file into a DataFrame
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            st.stop()   # stop execution for this page — don't continue

        st.markdown(f"**{len(df)} customers loaded.** Preview:")
        st.dataframe(df.head(10), use_container_width=True)

        # Validate that all required columns are present
        required_cols = [
            "Customer_ID",
            "Credit_Utilization", "Missed_Payments", "Credit_Score",
            "Debt_to_Income_Ratio", "Income", "Loan_Balance", "Age", "Account_Tenure"
        ]
        missing_cols = [c for c in required_cols if c not in df.columns]

        if missing_cols:
            # Show exactly which columns are missing
            st.error(f"Missing columns: {missing_cols}")
            st.info("Download the template above to see the correct format.")
            st.stop()

        # Run batch prediction button
        if st.button("🚀 Run Batch Prediction", use_container_width=True):

            with st.spinner(f"Predicting risk for {len(df)} customers..."):
                try:
                    # Convert DataFrame rows to list of dicts (what the API expects)
                    customers_list = df[required_cols].to_dict(orient="records")

                    result = predict_batch(customers_list)
                    predictions = result["predictions"]

                    # Build a results DataFrame
                    results_df = pd.DataFrame(predictions)

                    # Add a colour column for display
                    results_df["Tier Indicator"] = results_df["risk_tier"].map(tier_colour)

                    st.divider()
                    st.markdown(f"### ✅ Results — {result['total']} customers scored")

                    # Summary metrics
                    tier_counts = results_df["risk_tier"].value_counts()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("🔴 High Risk",   tier_counts.get("High",   0))
                    m2.metric("🟡 Medium Risk", tier_counts.get("Medium", 0))
                    m3.metric("🟢 Low Risk",    tier_counts.get("Low",    0))

                    # Full results table
                    st.dataframe(
                        results_df[["customer_index", "Tier Indicator", "risk_tier",
                                    "confidence", "risk_score", "intervention"]],
                        use_container_width=True
                    )

                    # Download results as CSV
                    # io.StringIO() creates an in-memory text file — no disk needed
                    output = io.StringIO()
                    results_df.to_csv(output, index=False)
                    csv_bytes = output.getvalue().encode("utf-8")

                    st.download_button(
                        label="⬇️ Download Results CSV",
                        data=csv_bytes,
                        file_name="geldium_predictions.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                except (ValueError, ConnectionError, TimeoutError) as e:
                    st.error(f"**Batch prediction failed:** {e}")
