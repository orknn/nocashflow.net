/**
 * NoCashFlow · newsletter subscription API (Cloudflare Worker + D1)
 *
 * Routes (all under nocashflow.net/api/*):
 *   POST /api/subscribe          {email, lang, hp}  · double opt-in, sends confirm mail
 *   GET  /api/confirm?token=...                     · status→confirmed, redirect to thank-you
 *   GET  /api/unsubscribe?token=...                 · status→unsubscribed, redirect
 *   GET  /api/subscribers?lang=tr  (Bearer ADMIN)   · confirmed list {email, token} for pipeline
 *
 * Store: D1 binding `DB` (table `subscribers`, see schema.sql).
 * Personal data lives ONLY in D1 — never in the repo.
 *
 * Secrets (wrangler secret put <NAME>):
 *   RESEND_API_KEY  — Resend transactional key (sends the confirm mail)
 *   ADMIN_TOKEN     — Bearer required by GET /api/subscribers
 */

// Where the static thank-you pages live (GitHub Pages, DNS-only on Cloudflare).
const SITE = "https://nocashflow.net";
// Where the Worker itself is reachable. nocashflow.net/* is NOT proxied, so the
// /api/* paths only resolve via the workers.dev hostname — every link that must
// hit the Worker (confirm, unsubscribe) is built from BASE, never SITE.
const BASE = "https://ncf-subscribe.bicenorkun.workers.dev";
const FROM = "NoCashFlow <noreply@nocashflow.net>";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, ""); // tolerate trailing slash

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors() });
    }

    try {
      if (path === "/api/subscribe" && request.method === "POST") {
        return await handleSubscribe(request, env);
      }
      if (path === "/api/confirm" && request.method === "GET") {
        return await handleConfirm(url, env);
      }
      if (path === "/api/unsubscribe" && request.method === "GET") {
        return await handleUnsubscribe(url, env);
      }
      if (path === "/api/subscribers" && request.method === "GET") {
        return await handleSubscribers(request, url, env);
      }
    } catch (err) {
      return json({ ok: false, error: "server_error" }, 500);
    }

    return json({ ok: false, error: "not_found" }, 404);
  },
};

/* ────────────────────────── POST /api/subscribe ────────────────────────── */
async function handleSubscribe(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "bad_json" }, 400);
  }

  // Honeypot: a real human never fills `hp`. If present, pretend success.
  if (String(body.hp || "").trim() !== "") {
    return json({ ok: true }, 200);
  }

  const email = String(body.email || "").trim().toLowerCase();
  const lang = body.lang === "tr" ? "tr" : "en";
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return json({ ok: false, error: "invalid_email" }, 400);
  }
  if (!env.RESEND_API_KEY) {
    return json({ ok: false, error: "not_configured" }, 503);
  }

  const now = new Date().toISOString();
  const existing = await env.DB.prepare(
    "SELECT id, status FROM subscribers WHERE email = ?"
  ).bind(email).first();

  // Already a confirmed subscriber → no duplicate, no second mail.
  if (existing && existing.status === "confirmed") {
    return json({ ok: true, status: "already_confirmed" }, 200);
  }

  const token = crypto.randomUUID();

  if (existing) {
    // pending or previously unsubscribed → reset to pending, fresh token + lang.
    await env.DB.prepare(
      "UPDATE subscribers SET status='pending', token=?, lang=?, created_at=?, confirmed_at=NULL WHERE id=?"
    ).bind(token, lang, now, existing.id).run();
  } else {
    await env.DB.prepare(
      "INSERT INTO subscribers (id, email, lang, status, token, created_at) VALUES (?, ?, ?, 'pending', ?, ?)"
    ).bind(crypto.randomUUID(), email, lang, token, now).run();
  }

  const sent = await sendConfirmEmail(env, email, lang, token);
  if (!sent) {
    return json({ ok: false, error: "mail_failed" }, 502);
  }
  return json({ ok: true, status: "pending" }, 200);
}

/* ─────────────────────────── GET /api/confirm ──────────────────────────── */
async function handleConfirm(url, env) {
  const token = (url.searchParams.get("token") || "").trim();
  if (!token) return redirect(`${SITE}/`);

  const row = await env.DB.prepare(
    "SELECT id, lang, status FROM subscribers WHERE token = ?"
  ).bind(token).first();

  if (!row) return redirect(`${SITE}/`);

  if (row.status !== "confirmed") {
    await env.DB.prepare(
      "UPDATE subscribers SET status='confirmed', confirmed_at=? WHERE id=?"
    ).bind(new Date().toISOString(), row.id).run();
  }
  return redirect(thankYouUrl(row.lang, "subscribed"));
}

/* ───────────────────────── GET /api/unsubscribe ────────────────────────── */
async function handleUnsubscribe(url, env) {
  const token = (url.searchParams.get("token") || "").trim();
  if (!token) return redirect(`${SITE}/`);

  const row = await env.DB.prepare(
    "SELECT id, lang FROM subscribers WHERE token = ?"
  ).bind(token).first();

  if (row) {
    await env.DB.prepare(
      "UPDATE subscribers SET status='unsubscribed' WHERE id=?"
    ).bind(row.id).run();
  }
  // Always land on the friendly page, even for an unknown/expired token.
  return redirect(thankYouUrl(row ? row.lang : "en", "unsubscribed"));
}

