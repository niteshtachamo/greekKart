from django.shortcuts import render
from django.db.models import Avg, Count
from store.models import Product

def home(request):
    products = Product.objects.filter(is_available=True)

    # Top Rated Products (with reviews only)
    high_rated_products = Product.objects.filter(
        is_available=True,
        reviewrating__status=True  # only approved reviews
    ).annotate(
        avg_rating=Avg('reviewrating__rating'),
        review_count=Count('reviewrating')
    ).filter(
        review_count__gt=0
    ).order_by('-avg_rating')[:8]

    # Most Clicked Products
    most_clicked_products = products.order_by('-click_count')[:8]

    # Recommended Products using collaborative filtering
    recommended_products = Product.objects.first().get_recommended_products(request.user, limit=8)

    context = {
        'high_rated_products': high_rated_products,
        'most_clicked_products': most_clicked_products,
        'recommended_products': recommended_products,
    }
    return render(request, 'home.html', context)
