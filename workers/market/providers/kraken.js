/**
 * Kraken provider — crypto fallback.
 *
 * CoinGecko is the primary crypto source but rate-limits datacenter egress
 * hard (403). Kraken's public ticker is keyless, unrestricted from server
 * ranges, and returns today's opening price, so the change can be derived
 * without a second call.
 */
const URL_ = "https://api.kraken.com/0/public/Ticker";
export const PAIRS = { bitcoin: "XBTUSD" };

export async function fetchQuotes(keys, signal) {
  const wanted = keys.filter((k) => PAIRS[k]);
  if (!wanted.length) return [];
  const pair = wanted.map((k) => PAIRS[k]).join(",");

  let json;
  try {
    const res = await fetch(`${URL_}?pair=${pair}`, {
      signal,
      headers: { Accept: "application/json" },
      cf: { cacheTtl: 45, cacheEverything: true },
    });
    if (!res.ok) return wanted.map((k) => ({ key: k, error: `http_${res.status}` }));
    json = await res.json();
  } catch (e) {
    return wanted.map((k) => ({
      key: k, error: e?.name === "AbortError" ? "timeout" : "fetch_failed",
    }));
  }
  if (json?.error?.length) {
    return wanted.map((k) => ({ key: k, error: "provider_error" }));
  }

  // Kraken returns its own pair naming (XXBTZUSD); take the single result
  const result = json?.result || {};
  const row = Object.values(result)[0];
  const price = Number(row?.c?.[0]);
  const open = Number(row?.o);
  if (!Number.isFinite(price)) return wanted.map((k) => ({ key: k, error: "missing_price" }));

  const prev = Number.isFinite(open) && open > 0 ? open : null;
  return wanted.map((k) => ({
    key: k,
    symbol: "BTC",
    price,
    previousClose: prev,
    change: prev === null ? null : price - prev,
    changePercent: prev ? ((price - prev) / prev) * 100 : null,
    timestamp: new Date().toISOString(),
    currency: "USD",
    exchangeState: "open",
    source: "kraken",
  }));
}

export const id = "kraken";
