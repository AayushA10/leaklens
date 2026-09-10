# LeakLens

LeakLens is a website revenue leak scanner that helps businesses identify SEO, conversion, performance, and technical issues that may be costing them traffic, leads, and revenue.

Users enter a website URL, receive an instant free scan, and can unlock a full AI-powered report with prioritized recommendations and a downloadable PDF.

## Features

- Website scanning
- SEO analysis
- Conversion analysis
- Performance analysis
- Revenue Leak Score
- AI-powered business recommendations
- Stripe Checkout integration
- Paid report access
- Downloadable PDF reports
- Persistent report storage
- SSRF-protected website scanning
- Responsive React frontend

## How It Works

1. A user enters a website URL.
2. LeakLens scans the website across SEO, conversion, and performance categories.
3. The scan is converted into a Revenue Leak Score.
4. The user receives a free preview containing the most important findings.
5. The full report can be unlocked through Stripe Checkout.
6. Groq generates an AI-powered analysis of the findings.
7. LeakLens prioritizes risks, recommendations, quick wins, and next steps.
8. The complete report can be downloaded as a PDF.

## Tech Stack

### Frontend
- React
- Vite
- JavaScript
- CSS

### Backend
- Python
- FastAPI
- SQLAlchemy
- Playwright
- BeautifulSoup

### Integrations
- Groq API
- Stripe
- ReportLab

### Database
- SQLite for local development
- PostgreSQL for production

## Project Structure

```text
leaklens/
├── backend/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   └── models.py
│   │
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── crawler.py
│   │   ├── seo.py
│   │   ├── conversion.py
│   │   ├── performance.py
│   │   └── scoring.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── groq_service.py
│   │   ├── pdf_service.py
│   │   ├── report_store.py
│   │   └── stripe_service.py
│   │
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

## Security

LeakLens includes URL validation and SSRF protection for its website scanning infrastructure.

The scanner prevents access to:

- Localhost
- Private IPv4 networks
- Private IPv6 networks
- Link-local addresses
- Reserved IP ranges
- Cloud metadata endpoints
- Unsupported URL protocols

Browser requests and redirect destinations are validated before access.

API keys, environment variables, local databases, virtual environments, generated reports, and Node dependencies are excluded from Git.

## Environment Variables

The backend uses environment variables such as:

```env
GROQ_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
FRONTEND_URL=
DATABASE_URL=
```

Real credentials must never be committed to the repository.

## Local Development

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

## Stripe Webhooks

For local Stripe webhook testing:

```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```

Production uses a separate Stripe webhook endpoint and signing secret.

## API Overview

```text
GET  /health
GET  /scan
GET  /report/{report_id}/preview
POST /report/{report_id}/checkout
POST /payments/confirm
POST /stripe/webhook
GET  /report/{report_id}
POST /report/{report_id}/generate-ai
GET  /report/{report_id}/pdf
```

## Production Architecture

```text
Users
  │
  ▼
LeakLens Frontend
  │
  └── Vercel
        │
        ▼
FastAPI Backend
  │
  ├── Website Scanner
  ├── Playwright
  ├── Groq
  ├── Stripe
  └── PDF Generation
        │
        ▼
PostgreSQL
```

Planned production infrastructure:

- **Frontend:** Vercel
- **Backend:** Render
- **Database:** PostgreSQL
- **Payments:** Stripe
- **AI:** Groq
- **Source Code:** Private GitHub repository

## Current MVP Status

LeakLens currently supports:

- Website crawling
- SEO analysis
- Conversion analysis
- Performance analysis
- Revenue Leak Score calculation
- Free report previews
- AI-powered full reports
- Stripe Checkout
- Stripe webhook processing
- Persistent report storage
- PDF generation
- Responsive frontend
- SSRF-protected scanning

## Roadmap

- Production PostgreSQL database
- Dockerized Playwright environment
- Production deployment
- Custom domain
- Rate limiting
- Production CORS configuration
- Logging and monitoring
- User authentication
- User accounts
- Scan history
- Additional website checks
- Subscription plans

## Author

**Aayush Anand**

Software Engineer  
M.S. Computer Science, NYU Tandon School of Engineering

---

LeakLens is currently under active development.