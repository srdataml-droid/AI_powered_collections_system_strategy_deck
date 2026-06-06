# 🏦 Geldium AI Collections System
### From Business Problem to Live AI System — Built as Part of the Tata iQ AI Transformation Virtual Experience

---

> **"What if a bank could predict which customers are about to miss payments — before it happens — and automatically reach out to help them?"**
> 
> That's the question this project answers.

---

## 📖 The Story

### The Problem

Geldium Finance was losing money.

Not because their products were bad. Not because their customers were irresponsible. But because by the time the collections team found out a customer was in financial trouble — it was already too late.

The traditional approach looked like this:

```
Customer misses payment → Bank notices → Bank calls → Customer is already in debt spiral
```

Reactive. Slow. Expensive. And frankly, not great for the customer either.

### The Brief

As part of the **Tata iQ AI Transformation Consultant virtual experience**, I was given a fictional but realistic scenario:

> Geldium Finance needs an AI-powered collections system that can identify at-risk customers early, recommend the right intervention for each one, and do it at scale — fairly, transparently, and responsibly.

Three tasks. Three deliverables. One end-to-end AI system.

---

### Task 1 — Understand the Data

Before building anything, I had to understand what the data was telling us.

**500 Geldium customers. 18 columns. One question: who is likely to go delinquent?**

After exploratory analysis, five variables stood out as the strongest predictors:

| Variable | Why It Matters |
|----------|---------------|
| Credit Utilization | Customers using >80% of their credit limit are stretched thin |
| Missed Payments | Past behaviour is the strongest predictor of future behaviour |
| Credit Score | A low score signals accumulated financial stress |
| Debt-to-Income Ratio | High debt relative to income = less room to absorb shocks |
| Income Level | Lower income customers have less financial buffer |

**The insight:** It's not one factor that predicts delinquency — it's the combination. A customer with high utilization AND missed payments is in a fundamentally different situation than one with just high utilization alone.

---

### Task 2 — Build the Predictive Framework

Armed with those insights, the next step was turning them into a **SMART business goal:**

> *"Reduce delinquency among high-risk customers by 10% within 12 months by implementing an early-warning intervention program targeting customers whose credit utilization exceeds 80% and who have recorded at least one missed payment in the previous six months."*

This became the backbone of the entire system — a concrete, measurable target that the AI would be built to achieve.

**Three risk tiers were defined:**

```
🔴 HIGH RISK   →  Credit utilization > 80% + at least 1 missed payment
                   Action: Escalate to human agent immediately

🟡 MEDIUM RISK →  Elevated utilization OR missed payments with low credit score
                   Action: Proactive outreach + repayment plan offer

🟢 LOW RISK    →  Stable repayment behaviour
                   Action: Standard automated payment reminder
```

---

### Task 3 — Responsible AI First

Before writing a single line of model code, the ethical framework came first.

Because here's the uncomfortable truth about AI in finance: **a biased model doesn't just make wrong predictions — it can systematically harm certain groups of people.**

Two key risks were identified and addressed:

**Risk 1: Historical bias**
If past lending decisions were discriminatory, the model learns those patterns and amplifies them.
*Mitigation: Regular fairness testing across customer segments. Monitor outcomes, not just accuracy.*

**Risk 2: Stale data**
A customer's 2-year-old credit behaviour may not reflect their current situation.
*Mitigation: Human review for all high-stakes decisions. Model predictions inform — not replace — human judgment.*

The guardrails built into the system:
- ✅ Fairness monitoring across demographic segments
- ✅ Explainable predictions in plain business language
- ✅ ECOA and GDPR aligned design
- ✅ Human-in-the-loop for all High risk escalations

---

### Then I Built the Whole Thing

The brief asked for a strategy deck. I built the strategy deck — and then kept going.

```
Week 1: Data analysis + risk framework + responsible AI report
Week 2: Trained ML model (98% accuracy on held-out test data)
Week 3: FastAPI backend serving live predictions
Week 4: Streamlit dashboard — single and batch predictions
Week 5: Cloud deployed — live on the internet
```

Here's what the system looks like end to end:

```
📊 Customer Data (CSV)
         ↓
🤖 ML Model scores each customer
         ↓
⚡ FastAPI serves the prediction via REST API
         ↓
🎨 Streamlit Dashboard displays results
         ↓
🔴 High Risk   → Human agent alerted
🟡 Medium Risk → Automated outreach triggered  
🟢 Low Risk    → Standard reminder sent
```

