# Varroc Design Copilot  — AI-Powered CAD Validation

<div align="center">

**Analyze CAD files for manufacturability risks using explainable AI**

*SHAP-based feature explanations · Rule-based DFM validation · AI-generated recommendations*

</div>

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- *(Optional)* Supabase account for persistent storage
- *(Optional)* OpenAI API key for AI-powered recommendations

### 1. Clone & Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Create the demo model
python create_mock_model.py

# Copy and configure environment
copy .env.example .env
# Edit .env with your Supabase credentials (optional)
```

### 2. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment config
copy .env.local.example .env.local
```

### 3. Run Both Servers

**Terminal 1 — Backend (port 8000):**
```bash
cd backend
python main.py
# OR: uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend (port 3000):**
```bash
cd frontend
npm run dev
```

### 4. Open the App

Navigate to **http://localhost:3000** in your browser.

---

## 🏗️ Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Next.js 14     │────▶│   FastAPI         │────▶│   Supabase       │
│   (Frontend)     │◀────│   (Backend)       │◀────│   (PostgreSQL)   │
│   Port 3000      │     │   Port 8000       │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                               │
                          ┌────┴────┐
                          │ model.pkl│  ← GradientBoosting
                          │ SHAP     │  ← TreeExplainer
                          │ LLM/Tmpl │  ← Recommendations
                          └─────────┘
```

### API Flow
```
Upload File → Feature Extraction → Model Prediction → SHAP Values → Violations → Recommendations → Store → Response
```

---

## 📁 Project Structure

```
CADguard/
├── backend/
│   ├── main.py                  # FastAPI app & routes
│   ├── model_loader.py          # Load model.pkl, predict risk
│   ├── feature_extractor.py     # Extract features from CAD files
│   ├── violation_checker.py     # Rule-based DFM violations
│   ├── shap_explainer.py        # SHAP value computation
│   ├── recommendation_engine.py # LLM + template recommendations
│   ├── supabase_client.py       # Database operations
│   ├── create_mock_model.py     # Generate demo model.pkl
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.js        # Root layout + navbar
│   │   │   ├── page.js          # Home page (upload)
│   │   │   ├── globals.css      # Global styles
│   │   │   └── results/[id]/
│   │   │       └── page.js      # Results page
│   │   ├── components/
│   │   │   ├── Navbar.js        # Navigation bar
│   │   │   ├── FileUpload.js    # Drag-and-drop upload
│   │   │   ├── MaterialSelector.js
│   │   │   ├── RecentAnalyses.js
│   │   │   ├── RiskGauge.js     # Animated circular gauge
│   │   │   ├── ShapChart.js     # SHAP bar chart (Recharts)
│   │   │   ├── ViolationsList.js
│   │   │   ├── FeatureTable.js
│   │   │   └── Recommendations.js
│   │   └── lib/
│   │       └── api.js           # API client
│   ├── .env.local.example
│   └── package.json
│
└── README.md
```

---

## ⚙️ Features

### 🔬 Feature Extraction
- **STL files**: Uses `trimesh` for bounding box, aspect ratio, volume/area analysis
- **Other files**: Simulates realistic DFM features for demo

### 🧠 ML Prediction
- **GradientBoosting** classifier trained on synthetic DFM data
- Predicts risk probability → mapped to score (0–100)
- Labels: LOW (<40), MEDIUM (40–70), HIGH (>70)

### 📊 SHAP Explainability
- **TreeExplainer** for GBM models (KernelExplainer fallback)
- Per-feature contribution to risk score
- Interactive bar chart showing positive (risk-increasing) and negative (risk-decreasing) effects

### ⚠️ DFM Violations
Rule-based checks for:
- Wall thickness (min: 1.0mm, max: 8.0mm)
- Draft angle (min: 1.5°)
- Corner radius (min: 0.5mm)
- Aspect ratio (max: 8.0:1)
- Undercut presence
- Wall uniformity (min: 0.6)

### 💡 AI Recommendations
- **LLM-powered** (OpenAI GPT) when API key is provided
- **Template-based** fallback for reliable demo operation
- Feature-specific, actionable engineering advice

### 💾 Storage
- **Supabase** for persistent storage (with table schema provided)
- **In-memory fallback** when Supabase is not configured

---

## 🗄️ Supabase Setup (Optional)

Create the `analyses` table in your Supabase project:

```sql
CREATE TABLE analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_name TEXT NOT NULL,
    material TEXT NOT NULL,
    risk_score REAL NOT NULL,
    risk_label TEXT NOT NULL,
    features JSONB,
    violations JSONB,
    shap_values JSONB,
    recommendations JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE app_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

Then update your `backend/.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_KEY=your-anon-key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DEMO_LOGIN_EMAIL=demo@cadguard.ai
DEMO_LOGIN_PASSWORD=cadguard123
AUTH_PASSWORD_SALT=change-this-salt
AUTH_HASH_ITERATIONS=310000
```

You can run the full table setup from:
`supabase/init.sql`

> **Note**: The app works perfectly without Supabase using in-memory storage.

---

## 🔑 Environment Variables

### Backend (`backend/.env`)
| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Optional | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Recommended | Service role key used by backend for inserts/auth verification |
| `SUPABASE_KEY` | Optional | Supabase anon key |
| `AUTH_PASSWORD_SALT` | Recommended | Salt for password hashing |
| `AUTH_HASH_ITERATIONS` | Optional | PBKDF2 iterations for password hashing (default: `310000`) |
| `OPENAI_API_KEY` | Optional | OpenAI API key for recommendations |

### Frontend (`frontend/.env.local`)
| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Backend URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_BACKEND_URL` | Optional | Fallback backend URL alias |
| `NEXT_PUBLIC_DEFAULT_LOGIN_EMAIL` | Optional | Prefills login page email |
| `NEXT_PUBLIC_DEFAULT_LOGIN_PASSWORD` | Optional | Prefills login page password |

### Auth Test Flow
1. Open `/login` in the frontend.
2. Click **Seed Demo Credential** (calls backend `/api/auth/seed-demo-user`).
3. Click **Login** (calls backend `/api/auth/login`).
4. Success toast confirms frontend-backend communication and credential verification.

---

## 🎯 Input Features

| Feature | Type | Description |
|---|---|---|
| `wall_thickness` | float | Minimum wall thickness (mm) |
| `draft_angle` | float | Draft angle for mold release (degrees) |
| `corner_radius` | float | Internal corner radius (mm) |
| `aspect_ratio` | float | Bounding box aspect ratio |
| `undercut_present` | int (0/1) | Whether undercuts exist |
| `wall_uniformity` | float (0–1) | Wall thickness consistency |
| `material_encoded` | int | Material type code |

---

## 📜 License

MIT — Built for hackathon demonstration purposes.
