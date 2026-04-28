-- repo-hub PostgreSQL schema
-- Run once: psql $DATABASE_URL -f schema.sql
-- Requires: pgvector, pg_trgm (pre-installed on Supabase/Neon)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── repos ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS repos (
    id                TEXT PRIMARY KEY,           -- {org}/{name}
    org               TEXT NOT NULL,
    name              TEXT NOT NULL,
    url               TEXT,
    description       TEXT,
    stars             INTEGER DEFAULT 0,
    forks             INTEGER DEFAULT 0,
    open_issues       INTEGER DEFAULT 0,
    language          TEXT,
    license           TEXT,                       -- SPDX identifier, NULL = no license
    last_pushed_at    TIMESTAMPTZ,
    is_archived       BOOLEAN DEFAULT FALSE,
    is_fork           BOOLEAN DEFAULT FALSE,
    topics            JSONB    DEFAULT '[]',       -- ["cuda","inference",...]
    assigned_domains  JSONB    DEFAULT '[]',       -- ["gpu_runtime","ai_compiler"]
    extracted_deps    JSONB    DEFAULT '{}',       -- {"requirements.txt": ["torch",...]}
    s_activity        REAL     DEFAULT 0,          -- sub-scores, 0–1
    s_ontology        REAL     DEFAULT 0,
    s_deps            REAL     DEFAULT 0,
    s_profile         REAL     DEFAULT 0,
    score             REAL     DEFAULT 0,          -- final 0–100
    matched_signals   JSONB    DEFAULT '{}',       -- {domain: [signal,...]}
    source            TEXT     DEFAULT 'github',   -- 'github' | 'huggingface'
    classified_at     TIMESTAMPTZ,
    fetched_at        TIMESTAMPTZ
);

-- ── repo_embeddings ───────────────────────────────────────────────────────────
-- Populated by `repo-hub embed` using BAAI/bge-small-en-v1.5 (384 dims)
CREATE TABLE IF NOT EXISTS repo_embeddings (
    repo_id     TEXT        PRIMARY KEY REFERENCES repos(id) ON DELETE CASCADE,
    embedding   vector(384),
    model       TEXT        DEFAULT 'BAAI/bge-small-en-v1.5',
    embedded_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── user_data ─────────────────────────────────────────────────────────────────
-- Your second-brain annotation layer — only you write here
CREATE TABLE IF NOT EXISTS user_data (
    repo_id          TEXT        PRIMARY KEY REFERENCES repos(id) ON DELETE CASCADE,
    status           TEXT        DEFAULT 'new',
    -- new | reviewing | bookmarked | in-use | dismissed
    tags             JSONB       DEFAULT '[]',     -- ["mlir","priority"]
    notes            TEXT,                         -- freeform markdown
    projects         JSONB       DEFAULT '[]',     -- ["suryaos-laptop","alveo"]
    priority         INTEGER     DEFAULT 0,        -- 0=normal 1=high 2=critical
    first_seen_at    TIMESTAMPTZ DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ
);

-- ── dep_edges ─────────────────────────────────────────────────────────────────
-- Cross-repo dependency graph
CREATE TABLE IF NOT EXISTS dep_edges (
    from_repo     TEXT REFERENCES repos(id) ON DELETE CASCADE,
    dep_name      TEXT NOT NULL,                  -- package/library name as found
    dep_type      TEXT,                           -- python|cmake|cargo|npm|go
    resolved_repo TEXT REFERENCES repos(id),      -- NULL if dep not in our DB
    PRIMARY KEY (from_repo, dep_name, dep_type)
);

-- ── digest ────────────────────────────────────────────────────────────────────
-- Change log powering `repo-hub digest`
CREATE TABLE IF NOT EXISTS digest (
    id           BIGSERIAL   PRIMARY KEY,
    repo_id      TEXT        REFERENCES repos(id) ON DELETE CASCADE,
    event        TEXT,                            -- new_repo|star_delta|push|archived|domain_added
    detail       JSONB,                           -- {"stars_before":100,"stars_after":150}
    detected_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── hf_repos ──────────────────────────────────────────────────────────────────
-- HuggingFace Hub models, datasets, and spaces
CREATE TABLE IF NOT EXISTS hf_repos (
    id               TEXT        PRIMARY KEY,     -- {org}/{name}
    org              TEXT,
    name             TEXT,
    type             TEXT,                        -- model|dataset|space
    downloads        INTEGER     DEFAULT 0,
    likes            INTEGER     DEFAULT 0,
    tags             JSONB       DEFAULT '[]',
    pipeline_tag     TEXT,                        -- text-generation|image-classification|...
    assigned_domains JSONB       DEFAULT '[]',
    score            REAL        DEFAULT 0,
    fetched_at       TIMESTAMPTZ
);

-- ── indexes ───────────────────────────────────────────────────────────────────

-- Query patterns: score, org filter, domain filter, pushed recency
CREATE INDEX IF NOT EXISTS idx_repos_score        ON repos (score DESC);
CREATE INDEX IF NOT EXISTS idx_repos_org          ON repos (org);
CREATE INDEX IF NOT EXISTS idx_repos_language     ON repos (language);
CREATE INDEX IF NOT EXISTS idx_repos_pushed       ON repos (last_pushed_at DESC);
CREATE INDEX IF NOT EXISTS idx_repos_source       ON repos (source);

-- JSONB containment queries  →  WHERE topics @> '["mlir"]'
CREATE INDEX IF NOT EXISTS idx_repos_topics       ON repos USING GIN (topics);
CREATE INDEX IF NOT EXISTS idx_repos_domains      ON repos USING GIN (assigned_domains);
CREATE INDEX IF NOT EXISTS idx_repos_deps         ON repos USING GIN (extracted_deps);
CREATE INDEX IF NOT EXISTS idx_repos_signals      ON repos USING GIN (matched_signals);

-- Full-text search  →  WHERE fts_doc @@ to_tsquery('mlir & inference')
ALTER TABLE repos
    ADD COLUMN IF NOT EXISTS fts_doc tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(name, '') || ' ' ||
            coalesce(description, '')
        )
    ) STORED;
