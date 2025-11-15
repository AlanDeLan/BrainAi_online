import argparse
import sys
from typing import Iterable

from core.settings import settings
from core.database import init_database, db_manager
from core.db_models import ChatMessage, ChatEmbedding
from core.semantic_search import index_message
from core.logger import logger


def batched_query(session, query, batch_size: int, use_id_scan: bool = True) -> Iterable[ChatMessage]:
    last_id = 0
    while True:
        q = query
        if use_id_scan:
            q = q.filter(ChatMessage.id > last_id).order_by(ChatMessage.id.asc())
        items = q.limit(batch_size).all()
        if not items:
            break
        for it in items:
            last_id = it.id
            yield it
        if not use_id_scan:
            break


def main():
    parser = argparse.ArgumentParser(description="Backfill or rebuild pgvector embeddings for chats")
    parser.add_argument("--all", action="store_true", help="Reindex all eligible messages (assistant,file), replacing existing embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes; just report counts")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for processing (default: 500)")
    parser.add_argument("--user-id", type=int, default=None, help="Limit to specific user id")
    args = parser.parse_args()

    # Init database
    if not settings.database_url:
        logger.error("DATABASE_URL not configured; aborting")
        sys.exit(1)
    init_database(settings.database_url)
    session = db_manager.get_session()  # type: ignore

    try:
        base_q = session.query(ChatMessage).filter(ChatMessage.role.in_(["assistant", "file"]))
        if args.user_id is not None:
            base_q = base_q.filter(ChatMessage.user_id == args.user_id)

        if args.all:
            logger.info("Reindex mode: ALL (existing embeddings will be replaced)")
            total = 0
            indexed = 0
            for msg in batched_query(session, base_q, args.batch_size, use_id_scan=True):
                total += 1
                if args.dry_run:
                    continue
                # remove existing embeddings for this message
                try:
                    session.query(ChatEmbedding).filter(ChatEmbedding.message_id == msg.id).delete()
                    session.flush()
                except Exception as e:
                    session.rollback()
                    logger.debug(f"Cleanup existing embeddings failed (msg_id={msg.id}): {e}")
                ok = index_message(session, msg)
                if ok:
                    indexed += 1
            logger.info(f"Processed messages: {total}; Indexed: {indexed}")
        else:
            logger.info("Reindex mode: MISSING ONLY (no replacement)")
            from sqlalchemy.sql import exists
            subq = session.query(ChatEmbedding.id).filter(ChatEmbedding.message_id == ChatMessage.id)
            q = base_q.filter(~exists(subq))
            total = 0
            indexed = 0
            for msg in batched_query(session, q, args.batch_size, use_id_scan=True):
                total += 1
                if args.dry_run:
                    continue
                ok = index_message(session, msg)
                if ok:
                    indexed += 1
            logger.info(f"Missing messages: {total}; Newly indexed: {indexed}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
