import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from orders.models import OrderProduct
from store.models import Product
from django.utils import timezone
from datetime import timedelta
from django.db.models import Case, When, Count


def get_collaborative_recommendations(user, limit=8):
    if not user.is_authenticated:
        # For anonymous users, fallback to popular products in last 7 days
        recent = (
            OrderProduct.objects
            .filter(ordered=True, order__created_at__gte=timezone.now() - timedelta(days=7))
            .values('product_id')
            .annotate(purchase_count=Count('product_id'))
            .order_by('-purchase_count')[:limit]
        )
        product_ids = [r['product_id'] for r in recent]
        if not product_ids:
            return Product.objects.filter(is_available=True)[:limit]
        preserved = Case(*[When(pk=pid, then=pos) for pos, pid in enumerate(product_ids)])
        return Product.objects.filter(id__in=product_ids, is_available=True).order_by(preserved)

    # Filter order products in last 7 days and successful orders only
    order_products = OrderProduct.objects.filter(
        ordered=True,
        order__created_at__gte=timezone.now() - timedelta(days=7)
    ).values('user_id', 'product_id')

    if not order_products.exists():
        return Product.objects.filter(is_available=True)[:limit]

    # Build user-product purchase matrix: rows=user, columns=product, values=counts
    df = pd.DataFrame(list(order_products))

    # Count purchases per user-product pair
    purchase_matrix = df.groupby(['user_id', 'product_id']).size().unstack(fill_value=0)

    # Compute cosine similarity between users
    user_sim_matrix = cosine_similarity(purchase_matrix)
    user_sim_df = pd.DataFrame(user_sim_matrix, index=purchase_matrix.index, columns=purchase_matrix.index)

    if user.id not in user_sim_df.index:
        # User has no recent purchases, fallback
        return Product.objects.filter(is_available=True)[:limit]

    # Get similarity scores of current user with others
    sim_scores = user_sim_df.loc[user.id]

    # Exclude self similarity
    sim_scores = sim_scores.drop(labels=[user.id], errors='ignore')

    # Select top similar users
    top_users = sim_scores[sim_scores > 0].sort_values(ascending=False).index

    if len(top_users) == 0:
        return Product.objects.filter(is_available=True)[:limit]

    # Weighted sum of product purchases by similar users
    similar_users_purchases = purchase_matrix.loc[top_users]

    weighted_scores = similar_users_purchases.T.dot(sim_scores[top_users])

    # Remove products the user already bought
    user_products = purchase_matrix.loc[user.id]
    products_already_bought = user_products[user_products > 0].index

    weighted_scores = weighted_scores.drop(labels=products_already_bought, errors='ignore')

    # Pick top products by weighted score
    recommended_product_ids = weighted_scores.sort_values(ascending=False).head(limit).index.tolist()

    # Return products queryset ordered by this recommendation order
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(recommended_product_ids)])
    recommended_products = Product.objects.filter(id__in=recommended_product_ids, is_available=True).order_by(preserved)

    # If not enough recommendations, fill with popular products
    if recommended_products.count() < limit:
        needed = limit - recommended_products.count()
        popular_products = Product.objects.filter(is_available=True).exclude(id__in=recommended_product_ids).order_by('-created_date')[:needed]
        recommended_products = list(recommended_products) + list(popular_products)

    return recommended_products[:limit]