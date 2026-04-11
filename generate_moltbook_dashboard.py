#!/usr/bin/env python3
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "moltbook"
DB_PATH = DATA_DIR / "moltbook.sqlite"
PUBLIC_DIR = ROOT / "public"
PUBLIC_DATA = PUBLIC_DIR / "data"
DOCS_DIR = ROOT / "docs"
DOCS_DATA = DOCS_DIR / "data"
UPDATE_INTERVAL_MINUTES = 30


def latest_capture(conn):
    row = conn.execute("SELECT MAX(captured_at) FROM snapshots").fetchone()
    return row[0] if row and row[0] else None


def previous_capture(conn, captured_at):
    row = conn.execute(
        "SELECT MAX(captured_at) FROM snapshots WHERE captured_at < ?",
        (captured_at,),
    ).fetchone()
    return row[0] if row and row[0] else None


def q(conn, sql, params=()):
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def load_homepage_payload(conn, captured_at):
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
    anomalies.sort(key=lambda x: ((x.get("comment_score_ratio") or 0), x.get("comment_count") or 0), reverse=True)
    return anomalies[:12]


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
            g[f"delta_{key}"] = (val - prev.get(key)) if prev and isinstance(val, int) and isinstance(prev.get(key), int) else None
        growth.append(g)
        prev = d
    return growth


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
        SELECT post_id, title, score, comment_count, hot_score, created_at, author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ? AND feed = 'posts_hot'
        ORDER BY COALESCE(score,0) DESC LIMIT 12
    """, (captured_at,)))

    top_realtime_comments = add_ratios(q(conn, """
        SELECT post_id, title, score, comment_count, hot_score, created_at, author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ? AND feed = 'posts_realtime'
        ORDER BY COALESCE(comment_count,0) DESC LIMIT 12
    """, (captured_at,)))

    top_authors = add_agent_urls(q(conn, """
        SELECT author_name, MAX(author_karma) AS karma, MAX(author_followers) AS followers, MAX(author_following) AS following, COUNT(*) AS sampled_posts
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
        SELECT post_id, title, score, comment_count, hot_score, created_at, author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ?
    """, (captured_at,)))

    anomalies = detect_anomalies(all_sampled)

    return {
        "capturedAt": captured_at,
        "previousCapturedAt": prev_capture,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "updateIntervalMinutes": UPDATE_INTERVAL_MINUTES,
        "stats": stats,
        "statsDelta": stats_delta,
        "history": full_history[-60:],
        "dailyHistory": daily_history,
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
        raise SystemExit("No snapshots found")
    payload = build_payload(conn, captured_at)
    write_payload(PUBLIC_DATA / "latest.json", payload)
    write_payload(DOCS_DATA / "latest.json", payload)
    print(f"latest\t{PUBLIC_DATA / 'latest.json'}")
    print(f"docs\t{DOCS_DATA / 'latest.json'}")


if __name__ == "__main__":
    main()
