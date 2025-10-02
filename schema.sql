-- ========================
-- MCP Server Schema
-- ========================

-- Create ENUM for status
DO $$ BEGIN
  CREATE TYPE review_status AS ENUM ('received','processing','evaluated','finalized','failed');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Table: reviews_table
CREATE TABLE IF NOT EXISTS reviews_table (
  id BIGSERIAL PRIMARY KEY,
  response_id_of_expertiza BIGINT NOT NULL,
  review TEXT NOT NULL,

  llm_generated_feedback TEXT,
  llm_generated_score NUMERIC(5,2),
  llm_details_reasoning TEXT,

  finalized_feedback TEXT,
  finalized_score NUMERIC(5,2),

  status review_status NOT NULL DEFAULT 'received',
  idempotency_key TEXT UNIQUE,
  model_name TEXT,
  prompt_version TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add useful indexes
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews_table(status);
CREATE UNIQUE INDEX IF NOT EXISTS ux_reviews_response ON reviews_table(response_id_of_expertiza);

-- Score sanity check (0–100 range)
ALTER TABLE reviews_table
  ADD CONSTRAINT chk_scores_reasonable
  CHECK (
    (llm_generated_score IS NULL OR (llm_generated_score >= 0 AND llm_generated_score <= 100)) AND
    (finalized_score     IS NULL OR (finalized_score     >= 0 AND finalized_score     <= 100))
  );

-- Table: failed_jobs
CREATE TABLE IF NOT EXISTS failed_jobs (
  id BIGSERIAL PRIMARY KEY,
  reviews_id_from_review_table BIGINT NOT NULL REFERENCES reviews_table(id) ON DELETE CASCADE,
  error_type TEXT,
  error_message TEXT,
  attempt_number INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_failed_jobs_review ON failed_jobs(reviews_id_from_review_table);
