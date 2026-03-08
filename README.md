# SMA 30 Crossover Stock Screener

A full-stack web app that scans all US-listed stocks for 30-day simple moving average (SMA) crossovers. When a stock's price crosses above its SMA 30, it's flagged as a potential bullish signal. The app combines this technical signal with company fundamentals (market cap, revenue, P/E) and recent news to surface the most notable opportunities.

## Features

- **Daily scanning** of all US equities via yfinance
- **SMA 30 crossover detection** with configurable fundamental filters
- **Interactive dashboard** with sortable table, sector filters, and sparkline charts
- **Detail view** with Liveline real-time chart, SMA 30 reference line, fundamentals, and news
- **Email alerts** via Resend when new crossover signals appear
- **Manual scan trigger** from the UI for on-demand analysis

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (Resend API key, email, etc.)

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` requests to the backend.

### First Scan

Click the **Run Scan** button in the UI, or hit the API directly:

```bash
curl -X POST http://localhost:8000/api/scan
```

The first scan downloads ~3 months of daily price data for all US stocks and takes several minutes. Subsequent scans are faster since the data pipeline is warmed up.

## Configuration

All settings are in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `RESEND_API_KEY` | — | Resend API key for email notifications |
| `NOTIFICATION_EMAIL` | — | Default recipient for scan alerts |
| `SCAN_HOUR` | `16` | Hour (ET) to run the daily scan |
| `SCAN_MINUTE` | `30` | Minute to run the daily scan |
| `MIN_MARKET_CAP` | `500000000` | Minimum market cap filter ($500M) |
| `MIN_AVG_VOLUME` | `100000` | Minimum average daily volume filter |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stocks` | List qualifying stocks (supports `sector`, `sort_by`, `sort_dir`, `limit`, `offset`) |
| `GET` | `/api/stocks/{ticker}` | Full detail for a single stock |
| `GET` | `/api/stocks/{ticker}/chart` | Price + SMA 30 chart data |
| `GET` | `/api/stats` | Summary stats and sector breakdown |
| `GET` | `/api/sectors` | List of distinct sectors |
| `POST` | `/api/subscribe` | Register email for alerts (`{ "email": "..." }`) |
| `POST` | `/api/scan` | Trigger a manual scan |

## Architecture

- **Backend**: Python / FastAPI / SQLAlchemy / SQLite
- **Scanner**: yfinance for market data, pandas for SMA calculation
- **Scheduler**: APScheduler runs daily Mon–Fri after market close
- **Email**: Resend API
- **Frontend**: React / TypeScript / Vite / Tailwind CSS
- **Charts**: Recharts sparklines in the table, Liveline for the detail view

## Disclaimer

This tool is for informational and educational purposes only. It is not financial advice. Always do your own research before making investment decisions.
