"""
resource_db.py
Database access for the resource-suggestion feature.
Reads the missing_skills column of the resume_analyzer table using the same
get_connection() as main.py.
"""
from typing import Any, Callable, Optional

SELECT_MISSING_SKILLS = "SELECT missing_skills FROM resume_analyzer WHERE Analysis_Id = %s"


def fetch_missing_skills_from_db(
    analysis_id: int,
    connection_factory: Optional[Callable[[], Any]] = None,
):
    """
    Returns the raw missing_skills value:
      - the stored value (a JSON string like '["sql", "docker"]'), or "" if the column is NULL
      - None if no row exists for this id
    Raises the original database error if the connection or query fails.
    connection_factory is only for tests; it defaults to database.get_connection.
    """
    if connection_factory is None:
        # pyrefly: ignore[missing-import]
        from database import get_connection   # lazy: keeps tests free of mysql.connector
        connection_factory = get_connection

    connection = None
    cursor = None
    try:
        connection = connection_factory()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(SELECT_MISSING_SKILLS, (analysis_id,))
        row = cursor.fetchone()
        return None if row is None else (row["missing_skills"] or "")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    import sys

    try:
        analysis_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    except ValueError:
        print("Usage: python resource_db.py <analysis_id>")
        sys.exit(1)

    try:
        value = fetch_missing_skills_from_db(analysis_id)
    except Exception as error:
        print("Database error:", error)
        sys.exit(1)

    if value is None:
        print(f"No analysis found with id {analysis_id}")
    else:
        print(f"missing_skills for id {analysis_id}: {value}")