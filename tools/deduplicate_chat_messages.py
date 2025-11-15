import os
from typing import List, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def get_database_url() -> str:
    # Reuse app settings if available
    try:
        from core.settings import settings
        return settings.database_url
    except Exception:
        # Fallback to env var or sqlite
        return os.getenv("DATABASE_URL", "sqlite:///./brainai.db")


def deduplicate_messages(dry_run: bool = True) -> Tuple[int, List[Tuple[str, int, int, int]]]:
    """
    Remove duplicate rows in chat_messages per (user_id, chat_id, message_index).
    Keeps the smallest id; deletes the rest.

    Returns total_deleted and sample of affected groups.
    """
    db_url = get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    sample_groups: List[Tuple[str, int, int, int]] = []
    total_deleted = 0

    with engine.begin() as conn:
        # Find groups with duplicates
        dup_sql = text(
            """
            SELECT chat_id, user_id, message_index, COUNT(*) AS cnt
            FROM chat_messages
            GROUP BY chat_id, user_id, message_index
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            """
        )
        result = conn.execute(dup_sql).fetchall()

        for row in result:
            chat_id, user_id, msg_index, cnt = row
            if len(sample_groups) < 10:
                sample_groups.append((chat_id, user_id, msg_index, cnt))

            # Get all ids for this group ordered by id (keep first)
            ids_sql = text(
                """
                SELECT id FROM chat_messages
                WHERE chat_id = :chat_id AND user_id = :user_id AND message_index = :mi
                ORDER BY id ASC
                """
            )
            ids = [r[0] for r in conn.execute(ids_sql, {"chat_id": chat_id, "user_id": user_id, "mi": msg_index}).fetchall()]
            keep_id = ids[0]
            delete_ids = ids[1:]

            if delete_ids:
                total_deleted += len(delete_ids)
                if not dry_run:
                    del_sql = text("DELETE FROM chat_messages WHERE id = ANY(:ids)")
                    # For SQLite fallback, emulate ANY
                    if db_url.startswith("sqlite"):
                        placeholders = ",".join([":id" + str(i) for i in range(len(delete_ids))])
                        del_sql = text(f"DELETE FROM chat_messages WHERE id IN ({placeholders})")
                        params = {("id" + str(i)): delete_ids[i] for i in range(len(delete_ids))}
                        conn.execute(del_sql, params)
                    else:
                        conn.execute(del_sql, {"ids": delete_ids})

    return total_deleted, sample_groups


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deduplicate chat_messages table")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    deleted, groups = deduplicate_messages(dry_run=not args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Mode: {mode}")
    print(f"Total duplicate rows to delete: {deleted}")
    if groups:
        print("Examples of duplicate groups (chat_id, user_id, message_index, duplicates):")
        for g in groups:
            print("  ", g)
    if args.apply:
        print("✅ Deduplication applied")
    else:
        print("ℹ️  Run again with --apply to delete duplicates")
