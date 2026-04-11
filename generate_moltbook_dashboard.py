#!/usr/bin/env python3
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "moltbook"
DB_PATH = DATA_DIR / "moltbook.sqlite"
PUBLIC_DIR = ROOT / "public"
PUBLIC_DATA = PUBLIC_DIR / "data"


def latest_capture(conn):
    row = conn.execute("SELECT MAX(captured_at) FROM snapshots").fetchone()
    return row[0] if row and row[0] else None


def q(conn, sql, params=()):
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def build_payload(conn, captured_at):
    stats_row = q(conn, "SELECT payload_json FROM snapshots WHERE captured_at = ? AND source = 'homepage' LIMIT 1", (captured_at,))
    stats = {}
    trending_agents = []
    trending_submolts = []
    top_humans = []
    if stats_row:
        payload = json.loads(stats_row[0]["payload_json"])
        stats = payload.get("stats", {})
        trending_agents = payload.get("trendingAgents", [])
        trending_submolts = payload.get("trendingSubmolts", [])
        top_humans = payload.get("topHumans", [])

    top_hot = q(conn, """
        SELECT post_id, title, score, comment_count, hot_score, created_at, author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ? AND feed = 'posts_hot'
        ORDER BY COALESCE(score,0) DESC LIMIT 12
    """, (captured_at,))

    top_realtime_comments = q(conn, """
        SELECT post_id, title, score, comment_count, hot_score, created_at, author_name, author_karma, author_followers, author_following
        FROM post_samples WHERE captured_at = ? AND feed = 'posts_realtime'
        ORDER BY COALESCE(comment_count,0) DESC LIMIT 12
    """, (captured_at,))

    top_authors = q(conn, """
        SELECT author_name, MAX(author_karma) AS karma, MAX(author_followers) AS followers, MAX(author_following) AS following, COUNT(*) AS sampled_posts
        FROM post_samples WHERE captured_at = ?
        GROUP BY author_name
        ORDER BY followers DESC, karma DESC
        LIMIT 12
    """, (captured_at,))

    activity_breakdown = q(conn, """
        SELECT event_type, COUNT(*) AS count
        FROM activity_samples WHERE captured_at = ?
        GROUP BY event_type
        ORDER BY count DESC
    """, (captured_at,))

    top_commenters = q(conn, """
        SELECT agent_name, COUNT(*) AS count
        FROM activity_samples
        WHERE captured_at = ? AND event_type = 'comment'
        GROUP BY agent_name
        ORDER BY count DESC, agent_name ASC
        LIMIT 12
    """, (captured_at,))

    recent_activity = q(conn, """
        SELECT event_type, agent_name, title, post_id, event_time
        FROM activity_samples
        WHERE captured_at = ?
        ORDER BY idx ASC
        LIMIT 20
    """, (captured_at,))

    return {
        "capturedAt": captured_at,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "stats": stats,
        "trendingAgents": trending_agents,
        "trendingSubmolts": trending_submolts,
        "topHumans": top_humans,
        "topHotPosts": top_hot,
        "topRealtimeByComments": top_realtime_comments,
        "topAuthors": top_authors,
        "activityBreakdown": activity_breakdown,
        "topCommenters": top_commenters,
        "recentActivity": recent_activity,
    }


def write_public_files(payload):
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DATA / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    conn = sqlite3.connect(DB_PATH)
    captured_at = latest_capture(conn)
    if not captured_at:
        raise SystemExit("No snapshots found")
    payload = build_payload(conn, captured_at)
    write_public_files(payload)
    print(f"latest\t{PUBLIC_DATA / 'latest.json'}")


if __name__ == "__main__":
    main()
