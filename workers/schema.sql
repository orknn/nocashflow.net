-- NoCashFlow · newsletter subscribers (Cloudflare D1)
--
-- Apply with:
--   wrangler d1 execute ncf_subscribers --file=./schema.sql            (local)
--   wrangler d1 execute ncf_subscribers --remote --file=./schema.sql   (production)
--
-- Personal data (email) lives ONLY here — never in the git repo.

CREATE TABLE IF NOT EXISTS subscribers (
  id           TEXT PRIMARY KEY,                 -- crypto.randomUUID()
  email        TEXT NOT NULL,                    -- stored lowercased
  lang         TEXT NOT NULL CHECK (lang IN ('tr','en')),
  status       TEXT NOT NULL DEFAULT 'pending'   -- pending | confirmed | unsubscribed
               CHECK (status IN ('pending','confirmed','unsubscribed')),
  token        TEXT NOT NULL,                     -- confirm + unsubscribe (crypto.randomUUID())
  created_at   TEXT NOT NULL,                     -- ISO 8601 UTC
  confirmed_at TEXT                               -- ISO 8601 UTC, set on confirm
);

-- One row per address; case handled by storing lowercase before insert.
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);

-- Fast lookups by token (confirm / unsubscribe) and by the send-list query.
CREATE INDEX IF NOT EXISTS idx_subscribers_token  ON subscribers(token);
CREATE INDEX IF NOT EXISTS idx_subscribers_status ON subscribers(status, lang);
