# LeakLens

**LeakLens** is a full-stack Revenue Leak Detection and Website Monitoring SaaS that helps businesses identify SEO, conversion, performance, and technical issues that may be costing them traffic, leads, and revenue.

Users can run an instant free website scan, receive a Revenue Leak Score, unlock an AI-powered full report, download a PDF report, and continuously monitor websites through authenticated SaaS plans.

## Live Application

- **Live App:** https://leaklens-beige.vercel.app
- **Backend API:** https://leaklens-qk7t.onrender.com
- **GitHub:** https://github.com/AayushA10/leaklens

## Core Product Flow

**Scan → Find Revenue Leaks → AI Recommendations → Monitor Continuously → Track Fixes**

## Features

### Revenue Leak Scanner

- Instant website scanning
- SEO analysis
- Conversion analysis
- Performance analysis
- Revenue Leak Score
- Business-focused issue detection
- Free report preview
- Top findings and prioritized issues
- Persistent report storage

### AI-Powered Reports

LeakLens uses Groq to transform technical findings into business-focused recommendations.

AI analysis includes:

- Executive summary
- Business risks
- Prioritized fixes
- Quick wins
- Actionable next steps

### $29 Full Report

Users can unlock an individual full report through Stripe Checkout.

The paid report flow includes:

- $29 one-time payment
- Stripe Checkout
- Payment verification
- AI-powered analysis
- Full report access
- Downloadable PDF
- Persistent payment state

### Website Monitoring

Authenticated users can continuously monitor websites from their dashboard.

Monitoring includes:

- Add monitored websites
- Automatic scheduled scans
- Manual monitoring scans
- Scan history
- Open issue tracking
- Resolved issue tracking
- Issue lifecycle detection
- Pause/resume monitoring
- Run Scan Now
- AI analysis of latest monitoring results
- Per-user website ownership

### Issue Lifecycle Tracking

LeakLens compares monitoring scans over time and tracks whether problems remain or have been fixed.

**Detected → Open → Persistent → Resolved**

### Automated Monitoring

Monitoring frequency depends on the user's SaaS plan.

- Weekly monitoring for Free
- Daily monitoring for paid plans
- Automatic next-scan scheduling
- Failed-scan retry scheduling
- GitHub Actions scheduled runner
- Protected internal monitoring endpoint

### Authentication

LeakLens uses Clerk for authentication.

Authenticated functionality includes:

- User dashboard
- Protected monitoring endpoints
- User-specific monitored websites
- Subscription management
- Usage tracking
- Manual monitoring scans
- AI monitoring analysis

### Stripe Subscriptions

LeakLens supports recurring monthly SaaS subscriptions through Stripe.

Users can:

- Subscribe through Stripe Checkout
- Upgrade plans
- Downgrade plans
- Manage subscriptions through Stripe Customer Portal
- Automatically synchronize subscription changes through Stripe webhooks

## SaaS Plans

### Free — $0/month

- 1 monitored website
- Weekly automatic monitoring
- 3 manual monitoring scans per month
- 2 AI analyses per month
- 7-day history

### Starter — $5/month

- 3 monitored websites
- Daily automatic monitoring
- 20 manual monitoring scans per month
- 10 AI analyses per month
- 30-day history

### Growth — $15/month

- 10 monitored websites
- Daily automatic monitoring
- 100 manual monitoring scans per month
- 50 AI analyses per month
- 90-day history

### Pro — $29/month

- 25 monitored websites
- Daily automatic monitoring
- 300 manual monitoring scans per month
- 150 AI analyses per month
- 1-year history

## Usage Controls

LeakLens enforces SaaS limits on the backend.

Tracked usage includes:

- Monitored websites
- Manual monitoring scans
- AI analyses
- Monitoring frequency
- History entitlement

The public Free Scan is separate from authenticated dashboard manual monitoring scan quotas.

## Dashboard

The LeakLens dashboard displays:

- Current subscription plan
- Website usage
- Manual monitoring scan usage
- AI analysis usage
- Monitoring frequency
- History limits
- Monitored websites
- Open issues
- Resolved issues
- Scan history
- Monitoring status

## How It Works

1. A visitor enters a website URL.
2. LeakLens validates and scans the website.
3. SEO, conversion, and performance signals are analyzed.
4. LeakLens calculates a Revenue Leak Score.
5. The visitor receives a free preview.
6. A detailed report can be unlocked for $29 through Stripe.
7. Groq generates AI-powered business recommendations.
8. The full report can be downloaded as a PDF.
9. Authenticated users can add websites to monitoring.
10. LeakLens automatically rescans websites based on the user's plan.
11. New, persistent, and resolved issues are tracked.
12. Users can run manual scans and AI analyses within plan limits.
13. Paid users can manage subscriptions through Stripe.

## Tech Stack

### Frontend

- React
- Vite
- JavaScript
- CSS
- Clerk

### Backend

- Python
- FastAPI
- SQLAlchemy
- Playwright
- BeautifulSoup

### AI

- Groq API

### Payments

- Stripe Checkout
- Stripe Subscriptions
- Stripe Customer Portal
- Stripe Webhooks

### Database

- SQLite for local development
- PostgreSQL for production

### Reporting

- ReportLab
- AI-powered report generation
- Downloadable PDF reports

### Infrastructure

- Vercel — Frontend
- Render — Backend
- PostgreSQL — Production database
- GitHub Actions — Scheduled monitoring
- GitHub — Source control

## Project Structure

