"""PostgreSQL facade using psycopg3 async API."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

try:
    import psycopg
    from psycopg_pool import AsyncConnectionPool
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None  # type: ignore
    AsyncConnectionPool = None  # type: ignore
    dict_row = None  # type: ignore

_pool: Any = None


async def get_pool(dsn: str) -> Any:
    """Return singleton async connection pool."""
    global _pool
    if _pool is None:
        if psycopg is None:
            raise ImportError("psycopg[binary] is required for database access")
        _pool = AsyncConnectionPool(dsn, min_size=1, max_size=5, open=False)
        await _pool.open()
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def ensure_schema(conn: Any) -> bool:
    """Check schema_version table exists. Returns True if schema is present."""
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'schema_version')"
        )
        row = await cur.fetchone()
        return bool(row[0]) if row else False


async def upsert_repos(conn: Any, repos: list[dict]) -> int:
    """Batch upsert repos. Returns count upserted."""
    if not repos:
        return 0

    sql = """
        INSERT INTO repos (
            id, org, name, url, description, stars, forks, open_issues,
            language, license, last_pushed_at, is_archived, is_fork,
            topics, assigned_domains, extracted_deps,
            s_activity, s_ontology, s_deps, s_profile, score,
            matched_signals, source, classified_at, fetched_at
        ) VALUES (
            %(id)s, %(org)s, %(name)s, %(url)s, %(description)s,
            %(stars)s, %(forks)s, %(open_issues)s,
            %(language)s, %(license)s, %(last_pushed_at)s,
            %(is_archived)s, %(is_fork)s,
            %(topics)s::jsonb, %(assigned_domains)s::jsonb, %(extracted_deps)s::jsonb,
            %(s_activity)s, %(s_ontology)s, %(s_deps)s, %(s_profile)s, %(score)s,
            %(matched_signals)s::jsonb, %(source)s, %(classified_at)s, %(fetched_at)s
        )
        ON CONFLICT (id) DO UPDATE SET
            org = EXCLUDED.org,
            name = EXCLUDED.name,
            url = EXCLUDED.url,
            description = EXCLUDED.description,
            stars = EXCLUDED.stars,
            forks = EXCLUDED.forks,
            open_issues = EXCLUDED.open_issues,
            language = EXCLUDED.language,
            license = EXCLUDED.license,
            last_pushed_at = EXCLUDED.last_pushed_at,
            is_archived = EXCLUDED.is_archived,
            is_fork = EXCLUDED.is_fork,
            topics = EXCLUDED.topics,
            assigned_domains = EXCLUDED.assigned_domains,
            extracted_deps = EXCLUDED.extracted_deps,
            s_activity = EXCLUDED.s_activity,
            s_ontology = EXCLUDED.s_ontology,
            s_deps = EXCLUDED.s_deps,
            s_profile = EXCLUDED.s_profile,
            score = EXCLUDED.score,
            matched_signals = EXCLUDED.matched_signals,
            source = EXCLUDED.source,
            classified_at = EXCLUDED.classified_at,
            fetched_at = EXCLUDED.fetched_at
    """

    rows = []
    for repo in repos:
        row = {
            "id": repo.get("id", ""),
            "org": repo.get("org", ""),
            "name": repo.get("name", ""),
            "url": repo.get("url"),
            "description": repo.get("description"),
            "stars": repo.get("stars", 0),
            "forks": repo.get("forks", 0),
            "open_issues": repo.get("open_issues", 0),
            "language": repo.get("language"),
            "license": repo.get("license"),
            "last_pushed_at": repo.get("last_pushed_at"),
            "is_archived": repo.get("is_archived", False),
            "is_fork": repo.get("is_fork", False),
            "topics": json.dumps(repo.get("topics", [])),
            "assigned_domains": json.dumps(repo.get("assigned_domains", [])),
            "extracted_deps": json.dumps(repo.get("extracted_deps", {})),
            "s_activity": repo.get("s_activity", 0.0),
            "s_ontology": repo.get("s_ontology", 0.0),
            "s_deps": repo.get("s_deps", 0.0),
            "s_profile": repo.get("s_profile", 0.0),
            "score": repo.get("score", 0.0),
            "matched_signals": json.dumps(repo.get("matched_signals", {})),
            "source": repo.get("source", "github"),
            "classified_at": repo.get("classified_at"),
            "fetched_at": repo.get("fetched_at"),
        }
        rows.append(row)

    async with conn.cursor() as cur:
        await cur.executemany(sql, rows)
    return len(rows)


async def upsert_embeddings(conn: Any, rows: list[dict]) -> int:
    """Batch upsert repo_embeddings."""
    if not rows:
        return 0
    sql = """
        INSERT INTO repo_embeddings (repo_id, embedding, model, embedded_at)
        VALUES (%(repo_id)s, %(embedding)s::vector, %(model)s, NOW())
        ON CONFLICT (repo_id) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            model = EXCLUDED.model,
            embedded_at = NOW()
    """
    async with conn.cursor() as cur:
        await cur.executemany(sql, rows)
    return len(rows)


async def upsert_dep_edges(conn: Any, edges: list[dict]) -> int:
    """Batch upsert dep_edges."""
    if not edges:
        return 0
    sql = """
        INSERT INTO dep_edges (from_repo, dep_name, dep_type, resolved_repo)
        VALUES (%(from_repo)s, %(dep_name)s, %(dep_type)s, %(resolved_repo)s)
        ON CONFLICT (from_repo, dep_name, dep_type) DO UPDATE SET
            resolved_repo = EXCLUDED.resolved_repo
    """
    rows = [
        {
            "from_repo": e.get("from_repo"),
            "dep_name": e.get("dep_name"),
            "dep_type": e.get("dep_type"),
            "resolved_repo": e.get("resolved_repo"),
        }
        for e in edges
    ]
    async with conn.cursor() as cur:
        await cur.executemany(sql, rows)
    return len(rows)


async def upsert_user_data(conn: Any, repo_id: str, **kwargs: Any) -> None:
    """Upsert a single user_data row."""
    fields = ["repo_id"]
    values: dict[str, Any] = {"repo_id": repo_id}

    allowed = {"status", "tags", "notes", "projects", "priority"}
    for key in allowed:
        if key in kwargs:
            fields.append(key)
            val = kwargs[key]
            if key in ("tags", "projects") and isinstance(val, list):
                val = json.dumps(val)
            values[key] = val

    if len(fields) == 1:
        return

    set_clauses = []
    for f in fields[1:]:
        if f in ("tags", "projects"):
            set_clauses.append(f"{f} = EXCLUDED.{f}::jsonb")
        else:
            set_clauses.append(f"{f} = EXCLUDED.{f}")
    set_clauses.append("last_reviewed_at = NOW()")

    col_str = ", ".join(fields)
    val_str = ", ".join(
        f"%({f})s::jsonb" if f in ("tags", "projects") else f"%({f})s"
        for f in fields
    )

    sql = f"""
        INSERT INTO user_data ({col_str}, first_seen_at)
        VALUES ({val_str}, NOW())
        ON CONFLICT (repo_id) DO UPDATE SET
            {", ".join(set_clauses)}
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, values)


