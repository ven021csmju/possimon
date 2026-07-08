import datetime
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import DailyUserStats, Order, OrderItem, Product, Recommendation, User, UserLog, Wine


TOP_N = 20
MIN_COLLABORATIVE_USERS = 5
MIN_COLLABORATIVE_EVENTS = 20
RECOMMENDATION_LOCK_ID = 52719031

EVENT_WEIGHTS = {
    "view": 0.10,
    "click": 0.25,
    "add_to_cart": 0.60,
    "purchase": 1.00,
}


@dataclass
class ProductFeature:
    product_id: int
    tokens: Set[str]


def normalize_score(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return min(value / max_value, 1.0)


def tokenize(text: str | None) -> Set[str]:
    if not text:
        return set()
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(token) >= 2}


def table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.bind).has_table(table_name)


def try_advisory_lock(db: Session) -> bool:
    if db.bind.dialect.name != "postgresql":
        return True
    return bool(db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": RECOMMENDATION_LOCK_ID}).scalar())


def load_products(db: Session) -> List[Product]:
    query = db.query(Product)
    if hasattr(Product, "status"):
        query = query.filter((Product.status == "active") | (Product.status.is_(None)))
    return query.all()


def build_product_features(db: Session, products: Iterable[Product]) -> Dict[int, ProductFeature]:
    product_by_id = {product.id: product for product in products}
    wine_by_id = {wine.id: wine for wine in db.query(Wine).all()} if table_exists(db, "wines") else {}
    features: Dict[int, ProductFeature] = {}

    for product_id, product in product_by_id.items():
        wine = wine_by_id.get(product_id)
        content_parts = [
            product.name,
            product.sku,
            product.barcode,
            product.type,
            getattr(wine, "designation", None),
            getattr(wine, "wine_type", None),
            getattr(wine, "description", None),
            getattr(wine, "food_pairing", None),
            getattr(wine, "tasting_notes", None),
            getattr(wine, "aging_notes", None),
        ]
        features[product_id] = ProductFeature(
            product_id=product_id,
            tokens=tokenize(" ".join(str(part) for part in content_parts if part)),
        )

    return features


def load_popularity_scores(db: Session, product_ids: Set[int]) -> Dict[int, float]:
    scores = Counter()

    order_rows = (
        db.query(OrderItem.product_id, OrderItem.quantity)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.product_id.in_(product_ids))
        .filter(Order.status.in_(["paid", "completed"]))
        .all()
    )
    for product_id, quantity in order_rows:
        scores[int(product_id)] += float(quantity or 1)

    if table_exists(db, "user_logs"):
        log_rows = db.query(UserLog.product_id, UserLog.event_type).filter(UserLog.product_id.in_(product_ids)).all()
        for product_id, event_type in log_rows:
            scores[int(product_id)] += EVENT_WEIGHTS.get(str(event_type), 0.0)

    if table_exists(db, "daily_user_stats"):
        stat_rows = (
            db.query(DailyUserStats.product_id, DailyUserStats.event_type, DailyUserStats.event_count)
            .filter(DailyUserStats.product_id.in_(product_ids))
            .all()
        )
        for product_id, event_type, event_count in stat_rows:
            scores[int(product_id)] += EVENT_WEIGHTS.get(str(event_type), 0.0) * float(event_count or 0)

    max_score = max(scores.values(), default=0.0)
    return {product_id: normalize_score(score, max_score) for product_id, score in scores.items()}


def load_user_interactions(db: Session, user_id: int, product_ids: Set[int]) -> Dict[int, float]:
    interactions = Counter()

    purchased_rows = (
        db.query(OrderItem.product_id, OrderItem.quantity)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.user_id == user_id)
        .filter(Order.status.in_(["paid", "completed"]))
        .filter(OrderItem.product_id.in_(product_ids))
        .all()
    )
    for product_id, quantity in purchased_rows:
        interactions[int(product_id)] += EVENT_WEIGHTS["purchase"] * float(quantity or 1)

    if table_exists(db, "user_logs"):
        log_rows = (
            db.query(UserLog.product_id, UserLog.event_type)
            .filter(UserLog.user_id == user_id)
            .filter(UserLog.product_id.in_(product_ids))
            .all()
        )
        for product_id, event_type in log_rows:
            interactions[int(product_id)] += EVENT_WEIGHTS.get(str(event_type), 0.0)

    if table_exists(db, "daily_user_stats"):
        stat_rows = (
            db.query(DailyUserStats.product_id, DailyUserStats.event_type, DailyUserStats.event_count)
            .filter(DailyUserStats.user_id == user_id)
            .filter(DailyUserStats.product_id.in_(product_ids))
            .all()
        )
        for product_id, event_type, event_count in stat_rows:
            interactions[int(product_id)] += EVENT_WEIGHTS.get(str(event_type), 0.0) * float(event_count or 0)

    return dict(interactions)