/* ───────────────────── GET /api/subscribers (AUTHED) ───────────────────── */
async function handleSubscribers(request, url, env) {
  const auth = request.headers.get("Authorization") || "";
  const expected = `Bearer ${env.ADMIN_TOKEN}`;
  if (!env.ADMIN_TOKEN || auth !== expected) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  const lang = url.searchParams.get("lang");
  let stmt;
  if (lang === "tr" || lang === "en") {
    stmt = env.DB.prepare(
      "SELECT email, token FROM subscribers WHERE status='confirmed' AND lang=? ORDER BY confirmed_at"
    ).bind(lang);
  } else {
    stmt = env.DB.prepare(
      "SELECT email, token, lang FROM subscribers WHERE status='confirmed' ORDER BY confirmed_at"
    );
  }

  const { results } = await stmt.all();
  return json({ ok: true, count: results.length, subscribers: results }, 200);
}

/* ───────────────────────────── confirm mail ────────────────────────────── */
async function sendConfirmEmail(env, email, lang, token) {
  const confirmUrl = `${BASE}/api/confirm?token=${encodeURIComponent(token)}`;
  const { subject, html } = confirmTemplate(lang, confirmUrl);

  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ from: FROM, to: [email], subject, html }),
    });
    return r.ok;
  } catch {
    return false;
  }
}

/** Bilingual — exactly ONE language is rendered, never both. On-brand HTML. */
function confirmTemplate(lang, confirmUrl) {
  const t = lang === "tr"
    ? {
        subject: "NoCashFlow · aboneliğini onayla",
        pre: "Tek adım kaldı — aboneliğini onayla.",
        kicker: "THE BULLETIN",
        title: "Neredeyse hazırsın.",
        body: "NoCashFlow bültenine abone olmak için bu adresi kullandın. Onaylamak için aşağıdaki düğmeye dokun — her sabah veriyle başla.",
        cta: "Aboneliği onayla",
        ignore: "Bu isteği sen yapmadıysan bu maili görmezden gel; hiçbir şey eklenmeyecek.",
        foot: "NoCashFlow · Gürültü yok, sadece piyasalar.",
      }
    : {
        subject: "NoCashFlow · confirm your subscription",
        pre: "One step left — confirm your subscription.",
        kicker: "THE BULLETIN",
        title: "Almost there.",
        body: "You used this address to subscribe to the NoCashFlow bulletin. Tap the button below to confirm — and start your mornings with data.",
        cta: "Confirm subscription",
        ignore: "If you didn’t request this, just ignore this email — nothing will be added.",
        foot: "NoCashFlow · No noise. Just markets.",
      };

  const html = `<!DOCTYPE html><html lang="${lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=IBM+Plex+Mono:wght@400;500&display=swap');
  body{margin:0;background:#F2EEE6;font-family:'IBM Plex Mono',ui-monospace,monospace;color:#191512;}
  .wrap{max-width:520px;margin:0 auto;padding:40px 24px;}
  .card{background:#FAF9F6;border:1px solid #D4CFC4;border-radius:4px;padding:40px 36px;}
  .kicker{font-size:11px;letter-spacing:.22em;color:#D83A1E;font-weight:500;}
  .rule{height:1px;background:#D4CFC4;margin:18px 0 26px;}
  h1{font-family:'Fraunces',Georgia,serif;font-weight:600;font-size:30px;line-height:1.15;margin:0 0 16px;letter-spacing:-.01em;}
  p{font-family:'Fraunces',Georgia,serif;font-size:16px;line-height:1.6;color:#574f47;margin:0 0 22px;}
  .btn{display:inline-block;background:#D83A1E;color:#fff !important;text-decoration:none;font-family:'IBM Plex Mono',monospace;font-size:13px;letter-spacing:.04em;padding:14px 26px;border-radius:3px;}
  .small{font-size:12px;color:#9a9082;margin:26px 0 0;font-family:'IBM Plex Mono',monospace;line-height:1.6;}
  .foot{font-size:11px;letter-spacing:.06em;color:#9a9082;text-align:center;margin:24px 0 0;font-family:'IBM Plex Mono',monospace;}
  a.plain{color:#D83A1E;word-break:break-all;}
</style>
<title>${esc(t.subject)}</title></head>
<body>
  <span style="display:none;opacity:0;color:transparent;height:0;width:0;overflow:hidden">${esc(t.pre)}</span>
  <div class="wrap">
    <div class="card">
      <div class="kicker">${esc(t.kicker)}</div>
      <div class="rule"></div>
      <h1>${esc(t.title)}</h1>
      <p>${esc(t.body)}</p>
      <a class="btn" href="${confirmUrl}">${esc(t.cta)}</a>
      <p class="small">${esc(t.ignore)}<br><br><a class="plain" href="${confirmUrl}">${confirmUrl}</a></p>
    </div>
    <div class="foot">${esc(t.foot)}</div>
  </div>
</body></html>`;

  return { subject: t.subject, html };
}

/* ───────────────────────────────── utils ──────────────────────────────── */
function thankYouUrl(lang, page) {
  // tr pages live under /tr/, en at the root
  return lang === "tr" ? `${SITE}/tr/${page}.html` : `${SITE}/${page}.html`;
}

function redirect(location) {
  return new Response(null, { status: 302, headers: { Location: location } });
}

function cors() {
  return {
    "Access-Control-Allow-Origin": SITE,
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
}

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors() },
  });
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
