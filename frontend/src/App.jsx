import { useEffect, useMemo, useState } from "react";
import { Show, SignInButton, UserButton } from "@clerk/react";import {
  ArrowRight,
  Search,
  TrendingUp,
  Zap,
  Target,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  RotateCcw,
  LockOpen,
  Sparkles,
  ClipboardCheck,
  Rocket,
  CalendarDays,
  CreditCard,
  Download,
} from "lucide-react";
import "./App.css";
import LegalPage from "./LegalPage";

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

function App() {
  const legalPages = ["privacy", "terms", "refund", "contact"];
  const currentPath = window.location.pathname
    .replace(/^\/+|\/+$/g, "")
    .toLowerCase();

  const activeLegalPage = legalPages.includes(currentPath)
    ? currentPath
    : null;

  const goHome = () => {
    window.location.href = "/";
  };

  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const [unlocking, setUnlocking] = useState(false);
  const [fullReport, setFullReport] = useState(null);
  const [unlockError, setUnlockError] = useState("");
  const [paymentMessage, setPaymentMessage] = useState("");
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const normalizeUrl = (value) => {
    const trimmed = value.trim();

    if (
      trimmed.startsWith("http://") ||
      trimmed.startsWith("https://")
    ) {
      return trimmed;
    }

    return `https://${trimmed}`;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!url.trim()) {
      setError("Please enter a website URL.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setFullReport(null);
    setUnlockError("");

    try {
      const normalizedUrl = normalizeUrl(url);

      const response = await fetch(
        `${API_BASE_URL}/scan?url=${encodeURIComponent(
          normalizedUrl
        )}`
      );

      if (!response.ok) {
        throw new Error("The scan request failed.");
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(
          data?.error ||
            "We could not scan this website."
        );
      }

      setResult(data);
    } catch (err) {
      setError(
        err.message ||
          "Something went wrong while scanning the website."
      );
    } finally {
      setLoading(false);
    }
  };

  const buildPreviewFromReport = (reportId, report) => ({
    success: true,
    report_id: reportId,
    website: {
      url: report?.website?.url,
      final_url: report?.website?.final_url,
      title: report?.website?.title,
    },
    performance: {
      status: report?.performance?.status,
      load_time_ms: report?.performance?.load_time_ms,
      requests_count: report?.performance?.requests_count,
    },
    revenue_leak: report?.revenue_leak,
    payment: report?.payment,
  });

  const loadPaidReport = async (reportId) => {
    const response = await fetch(
      `${API_BASE_URL}/report/${reportId}`
    );

    if (!response.ok) {
      if (response.status === 402) {
        throw new Error(
          "Payment has not been confirmed for this report yet."
        );
      }

      if (response.status === 404) {
        throw new Error(
          "This report could not be found."
        );
      }

      throw new Error(
        "Unable to load the full report."
      );
    }

    const data = await response.json();

    if (!data.success || !data.report) {
      throw new Error(
        "The full report could not be loaded."
      );
    }

    let unlockedReport = data.report;

    if (!unlockedReport.ai_analysis) {
      const aiResponse = await fetch(
        `${API_BASE_URL}/report/${reportId}/generate-ai`,
        {
          method: "POST",
        }
      );

      if (!aiResponse.ok) {
        throw new Error(
          "Payment succeeded, but the AI analysis could not be generated."
        );
      }

      const aiData = await aiResponse.json();

      if (aiData.success && aiData.analysis) {
        unlockedReport = {
          ...unlockedReport,
          ai_analysis: aiData.analysis,
        };
      }
    }

    setResult(
      buildPreviewFromReport(
        reportId,
        unlockedReport
      )
    );

    setFullReport(
      unlockedReport
    );

    setPaymentMessage(
      "Payment confirmed. Your full report is unlocked."
    );

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const restorePreview = async (
    reportId,
    cancelled = false
  ) => {
    const response = await fetch(
      `${API_BASE_URL}/report/${reportId}/preview`
    );

    if (!response.ok) {
      return;
    }

    const data = await response.json();

    if (data.success) {
      setResult(data);

      if (cancelled) {
        setPaymentMessage(
          "Checkout was cancelled. Your free scan is still available."
        );
      }
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(
      window.location.search
    );

    const payment = params.get("payment");
    const reportId = params.get("report_id");
    const sessionId = params.get("session_id");

    if (
      payment === "success" &&
      reportId &&
      sessionId
    ) {
      setUnlocking(true);
      setUnlockError("");

      fetch(
        `${API_BASE_URL}/payments/confirm?session_id=${encodeURIComponent(
          sessionId
        )}`,
        {
          method: "POST",
        }
      )
        .then(async (response) => {
          if (!response.ok) {
            const data = await response
              .json()
              .catch(() => ({}));

            throw new Error(
              data?.detail ||
                "Unable to confirm Stripe payment."
            );
          }

          return response.json();
        })
        .then(() =>
          loadPaidReport(
            reportId
          )
        )
        .catch((err) => {
          setUnlockError(
            err.message ||
              "Something went wrong while confirming payment."
          );

          restorePreview(
            reportId
          );
        })
        .finally(() => {
          setUnlocking(false);

          window.history.replaceState(
            {},
            "",
            window.location.pathname
          );
        });

      return;
    }

    if (
      payment === "cancelled" &&
      reportId
    ) {
      restorePreview(
        reportId,
        true
      );

      window.history.replaceState(
        {},
        "",
        window.location.pathname
      );
    }
  }, []);

  const handleUnlockReport = async () => {
    if (!result?.report_id) {
      setUnlockError(
        "This scan does not have a valid report ID."
      );
      return;
    }

    setUnlocking(true);
    setUnlockError("");
    setPaymentMessage("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/report/${result.report_id}/checkout`,
        {
          method: "POST",
        }
      );

      const data = await response
        .json()
        .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Unable to start secure checkout."
        );
      }

      if (data.already_paid) {
        await loadPaidReport(
          result.report_id
        );
        return;
      }

      if (!data.checkout_url) {
        throw new Error(
          "Stripe checkout URL was not returned."
        );
      }

      window.location.href =
        data.checkout_url;
    } catch (err) {
      setUnlockError(
        err.message ||
          "Something went wrong while starting checkout."
      );

      setUnlocking(false);
    }
  };

  const handleDownloadPdf = () => {
    if (!result?.report_id) {
      return;
    }

    setDownloadingPdf(true);

    window.location.href =
      `${API_BASE_URL}/report/${result.report_id}/pdf`;

    window.setTimeout(
      () => {
        setDownloadingPdf(false);
      },
      1200
    );
  };

  const resetScan = () => {
    setResult(null);
    setFullReport(null);
    setError("");
    setUnlockError("");
    setPaymentMessage("");
    setDownloadingPdf(false);
    setUrl("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const getRiskClass = (riskLevel) => {
    const value = riskLevel?.toLowerCase();

    if (value === "excellent") {
      return "risk-excellent";
    }

    if (value === "low") {
      return "risk-low";
    }

    if (value === "moderate") {
      return "risk-moderate";
    }

    if (value === "high") {
      return "risk-high";
    }

    return "risk-critical";
  };

  const getSeverityClass = (severity) => {
    return `severity-${severity || "low"}`;
  };

  const allFullIssues = useMemo(() => {
    if (!fullReport) {
      return [];
    }

    const issues = [
      ...(fullReport?.seo?.issues || []),
      ...(fullReport?.conversion?.issues || []),
      ...(fullReport?.performance?.issues || []),
    ];

    const severityOrder = {
      critical: 4,
      high: 3,
      medium: 2,
      low: 1,
    };

    return [...issues].sort(
      (a, b) =>
        (severityOrder[b?.severity] || 0) -
        (severityOrder[a?.severity] || 0)
    );
  }, [fullReport]);

  const activeReport = fullReport || result;
  const aiAnalysis = fullReport?.ai_analysis || null;

  const navigateToSection = (sectionId) => {
    const scrollToTarget = () => {
      const target = document.getElementById(sectionId);

      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    };

    if (result) {
      resetScan();

      window.setTimeout(
        scrollToTarget,
        80
      );

      return;
    }

    scrollToTarget();
  };

  const formatCategoryScore = (score) => {
    if (score === null || score === undefined) {
      return "Unavailable";
    }

    return `${score}/100`;
  };

  const categoryWidth = (score) => {
    if (typeof score !== "number") {
      return "0%";
    }

    return `${Math.max(0, Math.min(100, score))}%`;
  };

  if (activeLegalPage) {
    return (
      <div className="app">
        <LegalPage
          page={activeLegalPage}
          onHome={goHome}
        />
      </div>
    );
  }

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-container">
          <button
            className="logo logo-button"
            type="button"
            onClick={() => navigateToSection("scan")}
            aria-label="Go to LeakLens home"
          >
            <div className="logo-icon">
              <TrendingUp size={20} />
            </div>

            <span>
              Leak<span className="logo-accent">Lens</span>
            </span>
          </button>

          <div className="nav-links">
            <button
              type="button"
              onClick={() => navigateToSection("how-it-works")}
            >
              How it works
            </button>

            <button
              type="button"
              onClick={() => navigateToSection("features")}
            >
              Features
            </button>

            <button
              type="button"
              onClick={() => navigateToSection("pricing")}
            >
              Pricing
            </button>
          </div>

          <div className="nav-actions">
            <button
              className="nav-button"
              type="button"
              onClick={() => navigateToSection("scan")}
            >
              Free Scan
            </button>

            <Show when="signed-out">
              <SignInButton mode="modal">
                <button className="nav-button" type="button">
                  Sign In
                </button>
              </SignInButton>
            </Show>

            <Show when="signed-in">
              <UserButton />
            </Show>
          </div>
        </div>
      </nav>

      <main>
        {!result && (
          <>
            <section
              className="hero"
              id="scan"
            >
              <div className="hero-glow hero-glow-one" />
              <div className="hero-glow hero-glow-two" />

              <div className="hero-content">
                <div className="eyebrow">
                  <Zap size={15} fill="currentColor" />
                  Free Website Revenue Audit
                </div>

                <h1>
                  Find the website leaks
                  <br />
                  <span>costing you customers.</span>
                </h1>

                <p className="hero-description">
                  LeakLens scans SEO, conversion pathways, and
                  real browser performance to uncover friction,
                  rank the biggest problems, and show you what
                  to fix first.
                </p>

                <form
                  className="scanner"
                  onSubmit={handleSubmit}
                >
                  <div className="input-wrapper">
                    <Search size={21} />

                    <input
                      type="text"
                      value={url}
                      disabled={loading}
                      onChange={(event) =>
                        setUrl(event.target.value)
                      }
                      placeholder="Enter your website — example.com"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner" />
                        Scanning...
                      </>
                    ) : (
                      <>
                        Scan My Website
                        <ArrowRight size={19} />
                      </>
                    )}
                  </button>
                </form>

                {loading && (
                  <div className="scan-progress">
                    <span>Checking SEO structure</span>
                    <span>•</span>
                    <span>Analyzing conversion paths</span>
                    <span>•</span>
                    <span>Testing browser performance</span>
                  </div>
                )}

                {error && (
                  <div className="error-box">
                    <AlertTriangle size={18} />
                    {error}
                  </div>
                )}

                <div className="scanner-note">
                  <ShieldCheck size={16} />
                  No signup required
                  <span>•</span>
                  Free instant scan
                  <span>•</span>
                  No code installation
                </div>

                <div className="hero-proof">
                  <div>
                    <strong>3</strong>
                    <span>core leak categories</span>
                  </div>
                  <div>
                    <strong>Free</strong>
                    <span>score + top findings</span>
                  </div>
                  <div>
                    <strong>$29</strong>
                    <span>one-time full report</span>
                  </div>
                </div>
              </div>
            </section>

            <section
              className="how-section"
              id="how-it-works"
            >
              <div className="landing-container">
                <div className="section-heading">
                  <span className="section-label">
                    HOW IT WORKS
                  </span>

                  <h2>
                    From a URL to a prioritized action plan.
                  </h2>

                  <p>
                    No analytics login, CMS access, or installation.
                    LeakLens starts with the public website experience
                    your visitors and search engines can actually see.
                  </p>
                </div>

                <div className="steps-grid">
                  <article className="step-card">
                    <div className="step-top">
                      <span className="step-number">01</span>
                      <Search size={22} />
                    </div>

                    <h3>Enter your website</h3>

                    <p>
                      Paste a public URL. LeakLens opens the page,
                      follows the visible experience, and prepares
                      the diagnostic scan.
                    </p>

                    <span className="step-detail">
                      No signup • No installation
                    </span>
                  </article>

                  <article className="step-card">
                    <div className="step-top">
                      <span className="step-number">02</span>
                      <Gauge size={22} />
                    </div>

                    <h3>We inspect the leaks</h3>

                    <p>
                      The scanner checks SEO structure, conversion
                      friction, page weight, load time, network
                      requests, and other visible signals.
                    </p>

                    <span className="step-detail">
                      SEO • Conversion • Performance
                    </span>
                  </article>

                  <article className="step-card">
                    <div className="step-top">
                      <span className="step-number">03</span>
                      <ClipboardCheck size={22} />
                    </div>

                    <h3>Fix what matters first</h3>

                    <p>
                      Get your Revenue Leak Score and top findings
                      free. Unlock the complete AI-powered action plan
                      and PDF only when you want it.
                    </p>

                    <span className="step-detail">
                      Priorities • Quick wins • 30-day plan
                    </span>
                  </article>
                </div>

                <button
                  className="section-cta"
                  type="button"
                  onClick={() => navigateToSection("scan")}
                >
                  Run My Free Scan
                  <ArrowRight size={18} />
                </button>
              </div>
            </section>

            <section
              className="problem-section"
              id="features"
            >
              <div className="landing-container">
                <div className="section-heading">
                  <span className="section-label">
                    WHAT LEAKLENS CHECKS
                  </span>

                  <h2>
                    Three categories. One clear picture of
                    website friction.
                  </h2>

                  <p>
                    The scanner turns visible technical signals
                    into business-focused findings instead of
                    giving you another generic score with no next step.
                  </p>
                </div>

                <div className="feature-grid detailed-feature-grid">
                  <article className="feature-card">
                    <div className="feature-icon">
                      <Search size={23} />
                    </div>

                    <div className="feature-card-heading">
                      <div>
                        <span className="feature-kicker">DISCOVERY</span>
                        <h3>SEO Leaks</h3>
                      </div>

                      <span className="feature-score">
                        SEO score
                      </span>
                    </div>

                    <p>
                      Find on-page signals that can make it harder
                      for search engines and potential customers to
                      understand and discover the page.
                    </p>

                    <ul className="feature-check-list">
                      <li>
                        <CheckCircle2 size={16} />
                        Page title quality and length
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Meta description coverage
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        H1 and page structure
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Internal linking signals
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Visible content and page context
                      </li>
                    </ul>
                  </article>

                  <article className="feature-card featured">
                    <div className="feature-icon">
                      <Target size={23} />
                    </div>

                    <div className="feature-card-heading">
                      <div>
                        <span className="feature-kicker">ACTION</span>
                        <h3>Conversion Leaks</h3>
                      </div>

                      <span className="feature-score">
                        Conversion score
                      </span>
                    </div>

                    <p>
                      Surface missing customer pathways and friction
                      that may stop visitors before they contact,
                      book, buy, or move deeper into the website.
                    </p>

                    <ul className="feature-check-list">
                      <li>
                        <CheckCircle2 size={16} />
                        Calls-to-action and action paths
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Contact options and clickable methods
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Forms and lead-capture signals
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Internal navigation and journey gaps
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Paths toward key conversion pages
                      </li>
                    </ul>
                  </article>

                  <article className="feature-card">
                    <div className="feature-icon">
                      <Zap size={23} />
                    </div>

                    <div className="feature-card-heading">
                      <div>
                        <span className="feature-kicker">SPEED</span>
                        <h3>Performance Leaks</h3>
                      </div>

                      <span className="feature-score">
                        Performance score
                      </span>
                    </div>

                    <p>
                      Measure browser-observed performance signals
                      that can create friction before a visitor has
                      a chance to engage with the page.
                    </p>

                    <ul className="feature-check-list">
                      <li>
                        <CheckCircle2 size={16} />
                        Browser-measured page load time
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Total transferred page size
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Network request volume
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Heavy resource overhead
                      </li>
                      <li>
                        <CheckCircle2 size={16} />
                        Performance severity and fixes
                      </li>
                    </ul>
                  </article>
                </div>

                <div className="feature-outcome-strip">
                  <div>
                    <Sparkles size={21} />
                    <span>
                      <strong>AI business summary</strong>
                      Translate technical findings into business impact.
                    </span>
                  </div>

                  <div>
                    <Rocket size={21} />
                    <span>
                      <strong>Prioritized fixes</strong>
                      Know what to address first instead of guessing.
                    </span>
                  </div>

                  <div>
                    <CalendarDays size={21} />
                    <span>
                      <strong>30-day roadmap</strong>
                      Turn the audit into a practical execution plan.
                    </span>
                  </div>

                  <div>
                    <Download size={21} />
                    <span>
                      <strong>PDF report</strong>
                      Save or share the complete paid report.
                    </span>
                  </div>
                </div>
              </div>
            </section>

            <section className="report-value-section">
              <div className="landing-container value-layout">
                <div className="value-copy">
                  <span className="section-label">
                    BUILT FOR ACTION
                  </span>

                  <h2>
                    Not just “what is wrong.”
                    LeakLens tells you what to do next.
                  </h2>

                  <p>
                    The full report combines scanner evidence with
                    an AI-generated business interpretation so the
                    output is useful to founders, marketers,
                    developers, and website owners.
                  </p>

                  <div className="value-list">
                    <div>
                      <span>01</span>
                      <p>
                        <strong>Business risks</strong>
                        Understand how each meaningful issue can affect
                        discovery, engagement, or conversion.
                      </p>
                    </div>

                    <div>
                      <span>02</span>
                      <p>
                        <strong>Prioritized action plan</strong>
                        Fix the highest-impact problems first with
                        specific recommended actions.
                      </p>
                    </div>

                    <div>
                      <span>03</span>
                      <p>
                        <strong>Quick wins + 30-day plan</strong>
                        Separate immediate improvements from the
                        work that should follow over the next month.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="report-preview-card">
                  <div className="preview-window-top">
                    <div className="preview-dots">
                      <span />
                      <span />
                      <span />
                    </div>

                    <span>LeakLens Report</span>
                  </div>

                  <div className="preview-body">
                    <span className="section-label">
                      REVENUE LEAK SCORE
                    </span>

                    <div className="preview-score-row">
                      <strong>38</strong>
                      <span>/100</span>
                      <em>Moderate Risk</em>
                    </div>

                    <div className="preview-bars">
                      <div>
                        <span>SEO</span>
                        <i>
                          <b style={{ width: "76%" }} />
                        </i>
                        <strong>76</strong>
                      </div>

                      <div>
                        <span>Conversion</span>
                        <i>
                          <b style={{ width: "64%" }} />
                        </i>
                        <strong>64</strong>
                      </div>

                      <div>
                        <span>Performance</span>
                        <i>
                          <b style={{ width: "71%" }} />
                        </i>
                        <strong>71</strong>
                      </div>
                    </div>

                    <div className="preview-finding">
                      <AlertTriangle size={18} />
                      <span>
                        <strong>High-priority issue</strong>
                        Slow page load may create friction before
                        visitors engage.
                      </span>
                    </div>

                    <div className="preview-finding good">
                      <CheckCircle2 size={18} />
                      <span>
                        <strong>Recommended action</strong>
                        Compress heavy assets and defer non-critical scripts.
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section
              className="pricing-section"
              id="pricing"
            >
              <div className="landing-container">
                <div className="section-heading">
                  <span className="section-label">
                    SIMPLE PRICING
                  </span>

                  <h2>
                    Scan free. Unlock the complete report only
                    when it is worth it.
                  </h2>

                  <p>
                    No subscription and no recurring charge.
                    The $29 payment applies to the full report
                    for the website scan you choose to unlock.
                  </p>
                </div>

                <div className="pricing-grid">
                  <article className="pricing-card">
                    <div className="pricing-top">
                      <span className="pricing-name">
                        FREE WEBSITE SCAN
                      </span>

                      <div className="price">
                        <strong>$0</strong>
                        <span>forever to scan</span>
                      </div>

                      <p>
                        See the core score and biggest visible
                        problems before paying anything.
                      </p>
                    </div>

                    <ul className="pricing-list">
                      <li>
                        <CheckCircle2 size={17} />
                        Revenue Leak Score
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        SEO, conversion, and performance scores
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Top detected issues
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Basic recommended fixes
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        No signup required
                      </li>
                    </ul>

                    <button
                      className="pricing-button secondary-pricing"
                      type="button"
                      onClick={() => navigateToSection("scan")}
                    >
                      Start Free Scan
                      <ArrowRight size={18} />
                    </button>
                  </article>

                  <article className="pricing-card paid-pricing-card">
                    <div className="pricing-badge">
                      MOST COMPLETE
                    </div>

                    <div className="pricing-top">
                      <span className="pricing-name">
                        FULL REVENUE LEAK REPORT
                      </span>

                      <div className="price">
                        <strong>$29</strong>
                        <span>one-time</span>
                      </div>

                      <p>
                        Turn the scan into a complete technical
                        and business-focused execution plan.
                      </p>
                    </div>

                    <ul className="pricing-list">
                      <li>
                        <CheckCircle2 size={17} />
                        Everything in the free scan
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Every detected website issue
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        AI executive summary and business risks
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Prioritized fix recommendations
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Quick wins and 30-day roadmap
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Downloadable branded PDF
                      </li>
                    </ul>

                    <button
                      className="pricing-button primary-pricing"
                      type="button"
                      onClick={() => navigateToSection("scan")}
                    >
                      Scan & Unlock for $29
                      <ArrowRight size={18} />
                    </button>
                  </article>
                </div>

                <div className="pricing-assurance">
                  <ShieldCheck size={19} />
                  <span>
                    Your free scan does not require payment.
                    Checkout only begins when you explicitly choose
                    to unlock the full report.
                  </span>
                </div>
              </div>
            </section>

            <section className="faq-section">
              <div className="landing-container">
                <div className="section-heading">
                  <span className="section-label">
                    FAQ
                  </span>

                  <h2>
                    Know exactly what you are getting.
                  </h2>
                </div>

                <div className="faq-grid">
                  <article>
                    <h3>Do I need to install anything?</h3>
                    <p>
                      No. LeakLens scans the public website experience.
                      There is no plugin, tracking code, or CMS access
                      required for the current audit.
                    </p>
                  </article>

                  <article>
                    <h3>What is included for free?</h3>
                    <p>
                      The free scan includes the Revenue Leak Score,
                      category scores, and the top detected findings
                      with basic recommended fixes.
                    </p>
                  </article>

                  <article>
                    <h3>What does the $29 report add?</h3>
                    <p>
                      It unlocks the full detected issue list, AI
                      executive summary, business risks, prioritized
                      fixes, quick wins, 30-day plan, and PDF download.
                    </p>
                  </article>

                  <article>
                    <h3>Is $29 a subscription?</h3>
                    <p>
                      No. It is a one-time payment for the full report
                      generated from that website scan.
                    </p>
                  </article>

                  <article>
                    <h3>Does LeakLens estimate exact revenue loss?</h3>
                    <p>
                      No. The Revenue Leak Score is a diagnostic
                      website-friction index, not a claim that a
                      specific percentage of revenue has been lost.
                    </p>
                  </article>

                  <article>
                    <h3>Can I share the report?</h3>
                    <p>
                      Yes. The paid report includes a branded PDF that
                      can be downloaded and shared with your team,
                      developer, agency, or stakeholder.
                    </p>
                  </article>
                </div>

                <div className="final-cta">
                  <div>
                    <span className="section-label">
                      READY TO CHECK YOUR SITE?
                    </span>

                    <h2>
                      Find the leaks before more visitors hit them.
                    </h2>

                    <p>
                      Start with the free scan. Decide whether the
                      full report is worth unlocking after you see
                      the initial findings.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => navigateToSection("scan")}
                  >
                    Scan My Website
                    <ArrowRight size={19} />
                  </button>
                </div>
              </div>
            </section>
          </>
        )}

        {result && (
          <section className="results-page">
            <div className="results-container">
              <div className="results-topbar">
                <div>
                  <span className="section-label">
                    {fullReport
                      ? "FULL REPORT UNLOCKED"
                      : "WEBSITE SCAN COMPLETE"}
                  </span>

                  <h1>
                    {fullReport
                      ? "Full Revenue Leak Report"
                      : "Revenue Leak Report"}
                  </h1>

                  <p>
                    {activeReport?.website?.final_url}
                  </p>
                </div>

                <button
                  className="secondary-button"
                  onClick={resetScan}
                >
                  <RotateCcw size={17} />
                  Scan another site
                </button>
              </div>

              {paymentMessage && (
                <div className="payment-message">
                  <CheckCircle2 size={18} />
                  <span>{paymentMessage}</span>
                </div>
              )}

              {unlockError && fullReport && (
                <div className="error-box results-error">
                  <AlertTriangle size={18} />
                  {unlockError}
                </div>
              )}

              <div className="score-layout">
                <div className="main-score-card">
                  <div className="score-card-header">
                    <div>
                      <span className="score-label">
                        REVENUE LEAK SCORE
                      </span>

                      <p>
                        Website friction risk index
                      </p>
                    </div>

                    <Gauge size={27} />
                  </div>

                  <div className="score-main">
                    <span className="score-number">
                      {
                        activeReport.revenue_leak
                          .leak_score
                      }
                    </span>

                    <span className="score-total">
                      /100
                    </span>
                  </div>

                  <div
                    className={`risk-pill ${getRiskClass(
                      activeReport.revenue_leak
                        .risk_level
                    )}`}
                  >
                    {
                      activeReport.revenue_leak
                        .risk_level
                    }{" "}
                    Risk
                  </div>

                  <p className="score-disclaimer">
                    This score is a diagnostic risk index,
                    not an estimate of revenue percentage lost.
                  </p>
                </div>

                <div className="category-grid">
                  <div className="category-card">
                    <span>SEO</span>

                    <strong>
                      {formatCategoryScore(
                        activeReport.revenue_leak
                          .category_scores.seo
                      )}
                    </strong>

                    <div className="progress-track">
                      <div
                        className="progress-fill"
                        style={{
                          width: categoryWidth(
                            activeReport.revenue_leak
                              .category_scores.seo
                          ),
                        }}
                      />
                    </div>
                  </div>

                  <div className="category-card">
                    <span>Conversion</span>

                    <strong>
                      {formatCategoryScore(
                        activeReport.revenue_leak
                          .category_scores
                          .conversion
                      )}
                    </strong>

                    <div className="progress-track">
                      <div
                        className="progress-fill"
                        style={{
                          width: categoryWidth(
                            activeReport.revenue_leak
                              .category_scores
                              .conversion
                          ),
                        }}
                      />
                    </div>
                  </div>

                  <div className="category-card">
                    <span>Performance</span>

                    <strong>
                      {formatCategoryScore(
                        activeReport.revenue_leak
                          .category_scores
                          .performance
                      )}
                    </strong>

                    <div className="progress-track">
                      <div
                        className="progress-fill"
                        style={{
                          width: categoryWidth(
                            activeReport.revenue_leak
                              .category_scores
                              .performance
                          ),
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="summary-grid">
                <div className="summary-card">
                  <span>Total Issues</span>

                  <strong>
                    {
                      activeReport.revenue_leak
                        .total_issues
                    }
                  </strong>
                </div>

                <div className="summary-card">
                  <span>High Priority</span>

                  <strong>
                    {(
                      activeReport.revenue_leak
                        .critical_issues || 0
                    ) +
                      (activeReport.revenue_leak
                        .high_issues || 0)}
                  </strong>
                </div>

                <div className="summary-card">
                  <span>Page Load</span>

                  <strong>
                    {activeReport.performance
                      ?.load_time_ms
                      ? `${(
                          activeReport.performance
                            .load_time_ms / 1000
                        ).toFixed(2)}s`
                      : "N/A"}
                  </strong>
                </div>

                <div className="summary-card">
                  <span>Requests</span>

                  <strong>
                    {activeReport.performance
                      ?.requests_count ?? "N/A"}
                  </strong>
                </div>
              </div>

              {!fullReport && (
                <div className="issues-section">
                  <div className="issues-heading">
                    <div>
                      <span className="section-label">
                        TOP FINDINGS
                      </span>

                      <h2>
                        Your biggest potential leaks
                      </h2>
                    </div>

                    <span className="free-badge">
                      Free report
                    </span>
                  </div>

                  {result.revenue_leak.top_issues
                    ?.length === 0 ? (
                    <div className="clean-result">
                      <CheckCircle2 size={28} />

                      <div>
                        <h3>
                          No major issues detected
                        </h3>

                        <p>
                          This page performed well across
                          the checks in this scan.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="issue-list">
                      {result.revenue_leak.top_issues.map(
                        (issue, index) => (
                          <div
                            className="issue-card"
                            key={`${issue.type}-${index}`}
                          >
                            <div className="issue-number">
                              {index + 1}
                            </div>

                            <div className="issue-content">
                              <div className="issue-title-row">
                                <h3>
                                  {issue.message}
                                </h3>

                                <span
                                  className={`severity ${getSeverityClass(
                                    issue.severity
                                  )}`}
                                >
                                  {issue.severity}
                                </span>
                              </div>

                              {issue.business_impact && (
                                <p>
                                  <strong>
                                    Why it matters:
                                  </strong>{" "}
                                  {
                                    issue.business_impact
                                  }
                                </p>
                              )}

                              <p>
                                <strong>
                                  Recommended fix:
                                </strong>{" "}
                                {
                                  issue.recommendation
                                }
                              </p>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                  {unlockError && (
                    <div className="error-box">
                      <AlertTriangle size={18} />
                      {unlockError}
                    </div>
                  )}

                  <div className="upsell-card">
                    <div>
                      <span className="upsell-label">
                        FULL REPORT
                      </span>

                      <h3>
                        We found{" "}
                        {
                          result.revenue_leak
                            .total_issues
                        }{" "}
                        total potential issues.
                      </h3>

                      <p>
                        Get every finding, AI executive analysis,
                        prioritized fixes, a 30-day action plan,
                        and the downloadable PDF report.
                      </p>
                    </div>

                    <button
                      onClick={handleUnlockReport}
                      disabled={unlocking}
                    >
                      {unlocking ? (
                        <>
                          <span className="spinner" />
                          Unlocking...
                        </>
                      ) : (
                        <>
                          <CreditCard size={18} />
                          Unlock Full Report — $29
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {fullReport && aiAnalysis && (
                <div className="ai-report">
                  <section className="ai-executive-card">
                    <div className="ai-section-icon">
                      <Sparkles size={21} />
                    </div>

                    <div>
                      <span className="section-label">
                        AI EXECUTIVE SUMMARY
                      </span>
                      <h2>What this scan means for the business</h2>
                      <p>{aiAnalysis.executive_summary}</p>
                    </div>
                  </section>

                  {aiAnalysis.business_risks?.length > 0 && (
                    <section className="ai-section">
                      <div className="ai-section-heading">
                        <div>
                          <span className="section-label">
                            BUSINESS RISKS
                          </span>
                          <h2>Where the website may be losing opportunities</h2>
                        </div>
                        <AlertTriangle size={24} />
                      </div>

                      <div className="ai-card-grid">
                        {aiAnalysis.business_risks.map((risk, index) => (
                          <article className="ai-detail-card" key={`${risk.title}-${index}`}>
                            <div className="ai-card-top">
                              <span className="ai-index">
                                {String(index + 1).padStart(2, "0")}
                              </span>
                              <span
                                className={`severity ${getSeverityClass(
                                  risk.severity
                                )}`}
                              >
                                {risk.severity}
                              </span>
                            </div>
                            <h3>{risk.title}</h3>
                            <p>{risk.explanation}</p>
                            <div className="ai-impact">
                              <strong>Business impact</strong>
                              <span>{risk.business_impact}</span>
                            </div>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}

                  {aiAnalysis.prioritized_fixes?.length > 0 && (
                    <section className="ai-section">
                      <div className="ai-section-heading">
                        <div>
                          <span className="section-label">
                            PRIORITIZED ACTION PLAN
                          </span>
                          <h2>Fix these first</h2>
                        </div>
                        <ClipboardCheck size={24} />
                      </div>

                      <div className="priority-list">
                        {aiAnalysis.prioritized_fixes.map((fix, index) => (
                          <article className="priority-card" key={`${fix.title}-${index}`}>
                            <div className="priority-number">
                              #{fix.priority || index + 1}
                            </div>
                            <div className="priority-content">
                              <div className="priority-title-row">
                                <h3>{fix.title}</h3>
                                <div className="priority-tags">
                                  <span>{fix.category}</span>
                                  <span
                                    className={`severity ${getSeverityClass(
                                      fix.severity
                                    )}`}
                                  >
                                    {fix.severity}
                                  </span>
                                </div>
                              </div>
                              <p>
                                <strong>Why it matters:</strong>{" "}
                                {fix.why_it_matters}
                              </p>
                              <p>
                                <strong>Recommended action:</strong>{" "}
                                {fix.recommended_action}
                              </p>
                            </div>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}

                  {aiAnalysis.quick_wins?.length > 0 && (
                    <section className="ai-section">
                      <div className="ai-section-heading">
                        <div>
                          <span className="section-label">
                            QUICK WINS
                          </span>
                          <h2>High-value improvements you can start now</h2>
                        </div>
                        <Rocket size={24} />
                      </div>

                      <div className="quick-win-grid">
                        {aiAnalysis.quick_wins.map((win, index) => (
                          <article className="quick-win-card" key={`${win.title}-${index}`}>
                            <CheckCircle2 size={20} />
                            <h3>{win.title}</h3>
                            <p>{win.action}</p>
                            <div>
                              <strong>Expected benefit</strong>
                              <span>{win.expected_benefit}</span>
                            </div>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}

                  {aiAnalysis.thirty_day_plan?.length > 0 && (
                    <section className="ai-section">
                      <div className="ai-section-heading">
                        <div>
                          <span className="section-label">
                            30-DAY IMPROVEMENT PLAN
                          </span>
                          <h2>A practical month-long roadmap</h2>
                        </div>
                        <CalendarDays size={24} />
                      </div>

                      <div className="plan-grid">
                        {aiAnalysis.thirty_day_plan.map((week, index) => (
                          <article className="plan-card" key={`${week.period}-${index}`}>
                            <span className="plan-period">{week.period}</span>
                            <h3>{week.focus}</h3>
                            <ul>
                              {(week.actions || []).map((action, actionIndex) => (
                                <li key={`${action}-${actionIndex}`}>
                                  <CheckCircle2 size={15} />
                                  <span>{action}</span>
                                </li>
                              ))}
                            </ul>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}
                </div>
              )}

              {fullReport && (
                <div className="issues-section">
                  <div className="issues-heading">
                    <div>
                      <span className="section-label">
                        COMPLETE ANALYSIS
                      </span>

                      <h2>
                        All detected website issues
                      </h2>
                    </div>

                    <span className="free-badge">
                      <LockOpen size={13} />
                      Full report
                    </span>
                  </div>

                  {allFullIssues.length === 0 ? (
                    <div className="clean-result">
                      <CheckCircle2 size={28} />

                      <div>
                        <h3>
                          No significant issues detected
                        </h3>

                        <p>
                          This website performed strongly
                          across the current LeakLens checks.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="issue-list">
                      {allFullIssues.map(
                        (issue, index) => (
                          <div
                            className="issue-card"
                            key={`${issue.type}-${index}`}
                          >
                            <div className="issue-number">
                              {index + 1}
                            </div>

                            <div className="issue-content">
                              <div className="issue-title-row">
                                <h3>
                                  {issue.message}
                                </h3>

                                <span
                                  className={`severity ${getSeverityClass(
                                    issue.severity
                                  )}`}
                                >
                                  {issue.severity}
                                </span>
                              </div>

                              <p>
                                <strong>
                                  Category:
                                </strong>{" "}
                                {issue.category ||
                                  "SEO"}
                              </p>

                              {issue.business_impact && (
                                <p>
                                  <strong>
                                    Why it matters:
                                  </strong>{" "}
                                  {
                                    issue.business_impact
                                  }
                                </p>
                              )}

                              <p>
                                <strong>
                                  Recommended fix:
                                </strong>{" "}
                                {
                                  issue.recommendation
                                }
                              </p>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                  <div className="upsell-card">
                    <div>
                      <span className="upsell-label">
                        REPORT UNLOCKED
                      </span>

                      <h3>
                        Full technical findings are now
                        available.
                      </h3>

                      <p>
                        Your full AI-powered report is unlocked.
                        Review the complete findings above or download
                        the finished PDF report.
                      </p>
                    </div>

                    <button
                      onClick={handleDownloadPdf}
                      disabled={downloadingPdf}
                    >
                      {downloadingPdf ? (
                        <>
                          <span className="spinner" />
                          Preparing PDF...
                        </>
                      ) : (
                        <>
                          <Download size={18} />
                          Download PDF Report
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      <footer className="site-footer">
        <div className="site-footer-inner">
          <div className="footer-brand">
            <strong>LeakLens</strong>
            <span>Find the website issues costing you revenue.</span>
          </div>

          <nav className="footer-links" aria-label="Legal and support links">
            <a href="/privacy">Privacy</a>
            <a href="/terms">Terms</a>
            <a href="/refund">Refund</a>
            <a href="/contact">Contact</a>
          </nav>

          <div className="footer-meta">
            © {new Date().getFullYear()} LeakLens. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;