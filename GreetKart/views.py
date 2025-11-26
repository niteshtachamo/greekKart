from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count, Case, When
from store.models import Product
from store.utils import get_collaborative_recommendations
from orders.models import OrderProduct

def home(request):
    # Top-rated products (optional)
    high_rated_products = Product.objects.filter(
        is_available=True,
        reviewrating__status=True
    ).annotate(
        avg_rating=Avg('reviewrating__rating'),
        review_count=Count('reviewrating')
    ).filter(
        review_count__gt=0
    ).order_by('-avg_rating')[:8]

    # Trending products (most ordered in last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    trending_products_qs = (
        OrderProduct.objects.filter(
            order__is_ordered=True,
            order__payment__status='Completed',
            order__created_at__gte=seven_days_ago,
            product__is_available=True
        )
        .values('product')
        .annotate(order_count=Count('product'))
        .order_by('-order_count')[:8]
    )
    trending_product_ids = [item['product'] for item in trending_products_qs]
    if trending_product_ids:
        preserved_order = Case(*[
            When(pk=pk, then=pos) for pos, pk in enumerate(trending_product_ids)
        ])
        trending_products = Product.objects.filter(
            id__in=trending_product_ids,
            is_available=True
        ).order_by(preserved_order)
    else:
        trending_products = Product.objects.none()

    # Collaborative filtering recommendations
    recommended_products = get_collaborative_recommendations(request.user, limit=8)

    context = {
        'high_rated_products': high_rated_products,
        'trending_products': trending_products,
        'recommended_products': recommended_products,
    }

    return render(request, 'home.html', context)
