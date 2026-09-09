/**
 * Market status. Deliberately conservative: it reports "closed" unless the
 * clock is inside a known session, so the page never claims a market is open
 * just because someone is looking at it.
 *
 * KNOWN LIMITATION: no exchange holiday calendar. On a US market holiday this
 * returns "open" during what would be regular hours. The response carries
 * `holidayAware: false` so the front end can word things honestly, and the
 * per-instrument `timestamp` still shows when the price actually last moved.
 */
const MIN = (h, m) => h * 60 + m;

/** Minutes past midnight in New York, plus the weekday, for a given instant. */
function nyClock(now) {
  // en-US + America/New_York handles EST/EDT without a tz library
  const p = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "2-digit", minute: "2-digit", weekday: "short", hour12: false,
  }).formatToParts(now).reduce((a, x) => ((a[x.type] = x.value), a), {});
  const days = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return { minutes: MIN(+p.hour % 24, +p.minute), day: days[p.weekday] };
}

/**
 * @returns {"open"|"pre_market"|"after_hours"|"closed"|"weekend"|"always_open"}
 */
export function statusFor(calendar, now = new Date()) {
  if (calendar === "crypto") return "always_open";

  const { minutes, day } = nyClock(now);
  const weekend = day === 0 || day === 6;

  if (calendar === "fx" || calendar === "futures") {
    // both trade nearly around the clock Sunday evening → Friday evening
    if (day === 6) return "weekend";
    if (day === 0 && minutes < MIN(18, 0)) return "weekend";
    if (day === 5 && minutes >= MIN(17, 0)) return "closed";
    return "open";
  }

  if (weekend) return "weekend";

  if (calendar === "us_bond") {
    return minutes >= MIN(8, 0) && minutes < MIN(17, 0) ? "open" : "closed";
  }

  // us_equity — regular session 09:30–16:00 ET, with the usual extended windows
  if (minutes >= MIN(4, 0) && minutes < MIN(9, 30)) return "pre_market";
  if (minutes >= MIN(9, 30) && minutes < MIN(16, 0)) return "open";
  if (minutes >= MIN(16, 0) && minutes < MIN(20, 0)) return "after_hours";
  return "closed";
}

/** The headline status for the board: US equities drive it. */
export function overallStatus(now = new Date()) {
  return statusFor("us_equity", now);
}
