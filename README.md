## Machine Learning-Based Fraud Detection for Blockchain Wallets

This project is a **production-ready web application** for scanning blockchain wallet addresses (Ethereum and Bitcoin) and estimating a **fraud probability** using a pre-trained ML model (`fraud_model.pkl`).

The app consists of:
- **Backend**: FastAPI + PostgreSQL + ML model (LightGBM/XGBoost)
- **Frontend**: HTML + CSS + Vanilla JavaScript (responsive dark dashboard)

### Project Structure

- `backend/`
  - `main.py` - FastAPI entrypoint and API routes
  - `blockchain_api.py` - Blockchain data fetching (Etherscan, BlockCypher)
  - `feature_engineering.py` - Transaction feature construction
  - `model_loader.py` - ML model loading and prediction utilities
  - `database.py` - SQLAlchemy models and session helpers
  - `schemas.py` - Pydantic request/response models
  - `config.py` - Settings (API keys, DB URL, etc.)
  - `requirements.txt` - Python dependencies
- `frontend/`
  - `index.html` - Main dashboard UI
  - `styles.css` - Dark cybersecurity theme styling
  - `app.js` - Frontend logic and API calls

You must provide a trained model file at:

- `backend/models/fraud_model.pkl`

The model should accept features in the following order:

1. `transaction_count`
2. `avg_value`
3. `max_value`
4. `burst_activity`

and output a single fraud probability in \[0, 1\].

---

### Prerequisites

- **Python** 3.10+
- **PostgreSQL** 13+
- **Node/HTTP server (optional)** – to serve the frontend over HTTP (you can also open `index.html` directly in a browser during development)

---

### Backend Setup

1. **Create and activate a virtual environment**

```bash
cd fraud-wallet-app
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

2. **Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

3. **Create PostgreSQL database**

In `psql` or any PostgreSQL client:

```sql
CREATE DATABASE fraud_wallet_db;
```

4. **Configure environment variables**

Create a `.env` file in `backend/`:

```bash
cd backend
copy .env.example .env
```

Edit `.env` and set:

- `DATABASE_URL` (e.g. `postgresql+psycopg2://username:password@localhost:5432/fraud_wallet_db`)
- `ETHERSCAN_API_KEY`
- `BLOCKCYPHER_API_TOKEN` (optional, but recommended)

5. **Place the trained model**

Copy your trained LightGBM/XGBoost model to:

- `backend/models/fraud_model.pkl`

6. **Run database migrations (create tables)**

Tables are created automatically on app startup using SQLAlchemy metadata:

```bash
uvicorn main:app --reload
```

On first run, the `wallet_scans` table will be created.

7. **Run the FastAPI backend**

From `backend/`:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

---

### Frontend Setup

1. **Open the frontend**

Option A (simple):
- Open `frontend/index.html` directly in your browser.

Option B (recommended for CORS safety):
- Serve `frontend/` with a small static HTTP server, for example:

```bash
cd frontend
python -m http.server 5500
```

Then open:

- `http://localhost:5500`

2. **Configure backend URL (optional)**

By default, `app.js` points to `http://localhost:8000` for API calls. If you change the backend port or host, update the `API_BASE_URL` constant in `frontend/app.js`.

---

### Usage

1. Open the **dashboard** in your browser.
2. Enter a **wallet address**.
3. Select a **blockchain network** (Ethereum or Bitcoin).
4. Click **“Scan Wallet”**.
5. The app will:
   - Fetch recent transactions from Etherscan/BlockCypher.
   - Compute features (transaction count, average/max value, burst activity).
   - Run the ML model and obtain a fraud probability.
   - Classify the risk as **Low**, **Medium**, or **High**.
   - Persist the scan to PostgreSQL.
6. Scan history will appear in the **Scan History** table.

---

### API Endpoints

- **POST** `/scan-wallet`
  - Request body:
    - `wallet_address` (string)
    - `blockchain` (string: `"ethereum"` or `"bitcoin"`)
  - Response:
    - `scan_id`
    - `wallet_address`
    - `blockchain`
    - `transaction_count`
    - `avg_value`
    - `max_value`
    - `burst_activity`
    - `fraud_probability`
    - `risk_level`
    - `timestamp`

- **GET** `/scan-history`
  - Optional query parameters: `limit` (default 50)
  - Returns a list of recent scans with the same fields as above.

---

### Risk Level Logic

- **Low risk**: fraud probability \< 0.3
- **Medium risk**: 0.3 ≤ fraud probability ≤ 0.7
- **High risk**: fraud probability \> 0.7

---

### Production Notes

- Frontend uses **fetch** with JSON and decoupled CORS-friendly backend.
- Backend structured in modular layers:
  - blockchain data, feature engineering, model, persistence, and API.
- All inputs are validated via **Pydantic** models.
- PostgreSQL access via **SQLAlchemy** ORM.
- Replace `--reload` in production with a proper ASGI server (e.g. `gunicorn` + `uvicorn.workers.UvicornWorker`) and configure HTTPS + reverse proxy (e.g. Nginx).

