#!/usr/bin/env python3
"""
generate_moltbook_dashboard.py — genera los JSON de datos para el panel estático.

Qué produce:
  - public/data/latest.json  → usado por GitHub Pages (public/)
  - docs/data/latest.json    → usado por GitHub Pages (docs/)

El JSON incluye:
  - stats: métricas globales actuales + delta respecto a captura anterior
  - history / dailyHistory: evolución temporal para gráficos
  - weeklyInsights: hallazgos automáticos de los últimos 7 días
  - topHotPosts, topRealtimeByComments, topAuthors
  - trendingAgents, topCommenters, recentActivity
  - metricAnomalies: posts con ratios comment/score inusuales
  - dataQuality: indicadores de calidad del dataset
"""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "moltbook"
DB_PATH = DATA_DIR / "moltbook.sqlite"
PUBLIC_DIR = ROOT / "public"
PUBLIC_DATA = PUBLIC_DIR / "data"
DOCS_DIR = ROOT / "docs"
DOCS_DATA = DOCS_DIR / "data"
UPDATE_INTERVAL_MINUTES = 360


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def latest_capture(conn):
    row = conn.execute("SELECT MAX(captured_at) FROM snapshots").fetchone()
    return row[0] if row and row[0] else None


def previous_capture(conn, captured_at):
    row = conn.execute(
        "SELECT MAX(captured_at) FROM snapshots WHERE captured_at < ?",
        (captured_at,),
    ).fetchone()
    return row[0] if row and row[0] else None


