from django.shortcuts import render, get_object_or_404
from .models import Product,ProductGalary
from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id
from django.http import HttpResponse
from django.core.paginator import EmptyPage,PageNotAnInteger,Paginator
from django.db.models import Q
from store.models import Variation  # Make sure this is imported
from django.db.models import Avg, Count
from store.models import Product  



from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from.forms import ReviewForm
from .models import ReviewRating 
from orders.models import OrderProduct
# Create your views here.

from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from .models import Product, Category

def store(request, category_slug=None):
    categories = None
    products = Product.objects.filter(is_available=True)

    # Category filtering
    if category_slug is not None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=categories)

    # Price range filtering
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Pagination
    paginator = Paginator(products, 3)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': products,
        'product_count': products.count(),
    }
    return render(request, 'store/store.html', context)


# views.py
def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        single_product.save()

        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e

    if request.user.is_authenticated:
        orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
    else:
        orderproduct = None

    # Reviews
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)

    # Product gallery
    product_gallery = ProductGalary.objects.filter(product_id=single_product.id)

    # Filter color and size variations
    size_variations = Variation.objects.filter(product=single_product, variation_category='size', is_active=True)

    # Related products: same category, exclude current product
    related_products = Product.objects.filter(category=single_product.category).exclude(id=single_product.id)[:4]

    context = {
        'single_product': single_product,
        'in_cart': in_cart,
        'orderproduct': orderproduct,
        'reviews': reviews,
        'product_gallery': product_gallery,
        'sizes': size_variations,
        'related_products': related_products,
    }

    return render(request, 'store/product_detail.html', context)


def search(request):
    keyword = request.GET.get('keyword')

    if keyword:  
        products = Product.objects.order_by('-created_date').filter(
            Q(description__icontains=keyword) | Q(product_name__icontains=keyword)
        )
        product_count = products.count()
    else:
        products = []
        product_count = 0

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)



def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == "POST":
        try:
            review = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=review)
            form.save()

            # 🔄 Update product rating
            product = Product.objects.get(id=product_id)
            product.rating = product.averageReview()
            product.save()

            messages.success(request, "Your review has been updated. Thank YOU!!!")
            return redirect(url)

        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = ReviewRating()
                review.subject = form.cleaned_data['subject']
                review.review = form.cleaned_data['review']
                review.rating = form.cleaned_data['rating']
                review.ip = request.META.get('REMOTE_ADDR')
                review.product_id = product_id
                review.user_id = request.user.id
                review.save()

                # 🔄 Update product rating
                product = Product.objects.get(id=product_id)
                product.rating = product.averageReview()
                product.save()

                messages.success(request, "Your review has been submitted. Thank YOU!!!")
                return redirect(url)





