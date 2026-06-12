/**
 * NoCashFlow · newsletter subscribe endpoint (Cloudflare Worker)
 *
 * Route:  POST nocashflow.net/api/subscribe   body: {"email": "...", "lang": "tr"|"en"}
 * Adds the address to the matching Resend Audience — the same audiences the
 * bulletin pipeline already sends to (RESEND_AUDIENCE_TR / RESEND_AUDIENCE_EN).
 *
 * Secrets (wrangler secret put <NAME>):
 *   RESEND_API_KEY       — same key the newsletter repo uses
 *   RESEND_AUDIENCE_TR   — Resend audience id for the Turkish list
 *   RESEND_AUDIENCE_EN   — Resend audience id for the English list
 */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors() });
    }
    if (request.method !== "POST") {
      return json({ ok: false, error: "method_not_allowed" }, 405);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ ok: false, error: "bad_json" }, 400);
    }

    const email = String(body.email || "").trim().toLowerCase();
    const lang = body.lang === "tr" ? "tr" : "en";
    if (!EMAIL_RE.test(email) || email.length > 254) {
      return json({ ok: false, error: "invalid_email" }, 400);
    }

    const audienceId = lang === "tr" ? env.RESEND_AUDIENCE_TR : env.RESEND_AUDIENCE_EN;
    if (!env.RESEND_API_KEY || !audienceId) {
      return json({ ok: false, error: "not_configured" }, 503);
    }

    const r = await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, unsubscribed: false }),
    });

    if (r.ok || r.status === 409) {
      // 409 = already subscribed — treat as success for the user
      return json({ ok: true }, 200);
    }
    return json({ ok: false, error: "upstream" }, 502);
  },
};

function cors() {
  return {
    "Access-Control-Allow-Origin": "https://nocashflow.net",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors() },
  });
}
