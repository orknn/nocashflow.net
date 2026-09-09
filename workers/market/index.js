/**
 * NoCashFlow · market data API (Cloudflare Worker)
 *
 *   GET /market/overview            the seven headline instruments
 *   GET /market/overview?keys=a,b   a subset
 *   GET /health                     liveness
 *
 * Why a Worker: the browser cannot call Yahoo (no CORS headers), which is what
 * pushed the old front end onto public CORS proxies. Server-to-server there is
 * no such restriction, so this endpoint removes that dependency entirely. No
 * provider credentials are used today; if a keyed provider is added later its
 * secret stays here (wrangler secret put) and never reaches the browser.
 *
 * Contract is stable and provider-agnostic — see providers/index.js.
 */
import { INSTRUMENTS, ALL_KEYS, fetchAll } from "./providers/index.js";
import { statusFor, overallStatus } from "./market-status.js";

const UPSTREAM_TIMEOUT_MS = 6000;
const EDGE_TTL = 60;      // seconds a response is reusable at the edge
const BROWSER_TTL = 30;

const ALLOWED_ORIGINS = [
  "https://nocashflow.net",
  "https://www.nocashflow.net",
  "http://localhost:8899",
  "http://127.0.0.1:8899",
];

function cors(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}

const json = (body, status, origin, extra = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": `public, max-age=${BROWSER_TTL}, s-maxage=${EDGE_TTL}`,
      ...cors(origin),
      ...extra,
    },
  });

/** Round without ever emitting NaN/Infinity into the payload. */
const round = (v, d) =>
  typeof v === "number" && Number.isFinite(v) ? Number(v.toFixed(d)) : null;

/**
 * Shape one provider row into the public contract. A row that fails validation
 * becomes an explicit error entry — never a zero, never a silent omission.
 */
function normalise(row, now) {
  const meta = INSTRUMENTS[row.key];
  if (!meta) return null;
  const base = {
    symbol: meta.symbol,
    name: meta.name,
    marketStatus: statusFor(meta.calendar, now),
  };
  if (row.error || typeof row.price !== "number" || !Number.isFinite(row.price)) {
    return { ...base, price: null, change: null, changePercent: null,
             previousClose: null, timestamp: null, source: row.source || null,
             ok: false, error: row.error || "invalid_price" };
  }
  // a timestamp far in the future, or absurdly old, means the upstream is
  // confused — surface the price but do not vouch for the clock
  let ts = row.timestamp;
  if (ts) {
    const t = Date.parse(ts);
    if (!Number.isFinite(t) || t > now.getTime() + 6 * 3600e3) ts = null;
  }
  return {
    ...base,
    price: round(row.price, meta.decimals),
    change: round(row.change, meta.decimals),
    changePercent: round(row.changePercent, 2),
    previousClose: round(row.previousClose, meta.decimals),
    timestamp: ts,
    currency: row.currency || null,
    unit: meta.unit || null,
    source: row.source,
    ok: true,
  };
}

async function overview(url, origin) {
  const now = new Date();
  const raw = url.searchParams.get("keys");
  // restrict parameters to the known set — no pass-through to the provider
  const keys = raw
    ? raw.split(",").map((s) => s.trim()).filter((k) => ALL_KEYS.includes(k))
    : ALL_KEYS;
  if (!keys.length) {
    return json({ error: "no_valid_keys", allowed: ALL_KEYS }, 400, origin);
  }

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), UPSTREAM_TIMEOUT_MS);
  let rows;
  try {
    rows = await fetchAll(keys, ctrl.signal);
  } catch {
    rows = keys.map((k) => ({ key: k, error: "provider_failure" }));
  } finally {
    clearTimeout(timer);
  }

  const instruments = {};
  for (const row of rows) {
    const n = normalise(row, now);
    if (n) instruments[row.key] = n;
  }
  for (const k of keys) {
    if (!instruments[k]) instruments[k] = normalise({ key: k, error: "no_data" }, now);
  }

  const okCount = Object.values(instruments).filter((i) => i.ok).length;
  const body = {
    asOf: now.toISOString(),
    marketStatus: overallStatus(now),
    holidayAware: false,      // no exchange holiday calendar in v1
    instruments,
    meta: { requested: keys.length, ok: okCount, failed: keys.length - okCount },
  };
  // a total upstream failure is not a 200 — the caller must be able to tell
  return json(body, okCount === 0 ? 503 : 200, origin);
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors(origin) });
    }
    if (request.method !== "GET") {
      return json({ error: "method_not_allowed" }, 405, origin);
    }
    if (path === "/health") {
      return json({ ok: true, service: "ncf-market", ts: new Date().toISOString() }, 200, origin);
    }
    if (path === "/market/overview" || path === "/overview") {
      return overview(url, origin);
    }
    return json({ error: "not_found", routes: ["/market/overview", "/health"] }, 404, origin);
  },
};
