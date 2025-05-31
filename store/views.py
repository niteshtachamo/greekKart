from django.shortcuts import render, get_object_or_404
from .models import Product,ProductGalary
from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id
from django.http import HttpResponse
from django.core.paginator import EmptyPage,PageNotAnInteger,Paginator
from django.db.models import Q

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from.forms import ReviewForm
from .models import ReviewRating 
from orders.models import OrderProduct
# Create your views here.

def store(request, category_slug=None):
    categories = None
    products = None
    
    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
        paginator=Paginator(products,3)
        page=request.GET.get('page')
        paged_products=paginator.get_page(page)
        product_count = products.count()
    else:
        products = Product.objects.all().filter(is_available=True).order_by('id')
        paginator=Paginator(products,3)
        page=request.GET.get('page')
        paged_products=paginator.get_page(page)
        product_count=products.count()
    
    context = {
        'products': paged_products,
        'product_count':product_count,
    }
    return render(request,'store/store.html',context)

def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart =CartItem.objects.filter(cart__cart_id=_cart_id(request),product=single_product).exists()
    
    except Exception as e:
        raise e
    
    
    if request.user.is_authenticated:
        try:
            orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
        except OrderProduct.DoesNotExist:
            orderproduct = None
    else:
        orderproduct=None
        
    # reviews get
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)
    
    #product gallery
    product_gallery = ProductGalary.objects.filter(product_id=single_product.id)
     
    context = {
        'single_product': single_product,
        'in_cart':in_cart,
        'orderproduct':orderproduct,
        'reviews':reviews,
        'product_gallery':product_gallery,
    }

    return render(request, 'store/product_detail.html', context)


def search(request):
    keyword = request.GET.get('keyword')

    if keyword:  # Check if keyword is not None and not empty
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
            # If review already exists
            review = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=review)
            form.save()
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
                messages.success(request, "Your review has been submitted. Thank YOU!!!")
                return redirect(url)
            


