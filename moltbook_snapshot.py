#!/usr/bin/env python3
"""
moltbook_snapshot.py — captura periódica de datos públicos de Moltbook.

Qué hace:
  1. Llama a cinco endpoints públicos de la API de Moltbook con reintentos.
  2. Valida y limpia cada payload antes de ingestar.
  3. Guarda JSON raw en data/moltbook/snapshots/.
  4. Persiste en SQLite (post_samples, activity_samples, snapshots) con deduplicación.
  5. Escribe health.json con métricas detalladas del run.
  6. Genera un resumen .md legible del snapshot.
  7. Archiva (comprime) snapshots JSON con más de 30 días para ahorrar espacio.

Periodicidad: se invoca desde el workflow GitHub Actions cada 6 horas.
"""
import gzip
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = "https://www.moltbook.com"
ENDPOINTS = {
    "homepage": "/api/v1/homepage?sort=realtime",
    "posts_realtime": "/api/v1/posts?limit=50&sort=realtime",
    "posts_hot": "/api/v1/posts?limit=50&sort=hot",
    "posts_top": "/api/v1/posts?limit=50&sort=top",
    "activity_recent": "/api/v1/activity/recent?limit=50",
}

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
PUBLIC_DATA_DIR = PUBLIC_DIR / "data"
DOCS_DIR = ROOT / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"
DATA_DIR = ROOT / "data" / "moltbook"
SNAP_DIR = DATA_DIR / "snapshots"
DB_PATH = DATA_DIR / "moltbook.sqlite"
HEALTH_PATH = DATA_DIR / "health.json"
PUBLIC_HEALTH_PATH = PUBLIC_DATA_DIR / "health.json"
DOCS_HEALTH_PATH = DOCS_DATA_DIR / "health.json"

FETCH_RETRIES = 3
FETCH_BACKOFF_SECONDS = 2
ARCHIVE_AFTER_DAYS = 30


# ---------------------------------------------------------------------------
# Fetch con reintentos
# ---------------------------------------------------------------------------

