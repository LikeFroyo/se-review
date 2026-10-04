"""Team directory page — lists members with their team names."""


def get_member(conn, member_id):
    row = conn.execute(
        "SELECT id, name, team_id FROM members WHERE id = ?", (member_id,)
    ).fetchone()
    return row


def get_team_name(conn, team_id):
    row = conn.execute("SELECT name FROM teams WHERE id = ?", (team_id,)).fetchone()
    return row[0] if row else "unknown"


def directory(conn, member_ids):
    """Return [{name, team}] for every requested member."""
    cards = []
    for mid in member_ids:
        member = get_member(conn, mid)
        cards.append({"name": member[1], "team": get_team_name(conn, member[2])})
    return cards
