
# 🏥 GuardianMed: Intelligent Medication Adherence System

> 🚀 Transforming healthcare from reactive → proactive using AI & Machine Learning

---

## 📌 Overview

**GuardianMed** is an intelligent healthcare system that monitors medication adherence in real time, detects risks early, and predicts future adherence using Machine Learning.

It helps patients, caregivers, and doctors ensure medications are taken correctly and on time.

---

## ❗ Problem Statement

Medication non-adherence is a major healthcare challenge:

- Patients frequently miss doses
- Caregivers lack real-time visibility
- No early detection of health risks
- Leads to serious medical complications

👉 Existing systems are reactive, not proactive.

---

## 💡 Solution

GuardianMed provides a smart system that:

- Tracks medication intake in real time
- Detects missed doses and risky patterns
- Provides AI-based alerts and suggestions
- Predicts future adherence risk using ML

---

## 🏗️ System Architecture

```

User (Caregiver / Patient)
↓
Web Dashboard (HTML, CSS, JavaScript)
↓
Flask Backend (API Layer)
↓
Business Logic Layer
→ Risk Engine (AI Rules)
→ Guardian Score Calculator
→ ML Model (Random Forest)
↓
Database (SQLite)
↓
Real-Time Response to UI

```

---

## ⚙️ Tech Stack

**Frontend:**
- HTML
- CSS
- JavaScript

**Backend:**
- Flask (Python)

**Database:**
- SQLite

**Machine Learning:**
- Random Forest (Scikit-learn)

**AI Logic:**
- Rule-based Risk Engine

---

## ✨ Key Features

- 📅 Real-Time Medication Tracking  
- 📊 Guardian Score System  
- 🤖 AI-Based Alerts & Suggestions  
- ⚠️ Risk Detection (missed doses, patterns)  
- 📈 ML-Based Risk Prediction  
- 🔔 Smart Notifications  

---

## 🔄 Working Flow

```

User marks dose (Taken / Missed)
↓
Flask API updates database
↓
System recalculates adherence score
↓
AI detects patterns & risks
↓
ML predicts future risk probability
↓
Dashboard updates in real time

````

👉 Closed-loop intelligent healthcare system

---

## 📊 Guardian Score

The system calculates a score based on:

- Adherence (dose taken or missed)
- Timing (on-time or delayed)
- Risk patterns (frequent misses)

---

## 🤖 Machine Learning Model

- Model Used: Random Forest  
- Inputs:
  - Adherence history  
  - Timing patterns  
  - Miss frequency  
- Output:
  - Risk probability score  

---

## 🚀 Impact

- Improves medication adherence  
- Enables proactive healthcare  
- Reduces complications  
- Assists caregivers and doctors  
- Provides real-time insights  

---

## 🔮 Future Scope

- Mobile App (React Native)  
- Wearable Integration  
- Doctor Dashboard  
- Cloud Deployment (AWS/GCP)  
- Advanced ML models  

---

## 🧪 How to Run the Project

```bash
# Clone repository
git clone https://github.com/your-username/guardianmed.git

# Navigate to project
cd guardianmed

# Create virtual environment
python -m venv venv

# Activate environment
# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
````

Open in browser:

```
http://127.0.0.1:5000/
```

---

## 👩‍💻 Team

* Riti Matangi



