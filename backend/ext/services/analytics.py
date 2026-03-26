"""Business logic for ext-analytics (Platform Usage Analytics).

Pure SELECT queries on existing Onyx + ext tables.
No mutations, no ORM models needed — raw SQL via text().

All queries validated on DEV (2026-03-26):
- message_type is UPPERCASE ('ASSISTANT', 'USER', 'SYSTEM')
- ext_audit_log.timestamp (not created_at)
- chat_feedback has no created_at (join via chat_message)
- ext_token_usage.user_id can be NULL (system calls)
"""

import csv
import io
import logging
from datetime import date
from datetime import datetime
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("ext.analytics")


def get_analytics_summary(
    db_session: Session,
    from_date: date,
    to_date: date,
) -> dict:
    """All KPIs as dict, matching the AnalyticsSummaryResponse schema."""
    # Shift to_date to end of day for inclusive range
    to_ts = datetime.combine(to_date, datetime.max.time())
    from_ts = datetime.combine(from_date, datetime.min.time())
    period_days = (to_date - from_date).days or 1

    users = _get_user_metrics(db_session, from_ts, to_ts, period_days)
    sessions = _get_session_metrics(db_session, from_ts, to_ts)
    tokens = _get_token_metrics(db_session, from_ts, to_ts)
    quality = _get_quality_metrics(db_session, from_ts, to_ts)
    agents = _get_agent_metrics(db_session, from_ts, to_ts)
    content = _get_content_metrics(db_session)
    compliance = _get_compliance_metrics(db_session, from_ts, to_ts)

    return {
        "period": {"from_date": from_date, "to_date": to_date},
        "users": users,
        "sessions": sessions,
        "tokens": tokens,
        "quality": quality,
        "agents": agents,
        "content": content,
        "compliance": compliance,
    }


