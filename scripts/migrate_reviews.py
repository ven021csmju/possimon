import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.append(str(Path(__file__).resolve().parents[1]))

from database_nosql import db, migrate_review_collection


logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def _normalize_positive_int(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


async def inspect_reviews() -> Dict[str, Any]:
    if db is None:
        raise RuntimeError("MONGODB_URL is not configured.")

    scanned = 0
    null_wine_id = 0
    missing_wine_id = 0
    product_id_mappable = 0
    invalid_user_id = 0
    pairs: Dict[Tuple[int, str], List[str]] = {}

    async for review in db.reviews.find({}):
        scanned += 1
        wine_id = _normalize_positive_int(review.get("wine_id"))
        product_id = _normalize_positive_int(review.get("product_id"))
        user_id = str(review.get("user_id")).strip() if review.get("user_id") is not None else ""

        if "wine_id" not in review:
            missing_wine_id += 1
        elif review.get("wine_id") is None:
            null_wine_id += 1

        if wine_id is None and product_id is not None:
            product_id_mappable += 1
            wine_id = product_id

        if not user_id:
            invalid_user_id += 1

        if wine_id is not None and user_id:
            pairs.setdefault((wine_id, user_id), []).append(str(review["_id"]))

    duplicate_pairs = {
        f"wine_id={wine_id}, user_id={user_id}": ids
        for (wine_id, user_id), ids in pairs.items()
        if len(ids) > 1
    }

    return {
        "scanned": scanned,
        "null_wine_id": null_wine_id,
        "missing_wine_id": missing_wine_id,
        "product_id_mappable": product_id_mappable,
        "invalid_user_id": invalid_user_id,
        "duplicate_pair_count": len(duplicate_pairs),
        "duplicate_pairs": duplicate_pairs,
    }


async def rebuild_indexes():
    if db is None:
        raise RuntimeError("MONGODB_URL is not configured.")

    try:
        await db.reviews.drop_index("uniq_review_wine_user")
        logger.info("Dropped existing uniq_review_wine_user index.")
    except Exception as exc:
        logger.info("No existing uniq_review_wine_user index dropped: %s", exc)

    await db.reviews.create_index(
        [("wine_id", 1), ("user_id", 1)],
        unique=True,
        name="uniq_review_wine_user",
    )
    await db.reviews.create_index(
        [("wine_id", 1), ("created_at", -1)],
        name="idx_reviews_wine_created_at",
    )
    await db.reviews.create_index([("user_id", 1)], name="idx_reviews_user")


async def main():
    parser = argparse.ArgumentParser(description="Inspect and clean MongoDB reviews.")
    parser.add_argument("--apply", action="store_true", help="Apply cleanup and rebuild indexes.")
    args = parser.parse_args()

    before = await inspect_reviews()
    logger.info("Review inspection before migration: %s", before)

    if not args.apply:
        logger.info("Dry run only. Re-run with --apply to clean data and rebuild indexes.")
        return

    migration_result = await migrate_review_collection()
    await rebuild_indexes()
    after = await inspect_reviews()

    logger.info("Review migration result: %s", migration_result)
    logger.info("Review inspection after migration: %s", after)


if __name__ == "__main__":
    asyncio.run(main())
