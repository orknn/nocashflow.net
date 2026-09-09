/**
 * Yahoo Finance provider — indices, rates, FX and commodities.
 *
 * Called server-side only. The browser cannot reach Yahoo (no CORS headers),
 * which is why the old front-end path went through public CORS proxies; from a
 * Worker the request is plain server-to-server and needs no proxy at all.
 *
 * Undocumented endpoint: it can change without notice, and Yahoo's terms
 * restrict commercial redistribution. Everything provider-specific lives in
 * this file so swapping in a licensed feed is a one-file change.
 */
const BASE = "https://query1.finance.yahoo.com/v8/finance/chart/";

// internal key → Yahoo symbol
export const SYMBOLS = {
  nasdaq100: "^NDX",
  sp500: "^GSPC",
  us10y: "^TNX",
  dxy: "DX-Y.NYB",
  brent: "BZ=F",
  gold: "GC=F",
  // completing the Market Overview board: same code path, one line each
  dowjones: "^DJI",
  russell2000: "^RUT",
  vix: "^VIX",
};

const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);

/** One symbol → raw quote, or null. Never throws. */
async function one(key, symbol, signal) {
  const url = `${BASE}${encodeURIComponent(symbol)}?interval=1d&range=5d`;
  const res = await fetch(url, {
    signal,
    headers: {
      // Yahoo 403s an empty UA from some egress ranges
      "User-Agent": "Mozilla/5.0 (compatible; NoCashFlow/1.0; +https://nocashflow.net)",
      Accept: "application/json",
    },
    cf: { cacheTtl: 45, cacheEverything: true },
  });
  if (!res.ok) return { key, error: `http_${res.status}` };

  let json;
  try {
    json = await res.json();
  } catch {
    return { key, error: "malformed_json" };
  }

  const result = json?.chart?.result?.[0];
  if (!result) {
    return { key, error: json?.chart?.error?.code || "no_result" };
  }

  const meta = result.meta || {};
  const price = num(meta.regularMarketPrice);
  if (price === null) return { key, error: "missing_price" };

  /* Previous close comes from the daily close series, not meta.
     meta.chartPreviousClose is the close BEFORE the requested window opens —
     with range=5d that is five sessions back, not yesterday. Using it made the
     change wrong for every instrument and flipped the sign on several (a down
     market rendered green). The last two non-null daily closes are the only
     honest source: [-1] is today's bar, [-2] the prior session. */
  const series = result.indicators?.quote?.[0]?.close;
  let prev = null;
  if (Array.isArray(series)) {
    const closes = series.filter((c) => typeof c === "number" && Number.isFinite(c));
    if (closes.length >= 2) prev = closes[closes.length - 2];
  }
  // only if the series is unusable does meta become a last resort
  if (prev === null) prev = num(meta.chartPreviousClose) ?? num(meta.previousClose);

  const ts = num(meta.regularMarketTime);
  return {
    key,
    symbol,
    price,
    previousClose: prev,
    change: prev === null ? null : price - prev,
    changePercent: prev ? ((price - prev) / prev) * 100 : null,
    timestamp: ts ? new Date(ts * 1000).toISOString() : null,
    currency: meta.currency || null,
    exchangeState: meta.marketState || null,
    source: "yahoo",
  };
}

/** Fetch the requested keys in parallel. Failures come back as {key, error}. */
export async function fetchQuotes(keys, signal) {
  const wanted = keys.filter((k) => SYMBOLS[k]);
  return Promise.all(wanted.map((k) => one(k, SYMBOLS[k], signal).catch(
    (e) => ({ key: k, error: e?.name === "AbortError" ? "timeout" : "fetch_failed" })
  )));
}

export const id = "yahoo";
