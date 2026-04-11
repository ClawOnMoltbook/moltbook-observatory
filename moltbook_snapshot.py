#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone
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
DATA_DIR = ROOT / "data" / "moltbook"
SNAP_DIR = DATA_DIR / "snapshots"
DB_PATH = DATA_DIR / "moltbook.sqlite"


def fetch_json(path: str):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


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
        """
    )
    conn.commit()


def store_snapshot(conn: sqlite3.Connection, captured_at: str, source: str, payload):
    conn.execute(
        "INSERT INTO snapshots (captured_at, source, payload_json) VALUES (?, ?, ?)",
        (captured_at, source, json.dumps(payload, ensure_ascii=False)),
    )


def ingest_posts(conn: sqlite3.Connection, captured_at: str, feed: str, payload):
    posts = payload.get("posts", [])
    for p in posts:
        author = p.get("author") or {}
        conn.execute(
            """
            INSERT OR REPLACE INTO post_samples (
                captured_at, feed, post_id, title, score, comment_count, hot_score,
                created_at, author_name, author_karma, author_followers, author_following
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                captured_at,
                feed,
                p.get("id"),
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


def ingest_activity(conn: sqlite3.Connection, captured_at: str, payload):
    events = payload.get("events", [])
    for idx, e in enumerate(events):
        conn.execute(
            """
            INSERT OR REPLACE INTO activity_samples (
                captured_at, idx, event_type, agent_name, title, post_id, event_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                captured_at,
                idx,
                e.get("type"),
                e.get("agent_name"),
                e.get("title"),
                e.get("post_id"),
                e.get("time"),
            ),
        )


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


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    payloads = {}
    for name, path in ENDPOINTS.items():
        payload = fetch_json(path)
        payloads[name] = payload
        raw_path = SNAP_DIR / f"{name}_{captured_at.replace(':', '-')}".replace("+00-00", "Z")
        raw_path = raw_path.with_suffix(".json")
        raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    conn = sqlite3.connect(DB_PATH)
    ensure_db(conn)

    for name, payload in payloads.items():
        store_snapshot(conn, captured_at, name, payload)

    ingest_posts(conn, captured_at, "posts_realtime", payloads["posts_realtime"])
    ingest_posts(conn, captured_at, "posts_hot", payloads["posts_hot"])
    ingest_posts(conn, captured_at, "posts_top", payloads["posts_top"])
    ingest_activity(conn, captured_at, payloads["activity_recent"])
    conn.commit()

    summary_path = write_summary(conn, captured_at)
    conn.commit()
    conn.close()

    print(f"captured_at\t{captured_at}")
    print(f"db\t{DB_PATH}")
    print(f"summary\t{summary_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"error\t{e}", file=sys.stderr)
        sys.exit(1)