CREATE INDEX IF NOT EXISTS idx_repos_fts ON repos USING GIN (fts_doc);

-- Trigram similarity  →  WHERE name % 'llama'  or  similarity(name, 'llama') > 0.3
CREATE INDEX IF NOT EXISTS idx_repos_name_trgm ON repos USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_repos_desc_trgm ON repos USING GIN (description gin_trgm_ops);

-- User data
CREATE INDEX IF NOT EXISTS idx_user_status        ON user_data (status);
CREATE INDEX IF NOT EXISTS idx_user_tags          ON user_data USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_user_projects      ON user_data USING GIN (projects);

-- Dep graph
CREATE INDEX IF NOT EXISTS idx_dep_from           ON dep_edges (from_repo);
CREATE INDEX IF NOT EXISTS idx_dep_resolved       ON dep_edges (resolved_repo);

-- Digest timeline
CREATE INDEX IF NOT EXISTS idx_digest_repo        ON digest (repo_id);
CREATE INDEX IF NOT EXISTS idx_digest_event       ON digest (event);
CREATE INDEX IF NOT EXISTS idx_digest_at          ON digest (detected_at DESC);

-- HF repos
CREATE INDEX IF NOT EXISTS idx_hf_org             ON hf_repos (org);
CREATE INDEX IF NOT EXISTS idx_hf_type            ON hf_repos (type);
CREATE INDEX IF NOT EXISTS idx_hf_score           ON hf_repos (score DESC);
CREATE INDEX IF NOT EXISTS idx_hf_tags            ON hf_repos USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_hf_domains         ON hf_repos USING GIN (assigned_domains);

-- Vector index (HNSW — fast approximate cosine similarity)
-- Created after embeddings are populated (expensive to build on empty table)
-- Run: repo-hub db build-vector-index   (or manually):
-- CREATE INDEX idx_embeddings_hnsw ON repo_embeddings
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- ── useful views ──────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_repos_annotated AS
SELECT
    r.id, r.org, r.name, r.url, r.description,
    r.stars, r.language, r.license,
    r.last_pushed_at,
    r.assigned_domains,
    r.score,
    r.s_activity, r.s_ontology, r.s_deps, r.s_profile,
    r.topics,
    u.status,
    u.tags,
    u.notes,
    u.projects,
    u.priority,
    u.first_seen_at,
    u.last_reviewed_at
FROM repos r
LEFT JOIN user_data u ON u.repo_id = r.id
WHERE r.is_archived = FALSE
  AND r.is_fork     = FALSE;

CREATE OR REPLACE VIEW v_domain_stats AS
SELECT
    domain,
    COUNT(*)              AS repo_count,
    ROUND(AVG(score)::numeric, 1) AS avg_score,
    MAX(score)            AS top_score,
    SUM(stars)            AS total_stars
FROM repos, jsonb_array_elements_text(assigned_domains) AS domain
GROUP BY domain
ORDER BY avg_score DESC;

CREATE OR REPLACE VIEW v_dep_graph AS
SELECT
    e.from_repo,
    e.dep_name,
    e.dep_type,
    e.resolved_repo,
    rf.score  AS from_score,
    rt.score  AS to_score
FROM dep_edges e
JOIN repos rf ON rf.id = e.from_repo
LEFT JOIN repos rt ON rt.id = e.resolved_repo;