```text
leaklens/
├── backend/
│   ├── database/
│   │   ├── db.py
│   │   └── models.py
│   ├── scanner/
│   │   ├── crawler.py
│   │   ├── seo.py
│   │   ├── conversion.py
│   │   ├── performance.py
│   │   └── scoring.py
│   ├── services/
│   │   ├── groq_service.py
│   │   ├── monitoring_service.py
│   │   ├── pdf_service.py
│   │   ├── plan_service.py
│   │   ├── report_store.py
│   │   └── stripe_service.py
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── .github/
│   └── workflows/
│       └── monitoring.yml
├── .gitignore
└── README.md
```

## API Overview

### Public Scanner & Reports

```text
GET  /health
GET  /scan
GET  /report/{report_id}/preview
POST /report/{report_id}/checkout
GET  /report/{report_id}/payment-status
POST /payments/confirm
GET  /report/{report_id}
POST /report/{report_id}/generate-ai
GET  /report/{report_id}/pdf
POST /stripe/webhook
```

### Account & Subscriptions

```text
GET  /account/plan
POST /account/subscription/checkout
POST /account/subscription/manage
```

### Website Monitoring

```text
POST /monitoring/sites
GET  /monitoring/sites
GET  /monitoring/sites/{site_id}
POST /monitoring/sites/{site_id}/scan
GET  /monitoring/sites/{site_id}/history
GET  /monitoring/sites/{site_id}/issues
POST /monitoring/sites/{site_id}/toggle
POST /monitoring/sites/{site_id}/ai-analysis
```

### Internal Automation

```text
POST /internal/run-monitoring
```

## Security

LeakLens includes security controls for both public scanning and authenticated SaaS functionality.

### SSRF Protection

The scanner prevents access to:

- Localhost
- Private IPv4 networks
- Private IPv6 networks
- Link-local addresses
- Reserved IP ranges
- Cloud metadata endpoints
- Unsupported URL protocols

Browser requests and redirect destinations are validated before access.

### Application Security

- Clerk authentication
- Per-user resource ownership
- Stripe webhook signature verification
- Cron-secret protected automation
- Backend plan enforcement
- URL validation
- Public scanner rate limiting
- Environment-based secret management
- Production CORS configuration

API keys, environment files, local databases, virtual environments, generated reports, and Node dependencies are excluded from Git.

## Environment Variables

Backend configuration includes:

```env
GROQ_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_STARTER_PRICE_ID=
STRIPE_GROWTH_PRICE_ID=
STRIPE_PRO_PRICE_ID=
CLERK_SECRET_KEY=
DATABASE_URL=
FRONTEND_URL=
CORS_ORIGINS=
CRON_SECRET=
```

Frontend configuration includes:

```env
VITE_API_URL=
VITE_CLERK_PUBLISHABLE_KEY=
```

Never commit real credentials to the repository.

## Local Development

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## Stripe Webhooks

For local webhook testing:

```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```

Important Stripe events handled by LeakLens include:

```text
checkout.session.completed
checkout.session.async_payment_succeeded
customer.subscription.updated
customer.subscription.deleted
```

Production uses a separate Stripe webhook endpoint and signing secret.

## Production Architecture

```text
Users
  │
  ▼
React + Vite Frontend
Vercel
  │
  ▼
FastAPI Backend
Render
  │
  ├── Website Scanner / Playwright
  ├── Groq AI
  ├── Stripe Payments & Subscriptions
  ├── Monitoring Engine
  └── PDF Generation
  │
  ▼
PostgreSQL
  │
  ├── Reports
  ├── Monitoring Sites
  ├── Scan Snapshots
  ├── Issues
  ├── Subscriptions
  └── Usage

GitHub Actions
  │
  ▼
Scheduled Monitoring Runner
```

## Deployment

### Frontend

Production frontend:

**https://leaklens-beige.vercel.app**

Hosted on Vercel.

### Backend

Production API:

**https://leaklens-qk7t.onrender.com**

Hosted on Render.

### Source Code

**https://github.com/AayushA10/leaklens**

## Current Status

LeakLens currently includes:

- Production frontend
- Production FastAPI backend
- PostgreSQL persistence
- Website crawling
- SEO analysis
- Conversion analysis
- Performance analysis
- Revenue Leak Score
- Free report previews
- $29 one-time report unlock
- AI-powered reports
- PDF generation
- Stripe Checkout
- Stripe recurring subscriptions
- Stripe Customer Portal
- Clerk authentication
- User dashboard
- Website monitoring
- Scheduled monitoring
- Manual monitoring scans
- Issue lifecycle tracking
- Open and resolved issues
- Scan history
- AI monitoring analysis
- Monthly usage tracking
- Free, Starter, Growth, and Pro plans
- Plan-based website limits
- Plan-based scan limits
- Plan-based AI limits
- SSRF protection
- Rate limiting
- GitHub Actions automation
- Responsive React frontend

## Roadmap

Planned improvements include:

- AI monitoring analysis persistence and caching
- Stronger concurrency-safe usage accounting
- Automatic history-retention enforcement
- Expanded Stripe subscription lifecycle handling
- Additional website health checks
- Advanced monitoring analytics
- Improved alerting
- Production observability
- Custom domain
- Additional integrations

## Author

**Aayush Anand**

Software Engineer  
M.S. Computer Science — NYU Tandon School of Engineering

GitHub: https://github.com/AayushA10

## Disclaimer

LeakLens identifies technical and conversion-related signals that may affect website performance and business outcomes. AI-generated recommendations are decision-support insights and do not guarantee financial results.

---

**LeakLens — Find the leaks. Prioritize what matters. Monitor what improves.**
