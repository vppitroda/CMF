-- Docsearch POC schema (scope.md §6). Applied by the loader if the tables do not exist.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS documents (
  id                bigserial PRIMARY KEY,
  rel_path          text   NOT NULL UNIQUE,          -- relative to DOCSEARCH_ROOT
  file_name         text   NOT NULL,
  ext               text   NOT NULL,
  sha256            text   NOT NULL,
  size_bytes        bigint NOT NULL,
  source_folder     text,                            -- ELECON | SMS
  kind              text   NOT NULL,                 -- pdf | xlsx | cad
  category          text   NOT NULL,                 -- see scope §3
  product_class     text,                            -- PP | HA | HQ | HV
  project_code      text,                            -- PP60056, HAS90265 (a document label, NOT a filter)
  doc_prefix        text,                            -- 01 | 02 | 03
  revision          text,                            -- '0','a','b',...
  rev_rank          int,                             -- 0 for '0', 1 for 'a', ...
  application       text,                            -- WT+WC+WG, SAC, E+T ...
  family_key        text   NOT NULL,
  is_latest         boolean NOT NULL DEFAULT true,
  duplicate_of      bigint REFERENCES documents(id),
  page_count        int,
  parse_status      text   NOT NULL DEFAULT 'pending',  -- pending|ok|partial|failed|skipped
  parse_warnings    jsonb  NOT NULL DEFAULT '[]',
  extractor_version text,
  extract_hash      text,                            -- hash of the extraction loaded into spec_* tables (load skips if unchanged)
  indexed_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS documents_cat_latest ON documents (category, is_latest) WHERE duplicate_of IS NULL;
CREATE INDEX IF NOT EXISTS documents_family     ON documents (family_key);
CREATE INDEX IF NOT EXISTS documents_sha        ON documents (sha256);

-- registry that drives step 2 of the UI
CREATE TABLE IF NOT EXISTS properties (
  category     text NOT NULL,
  prop_key     text NOT NULL,
  label        text NOT NULL,
  data_type    text NOT NULL CHECK (data_type IN ('number','text')),
  sort_order   int  NOT NULL DEFAULT 0,
  PRIMARY KEY (category, prop_key)
);

CREATE TABLE IF NOT EXISTS spec_fields (
  id           bigserial PRIMARY KEY,
  document_id  bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  prop_key     text   NOT NULL,
  value_text   text   NOT NULL,        -- as printed, whitespace-normalised
  value_canon  text   NOT NULL,        -- lowercase, typo-aliased, remarks stripped: used for grouping/fuzzy
  unit         text,                   -- as printed: Bar, lpm, V, mm ...
  list_sep     text,                   -- '/' | '+' | NULL
  extra        jsonb,                  -- current: AC/DC, frequency_hz, remark ...
  page         int,
  bbox         jsonb,                  -- [x0,y0,x1,y1] points, top-left origin, displayed orientation
  UNIQUE (document_id, prop_key)
);
CREATE INDEX IF NOT EXISTS spec_fields_prop   ON spec_fields (prop_key);
CREATE INDEX IF NOT EXISTS spec_fields_canon  ON spec_fields USING gin (value_canon gin_trgm_ops);

CREATE TABLE IF NOT EXISTS spec_numbers (  -- one row per number in a numeric field (supports "any value near")
  field_id  bigint NOT NULL REFERENCES spec_fields(id) ON DELETE CASCADE,
  ord       int    NOT NULL,
  num       numeric NOT NULL,
  PRIMARY KEY (field_id, ord)
);
CREATE INDEX IF NOT EXISTS spec_numbers_num ON spec_numbers (num);

CREATE TABLE IF NOT EXISTS terminations (
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  tbl text, name text, size text, connection text, tube_pipe text,
  page int, bbox jsonb
);
CREATE TABLE IF NOT EXISTS notes (
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  no text, text text, page int
);
CREATE TABLE IF NOT EXISTS doc_links (
  from_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  to_id   bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  link_type text NOT NULL,             -- cad_sibling | same_project | reused_on
  PRIMARY KEY (from_id, to_id, link_type)
);
CREATE TABLE IF NOT EXISTS bom_lines (     -- M5
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  item_no text, customer_item_no text, rev text, part_no text, part_no_canon text,
  description text, model_code text, make text, qty text, remarks text, page int, bbox jsonb
);
CREATE INDEX IF NOT EXISTS bom_part_canon ON bom_lines USING gin (part_no_canon gin_trgm_ops);
CREATE INDEX IF NOT EXISTS bom_desc       ON bom_lines USING gin (to_tsvector('simple', description));
