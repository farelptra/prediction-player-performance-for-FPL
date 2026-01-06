# EPL Predictor (FPL API + Random Forest)

## 1) MySQL/MariaDB

- `sql/schema_fpl.sql` (official Fantasy Premier League API)

## 2) Backend (FastAPI)
```bash
cd backend
copy .env.example .env   # Windows
# edit DB credentials if needed

python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

# (optional) generate more dummy stats
python scripts/generate_dummy_data.py

# train models (Random Forest)
python -m app.cli train

# run API
uvicorn app.main:app --reload --port 8000
```

API docs:
- http://localhost:8000/docs

## 3) Frontend (React + Tailwind + Recharts)
```bash
cd frontend
npm install
npm run dev
```
Set API base in `frontend/src/lib/api.js` (default: http://localhost:8000)


## Using real FPL data (official Fantasy Premier League API)

1) Import schema:
- Run `sql/schema_fpl.sql` in your MySQL.

2) Configure backend DB in `backend/.env` (DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME).

3) Import data:
```bash
cd backend
.venv\Scripts\activate
python scripts/import_fpl_api.py
```
This pulls teams, players, fixtures, and all **finished** gameweeks' live stats.

4) Train model:
```bash
python -m app.cli train
```

5) Generate predictions for a GW:
```bash
python -m app.cli predict-gw 10
```
(or use the API `POST /predict/gw/{gw}`)