def content_based_scores(
    product_features: Dict[int, ProductFeature],
    user_interactions: Dict[int, float],
) -> Dict[int, float]:
    profile = Counter()
    for product_id, weight in user_interactions.items():
        for token in product_features.get(product_id, ProductFeature(product_id, set())).tokens:
            profile[token] += weight

    if not profile:
        return {}

    scores = {}
    profile_norm = math.sqrt(sum(weight * weight for weight in profile.values()))

    for product_id, feature in product_features.items():
        if product_id in user_interactions:
            continue
        dot = sum(profile[token] for token in feature.tokens)
        item_norm = math.sqrt(len(feature.tokens)) or 1.0
        scores[product_id] = dot / (profile_norm * item_norm) if profile_norm else 0.0

    max_score = max(scores.values(), default=0.0)
    return {product_id: normalize_score(score, max_score) for product_id, score in scores.items()}


def load_all_interactions(db: Session, product_ids: Set[int]) -> Dict[int, Dict[int, float]]:
    interactions: Dict[int, Counter] = defaultdict(Counter)

    purchased_rows = (
        db.query(Order.user_id, OrderItem.product_id, OrderItem.quantity)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(Order.status.in_(["paid", "completed"]))
        .filter(OrderItem.product_id.in_(product_ids))
        .all()
    )
    for user_id, product_id, quantity in purchased_rows:
        if user_id:
            interactions[int(user_id)][int(product_id)] += EVENT_WEIGHTS["purchase"] * float(quantity or 1)

    if table_exists(db, "user_logs"):
        log_rows = db.query(UserLog.user_id, UserLog.product_id, UserLog.event_type).filter(UserLog.product_id.in_(product_ids)).all()
        for user_id, product_id, event_type in log_rows:
            if user_id and product_id:
                interactions[int(user_id)][int(product_id)] += EVENT_WEIGHTS.get(str(event_type), 0.0)

    if table_exists(db, "daily_user_stats"):
        stat_rows = (
            db.query(DailyUserStats.user_id, DailyUserStats.product_id, DailyUserStats.event_type, DailyUserStats.event_count)
            .filter(DailyUserStats.product_id.in_(product_ids))
            .all()
        )
        for user_id, product_id, event_type, event_count in stat_rows:
            if user_id and product_id:
                interactions[int(user_id)][int(product_id)] += EVENT_WEIGHTS.get(str(event_type), 0.0) * float(event_count or 0)

    return {user_id: dict(items) for user_id, items in interactions.items()}


def cosine_similarity(left: Dict[int, float], right: Dict[int, float]) -> float:
    shared = set(left).intersection(right)
    if not shared:
        return 0.0
    dot = sum(left[product_id] * right[product_id] for product_id in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def collaborative_scores(db: Session, user_id: int, product_ids: Set[int]) -> Dict[int, float]:
    all_interactions = load_all_interactions(db, product_ids)
    target = all_interactions.get(user_id, {})

    total_events = sum(len(items) for items in all_interactions.values())
    if len(all_interactions) < MIN_COLLABORATIVE_USERS or total_events < MIN_COLLABORATIVE_EVENTS or not target:
        return {}

    scores = Counter()
    similarities = {}
    for other_user_id, other_items in all_interactions.items():
        if other_user_id == user_id:
            continue
        similarity = cosine_similarity(target, other_items)
        if similarity > 0:
            similarities[other_user_id] = similarity

    for other_user_id, similarity in similarities.items():
        for product_id, weight in all_interactions[other_user_id].items():
            if product_id not in target:
                scores[product_id] += similarity * weight

    max_score = max(scores.values(), default=0.0)
    return {product_id: normalize_score(score, max_score) for product_id, score in scores.items()}


def calculate_recommendations_for_user(db: Session, user_id: int) -> List[tuple[int, float]]:
    products = load_products(db)
    product_ids = {product.id for product in products}
    if not product_ids:
        return []

    product_features = build_product_features(db, products)
    popular = load_popularity_scores(db, product_ids)
    interactions = load_user_interactions(db, user_id, product_ids)
    content = content_based_scores(product_features, interactions)
    collaborative = collaborative_scores(db, user_id, product_ids)

    scores = Counter()
    for product_id in product_ids:
        if product_id in interactions:
            continue
        scores[product_id] += 0.35 * popular.get(product_id, 0.0)
        scores[product_id] += 0.40 * content.get(product_id, 0.0)
        scores[product_id] += 0.25 * collaborative.get(product_id, 0.0)

    if not any(scores.values()):
        scores.update(popular)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [(product_id, round(float(score), 6)) for product_id, score in ranked[:TOP_N] if score > 0]


def save_recommendations(db: Session, user_id: int, recommendations: List[tuple[int, float]]) -> None:
    db.query(Recommendation).filter(Recommendation.user_id == user_id).delete(synchronize_session=False)
    now = datetime.datetime.utcnow()
    for product_id, score in recommendations:
        db.add(
            Recommendation(
                user_id=user_id,
                product_id=product_id,
                score=score,
                created_at=now,
            )
        )


def rebuild_all_recommendations() -> dict:
    Base.metadata.create_all(bind=engine, tables=[Recommendation.__table__])
    db = SessionLocal()
    try:
        if not try_advisory_lock(db):
            return {"skipped": True, "reason": "recommendation job is already running"}

        users = db.query(User).all()
        total_rows = 0
        for user in users:
            recommendations = calculate_recommendations_for_user(db, user.id)
            save_recommendations(db, user.id, recommendations)
            total_rows += len(recommendations)

        db.commit()
        return {"users": len(users), "recommendations": total_rows}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = rebuild_all_recommendations()
    print(result)