def get_user_activity(
    db_session: Session,
    from_date: date,
    to_date: date,
) -> dict:
    """User activity table with sessions, messages, tokens."""
    from_ts = datetime.combine(from_date, datetime.min.time())
    to_ts = datetime.combine(to_date, datetime.max.time())

    rows = db_session.execute(
        text("""
            SELECT
                u.email,
                u.role,
                u.created_at as registered,
                COALESCE(s.session_count, 0) as sessions,
                COALESCE(s.message_count, 0) as messages,
                COALESCE(t.total_tokens, 0) as tokens,
                s.last_activity
            FROM "user" u
            LEFT JOIN (
                SELECT
                    user_id,
                    COUNT(DISTINCT cs.id) as session_count,
                    COUNT(cm.id) as message_count,
                    MAX(cs.time_created) as last_activity
                FROM chat_session cs
                LEFT JOIN chat_message cm
                    ON cm.chat_session_id = cs.id
                    AND cm.message_type = 'USER'
                WHERE NOT cs.deleted
                    AND cs.time_created BETWEEN :from_ts AND :to_ts
                GROUP BY cs.user_id
            ) s ON s.user_id = u.id
            LEFT JOIN (
                SELECT user_id, SUM(total_tokens) as total_tokens
                FROM ext_token_usage
                WHERE user_id IS NOT NULL
                    AND created_at BETWEEN :from_ts AND :to_ts
                GROUP BY user_id
            ) t ON t.user_id = u.id
            ORDER BY COALESCE(s.session_count, 0) DESC
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    users = [
        {
            "email": r.email,
            "role": r.role,
            "registered": r.registered,
            "sessions": r.sessions,
            "messages": r.messages,
            "tokens": r.tokens,
            "last_activity": r.last_activity,
        }
        for r in rows
    ]
    return {"total": len(users), "users": users}


def get_agent_detail(
    db_session: Session,
    from_date: date,
    to_date: date,
) -> dict:
    """Agent usage statistics."""
    from_ts = datetime.combine(from_date, datetime.min.time())
    to_ts = datetime.combine(to_date, datetime.max.time())

    rows = db_session.execute(
        text("""
            SELECT
                COALESCE(p.name, 'Unbekannt') as name,
                COUNT(DISTINCT cs.id) as sessions,
                COUNT(cm.id) as messages,
                COUNT(DISTINCT cs.user_id) as unique_users
            FROM chat_session cs
            LEFT JOIN persona p ON cs.persona_id = p.id
            LEFT JOIN chat_message cm
                ON cm.chat_session_id = cs.id
                AND cm.message_type IN ('USER', 'ASSISTANT')
            WHERE NOT cs.deleted
                AND cs.time_created BETWEEN :from_ts AND :to_ts
            GROUP BY p.name
            ORDER BY sessions DESC
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    agents = [
        {
            "name": r.name,
            "sessions": r.sessions,
            "messages": r.messages,
            "unique_users": r.unique_users,
        }
        for r in rows
    ]
    return {"total": len(agents), "agents": agents}


def export_analytics_csv(
    db_session: Session,
    from_date: date,
    to_date: date,
) -> str:
    """CSV export of all KPIs + user activity table."""
    summary = get_analytics_summary(db_session, from_date, to_date)
    users = get_user_activity(db_session, from_date, to_date)

    output = io.StringIO()
    writer = csv.writer(output)

    # Section 1: Summary KPIs
    writer.writerow(["Kategorie", "KPI", "Wert"])
    writer.writerow([])

    _write_section(writer, "Nutzung", {
        "Registrierte User": summary["users"]["registered"],
        "Aktive User (Zeitraum)": summary["users"]["active_period"],
        "DAU Durchschnitt": summary["users"]["dau_avg"],
        "Neue User": summary["users"]["new_in_period"],
        "Inaktive User (30d)": summary["users"]["inactive_30d"],
    })
    _write_section(writer, "Sessions", {
        "Sessions gesamt": summary["sessions"]["total"],
        "Sessions pro User": summary["sessions"]["avg_per_user"],
        "Nachrichten pro Session": summary["sessions"]["avg_messages_per_session"],
        "Durchschnittliche Dauer (s)": summary["sessions"]["avg_duration_seconds"],
    })
    _write_section(writer, "Token", {
        "Total Tokens": summary["tokens"]["total"],
        "Prompt Tokens": summary["tokens"]["prompt"],
        "Completion Tokens": summary["tokens"]["completion"],
        "Requests": summary["tokens"]["requests"],
    })
    for m in summary["tokens"]["by_model"]:
        writer.writerow(["Token", f"Modell: {m['model']}", f"{m['tokens']} Tokens / {m['requests']} Requests"])

    _write_section(writer, "Qualitaet", {
        "Feedback gesamt": summary["quality"]["feedback_total"],
        "Positiv": summary["quality"]["feedback_positive"],
        "Negativ": summary["quality"]["feedback_negative"],
        "Zufriedenheit (%)": summary["quality"]["satisfaction_pct"],
        "Fehlerrate (%)": summary["quality"]["error_rate_pct"],
        "Antwortzeit Median (s)": summary["quality"]["avg_response_time_seconds"],
        "Antwortzeit P95 (s)": summary["quality"]["p95_response_time_seconds"],
    })
    _write_section(writer, "Content", {
        "Indexierte Dokumente": summary["content"]["total_documents"],
        "Aktive Connectors": summary["content"]["active_connectors"],
        "Fehlerhafte Connectors": summary["content"]["error_connectors"],
        "Document Sets": summary["content"]["document_sets"],
    })
    _write_section(writer, "Compliance", {
        "Admin-Aktionen": summary["compliance"]["admin_actions"],
    })
    for action_type, count in summary["compliance"]["admin_actions_by_type"].items():
        writer.writerow(["Compliance", f"Aktion: {action_type}", count])

    # Section 2: User Activity Table
    writer.writerow([])
    writer.writerow(["User", "Rolle", "Registriert", "Sessions", "Nachrichten", "Tokens", "Letzte Aktivitaet"])
    for u in users["users"]:
        writer.writerow([
            u["email"],
            u["role"],
            u["registered"].strftime("%Y-%m-%d") if u["registered"] else "",
            u["sessions"],
            u["messages"],
            u["tokens"],
            u["last_activity"].strftime("%Y-%m-%d %H:%M") if u["last_activity"] else "",
        ])

    return output.getvalue()


# ---------------------------------------------------------------------------
# Internal helper queries
# ---------------------------------------------------------------------------


def _write_section(writer: object, category: str, kpis: dict) -> None:
    for key, value in kpis.items():
        writer.writerow([category, key, value])


def _get_user_metrics(
    db_session: Session, from_ts: datetime, to_ts: datetime, period_days: int
) -> dict:
    row = db_session.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM "user") as registered,
                (SELECT COUNT(DISTINCT user_id) FROM chat_session
                 WHERE NOT deleted AND time_created BETWEEN :from_ts AND :to_ts) as active_period,
                (SELECT COUNT(*) FROM "user"
                 WHERE created_at BETWEEN :from_ts AND :to_ts) as new_in_period
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    # DAU average: total distinct user-days / period days
    dau_row = db_session.execute(
        text("""
            SELECT COALESCE(SUM(dau)::float / :days, 0) as dau_avg
            FROM (
                SELECT DATE(time_created) as day, COUNT(DISTINCT user_id) as dau
                FROM chat_session
                WHERE NOT deleted AND time_created BETWEEN :from_ts AND :to_ts
                GROUP BY DATE(time_created)
            ) sub
        """),
        {"from_ts": from_ts, "to_ts": to_ts, "days": period_days},
    ).fetchone()

    # Inactive: users with no session in last 30 days
    inactive_row = db_session.execute(
        text("""
            SELECT COUNT(*) FROM "user" u
            WHERE NOT EXISTS (
                SELECT 1 FROM chat_session cs
                WHERE cs.user_id = u.id AND NOT cs.deleted
                    AND cs.time_created >= now() - interval '30 days'
            )
        """),
    ).fetchone()

    return {
        "registered": row.registered,
        "active_period": row.active_period,
        "dau_avg": round(dau_row.dau_avg, 1),
        "new_in_period": row.new_in_period,
        "inactive_30d": inactive_row[0],
    }


def _get_session_metrics(
    db_session: Session, from_ts: datetime, to_ts: datetime
) -> dict:
    row = db_session.execute(
        text("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT user_id) as unique_users,
                COALESCE(
                    ROUND(AVG(EXTRACT(EPOCH FROM (time_updated - time_created)))::numeric, 0),
                    0
                ) as avg_duration
            FROM chat_session
            WHERE NOT deleted AND time_created BETWEEN :from_ts AND :to_ts
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    msg_row = db_session.execute(
        text("""
            SELECT COALESCE(ROUND(AVG(msg_count)::numeric, 1), 0) as avg_messages
            FROM (
                SELECT chat_session_id, COUNT(*) as msg_count
                FROM chat_message cm
                JOIN chat_session cs ON cs.id = cm.chat_session_id
                WHERE cm.message_type IN ('USER', 'ASSISTANT')
                    AND NOT cs.deleted
                    AND cs.time_created BETWEEN :from_ts AND :to_ts
                GROUP BY chat_session_id
            ) sub
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    unique_users = row.unique_users or 1
    return {
        "total": row.total,
        "avg_per_user": round(float(row.total) / unique_users, 1),
        "avg_messages_per_session": float(msg_row.avg_messages),
        "avg_duration_seconds": float(row.avg_duration),
    }


def _get_token_metrics(
    db_session: Session, from_ts: datetime, to_ts: datetime
) -> dict:
    row = db_session.execute(
        text("""
            SELECT
                COALESCE(SUM(total_tokens), 0) as total,
                COALESCE(SUM(prompt_tokens), 0) as prompt,
                COALESCE(SUM(completion_tokens), 0) as completion,
                COUNT(*) as requests
            FROM ext_token_usage
            WHERE created_at BETWEEN :from_ts AND :to_ts
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    by_model_rows = db_session.execute(
        text("""
            SELECT
                model_name,
                SUM(total_tokens) as tokens,
                COUNT(*) as requests
            FROM ext_token_usage
            WHERE created_at BETWEEN :from_ts AND :to_ts
            GROUP BY model_name
            ORDER BY tokens DESC
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return {
        "total": row.total,
        "prompt": row.prompt,
        "completion": row.completion,
        "requests": row.requests,
        "by_model": [
            {"model": r.model_name, "tokens": r.tokens, "requests": r.requests}
            for r in by_model_rows
        ],
    }


def _get_quality_metrics(
    db_session: Session, from_ts: datetime, to_ts: datetime
) -> dict:
    fb_row = db_session.execute(
        text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN cf.is_positive = true THEN 1 END) as positive,
                COUNT(CASE WHEN cf.is_positive = false THEN 1 END) as negative
            FROM chat_feedback cf
            JOIN chat_message cm ON cm.id = cf.chat_message_id
            WHERE cm.time_sent BETWEEN :from_ts AND :to_ts
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    satisfaction = (
        round(float(fb_row.positive) / fb_row.total * 100, 1)
        if fb_row.total > 0
        else 0.0
    )

    err_row = db_session.execute(
        text("""
            SELECT
                COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as errors,
                COUNT(*) as total
            FROM chat_message
            WHERE message_type = 'ASSISTANT'
                AND time_sent BETWEEN :from_ts AND :to_ts
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    error_rate = (
        round(float(err_row.errors) / err_row.total * 100, 2)
        if err_row.total > 0
        else 0.0
    )

    rt_row = db_session.execute(
        text("""
            SELECT
                PERCENTILE_CONT(0.5) WITHIN GROUP
                    (ORDER BY processing_duration_seconds)::numeric(10,2) as median,
                PERCENTILE_CONT(0.95) WITHIN GROUP
                    (ORDER BY processing_duration_seconds)::numeric(10,2) as p95
            FROM chat_message
            WHERE message_type = 'ASSISTANT'
                AND processing_duration_seconds IS NOT NULL
                AND processing_duration_seconds > 0
                AND time_sent BETWEEN :from_ts AND :to_ts
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    return {
        "feedback_total": fb_row.total,
        "feedback_positive": fb_row.positive,
        "feedback_negative": fb_row.negative,
        "satisfaction_pct": satisfaction,
        "error_rate_pct": error_rate,
        "avg_response_time_seconds": float(rt_row.median) if rt_row.median else None,
        "p95_response_time_seconds": float(rt_row.p95) if rt_row.p95 else None,
    }


def _get_agent_metrics(
    db_session: Session, from_ts: datetime, to_ts: datetime
) -> dict:
    total_row = db_session.execute(
        text("SELECT COUNT(*) FROM persona WHERE is_visible AND NOT deleted"),
    ).fetchone()

    rows = db_session.execute(
        text("""
            SELECT
                COALESCE(p.name, 'Unbekannt') as name,
                COUNT(DISTINCT cs.id) as sessions,
                COUNT(cm.id) as messages
            FROM chat_session cs
            LEFT JOIN persona p ON cs.persona_id = p.id
            LEFT JOIN chat_message cm
                ON cm.chat_session_id = cs.id
                AND cm.message_type IN ('USER', 'ASSISTANT')
            WHERE NOT cs.deleted
                AND cs.time_created BETWEEN :from_ts AND :to_ts
            GROUP BY p.name
            ORDER BY sessions DESC
            LIMIT 10
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return {
        "total": total_row[0],
        "active_in_period": len(rows),
        "top": [
            {"name": r.name, "sessions": r.sessions, "messages": r.messages}
            for r in rows
        ],
    }


def _get_content_metrics(db_session: Session) -> dict:
    row = db_session.execute(
        text("""
            SELECT
                COALESCE(SUM(total_docs_indexed), 0) as total_docs,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active,
                COUNT(CASE WHEN status != 'ACTIVE'
                    OR in_repeated_error_state = true THEN 1 END) as errors
            FROM connector_credential_pair
        """),
    ).fetchone()

    ds_row = db_session.execute(
        text("SELECT COUNT(*) FROM document_set"),
    ).fetchone()

    return {
        "total_documents": row.total_docs,
        "active_connectors": row.active,
        "error_connectors": row.errors,
        "document_sets": ds_row[0],
    }


def _get_compliance_metrics(
    db_session: Session, from_ts: datetime, to_ts: datetime
) -> dict:
    total_row = db_session.execute(
        text("""
            SELECT COUNT(*) FROM ext_audit_log
            WHERE timestamp BETWEEN :from_ts AND :to_ts
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchone()

    by_type_rows = db_session.execute(
        text("""
            SELECT action, COUNT(*) as cnt
            FROM ext_audit_log
            WHERE timestamp BETWEEN :from_ts AND :to_ts
            GROUP BY action
            ORDER BY cnt DESC
        """),
        {"from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return {
        "admin_actions": total_row[0],
        "admin_actions_by_type": {r.action: r.cnt for r in by_type_rows},
    }
