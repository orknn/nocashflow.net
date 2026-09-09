/**
 * Provider registry. The router asks for keys, not for a provider — which one
 * serves an instrument is decided here, so the endpoint contract stays stable
 * when a source is swapped.
 */
import * as yahoo from "./yahoo.js";
import * as coingecko from "./coingecko.js";
import * as kraken from "./kraken.js";

// internal key → display name + how to format on the front end
export const INSTRUMENTS = {
  nasdaq100: { symbol: "NDX",   name: "Nasdaq 100",  decimals: 0, calendar: "us_equity" },
  sp500:     { symbol: "SPX",   name: "S&P 500",     decimals: 0, calendar: "us_equity" },
  us10y:     { symbol: "US10Y", name: "US 10Y",      decimals: 2, calendar: "us_bond", unit: "%" },
  dxy:       { symbol: "DXY",   name: "Dollar Index", decimals: 2, calendar: "fx" },
  brent:     { symbol: "BRENT", name: "Brent Crude", decimals: 2, calendar: "futures" },
  gold:      { symbol: "XAU",   name: "Gold",        decimals: 2, calendar: "futures" },
  bitcoin:   { symbol: "BTC",   name: "Bitcoin",     decimals: 0, calendar: "crypto" },
  dowjones:  { symbol: "DJI",   name: "Dow Jones",   decimals: 0, calendar: "us_equity" },
  russell2000: { symbol: "RUT", name: "Russell 2000", decimals: 0, calendar: "us_equity" },
  vix:       { symbol: "VIX",   name: "Volatility index", decimals: 2, calendar: "us_equity" },
};

export const ALL_KEYS = Object.keys(INSTRUMENTS);

const PRIMARY = [yahoo, coingecko];
// tried only for keys the primaries could not serve, so a rate-limited source
// costs one extra request rather than degrading the whole board
const FALLBACK = [kraken];

const usable = (r) => r && !r.error && typeof r.price === "number";

/** Ask every provider for its share of `keys`, primaries in parallel. */
export async function fetchAll(keys, signal) {
  const batches = await Promise.all(PRIMARY.map((p) => p.fetchQuotes(keys, signal)));
  const rows = new Map();
  for (const r of batches.flat()) {
    if (usable(r) || !rows.has(r.key)) rows.set(r.key, r);
  }

  const missing = keys.filter((k) => !usable(rows.get(k)));
  if (missing.length) {
    const extra = await Promise.all(FALLBACK.map((p) => p.fetchQuotes(missing, signal)));
    for (const r of extra.flat()) if (usable(r)) rows.set(r.key, r);
  }
  return [...rows.values()];
}
