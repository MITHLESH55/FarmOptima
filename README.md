# FarmOptima

AI-powered smart crop decision support — satellite data, MCDM (AHP/TOPSIS/ELECTRE), and a genetic algorithm (GPO) for resource optimization.

**See `backend/README.md` for the full architecture, setup, and design rationale** — this version restructures the backend into a proper layered architecture (routes / services / core algorithms / models / schemas / database / utils), following a backend-first build order.

Quick start:
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
Then, in a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