def fetch_json(path: str, retries: int = FETCH_RETRIES, backoff: int = FETCH_BACKOFF_SECONDS):
    import urllib.request
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(BASE + path, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
    raise last_error


# ---------------------------------------------------------------------------
# Validación de payloads
# ---------------------------------------------------------------------------

def validate_payload(name: str, payload) -> tuple[bool, list[str]]:
    """Devuelve (es_válido, lista_de_warnings). No rechaza datos parciales,
    solo registra qué campos faltan para los logs de calidad."""
    warnings = []
    if not isinstance(payload, dict):
        return False, ["payload no es dict"]

    if name == "homepage":
        if "stats" not in payload:
            warnings.append("homepage: falta 'stats'")
        else:
            for field in ("agents", "posts", "comments", "submolts"):
                if field not in payload["stats"]:
                    warnings.append(f"homepage.stats: falta '{field}'")

    elif name in ("posts_realtime", "posts_hot", "posts_top"):
        posts = payload.get("posts")
        if not isinstance(posts, list):
            warnings.append(f"{name}: 'posts' no es lista o falta")
        else:
            for i, p in enumerate(posts[:3]):  # Solo validar los primeros 3
                for field in ("id", "title", "score"):
                    if field not in p:
                        warnings.append(f"{name}[{i}]: falta '{field}'")

    elif name == "activity_recent":
        events = payload.get("events")
        if not isinstance(events, list):
            warnings.append("activity_recent: 'events' no es lista o falta")

    return True, warnings


# ---------------------------------------------------------------------------
# Esquema de base de datos con índices mejorados
# ---------------------------------------------------------------------------

def ensure_db(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            source TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS post_samples (
            captured_at TEXT NOT NULL,
            feed TEXT NOT NULL,
            post_id TEXT NOT NULL,
            title TEXT,
            score INTEGER,
            comment_count INTEGER,
            hot_score REAL,
            created_at TEXT,
            author_name TEXT,
            author_karma INTEGER,
            author_followers INTEGER,
            author_following INTEGER,
            PRIMARY KEY (captured_at, feed, post_id)
        );

        CREATE TABLE IF NOT EXISTS activity_samples (
            captured_at TEXT NOT NULL,
            idx INTEGER NOT NULL,
            event_type TEXT,
            agent_name TEXT,
            title TEXT,
            post_id TEXT,
            event_time TEXT,
            PRIMARY KEY (captured_at, idx)
        );

        -- Índices para consultas comunes del dashboard
        CREATE INDEX IF NOT EXISTS idx_snapshots_captured ON snapshots(captured_at, source);
        CREATE INDEX IF NOT EXISTS idx_snapshots_source_time ON snapshots(source, captured_at DESC);
        CREATE INDEX IF NOT EXISTS idx_posts_captured_feed ON post_samples(captured_at, feed);
        CREATE INDEX IF NOT EXISTS idx_posts_author ON post_samples(author_name, captured_at DESC);
        CREATE INDEX IF NOT EXISTS idx_posts_score ON post_samples(feed, score DESC);
        CREATE INDEX IF NOT EXISTS idx_activity_captured ON activity_samples(captured_at, event_type);
        CREATE INDEX IF NOT EXISTS idx_activity_agent ON activity_samples(agent_name, captured_at DESC);
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Deduplicación: evitar insertar si ya existe un snapshot de la misma hora
# ---------------------------------------------------------------------------

def snapshot_exists(conn: sqlite3.Connection, captured_at: str, source: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM snapshots WHERE captured_at = ? AND source = ?",
        (captured_at, source),
    ).fetchone()
    return row is not None


def store_snapshot(conn: sqlite3.Connection, captured_at: str, source: str, payload):
    if snapshot_exists(conn, captured_at, source):
        return False  # ya existe, no duplicar
    conn.execute(
        "INSERT INTO snapshots (captured_at, source, payload_json) VALUES (?, ?, ?)",
        (captured_at, source, json.dumps(payload, ensure_ascii=False)),
    )
    return True


# ---------------------------------------------------------------------------
# Ingesta de posts con deduplicación
# ---------------------------------------------------------------------------

def ingest_posts(conn: sqlite3.Connection, captured_at: str, feed: str, payload):
    posts = payload.get("posts", [])
    ingested = 0
    for p in posts:
        author = p.get("author") or {}
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO post_samples (
                    captured_at, feed, post_id, title, score, comment_count, hot_score,
                    created_at, author_name, author_karma, author_followers, author_following
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    captured_at, feed,
                    str(p.get("id", "")),
                    p.get("title"),
                    p.get("score"),
                    p.get("comment_count"),
                    p.get("hot_score"),
                    p.get("created_at"),
                    author.get("name"),
                    author.get("karma"),
                    author.get("followerCount"),
                    author.get("followingCount"),
                ),
            )
            ingested += conn.rowcount
        except Exception as e:
            print(f"warn\tingest_posts\t{feed}\t{e}", file=sys.stderr)
    return ingested


def ingest_activity(conn: sqlite3.Connection, captured_at: str, payload):
    events = payload.get("events", [])
    ingested = 0
    for idx, e in enumerate(events):
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO activity_samples (
                    captured_at, idx, event_type, agent_name, title, post_id, event_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    captured_at, idx,
                    e.get("type"),
                    e.get("agent_name"),
                    e.get("title"),
                    e.get("post_id"),
                    e.get("time"),
                ),
            )
            ingested += conn.rowcount
        except Exception as e:
            print(f"warn\tingest_activity\t{e}", file=sys.stderr)
    return ingested


# ---------------------------------------------------------------------------
# Archivado de snapshots JSON antiguos (> 30 días → .json.gz)
# ---------------------------------------------------------------------------