async def upsert_hf_repos(conn: Any, hf_repos: list[dict]) -> int:
    """Batch upsert hf_repos."""
    if not hf_repos:
        return 0
    sql = """
        INSERT INTO hf_repos (id, org, name, type, downloads, likes, tags, pipeline_tag,
                               assigned_domains, score, fetched_at)
        VALUES (%(id)s, %(org)s, %(name)s, %(type)s, %(downloads)s, %(likes)s,
                %(tags)s::jsonb, %(pipeline_tag)s, %(assigned_domains)s::jsonb,
                %(score)s, %(fetched_at)s)
        ON CONFLICT (id) DO UPDATE SET
            org = EXCLUDED.org,
            name = EXCLUDED.name,
            type = EXCLUDED.type,
            downloads = EXCLUDED.downloads,
            likes = EXCLUDED.likes,
            tags = EXCLUDED.tags,
            pipeline_tag = EXCLUDED.pipeline_tag,
            assigned_domains = EXCLUDED.assigned_domains,
            score = EXCLUDED.score,
            fetched_at = EXCLUDED.fetched_at
    """
    rows = [
        {
            "id": r.get("id", ""),
            "org": r.get("org", ""),
            "name": r.get("name", ""),
            "type": r.get("type", "model"),
            "downloads": r.get("downloads", 0),
            "likes": r.get("likes", 0),
            "tags": json.dumps(r.get("tags", [])),
            "pipeline_tag": r.get("pipeline_tag"),
            "assigned_domains": json.dumps(r.get("assigned_domains", [])),
            "score": r.get("score", 0.0),
            "fetched_at": r.get("fetched_at"),
        }
        for r in hf_repos
    ]
    async with conn.cursor() as cur:
        await cur.executemany(sql, rows)
    return len(rows)


