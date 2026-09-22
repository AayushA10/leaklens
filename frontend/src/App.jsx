import { useEffect, useMemo, useState } from "react";
import {
  Show,
  SignInButton,
  UserButton,
  useAuth,
} from "@clerk/react";
import {
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
  const { getToken, isSignedIn } = useAuth();

  const authenticatedFetch = async (
    endpoint,
    options = {}
  ) => {
    const token = await getToken();

    if (!token) {
      throw new Error(
        "Please sign in to access monitoring."
      );
    }

    const headers = new Headers(
      options.headers || {}
    );

    headers.set(
      "Authorization",
      `Bearer ${token}`
    );

    return fetch(
      `${API_BASE_URL}${endpoint}`,
      {
        ...options,
        headers,
      }
    );
  };

  const startSubscriptionManagement = async () => {
    try {
      const response = await authenticatedFetch(
        "/account/subscription/manage",
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Unable to open subscription management."
        );
      }

      if (!data.portal_url) {
        throw new Error(
          "Subscription management URL was not returned."
        );
      }

      window.location.href = data.portal_url;
    } catch (error) {
      window.alert(
        error.message ||
          "Unable to open subscription management."
      );
    }
  };

  const startSubscriptionCheckout = async (plan) => {
    try {
      const response = await authenticatedFetch(
        `/account/subscription/checkout?plan=${encodeURIComponent(plan)}`,
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
            "Unable to start subscription checkout."
        );
      }

      if (!data?.checkout_url) {
        throw new Error(
          "Stripe checkout URL was not returned."
        );
      }

      window.location.href = data.checkout_url;
    } catch (error) {
      console.error(
        "Unable to start subscription checkout:",
        error
      );

      window.alert(
        error?.message ||
          "Unable to start subscription checkout."
      );
    }
  };

  const getApiErrorMessage = (data, fallback) => {
    const detail = data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (detail && typeof detail === "object") {
      return detail.message || detail.detail || fallback;
    }

    return fallback;
  };

  const createMonitoredSite = async (
    websiteUrl,
    websiteTitle = null
  ) => {
    const response = await authenticatedFetch(
      "/monitoring/sites",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          website_url: websiteUrl,
          website_title: websiteTitle,
        }),
      }
    );

    const data = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        getApiErrorMessage(
          data,
          "Unable to add website monitoring."
        )
      );
    }

    return data;
  };

  const handleAddMonitoringSite = async (event) => {
    event.preventDefault();

    const websiteUrl = newMonitoringUrl.trim();

    if (!websiteUrl) {
      setDashboardError("Please enter a website URL.");
      return;
    }

    setAddingMonitoringSite(true);
    setDashboardError("");

    try {
      const data = await createMonitoredSite(websiteUrl);

      if (!data?.site) {
        throw new Error("Unable to add website monitoring.");
      }

      setNewMonitoringUrl("");

      window.location.href = `/dashboard/${data.site.site_id}`;
    } catch (error) {
      setDashboardError(
        error.message || "Unable to add website monitoring."
      );
    } finally {
      setAddingMonitoringSite(false);
    }
  };

  const legalPages = ["privacy", "terms", "refund", "contact"];
  const currentPath = window.location.pathname
    .replace(/^\/+|\/+$/g, "")
    .toLowerCase();

  const activeLegalPage = legalPages.includes(currentPath)
    ? currentPath
    : null;

  const dashboardParts = currentPath.split("/");

  const isDashboardPage =
    dashboardParts[0] === "dashboard";

  const dashboardSiteId =
    dashboardParts.length === 2
      ? dashboardParts[1]
      : null;

  const isDashboardDetailPage =
    Boolean(dashboardSiteId);

  const goDashboard = () => {
    window.location.href = "/dashboard";
  };

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

  const [monitoredSites, setMonitoredSites] = useState([]);
  const [dashboardLoading, setDashboardLoading] = useState(isDashboardPage);
  const [dashboardError, setDashboardError] = useState("");
  const [monitorScanLoading, setMonitorScanLoading] = useState(false);
  const [monitorScanMessage, setMonitorScanMessage] = useState("");
  const [monitorAiLoading, setMonitorAiLoading] = useState(false);
  const [monitorAiAnalysis, setMonitorAiAnalysis] = useState(null);
  const [monitorAiMessage, setMonitorAiMessage] = useState("");
  const [newMonitoringUrl, setNewMonitoringUrl] = useState("");
  const [addingMonitoringSite, setAddingMonitoringSite] = useState(false);
  const [accountPlan, setAccountPlan] = useState(null);

  useEffect(() => {
    if (!isDashboardPage || !isSignedIn) {
      return;
    }

    setDashboardLoading(true);
    setDashboardError("");

    authenticatedFetch("/account/plan")
      .then(async (response) => {
        const data = await response
          .json()
          .catch(() => ({}));

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              "Unable to load account plan."
          );
        }

        setAccountPlan(data);
      })
      .catch((error) => {
        console.error(
          "Unable to load account plan:",
          error
        );
      });

    authenticatedFetch("/monitoring/sites")
      .then(async (response) => {
        const data = await response
          .json()
          .catch(() => ({}));

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              "Unable to load monitored websites."
          );
        }

        const sites = data?.sites || [];

        const enrichedSites = await Promise.all(
          sites.map(async (site) => {
            const [
              issuesResponse,
              resolvedIssuesResponse,
              historyResponse,
            ] = await Promise.all([
              authenticatedFetch(
                `/monitoring/sites/${site.site_id}/issues?status=open`
              ),
              authenticatedFetch(
                `/monitoring/sites/${site.site_id}/issues?status=resolved`
              ),
              authenticatedFetch(
                `/monitoring/sites/${site.site_id}/history?limit=30`
              ),
            ]);

            const issuesData = await issuesResponse
              .json()
              .catch(() => ({}));

            const resolvedIssuesData =
              await resolvedIssuesResponse
                .json()
                .catch(() => ({}));

            const historyData = await historyResponse
              .json()
              .catch(() => ({}));

            if (!issuesResponse.ok) {
              throw new Error(
                issuesData?.detail ||
                  "Unable to load monitoring issues."
              );
            }

            if (!resolvedIssuesResponse.ok) {
              throw new Error(
                resolvedIssuesData?.detail ||
                  "Unable to load resolved issues."
              );
            }

            if (!historyResponse.ok) {
              throw new Error(
                historyData?.detail ||
                  "Unable to load scan history."
              );
            }

            return {
              ...site,
              open_issues:
                issuesData?.issues || [],
              resolved_issues:
                resolvedIssuesData?.issues || [],
              scan_history:
                historyData?.history || [],
            };
          })
        );

        setMonitoredSites(
          enrichedSites
        );
      })
      .catch((error) => {
        setDashboardError(
          error.message ||
            "Unable to load monitored websites."
        );
      })
      .finally(() => {
        setDashboardLoading(false);
      });
  }, [isDashboardPage, isSignedIn]);

  const handleMonitoringScan = async () => {
    if (!dashboardSiteId) {
      return;
    }

    setMonitorScanLoading(true);
    setMonitorScanMessage("");
    setDashboardError("");

    try {
      const scanResponse = await authenticatedFetch(
        `/monitoring/sites/${dashboardSiteId}/scan`,
        {
          method: "POST",
        }
      );

      const scanData = await scanResponse
        .json()
        .catch(() => ({}));

      if (!scanResponse.ok) {
        throw new Error(
          scanData?.detail ||
            "Unable to run monitoring scan."
        );
      }

      const [
        siteResponse,
        issuesResponse,
        resolvedIssuesResponse,
        historyResponse,
      ] = await Promise.all([
        authenticatedFetch(
          `/monitoring/sites/${dashboardSiteId}`
        ),
        authenticatedFetch(
          `/monitoring/sites/${dashboardSiteId}/issues?status=open`
        ),
        authenticatedFetch(
          `/monitoring/sites/${dashboardSiteId}/issues?status=resolved`
        ),
        authenticatedFetch(
          `/monitoring/sites/${dashboardSiteId}/history?limit=30`
        ),
      ]);

      const siteData = await siteResponse
        .json()
        .catch(() => ({}));

      const issuesData = await issuesResponse
        .json()
        .catch(() => ({}));

      const resolvedIssuesData =
        await resolvedIssuesResponse
          .json()
          .catch(() => ({}));

      const historyData = await historyResponse
        .json()
        .catch(() => ({}));

      if (!siteResponse.ok) {
        throw new Error(
          siteData?.detail ||
            "Unable to refresh monitored website."
        );
      }

      if (!issuesResponse.ok) {
        throw new Error(
          issuesData?.detail ||
            "Unable to refresh monitoring issues."
        );
      }

      if (!resolvedIssuesResponse.ok) {
        throw new Error(
          resolvedIssuesData?.detail ||
            "Unable to refresh resolved issues."
        );
      }

      if (!historyResponse.ok) {
        throw new Error(
          historyData?.detail ||
            "Unable to refresh scan history."
        );
      }

      setMonitoredSites((currentSites) =>
        currentSites.map((site) =>
          site.site_id === dashboardSiteId
            ? {
                ...site,
                ...(siteData?.site || {}),
                open_issues:
                  issuesData?.issues || [],
                resolved_issues:
                  resolvedIssuesData?.issues || [],
                scan_history:
                  historyData?.history || [],
              }
            : site
        )
      );

      setMonitorScanMessage(
        "Scan completed. Monitoring data has been refreshed."
      );
    } catch (error) {
      setDashboardError(
        error.message ||
          "Unable to run monitoring scan."
      );
    } finally {
      setMonitorScanLoading(false);
    }
  };


  const handleMonitoringAiAnalysis = async () => {
    if (!dashboardSiteId) {
      return;
    }

    setMonitorAiLoading(true);
    setMonitorAiMessage("");
    setDashboardError("");

    try {
      const response = await authenticatedFetch(
        `/monitoring/sites/${dashboardSiteId}/ai-analysis`,
        {
          method: "POST",
        }
      );

      const data = await response
        .json()
        .catch(() => ({}));

      if (!response.ok) {
        const detail = data?.detail;

        const message =
          typeof detail === "string"
            ? detail
            : detail?.message ||
              "Unable to generate AI analysis.";

        throw new Error(message);
      }

      setMonitorAiAnalysis(
        data?.analysis || null
      );

      setMonitorAiMessage(
        `AI analysis generated. ${data?.usage?.remaining ?? 0} analyses remaining this month.`
      );

      const planResponse = await authenticatedFetch(
        "/account/plan"
      );

      const planData = await planResponse
        .json()
        .catch(() => ({}));

      if (planResponse.ok) {
        setAccountPlan(planData);
      }
    } catch (error) {
      setDashboardError(
        error.message ||
          "Unable to generate AI analysis."
      );
    } finally {
      setMonitorAiLoading(false);
    }
  };


  const handleMonitoringToggle = async () => {
    if (!dashboardSiteId) {
      return;
    }

    setMonitorScanLoading(true);
    setMonitorScanMessage("");
    setDashboardError("");

    try {
      const response = await authenticatedFetch(
        `/monitoring/sites/${dashboardSiteId}/toggle`,
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
            "Unable to update monitoring."
        );
      }

      setMonitoredSites((currentSites) =>
        currentSites.map((site) =>
          site.site_id === dashboardSiteId
            ? {
                ...site,
                monitoring_enabled:
                  data.monitoring_enabled,
                next_scan_at:
                  data.next_scan_at,
              }
            : site
        )
      );
    } catch (error) {
      setDashboardError(
        error.message ||
          "Unable to update monitoring."
      );
    } finally {
      setMonitorScanLoading(false);
    }
  };

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

  useEffect(() => {
    if (isDashboardPage || activeLegalPage) {
      return;
    }

    const sectionId = window.location.hash.replace("#", "");

    if (!sectionId) {
      return;
    }

    const timer = window.setTimeout(() => {
      const target = document.getElementById(sectionId);

      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    }, 100);

    return () => window.clearTimeout(timer);
  }, [isDashboardPage, activeLegalPage]);

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

  const selectedDashboardSite =
    dashboardSiteId
      ? monitoredSites.find(
          (site) =>
            site.site_id === dashboardSiteId
        ) || null
      : null;

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

  if (isDashboardPage) {
    return (
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <button
              className="logo logo-button"
              type="button"
              onClick={goHome}
              aria-label="Go to LeakLens home"
            >
              <div className="logo-icon">
                <TrendingUp size={20} />
              </div>

              <span>
                Leak<span className="logo-accent">Lens</span>
              </span>
            </button>

            <div className="nav-actions">
              <button
                className="nav-button"
                type="button"
                onClick={goHome}
              >
                Free Scan
              </button>

              <Show when="signed-in">
                <UserButton />
              </Show>
            </div>
          </div>
        </nav>

        <main>
          <section className="dashboard-page">
            <div className="landing-container">
              {dashboardLoading && (
                <p>
                  Loading monitoring data...
                </p>
              )}

              {dashboardError && (
                <div className="error-message">
                  {dashboardError}
                </div>
              )}

              {!dashboardLoading &&
                !dashboardError &&
                isDashboardDetailPage &&
                selectedDashboardSite && (
                  <div className="dashboard-detail">
                    <button
                      className="nav-button"
                      type="button"
                      onClick={goDashboard}
                    >
                      ← Back to Dashboard
                    </button>

                    <div className="dashboard-detail-header">
                      <div className="dashboard-detail-actions">
                        <button
                          className="section-cta"
                          type="button"
                          onClick={handleMonitoringScan}
                          disabled={monitorScanLoading}
                        >
                          {monitorScanLoading
                            ? "Scanning..."
                            : "Scan Now"}
                        </button>

                        <button
                          className="section-cta"
                          type="button"
                          onClick={handleMonitoringToggle}
                          disabled={monitorScanLoading}
                        >
                          {selectedDashboardSite.monitoring_enabled
                            ? "Pause Monitoring"
                            : "Resume Monitoring"}
                        </button>

                        <button
                          className="section-cta"
                          type="button"
                          onClick={handleMonitoringAiAnalysis}
                          disabled={
                            monitorAiLoading ||
                            monitorScanLoading
                          }
                        >
                          {monitorAiLoading
                            ? "Analyzing..."
                            : "Analyze with AI"}
                        </button>
                      </div>

                      {monitorScanMessage && (
                        <div className="monitoring-message">
                          {monitorScanMessage}
                        </div>
                      )}

                      <span className="section-label">
                        {selectedDashboardSite.monitoring_enabled
                          ? "MONITORING ACTIVE"
                          : "MONITORING PAUSED"}
                      </span>

                      <h1>
                        {selectedDashboardSite.website_title ||
                          selectedDashboardSite.website_url}
                      </h1>

                      <p>
                        {selectedDashboardSite.website_url}
                      </p>
                    </div>

                    {monitorAiMessage && (
                      <div className="monitoring-message">
                        {monitorAiMessage}
                      </div>
                    )}

                    {monitorAiAnalysis && (
                      <div className="dashboard-ai-analysis">
                        <span className="section-label">
                          AI ANALYSIS
                        </span>

                        {monitorAiAnalysis.executive_summary && (
                          <div>
                            <h2>Executive Summary</h2>
                            <p>
                              {monitorAiAnalysis.executive_summary}
                            </p>
                          </div>
                        )}

                        {monitorAiAnalysis.business_risks?.length > 0 && (
                          <div>
                            <h3>Business Risks</h3>
                            <ul>
                              {monitorAiAnalysis.business_risks.map(
                                (risk, index) => (
                                  <li key={`risk-${index}`}>
                                    {typeof risk === "string"
                                      ? risk
                                      : risk?.description ||
                                        risk?.title ||
                                        JSON.stringify(risk)}
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}

                        {monitorAiAnalysis.prioritized_fixes?.length > 0 && (
                          <div>
                            <h3>Prioritized Fixes</h3>
                            <ul>
                              {monitorAiAnalysis.prioritized_fixes.map(
                                (fix, index) => (
                                  <li key={`fix-${index}`}>
                                    {typeof fix === "string"
                                      ? fix
                                      : fix?.recommendation ||
                                        fix?.description ||
                                        fix?.title ||
                                        JSON.stringify(fix)}
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}

                        {monitorAiAnalysis.quick_wins?.length > 0 && (
                          <div>
                            <h3>Quick Wins</h3>
                            <ul>
                              {monitorAiAnalysis.quick_wins.map(
                                (win, index) => (
                                  <li key={`win-${index}`}>
                                    {typeof win === "string"
                                      ? win
                                      : win?.recommendation ||
                                        win?.description ||
                                        win?.title ||
                                        JSON.stringify(win)}
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="dashboard-site-meta">
                      <div>
                        <strong>
                          {
                            selectedDashboardSite
                              .open_issues?.length || 0
                          }
                        </strong>
                        <span>Open issues</span>
                      </div>

                      <div>
                        <strong>
                          {
                            selectedDashboardSite
                              .scan_history?.length || 0
                          }
                        </strong>
                        <span>Scans recorded</span>
                      </div>

                      <div>
                        <strong>
                          {selectedDashboardSite.scan_frequency ||
                            "daily"}
                        </strong>
                        <span>Scan frequency</span>
                      </div>

                      <div>
                        <strong>Last scan</strong>
                        <span>
                          {selectedDashboardSite.last_scanned_at
                            ? new Date(
                                selectedDashboardSite
                                  .last_scanned_at
                              ).toLocaleString()
                            : "Not scanned yet"}
                        </span>
                      </div>

                      <div>
                        <strong>Next scan</strong>
                        <span>
                          {selectedDashboardSite.next_scan_at
                            ? new Date(
                                selectedDashboardSite
                                  .next_scan_at
                              ).toLocaleString()
                            : "Not scheduled"}
                        </span>
                      </div>
                    </div>

                    <section className="dashboard-detail-section">
                      <span className="section-label">
                        OPEN ISSUES
                      </span>

                      <h2>
                        Revenue leaks currently detected
                      </h2>

                      {selectedDashboardSite.open_issues?.length ? (
                        <div className="dashboard-issues">
                          {selectedDashboardSite.open_issues.map(
                            (issue) => (
                              <article
                                className="dashboard-issue-card"
                                key={issue.issue_id}
                              >
                                <div>
                                  <span
                                    className={`severity ${getSeverityClass(
                                      issue.severity
                                    )}`}
                                  >
                                    {issue.severity}
                                  </span>

                                  <span>
                                    {issue.category}
                                  </span>
                                </div>

                                <h3>
                                  {issue.issue_type
                                    .replaceAll("_", " ")}
                                </h3>

                                <p>
                                  {issue.message}
                                </p>

                                {issue.recommendation && (
                                  <p>
                                    <strong>
                                      Recommended fix:
                                    </strong>{" "}
                                    {issue.recommendation}
                                  </p>
                                )}

                                <small>
                                  First seen:{" "}
                                  {new Date(
                                    issue.first_seen_at
                                  ).toLocaleString()}
                                </small>
                              </article>
                            )
                          )}
                        </div>
                      ) : (
                        <p>
                          No open issues detected.
                        </p>
                      )}
                    </section>

                    <section className="dashboard-detail-section">
                      <span className="section-label">
                        RESOLVED ISSUES
                      </span>

                      <h2>
                        Revenue leaks fixed since monitoring began
                      </h2>

                      {selectedDashboardSite.resolved_issues?.length ? (
                        <div className="dashboard-issues">
                          {selectedDashboardSite.resolved_issues.map(
                            (issue) => (
                              <article
                                className="dashboard-issue-card"
                                key={issue.issue_id}
                              >
                                <div>
                                  <span className="section-label">
                                    RESOLVED
                                  </span>

                                  <span>
                                    {issue.category}
                                  </span>
                                </div>

                                <h3>
                                  {issue.issue_type
                                    .replaceAll("_", " ")}
                                </h3>

                                <p>
                                  {issue.message}
                                </p>

                                <small>
                                  Resolved:{" "}
                                  {issue.resolved_at
                                    ? new Date(
                                        issue.resolved_at
                                      ).toLocaleString()
                                    : "Unknown"}
                                </small>
                              </article>
                            )
                          )}
                        </div>
                      ) : (
                        <p>
                          No resolved issues yet.
                        </p>
                      )}
                    </section>

                    <section className="dashboard-detail-section">
                      <span className="section-label">
                        SCAN HISTORY
                      </span>

                      <h2>
                        Monitoring activity
                      </h2>

                      {selectedDashboardSite.scan_history?.length ? (
                        <div className="dashboard-history">
                          {selectedDashboardSite.scan_history.map(
                            (snapshot, index) => (
                              <div
                                className="dashboard-history-row"
                                key={snapshot.snapshot_id}
                              >
                                <div>
                                  <strong>
                                    Scan #
                                    {
                                      selectedDashboardSite
                                        .scan_history.length -
                                      index
                                    }
                                  </strong>

                                  <span>
                                    {new Date(
                                      snapshot.created_at
                                    ).toLocaleString()}
                                  </span>
                                </div>

                                <span>
                                  {snapshot.success
                                    ? "Successful"
                                    : "Failed"}
                                </span>
                              </div>
                            )
                          )}
                        </div>
                      ) : (
                        <p>
                          No scan history yet.
                        </p>
                      )}
                    </section>
                  </div>
                )}

              {!dashboardLoading &&
                !dashboardError &&
                isDashboardDetailPage &&
                !selectedDashboardSite && (
                  <div className="dashboard-empty">
                    <h1>
                      Monitored website not found
                    </h1>

                    <button
                      className="section-cta"
                      type="button"
                      onClick={goDashboard}
                    >
                      Back to Dashboard
                    </button>
                  </div>
                )}

              {!dashboardLoading &&
                !dashboardError &&
                !isDashboardDetailPage && (
                  <>
                    <span className="section-label">
                      MONITORING
                    </span>

                    <h1>
                      LeakLens Dashboard
                    </h1>

                    <p>
                      Monitor website health, recurring scans,
                      and revenue leak issues from one place.
                    </p>

                    {accountPlan && (
                      <div className="dashboard-plan-card">
                        <div className="dashboard-plan-heading">
                          <div>
                            <span className="section-label">
                              CURRENT PLAN
                            </span>
                            <h2>
                              {accountPlan.name} Plan
                            </h2>
                          </div>

                          <strong className="dashboard-plan-price">
                            ${accountPlan.price_monthly}
                            <span>/mo</span>
                          </strong>
                        </div>

                        <div className="dashboard-plan-usage">
                          <div>
                            <strong>
                              {accountPlan.usage.monitored_sites}/
                              {accountPlan.limits.max_sites}
                            </strong>
                            <span>Websites</span>
                          </div>

                          <div>
                            <strong>
                              {accountPlan.usage.manual_scans}/
                              {accountPlan.limits.manual_scans_per_month}
                            </strong>
                            <span>Manual monitoring scans</span>
                          </div>

                          <div>
                            <strong>
                              {accountPlan.usage.ai_analyses}/
                              {accountPlan.limits.ai_analyses_per_month}
                            </strong>
                            <span>AI analyses</span>
                          </div>

                          <div>
                            <strong>
                              {accountPlan.limits.scan_frequency}
                            </strong>
                            <span>Monitoring</span>
                          </div>

                          <div>
                            <strong>
                              {accountPlan.limits.history_days} days
                            </strong>
                            <span>History</span>
                          </div>
                        </div>

                        {accountPlan.plan === "free" ? (
                          <button
                            className="pricing-button primary-pricing dashboard-upgrade-button"
                            type="button"
                            onClick={() => {
                              window.location.href = "/#pricing";
                            }}
                          >
                            View Upgrade Plans
                            <ArrowRight size={18} />
                          </button>
                        ) : (
                          <button
                            className="pricing-button primary-pricing dashboard-upgrade-button"
                            type="button"
                            onClick={startSubscriptionManagement}
                          >
                            Manage Subscription
                            <ArrowRight size={18} />
                          </button>
                        )}
                      </div>
                    )}

                    <form
                      className="dashboard-add-site"
                      onSubmit={handleAddMonitoringSite}
                    >
                      <input
                        type="url"
                        value={newMonitoringUrl}
                        onChange={(event) =>
                          setNewMonitoringUrl(event.target.value)
                        }
                        placeholder="https://example.com"
                        required
                        disabled={addingMonitoringSite}
                        aria-label="Website URL"
                      />

                      <button
                        className="section-cta"
                        type="submit"
                        disabled={addingMonitoringSite}
                      >
                        {addingMonitoringSite
                          ? "Adding..."
                          : "Add Website"}
                      </button>
                    </form>

                    {monitoredSites.length === 0 ? (
                      <div className="dashboard-empty">
                        <h2>
                          No monitored websites yet
                        </h2>

                        <p>
                          Add a website to start recurring
                          monitoring and issue tracking.
                        </p>

                        <button
                          className="section-cta"
                          type="button"
                          onClick={goHome}
                        >
                          Scan a Website
                        </button>
                      </div>
                    ) : (
                      <div className="dashboard-sites">
                        {monitoredSites.map((site) => (
                          <button
                            className="dashboard-site-card"
                            key={site.site_id}
                            type="button"
                            onClick={() => {
                              window.location.href =
                                `/dashboard/${site.site_id}`;
                            }}
                          >
                            <div>
                              <span className="section-label">
                                {site.monitoring_enabled
                                  ? "MONITORING ACTIVE"
                                  : "MONITORING PAUSED"}
                              </span>

                              <h2>
                                {site.website_title ||
                                  site.website_url}
                              </h2>

                              <p>
                                {site.website_url}
                              </p>
                            </div>

                            <div className="dashboard-site-meta">
                              <div>
                                <strong>
                                  {site.open_issues?.length || 0}
                                </strong>
                                <span>Open issues</span>
                              </div>

                              <div>
                                <strong>
                                  {site.scan_history?.length || 0}
                                </strong>
                                <span>Scans recorded</span>
                              </div>

                              <div>
                                <strong>
                                  {site.scan_frequency || "daily"}
                                </strong>
                                <span>Scan frequency</span>
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
            </div>
          </section>
        </main>
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
              <button
                className="nav-button"
                type="button"
                onClick={goDashboard}
              >
                Dashboard
              </button>

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
                    SIMPLE SAAS PRICING
                  </span>

                  <h2>
                    Keep revenue leaks from coming back.
                  </h2>

                  <p>
                    Start free, then upgrade as you add more
                    websites, scans, monitoring, and AI analysis.
                  </p>
                </div>

                <div className="pricing-grid">
                  <article className="pricing-card">
                    <div className="pricing-top">
                      <span className="pricing-name">
                        FREE
                      </span>

                      <div className="price">
                        <strong>$0</strong>
                        <span>/ month</span>
                      </div>

                      <p>
                        For trying LeakLens on one website with
                        lightweight ongoing monitoring.
                      </p>
                    </div>

                    <ul className="pricing-list">
                      <li>
                        <CheckCircle2 size={17} />
                        1 monitored website
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Weekly automatic monitoring
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        3 manual monitoring scans per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        2 AI analyses per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        7-day issue history
                      </li>
                    </ul>

                    <button
                      className="pricing-button secondary-pricing"
                      type="button"
                      onClick={isSignedIn ? goDashboard : () => navigateToSection("scan")}
                    >
                      Start Free
                      <ArrowRight size={18} />
                    </button>
                  </article>

                  <article className="pricing-card">
                    <div className="pricing-top">
                      <span className="pricing-name">
                        STARTER
                      </span>

                      <div className="price">
                        <strong>$5</strong>
                        <span>/ month</span>
                      </div>

                      <p>
                        For solo operators managing a few websites
                        and needing daily leak detection.
                      </p>
                    </div>

                    <ul className="pricing-list">
                      <li>
                        <CheckCircle2 size={17} />
                        3 monitored websites
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Daily automatic monitoring
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        20 manual monitoring scans per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        10 AI analyses per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        30-day issue history
                      </li>
                    </ul>

                    <button
                      className="pricing-button secondary-pricing"
                      type="button"
                      onClick={() =>
                        startSubscriptionCheckout("starter")
                      }
                    >
                      Choose Starter
                      <ArrowRight size={18} />
                    </button>
                  </article>

                  <article className="pricing-card paid-pricing-card">
                    <div className="pricing-badge">
                      MOST POPULAR
                    </div>

                    <div className="pricing-top">
                      <span className="pricing-name">
                        GROWTH
                      </span>

                      <div className="price">
                        <strong>$15</strong>
                        <span>/ month</span>
                      </div>

                      <p>
                        For growing businesses monitoring multiple
                        revenue-generating websites.
                      </p>
                    </div>

                    <ul className="pricing-list">
                      <li>
                        <CheckCircle2 size={17} />
                        10 monitored websites
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Daily automatic monitoring
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        100 manual monitoring scans per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        50 AI analyses per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        90-day issue history
                      </li>
                    </ul>

                    <button
                      className="pricing-button primary-pricing"
                      type="button"
                      onClick={() =>
                        startSubscriptionCheckout("growth")
                      }
                    >
                      Choose Growth
                      <ArrowRight size={18} />
                    </button>
                  </article>

                  <article className="pricing-card">
                    <div className="pricing-top">
                      <span className="pricing-name">
                        PRO
                      </span>

                      <div className="price">
                        <strong>$29</strong>
                        <span>/ month</span>
                      </div>

                      <p>
                        For agencies and teams managing larger
                        website portfolios.
                      </p>
                    </div>

                    <ul className="pricing-list">
                      <li>
                        <CheckCircle2 size={17} />
                        25 monitored websites
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        Daily automatic monitoring
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        300 manual monitoring scans per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        150 AI analyses per month
                      </li>
                      <li>
                        <CheckCircle2 size={17} />
                        1-year issue history
                      </li>
                    </ul>

                    <button
                      className="pricing-button secondary-pricing"
                      type="button"
                      onClick={() =>
                        startSubscriptionCheckout("pro")
                      }
                    >
                      Choose Pro
                      <ArrowRight size={18} />
                    </button>
                  </article>
                </div>

                <div className="pricing-assurance">
                  <ShieldCheck size={19} />
                  <span>
                    Start on Free with no recurring charge.
                    Upgrade only when you need more websites,
                    scans, history, or AI analysis.
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