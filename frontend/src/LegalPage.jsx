const SUPPORT_EMAIL = "leaklen.support@gmail.com";

const pageContent = {
  privacy: {
    label: "PRIVACY POLICY",
    title: "Privacy Policy",
    paragraphs: [
      "LeakLens collects only the information needed to provide website scans, process payments, generate reports, and support customers.",
      "When you submit a website URL, LeakLens may temporarily process publicly accessible website content and technical metadata in order to generate the requested audit.",
      "Payment information is processed by Stripe. LeakLens does not store complete payment card details.",
      "We may retain report data, scan results, payment status, and support communications for service operation, troubleshooting, and customer support.",
    ],
    contactText: "For privacy questions or data-related requests, contact",
  },

  terms: {
    label: "TERMS OF SERVICE",
    title: "Terms of Service",
    paragraphs: [
      "LeakLens provides automated website diagnostics and AI-assisted recommendations for informational purposes only.",
      "You are responsible for ensuring that you have permission to scan any website you submit and for reviewing findings before making technical, business, SEO, or conversion-related changes.",
      "Scan results may vary because websites, third-party scripts, network conditions, and browser behavior can change over time.",
      "LeakLens does not guarantee specific rankings, traffic increases, conversion improvements, revenue gains, or business outcomes.",
      "By using LeakLens, you agree not to misuse the service, attempt to disrupt its infrastructure, bypass usage limits, or use it for unlawful activity.",
    ],
    contactText: "Questions about these terms can be sent to",
  },

  refund: {
    label: "REFUND POLICY",
    title: "Refund Policy",
    paragraphs: [
      "LeakLens sells one-time digital website reports that are generated and delivered electronically after purchase.",
      "Because the report is a digital product, purchases are generally non-refundable once the full report has been successfully unlocked or delivered.",
      "Refunds may be considered for duplicate charges, confirmed payment errors, or technical failures that prevent delivery of the purchased report.",
    ],
    contactText:
      "If you experience a billing or delivery problem, contact us as soon as possible at",
    contactSuffix: "with the website scanned and details of the issue.",
  },

  contact: {
    label: "CONTACT",
    title: "Need help with LeakLens?",
    paragraphs: [
      "For support, billing questions, report issues, or general inquiries, email us at",
    ],
    contactOnly: true,
  },
};

function LegalPage({ page, onHome }) {
  const content = pageContent[page];

  if (!content) {
    return null;
  }

  return (
    <main className="legal-page-shell">
      <section className="legal-page-section standalone-legal-page">
        <div className="legal-page-card">
          <button
            type="button"
            className="legal-back-button"
            onClick={onHome}
          >
            ← Back to LeakLens
          </button>

          <span className="section-label">{content.label}</span>
          <h1>{content.title}</h1>

          {content.contactOnly ? (
            <p>
              {content.paragraphs[0]}{" "}
              <a href={`mailto:${SUPPORT_EMAIL}`}>
                {SUPPORT_EMAIL}
              </a>
              .
            </p>
          ) : (
            <>
              {content.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}

              <p>
                {content.contactText}{" "}
                <a href={`mailto:${SUPPORT_EMAIL}`}>
                  {SUPPORT_EMAIL}
                </a>
                {content.contactSuffix
                  ? ` ${content.contactSuffix}`
                  : "."}
              </p>
            </>
          )}
        </div>
      </section>
    </main>
  );
}

export default LegalPage;