async def add_digest_event(
    conn: Any, repo_id: str, event: str, detail: dict
) -> None:
    """Add a digest event."""
    sql = """
        INSERT INTO digest (repo_id, event, detail, detected_at)
        VALUES (%(repo_id)s, %(event)s, %(detail)s::jsonb, NOW())
    """
    async with conn.cursor() as cur:
        await cur.execute(
            sql,
            {"repo_id": repo_id, "event": event, "detail": json.dumps(detail)},
        )


async def add_star_history(conn: Any, repo_id: str, stars: int) -> None:
    """Add a star history record."""
    sql = """
        INSERT INTO star_history (repo_id, stars, recorded_at)
        VALUES (%(repo_id)s, %(stars)s, NOW())
        ON CONFLICT (repo_id, recorded_at) DO NOTHING
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, {"repo_id": repo_id, "stars": stars})


async def get_repos(conn: Any, **filters: Any) -> list[dict]:
    """Get repos with optional filters."""
    conditions = ["1=1"]
    params: dict[str, Any] = {}

    if filters.get("domain"):
        domains = filters["domain"]
        if isinstance(domains, str):
            domains = [domains]
        # Filter: repo has at least one of the listed domains
        condition_parts = []
        for i, d in enumerate(domains):
            key = f"domain_{i}"
            condition_parts.append(f"assigned_domains @> %({key})s::jsonb")
            params[key] = json.dumps([d])
        conditions.append(f"({' OR '.join(condition_parts)})")

    if filters.get("org"):
        orgs = filters["org"]
        if isinstance(orgs, str):
            orgs = [orgs]
        condition_parts = [f"org = %(org_{i})s" for i in range(len(orgs))]
        for i, o in enumerate(orgs):
            params[f"org_{i}"] = o
        conditions.append(f"({' OR '.join(condition_parts)})")

    if filters.get("min_score") is not None:
        conditions.append("score >= %(min_score)s")
        params["min_score"] = filters["min_score"]

    if filters.get("status"):
        conditions.append(
            "EXISTS (SELECT 1 FROM user_data u WHERE u.repo_id = repos.id AND u.status = %(status)s)"
        )
        params["status"] = filters["status"]

    if filters.get("tag"):
        conditions.append(
            "EXISTS (SELECT 1 FROM user_data u WHERE u.repo_id = repos.id AND u.tags @> %(tag)s::jsonb)"
        )
        params["tag"] = json.dumps([filters["tag"]])

    if filters.get("search"):
        conditions.append(
            "fts_doc @@ plainto_tsquery('english', %(search)s)"
        )
        params["search"] = filters["search"]

    if filters.get("active"):
        conditions.append("is_archived = FALSE AND is_fork = FALSE")

    sort = filters.get("sort", "score")
    sort_map = {
        "score": "score DESC",
        "stars": "stars DESC",
        "pushed": "last_pushed_at DESC",
    }
    order = sort_map.get(sort, "score DESC")
    limit = filters.get("limit", 100)

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT r.*, u.status, u.tags, u.notes, u.priority, u.projects
        FROM repos r
        LEFT JOIN user_data u ON u.repo_id = r.id
        WHERE {where_clause}
        ORDER BY {order}
        LIMIT %(limit)s
    """
    params["limit"] = limit

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_repo(conn: Any, repo_id: str) -> dict | None:
    """Get a single repo by id."""
    sql = """
        SELECT r.*, u.status, u.tags, u.notes, u.priority, u.projects,
               u.first_seen_at, u.last_reviewed_at
        FROM repos r
        LEFT JOIN user_data u ON u.repo_id = r.id
        WHERE r.id = %(repo_id)s
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, {"repo_id": repo_id})
        row = await cur.fetchone()
    return dict(row) if row else None


async def get_user_data(conn: Any, repo_id: str) -> dict | None:
    """Get user_data for a single repo."""
    sql = "SELECT * FROM user_data WHERE repo_id = %(repo_id)s"
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, {"repo_id": repo_id})
        row = await cur.fetchone()
    return dict(row) if row else None


async def get_digest(
    conn: Any, since: datetime, domain: str | None = None
) -> list[dict]:
    """Get digest events since a given datetime."""
    params: dict[str, Any] = {"since": since}
    conditions = ["d.detected_at >= %(since)s"]

    if domain:
        conditions.append(
            "EXISTS (SELECT 1 FROM repos r WHERE r.id = d.repo_id "
            "AND r.assigned_domains @> %(domain)s::jsonb)"
        )
        params["domain"] = json.dumps([domain])

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT d.*, r.name, r.org, r.stars, r.score, r.assigned_domains
        FROM digest d
        JOIN repos r ON r.id = d.repo_id
        WHERE {where_clause}
        ORDER BY d.detected_at DESC
        LIMIT 500
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_stats(conn: Any, domain: str | None = None) -> dict:
    """Get aggregate stats."""
    params: dict[str, Any] = {}

    if domain:
        domain_filter = "AND assigned_domains @> %(domain)s::jsonb"
        params["domain"] = json.dumps([domain])
    else:
        domain_filter = ""

    total_sql = f"SELECT COUNT(*) FROM repos WHERE 1=1 {domain_filter}"
    async with conn.cursor() as cur:
        await cur.execute(total_sql, params)
        row = await cur.fetchone()
    total = row[0] if row else 0

    domain_sql = """
        SELECT d.domain, COUNT(*) AS cnt, ROUND(AVG(score)::numeric, 1) AS avg_score,
               MAX(score) AS top_score
        FROM repos, jsonb_array_elements_text(assigned_domains) AS d(domain)
        WHERE 1=1
        GROUP BY d.domain
        ORDER BY cnt DESC
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(domain_sql)
        domain_rows = await cur.fetchall()

    org_sql = f"""
        SELECT org, COUNT(*) AS cnt, ROUND(AVG(score)::numeric, 1) AS avg_score
        FROM repos
        WHERE score > 0 {domain_filter.replace('AND', 'AND')}
        GROUP BY org
        ORDER BY cnt DESC
        LIMIT 20
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(org_sql, params)
        org_rows = await cur.fetchall()

    return {
        "total": total,
        "by_domain": [dict(r) for r in domain_rows],
        "top_orgs": [dict(r) for r in org_rows],
    }


async def semantic_search(
    conn: Any, embedding: list[float], limit: int = 20
) -> list[dict]:
    """Vector similarity search using pgvector."""
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    sql = """
        SELECT r.id, r.org, r.name, r.description, r.score, r.assigned_domains,
               1 - (e.embedding <=> %(vec)s::vector) AS similarity
        FROM repos r
        JOIN repo_embeddings e ON e.repo_id = r.id
        ORDER BY e.embedding <=> %(vec)s::vector
        LIMIT %(limit)s
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, {"vec": vec_str, "limit": limit})
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def fts_search(conn: Any, query: str, limit: int = 20) -> list[dict]:
    """Full-text search using tsvector."""
    sql = """
        SELECT r.id, r.org, r.name, r.description, r.score, r.assigned_domains,
               ts_rank(fts_doc, plainto_tsquery('english', %(query)s)) AS rank
        FROM repos r
        WHERE fts_doc @@ plainto_tsquery('english', %(query)s)
        ORDER BY rank DESC
        LIMIT %(limit)s
    """
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, {"query": query, "limit": limit})
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