def capture_n_days_ago(conn, days: int):
    """Captura más cercana disponible hace N días."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = conn.execute(
        "SELECT MAX(captured_at) FROM snapshots WHERE captured_at <= ?",
        (cutoff,),
    ).fetchone()
    return row[0] if row and row[0] else None


def q(conn, sql, params=()):
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def load_homepage_payload(conn, captured_at):
    if not captured_at:
        return {}
    row = q(conn, "SELECT payload_json FROM snapshots WHERE captured_at = ? AND source = 'homepage' LIMIT 1", (captured_at,))
    if not row:
        return {}
    return json.loads(row[0]["payload_json"])


def add_ratios(posts):
    out = []
    for p in posts:
        score = p.get("score") or 0
        comments = p.get("comment_count") or 0
        ratio = round(comments / score, 2) if score else None
        p = dict(p)
        p["comment_score_ratio"] = ratio
        if p.get("author_name"):
            p["author_url"] = f"https://www.moltbook.com/u/{p['author_name']}"
        out.append(p)
    return out


def add_agent_urls(agents):
    out = []
    for a in agents:
        a = dict(a)
        name = a.get("name") or a.get("author_name")
        if name:
            a["url"] = f"https://www.moltbook.com/u/{name}"
        out.append(a)
    return out


# ---------------------------------------------------------------------------
# Anomalías métricas
# ---------------------------------------------------------------------------

def detect_anomalies(posts):
    anomalies = []
    for p in posts:
        comments = p.get("comment_count") or 0
        score = p.get("score") or 0
        ratio = p.get("comment_score_ratio")
        if comments >= 1000 or (ratio is not None and ratio >= 15):
            anomalies.append({
                "post_id": p.get("post_id"),
                "title": p.get("title"),
                "score": score,
                "comment_count": comments,
                "comment_score_ratio": ratio,
                "author_name": p.get("author_name"),
                "author_followers": p.get("author_followers"),
                "author_url": p.get("author_url"),
            })
    anomalies.sort(
        key=lambda x: ((x.get("comment_score_ratio") or 0), x.get("comment_count") or 0),
        reverse=True,
    )
    return anomalies[:12]


# ---------------------------------------------------------------------------
# Historial temporal
# ---------------------------------------------------------------------------

def build_history(conn):
    rows = q(conn, """
        SELECT captured_at, payload_json
        FROM snapshots
        WHERE source = 'homepage'
        ORDER BY captured_at ASC
        LIMIT 500
    """)
    history = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        stats = payload.get("stats", {})
        history.append({
            "capturedAt": row["captured_at"],
            "agents": stats.get("agents"),
            "posts": stats.get("posts"),
            "comments": stats.get("comments"),
            "submolts": stats.get("submolts"),
        })
    return history


def build_daily_history(history):
    by_day = {}
    for h in history:
        day = h["capturedAt"][:10]
        by_day[day] = h
    daily = [by_day[k] for k in sorted(by_day.keys())]

    growth = []
    prev = None
    for d in daily:
        g = {"day": d["capturedAt"][:10]}
        for key in ["agents", "posts", "comments", "submolts"]:
            val = d.get(key)
            g[key] = val
            g[f"delta_{key}"] = (
                (val - prev.get(key))
                if prev and isinstance(val, int) and isinstance(prev.get(key), int)
                else None
            )
        growth.append(g)
        prev = d
    return growth


# ---------------------------------------------------------------------------
# Hallazgos semanales automáticos
# ---------------------------------------------------------------------------

def build_weekly_insights(conn, captured_at: str) -> dict:
    """
    Genera observaciones automáticas sobre la semana en curso comparando
    el snapshot actual con el más antiguo disponible de hace ~7 días.

    Devuelve un dict con listas de 'findings' listos para renderizar en el panel.
    """
    capture_7d = capture_n_days_ago(conn, 7)
    capture_3d = capture_n_days_ago(conn, 3)

    findings = []
    growth_stats = {}

    # --- Crecimiento de plataforma (7 días) ---
    if capture_7d and capture_7d != captured_at:
        current_hp = load_homepage_payload(conn, captured_at).get("stats", {})
        old_hp = load_homepage_payload(conn, capture_7d).get("stats", {})
        for key, label in [("agents", "agentes"), ("posts", "posts"), ("comments", "comentarios")]:
            cv = current_hp.get(key)
            ov = old_hp.get(key)
            if isinstance(cv, int) and isinstance(ov, int) and ov > 0:
                delta = cv - ov
                pct = round((delta / ov) * 100, 2)
                growth_stats[key] = {"delta": delta, "pct": pct, "from": capture_7d, "to": captured_at}
                if delta > 0:
                    findings.append({
                        "type": "growth",
                        "metric": key,
                        "text": f"+{delta:,} {label} en 7 días ({pct:+.2f}%)",
                        "value": delta,
                        "pct": pct,
                    })

    # --- Agentes más activos en los últimos 7 días ---
    if capture_7d:
        top_agents_week = q(conn, """
            SELECT agent_name, COUNT(*) AS events
            FROM activity_samples
            WHERE captured_at > ? AND captured_at <= ? AND event_type = 'comment'
            GROUP BY agent_name
            ORDER BY events DESC
            LIMIT 5
        """, (capture_7d, captured_at))
        if top_agents_week:
            findings.append({
                "type": "top_agents_week",
                "text": "Agentes más activos esta semana (comentarios)",
                "agents": top_agents_week,
            })

    # --- Posts con mayor ratio comentarios/score (debate intenso) ---
    high_ratio = q(conn, """
        SELECT post_id, title, score, comment_count, author_name,
               CAST(comment_count AS REAL) / NULLIF(score, 0) AS ratio
        FROM post_samples
        WHERE captured_at = ? AND feed = 'posts_hot'
          AND score > 10
          AND CAST(comment_count AS REAL) / NULLIF(score, 0) > 5
        ORDER BY ratio DESC
        LIMIT 3
    """, (captured_at,))
    if high_ratio:
        findings.append({
            "type": "debate",
            "text": "Posts con debate intenso (alto ratio comentarios/score)",
            "posts": [
                {
                    "post_id": p["post_id"],
                    "title": p["title"],
                    "score": p["score"],
                    "comment_count": p["comment_count"],
                    "ratio": round(p["ratio"], 1) if p["ratio"] else None,
                    "author_name": p["author_name"],
                    "url": f"https://www.moltbook.com/post/{p['post_id']}",
                    "author_url": f"https://www.moltbook.com/u/{p['author_name']}" if p["author_name"] else None,
                }
                for p in high_ratio
            ],
        })

    # --- Autores nuevos con mucho engagement (alta ratio followers/karma) ---
    emerging = q(conn, """
        SELECT author_name, MAX(author_followers) AS followers, MAX(author_karma) AS karma,
               MAX(author_followers) * 1.0 / NULLIF(MAX(author_karma), 0) AS ratio
        FROM post_samples
        WHERE captured_at = ? AND author_followers > 100 AND author_karma < 500
        GROUP BY author_name
        ORDER BY ratio DESC
        LIMIT 3
    """, (captured_at,))
    if emerging:
        findings.append({
            "type": "emerging",
            "text": "Agentes emergentes (muchos seguidores, karma bajo → nuevos populares)",
            "agents": [
                {
                    "name": a["author_name"],
                    "followers": a["followers"],
                    "karma": a["karma"],
                    "url": f"https://www.moltbook.com/u/{a['author_name']}",
                }
                for a in emerging
            ],
        })

    # --- Tipo de actividad dominante ---
    activity_dist = q(conn, """
        SELECT event_type, COUNT(*) AS cnt
        FROM activity_samples
        WHERE captured_at = ?
        GROUP BY event_type
        ORDER BY cnt DESC
        LIMIT 1
    """, (captured_at,))
    if activity_dist:
        dominant = activity_dist[0]
        findings.append({
            "type": "activity_dominant",
            "text": f"Actividad dominante en la última captura: '{dominant['event_type']}' ({dominant['cnt']} eventos)",
            "event_type": dominant["event_type"],
            "count": dominant["cnt"],
        })

    return {
        "generatedFor": captured_at,
        "comparedWith7d": capture_7d,
        "comparedWith3d": capture_3d,
        "growthStats": growth_stats,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Calidad de datos
# ---------------------------------------------------------------------------

def build_data_quality(conn, captured_at: str) -> dict:
    """Métricas de calidad del dataset para monitoreo interno."""
    total_snapshots = conn.execute("SELECT COUNT(DISTINCT captured_at) FROM snapshots").fetchone()[0]
    total_posts = conn.execute("SELECT COUNT(*) FROM post_samples WHERE captured_at = ?", (captured_at,)).fetchone()[0]
    total_activity = conn.execute("SELECT COUNT(*) FROM activity_samples WHERE captured_at = ?", (captured_at,)).fetchone()[0]
    posts_with_author = conn.execute(
        "SELECT COUNT(*) FROM post_samples WHERE captured_at = ? AND author_name IS NOT NULL", (captured_at,)
    ).fetchone()[0]
    posts_with_score = conn.execute(
        "SELECT COUNT(*) FROM post_samples WHERE captured_at = ? AND score IS NOT NULL", (captured_at,)
    ).fetchone()[0]

    oldest = conn.execute("SELECT MIN(captured_at) FROM snapshots").fetchone()[0]
    newest = conn.execute("SELECT MAX(captured_at) FROM snapshots").fetchone()[0]

    return {
        "totalSnapshotDates": total_snapshots,
        "oldestCapture": oldest,
        "newestCapture": newest,
        "currentSnapshot": {
            "totalPostsSampled": total_posts,
            "totalActivityEvents": total_activity,
            "postsWithAuthor": posts_with_author,
            "postsWithScore": posts_with_score,
            "authorCompleteness": round(posts_with_author / total_posts, 3) if total_posts else None,
        },
    }


# ---------------------------------------------------------------------------
# Build del payload completo
# ---------------------------------------------------------------------------

def build_payload(conn, captured_at):
    homepage = load_homepage_payload(conn, captured_at)
    prev_capture = previous_capture(conn, captured_at)
    prev_homepage = load_homepage_payload(conn, prev_capture) if prev_capture else {}

    stats = homepage.get("stats", {})
    prev_stats = prev_homepage.get("stats", {})
    stats_delta = {}
    for k, v in stats.items():
        pv = prev_stats.get(k)
        if isinstance(v, int) and isinstance(pv, int):
            stats_delta[k] = v - pv

    full_history = build_history(conn)
    daily_history = build_daily_history(full_history)

    trending_agents = add_agent_urls(homepage.get("trendingAgents", []))
    trending_submolts = homepage.get("trendingSubmolts", [])
    top_humans = homepage.get("topHumans", [])

    top_hot = add_ratios(q(conn, """
        SELECT post_id, title, score, comment_count, hot_score, created_at,
               author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ? AND feed = 'posts_hot'
        ORDER BY COALESCE(score,0) DESC LIMIT 12
    """, (captured_at,)))

    top_realtime_comments = add_ratios(q(conn, """
        SELECT post_id, title, score, comment_count, hot_score, created_at,
               author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ? AND feed = 'posts_realtime'
        ORDER BY COALESCE(comment_count,0) DESC LIMIT 12
    """, (captured_at,)))

    top_authors = add_agent_urls(q(conn, """
        SELECT author_name, MAX(author_karma) AS karma, MAX(author_followers) AS followers,
               MAX(author_following) AS following, COUNT(*) AS sampled_posts
        FROM post_samples WHERE captured_at = ?
        GROUP BY author_name
        ORDER BY followers DESC, karma DESC
        LIMIT 12
    """, (captured_at,)))

    activity_breakdown = q(conn, """
        SELECT event_type, COUNT(*) AS count
        FROM activity_samples WHERE captured_at = ?
        GROUP BY event_type
        ORDER BY count DESC
    """, (captured_at,))

    top_commenters = add_agent_urls(q(conn, """
        SELECT agent_name AS author_name, COUNT(*) AS count
        FROM activity_samples
        WHERE captured_at = ? AND event_type = 'comment'
        GROUP BY agent_name
        ORDER BY count DESC, agent_name ASC
        LIMIT 12
    """, (captured_at,)))

    recent_activity = q(conn, """
        SELECT event_type, agent_name, title, post_id, event_time
        FROM activity_samples
        WHERE captured_at = ?
        ORDER BY idx ASC
        LIMIT 20
    """, (captured_at,))

    all_sampled = add_ratios(q(conn, """
        SELECT post_id, title, score, comment_count, hot_score, created_at,
               author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ?
    """, (captured_at,)))

    anomalies = detect_anomalies(all_sampled)
    weekly_insights = build_weekly_insights(conn, captured_at)
    data_quality = build_data_quality(conn, captured_at)

    return {
        "capturedAt": captured_at,
        "previousCapturedAt": prev_capture,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "updateIntervalMinutes": UPDATE_INTERVAL_MINUTES,
        "stats": stats,
        "statsDelta": stats_delta,
        "history": full_history[-60:],
        "dailyHistory": daily_history,
        "weeklyInsights": weekly_insights,
        "dataQuality": data_quality,
        "trendingAgents": trending_agents,
        "trendingSubmolts": trending_submolts,
        "topHumans": top_humans,
        "topHotPosts": top_hot,
        "topRealtimeByComments": top_realtime_comments,
        "topAuthors": top_authors,
        "activityBreakdown": activity_breakdown,
        "topCommenters": top_commenters,
        "recentActivity": recent_activity,
        "metricAnomalies": anomalies,
    }


def write_payload(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    conn = sqlite3.connect(DB_PATH)
    captured_at = latest_capture(conn)
    if not captured_at:
        raise SystemExit("No snapshots found in database")
    payload = build_payload(conn, captured_at)
    conn.close()
    write_payload(PUBLIC_DATA / "latest.json", payload)
    write_payload(DOCS_DATA / "latest.json", payload)
    print(f"captured_at\t{captured_at}")
    print(f"findings\t{len(payload['weeklyInsights']['findings'])}")
    print(f"public\t{PUBLIC_DATA / 'latest.json'}")
    print(f"docs\t{DOCS_DATA / 'latest.json'}")


if __name__ == "__main__":
    main()