---

## 🚀 Live Demo

| Service | Link |
|---------|------|
| 🎨 Dashboard | *[Your Streamlit URL here]* |
| ⚡ API Docs | *[Your Render URL here]/docs* |

---

## 🛠️ Technical Details

*For the developers — here's what's under the hood.*

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| ML Model | Scikit-learn RandomForestClassifier | Robust, handles mixed features, gives feature importance |
| API | FastAPI + Uvicorn | Async, fast, auto-generates OpenAPI docs |
| Dashboard | Streamlit | Python-native, rapid UI development |
| Backend Deploy | Render (free tier) | GitHub-connected, zero-config deployment |
| Frontend Deploy | Streamlit Cloud (free tier) | Native Streamlit hosting |

### Model Details

```
Algorithm:      Random Forest Classifier
Features:       8 (Credit_Utilization, Missed_Payments, Credit_Score,
                   Debt_to_Income_Ratio, Income, Loan_Balance, Age, Account_Tenure)
Target:         Risk_Tier (High / Medium / Low) — engineered via rule-based labelling
Train/Test:     80/20 split, stratified
Accuracy:       98% on held-out test set
Preprocessing:  StandardScaler (saved alongside model for inference consistency)
Serialisation:  pickle bundle (model + scaler + encoder + feature list)
```

### API Endpoints

```
GET  /              → Health check
POST /predict       → Single customer prediction
POST /predict/batch → Batch prediction (up to 1000 customers)
```

**Example request:**
```json
POST /predict
{
  "Credit_Utilization": 0.85,
  "Missed_Payments": 2,
  "Credit_Score": 480.0,
  "Debt_to_Income_Ratio": 0.6,
  "Income": 45000.0,
  "Loan_Balance": 12000.0,
  "Age": 34,
  "Account_Tenure": 3
}
```

**Example response:**
```json
{
  "risk_tier": "High",
  "intervention": "🔴 Escalate to human agent — offer personalised hardship plan or account review immediately.",
  "confidence": 0.87,
  "risk_score": 0.87
}
```

### Project Structure

```
├── train.py           # ML pipeline — load, clean, engineer, train, save
├── main.py            # FastAPI backend — load model, serve predictions
├── app.py             # Streamlit dashboard — UI, forms, batch upload
├── model.pkl          # Trained model bundle (model + scaler + encoder)
├── data.xlsx          # Geldium customer dataset (500 customers)
├── requirements.txt   # Python dependencies
└── render.yaml        # Render deployment config
```

### Running Locally

```bash
# 1. Clone the repo
git clone https://github.com/srdataml-droid/AI_powered-collections-system-strategy-deck.git
cd AI_powered-collections-system-strategy-deck

# 2. Install dependencies
pip install -r requirements.txt

# 3. Train the model (generates model.pkl)
python train.py

# 4. Start the API (Terminal 1)
python -m uvicorn main:app --reload

# 5. Start the dashboard (Terminal 2)
streamlit run app.py

# 6. Visit the dashboard
# http://localhost:8501

# 7. Visit the API docs
# http://localhost:8000/docs
```

---

## 📁 The Deliverables

| Task | Deliverable | Description |
|------|------------|-------------|
| Task 1 | Data Analysis | EDA on 500 customers, identified top 5 delinquency predictors |
| Task 2 | Predictive Framework | SMART goal, risk tier logic, intervention strategy |
| Task 3 | Responsible AI Report | Fairness risks, mitigations, compliance alignment |
| Bonus | Full Working System | Trained model + API + Dashboard + Cloud deployment |

---

## 💡 What I Learned

This project taught me that building an AI system is only 20% model training.

The other 80% is:
- Understanding the business problem deeply enough to define the right target variable
- Designing for fairness before writing model code — not as an afterthought
- Wrapping ML in infrastructure that non-ML teams can actually use
- Deploying so anyone can interact with it — not just people who can run Python

That last part matters most. An AI model that lives in a Jupyter notebook helps no one.

---

## 🙏 Acknowledgements

Built as part of the **[Tata iQ AI Transformation Consultant Virtual Experience](https://www.theforage.com/simulations/tata/data-analytics-t3zr/completed)** on Forage.

Massive credit to the Tata Group for designing a program that goes beyond surface-level tasks and actually challenges you to think like an AI professional.

---

*Built by [Irenikase Samuel Temitope] | [www.linkedin.com/in/samuel-irenikase-582954364*