def archive_old_snapshots():
    """Comprime snapshots JSON con más de ARCHIVE_AFTER_DAYS días."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ARCHIVE_AFTER_DAYS)
    archived = 0
    for f in SNAP_DIR.glob("*.json"):
        try:
            # Extraer timestamp del nombre de archivo
            stem = f.stem  # e.g. "homepage_2026-04-11T10-14-46Z"
            parts = stem.rsplit("_", 1)
            if len(parts) < 2:
                continue
            ts_str = parts[-1].replace("Z", "+00:00").replace("T", "T").replace("-", ":")
            # Corregir formato: 2026:04:11T10:14:46+00:00 → necesita guiones en fecha
            # El nombre tiene formato YYYY-MM-DDTHH-MM-SSZ, reconstruir:
            raw = parts[-1]  # 2026-04-11T10-14-46Z
            if "T" in raw:
                date_part, time_part = raw.split("T", 1)
                time_part = time_part.rstrip("Z")
                time_parts = time_part.split("-")
                if len(time_parts) == 3:
                    ts_iso = f"{date_part}T{time_parts[0]}:{time_parts[1]}:{time_parts[2]}+00:00"
                    ts = datetime.fromisoformat(ts_iso)
                    if ts < cutoff:
                        gz_path = f.with_suffix(".json.gz")
                        with f.open("rb") as fin, gzip.open(gz_path, "wb") as fout:
                            fout.write(fin.read())
                        f.unlink()
                        archived += 1
        except Exception:
            pass  # No interrumpir el proceso por un archivo malformado
    return archived


# ---------------------------------------------------------------------------
# Health.json detallado
# ---------------------------------------------------------------------------

def write_health(captured_at: str, payloads: dict, errors: dict,
                 ingestion_stats: dict, validation_warnings: list):
    posts_ingested = ingestion_stats.get("posts_ingested", 0)
    activity_ingested = ingestion_stats.get("activity_ingested", 0)
    posts_deduplicated = ingestion_stats.get("posts_deduplicated", 0)

    # Obtener stats de homepage si está disponible
    homepage_stats = {}
    if "homepage" in payloads:
        homepage_stats = payloads["homepage"].get("stats", {})

    health = {
        "last_run": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "captured_at": captured_at,
        "status": "ok" if payloads and not errors else "partial" if payloads else "failed",
        "endpoints_ok": sorted(payloads.keys()),
        "endpoints_failed": errors,
        "ingestion": {
            "posts_ingested": posts_ingested,
            "activity_events_ingested": activity_ingested,
            "posts_deduplicated": posts_deduplicated,
        },
        "platform_stats": {
            "agents": homepage_stats.get("agents"),
            "posts": homepage_stats.get("posts"),
            "comments": homepage_stats.get("comments"),
            "submolts": homepage_stats.get("submolts"),
        },
        "validation_warnings": validation_warnings[:20],  # Máximo 20 avisos
        "schema_version": "2",
    }
    for path in (HEALTH_PATH, PUBLIC_HEALTH_PATH, DOCS_HEALTH_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")
    return health


# ---------------------------------------------------------------------------
# Resumen legible
# ---------------------------------------------------------------------------

def write_summary(conn: sqlite3.Connection, captured_at: str):
    out = []
    out.append(f"# Moltbook snapshot\n")
    out.append(f"captured_at: {captured_at}\n")

    cur = conn.execute(
        "SELECT source, COUNT(*) FROM snapshots WHERE captured_at = ? GROUP BY source ORDER BY source",
        (captured_at,),
    )
    out.append("## Sources captured")
    for source, count in cur.fetchall():
        out.append(f"- {source}: {count}")

    out.append("\n## Top hot posts")
    cur = conn.execute(
        """
        SELECT title, score, comment_count, author_name, author_followers
        FROM post_samples
        WHERE captured_at = ? AND feed = 'posts_hot'
        ORDER BY COALESCE(score, 0) DESC
        LIMIT 10
        """,
        (captured_at,),
    )
    for row in cur.fetchall():
        out.append(f"- {row[0]} | score={row[1]} comments={row[2]} author={row[3]} followers={row[4]}")

    out.append("\n## Top realtime posts by comments")
    cur = conn.execute(
        """
        SELECT title, score, comment_count, author_name, author_followers
        FROM post_samples
        WHERE captured_at = ? AND feed = 'posts_realtime'
        ORDER BY COALESCE(comment_count, 0) DESC
        LIMIT 10
        """,
        (captured_at,),
    )
    for row in cur.fetchall():
        out.append(f"- {row[0]} | score={row[1]} comments={row[2]} author={row[3]} followers={row[4]}")

    out.append("\n## Recent activity breakdown")
    cur = conn.execute(
        """
        SELECT event_type, COUNT(*)
        FROM activity_samples
        WHERE captured_at = ?
        GROUP BY event_type
        ORDER BY COUNT(*) DESC
        """,
        (captured_at,),
    )
    for event_type, count in cur.fetchall():
        out.append(f"- {event_type}: {count}")

    out.append("\n## Top recent commenters")
    cur = conn.execute(
        """
        SELECT agent_name, COUNT(*) AS c
        FROM activity_samples
        WHERE captured_at = ? AND event_type = 'comment'
        GROUP BY agent_name
        ORDER BY c DESC, agent_name ASC
        LIMIT 10
        """,
        (captured_at,),
    )
    for name, count in cur.fetchall():
        out.append(f"- {name}: {count}")

    summary_path = SNAP_DIR / f"summary_{captured_at.replace(':', '-')}".replace("+00-00", "Z")
    summary_path = summary_path.with_suffix(".md")
    summary_path.write_text("\n".join(out), encoding="utf-8")
    return summary_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    # 1. Fetch de endpoints con validación
    payloads = {}
    errors = {}
    all_warnings = []
    for name, path in ENDPOINTS.items():
        try:
            payload = fetch_json(path)
            valid, warnings = validate_payload(name, payload)
            if warnings:
                all_warnings.extend(warnings)
                print(f"warn\tvalidation\t{name}\t{'; '.join(warnings)}", file=sys.stderr)
            if valid:
                payloads[name] = payload
                raw_path = SNAP_DIR / f"{name}_{captured_at.replace(':', '-')}".replace("+00-00", "Z")
                raw_path = raw_path.with_suffix(".json")
                raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            errors[name] = str(e)
            print(f"warn\tfetch\t{name}\t{e}", file=sys.stderr)

    if not payloads:
        write_health(captured_at, payloads, errors, {}, all_warnings)
        raise RuntimeError("Ningún endpoint respondió")

    # 2. Persistencia en SQLite
    conn = sqlite3.connect(DB_PATH)
    ensure_db(conn)

    ingestion_stats = {"posts_ingested": 0, "activity_ingested": 0, "posts_deduplicated": 0}

    for name, payload in payloads.items():
        store_snapshot(conn, captured_at, name, payload)

    for feed in ("posts_realtime", "posts_hot", "posts_top"):
        if feed in payloads:
            n = ingest_posts(conn, captured_at, feed, payloads[feed])
            ingestion_stats["posts_ingested"] += n
            total = len(payloads[feed].get("posts", []))
            ingestion_stats["posts_deduplicated"] += total - n

    if "activity_recent" in payloads:
        ingestion_stats["activity_ingested"] = ingest_activity(conn, captured_at, payloads["activity_recent"])

    conn.commit()
    summary_path = write_summary(conn, captured_at)
    conn.commit()
    conn.close()

    # 3. Health.json detallado
    health = write_health(captured_at, payloads, errors, ingestion_stats, all_warnings)

    # 4. Archivar snapshots antiguos
    archived = archive_old_snapshots()

    # Output para GitHub Actions
    print(f"captured_at\t{captured_at}")
    print(f"status\t{health['status']}")
    print(f"posts_ingested\t{ingestion_stats['posts_ingested']}")
    print(f"activity_ingested\t{ingestion_stats['activity_ingested']}")
    if archived:
        print(f"archived_snapshots\t{archived}")
    if errors:
        print(f"endpoints_failed\t{list(errors.keys())}")
    if all_warnings:
        print(f"validation_warnings\t{len(all_warnings)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"error\t{e}", file=sys.stderr)
        sys.exit(1)
