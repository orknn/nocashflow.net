/**
 * CoinGecko provider — crypto. Keyless public endpoint, 24/7 market.
 * Kept separate from the equity provider because the shape, the rate limit and
 * the trading calendar are all different.
 */
const URL_ = "https://api.coingecko.com/api/v3/simple/price";

// internal key → CoinGecko id
export const IDS = { bitcoin: "bitcoin" };

export async function fetchQuotes(keys, signal) {
  const wanted = keys.filter((k) => IDS[k]);
  if (!wanted.length) return [];
  const ids = wanted.map((k) => IDS[k]).join(",");
  const url = `${URL_}?ids=${ids}&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true`;

  let json;
  try {
    const res = await fetch(url, {
      signal,
      // CoinGecko 403s requests without a real UA from datacenter ranges
      headers: {
        Accept: "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; NoCashFlow/1.0; +https://nocashflow.net)",
      },
      cf: { cacheTtl: 45, cacheEverything: true },
    });
    if (!res.ok) return wanted.map((k) => ({ key: k, error: `http_${res.status}` }));
    json = await res.json();
  } catch (e) {
    return wanted.map((k) => ({
      key: k, error: e?.name === "AbortError" ? "timeout" : "fetch_failed",
    }));
  }

  return wanted.map((k) => {
    const row = json?.[IDS[k]];
    const price = typeof row?.usd === "number" && Number.isFinite(row.usd) ? row.usd : null;
    if (price === null) return { key: k, error: "missing_price" };
    const pct = typeof row.usd_24h_change === "number" && Number.isFinite(row.usd_24h_change)
      ? row.usd_24h_change : null;
    // CoinGecko gives a 24h % but no prior close; derive it so the contract
    // stays identical across providers rather than leaving holes.
    const prev = pct === null ? null : price / (1 + pct / 100);
    return {
      key: k,
      symbol: "BTC",
      price,
      previousClose: prev,
      change: prev === null ? null : price - prev,
      changePercent: pct,
      timestamp: row.last_updated_at
        ? new Date(row.last_updated_at * 1000).toISOString() : null,
      currency: "USD",
      exchangeState: "open", // crypto trades continuously
      source: "coingecko",
    };
  });
}

export const id = "coingecko";
