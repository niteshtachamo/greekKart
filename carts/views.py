from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    current_user=request.user
    product = Product.objects.get(id=product_id)
    # if user is authenticated
    if current_user.is_authenticated:
        product_variation = []
        # Check if variations are provided in the POST request and append them
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]
                
                try:
                    variation = Variation.objects.get(
                        product=product,
                        variation_category__iexact=key,
                        variation_value__iexact=value
                    )
                    product_variation.append(variation)
                except Variation.DoesNotExist:
                    pass

       

        # Check if the product with variations already exists in the cart
        cart_item_qs = CartItem.objects.filter(product=product, user=current_user)

        # Check if there is already a cart item with the same product and variations
        for item in cart_item_qs:
            existing_variation = item.variations.all()
            # If the product and variations match, increase quantity
            if set(existing_variation) == set(product_variation):
                item.quantity += 1
                item.save()
                return redirect('cart')  # Redirect to cart page

        # If no matching cart item found, create a new one
        cart_item = CartItem.objects.create(
            product=product,
            quantity=1,
            user=current_user
        )
        if len(product_variation) > 0:
            cart_item.variations.clear()
            cart_item.variations.add(*product_variation)
        cart_item.save()

        return redirect('cart')  # Redirect to cart page # Redirect to cart page
    # if user in not authenticated
    else:
        product_variation = []
        # Check if variations are provided in the POST request and append them
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]
                
                try:
                    variation = Variation.objects.get(
                        product=product,
                        variation_category__iexact=key,
                        variation_value__iexact=value
                    )
                    product_variation.append(variation)
                except Variation.DoesNotExist:
                    pass

        # Get or create a cart for the session
        cart, created = Cart.objects.get_or_create(cart_id=_cart_id(request))

        # Check if the product with variations already exists in the cart
        cart_item_qs = CartItem.objects.filter(product=product, cart=cart)

        # Check if there is already a cart item with the same product and variations
        for item in cart_item_qs:
            existing_variation = item.variations.all()
            # If the product and variations match, increase quantity
            if set(existing_variation) == set(product_variation):
                item.quantity += 1
                item.save()
                return redirect('cart')  # Redirect to cart page

        # If no matching cart item found, create a new one
        cart_item = CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
        )
        if len(product_variation) > 0:
            cart_item.variations.clear()
            cart_item.variations.add(*product_variation)
        cart_item.save()

        return redirect('cart')  # Redirect to cart page # Redirect to cart page



def remove_cart(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item=CartItem.objects.get(product=product,user=request.user,id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')

def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user ,id=cart_item_id)
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')

def cart(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user,is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

        tax = (2 * total) / 100
        grand_total = total + tax
    except ObjectDoesNotExist:
        cart_items = []

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/cart.html', context)


@login_required(login_url='login')
def checkout(request,total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user,is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

        tax = (2 * total) / 100
        grand_total = total + tax
    except ObjectDoesNotExist:
        cart_items = []

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/checkout.html', context)
