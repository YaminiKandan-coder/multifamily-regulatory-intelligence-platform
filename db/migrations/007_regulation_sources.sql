-- App settings (feature flags)
CREATE TABLE IF NOT EXISTS app_settings (
  key        TEXT        PRIMARY KEY,
  value      TEXT        NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed feature flag (disabled by default)
INSERT INTO app_settings (key, value)
  VALUES ('use_db_source_registry', 'false')
  ON CONFLICT (key) DO NOTHING;

-- Regulation sources registry (scrape targets, separate from scraped content)
CREATE TABLE IF NOT EXISTS regulation_sources (
  id              SERIAL      PRIMARY KEY,
  jurisdiction_id INT         NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
  source_name     TEXT        NOT NULL,
  url             TEXT        NOT NULL UNIQUE,
  domain          TEXT        NOT NULL DEFAULT 'housing',
  category        TEXT        NOT NULL DEFAULT 'General',
  state_code      CHAR(2)     NULL,
  is_active       BOOL        NOT NULL DEFAULT TRUE,
  last_scraped_at TIMESTAMPTZ NULL,
  last_error      TEXT        NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS regulation_sources_jurisdiction_idx ON regulation_sources(jurisdiction_id);
CREATE INDEX IF NOT EXISTS regulation_sources_state_code_idx   ON regulation_sources(state_code);
CREATE INDEX IF NOT EXISTS regulation_sources_is_active_idx    ON regulation_sources(is_active);

-- Permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON regulation_sources TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON app_settings       TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE regulation_sources_id_seq  TO anon, authenticated;

-- RLS
ALTER TABLE regulation_sources ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_regulation_sources" ON regulation_sources FOR ALL USING (true);

ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_app_settings" ON app_settings FOR ALL USING (true);
