def create_notification(con, user_id, title, body):
    con.execute(
        """
        INSERT INTO notifications (user_id, title, body, is_read)
        VALUES (?, ?, ?, 0)
        """,
        (user_id, title, body)
    )


def unread_notifications(con, user_id, limit=5):
    return con.execute(
        """
        SELECT * FROM notifications
        WHERE user_id=? AND is_read=0
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit)
    ).fetchall()