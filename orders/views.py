from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.core.mail import EmailMessage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from datetime import date
import json
import requests

from .forms import OrderForm
from .models import Order, Payment, OrderProduct
from carts.models import CartItem
from store.models import Product

from django.urls import reverse

import stripe



def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])

    payment = Payment(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total(),
        status=body['status'],
    )
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()

    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        order_product = OrderProduct()
        order_product.order = order
        order_product.payment = payment
        order_product.user = request.user
        order_product.product = item.product
        order_product.quantity = item.quantity
        order_product.sub_total()
        order_product.ordered = True
        order_product.save()
        order_product.variations.set(item.variations.all())
        order_product.save()

        if item.variations.exists():
            order_product.variations.set(item.variations.all())

        product = Product.objects.get(id=item.product.id)
        product.stock -= item.quantity
        product.save()

    CartItem.objects.filter(user=request.user).delete()


def place_order(request, total=0, quantity=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += cart_item.sub_total()
        quantity += cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            current_date = date.today().strftime('%Y%m%d')
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'total': total,
                'grand_total': grand_total,
                'tax': tax,
                'cart_items': cart_items,
            }
            return render(request, 'orders/payments.html', context)
        else:
            return redirect('checkout')
    else:
        form = OrderForm()
    return render(request, 'orders/place_order.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total,
        'quantity': quantity,
        'tax': tax,
        'grand_total': grand_total,
    })


# Khalti payment
class KhaltiRequestView(View):
    def get(self, request, *args, **kwargs):
        o_id = request.GET.get("o_id")
        order = get_object_or_404(Order, id=o_id, user=request.user, is_ordered=False)

        # Khalti payment request data
        url = "https://a.khalti.com/api/v2/epayment/initiate/"
        payload = {
            "return_url": request.build_absolute_uri(f"/orders/khalti-verify/?order_id={order.id}"),
            "website_url": request.build_absolute_uri("/"),
            "amount": int(order.order_total * 100),  # Khalti expects amount in paisa
            "purchase_order_id": str(order.id),
            "purchase_order_name": f"Order {order.order_number}",
        }
        headers = {
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        # Make the API request to Khalti
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        # If payment_url is returned, redirect user to Khalti page
        payment_url = data.get("payment_url")
        if payment_url:
            return redirect(payment_url)
        else:
            # If error, render a payment error page
            return render(request, "orders/payment_error.html", {
                "error": data.get("detail", "Failed to initiate Khalti payment.")
            })


class KhaltiVerifyView(View):
    def get(self, request, *args, **kwargs):
        pidx = request.GET.get("pidx")
        o_id = request.GET.get("order_id")

        # Khalti payment lookup API endpoint
        url = "https://a.khalti.com/api/v2/epayment/lookup/"
        payload = {
            "pidx": pidx
        }
        headers = {
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}"
        }

        # Get the order for current user
        order = get_object_or_404(Order, id=o_id, user=request.user)

        # Call Khalti API to verify payment
        response = requests.post(url, json=payload, headers=headers)
        resp_dict = response.json()

        if resp_dict.get("status") == "Completed":
            # Mark order as paid
            order.payment_completed = True
            order.is_ordered = True  # mark as ordered
            order.save()

            # Save order_id in session for payment_success view
            request.session['order_id'] = order.id

            return redirect('payment_success')
        else:
            # Return JSON error response if payment not completed
            return JsonResponse({"success": False, "error": resp_dict})



@csrf_exempt
@require_POST
def payment_complete(request):
    try:
        data = json.loads(request.body)
        trans_id = data.get("transID")
        payment_method = data.get("payment_method")
        status = data.get("status")
        order_id = data.get("orderID")

        order = get_object_or_404(Order, id=order_id, user=request.user, is_ordered=False)

        payment = Payment.objects.create(
            user=request.user,
            payment_id=trans_id,
            payment_method=payment_method,
            amount_paid=order.order_total,
            status=status,
        )

        order.payment = payment
        order.is_ordered = True
        order.save()

        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            order_product = OrderProduct.objects.create(
                order=order,
                payment=payment,
                user=request.user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True,
            )
            order_product.variations.set(item.variations.all())

            product = item.product
            product.stock -= item.quantity
            product.save()

        cart_items.delete()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeCheckoutRedirectView(View):
    def get(self, request, *args, **kwargs):
        o_id = request.GET.get("o_id")
        order = get_object_or_404(Order, id=o_id, user=request.user, is_ordered=False)
        request.session['order_id'] = order.id

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Order #{order.order_number}",
                    },
                    'unit_amount': int(order.order_total * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://localhost:8000/orders/payment-success/',
            cancel_url='http://localhost:8000/orders/payment-cancel/',
        )
        return redirect(session.url, code=303)


from django.contrib.auth.decorators import login_required


@login_required
@login_required
def payment_success(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('store')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Check if payment exists
    payment = Payment.objects.filter(order=order).first()

    if not payment:
        # No payment recorded yet - create based on order.is_ordered and payment method

        # For example, if order.is_ordered is False, treat as Stripe (adjust if needed)
        if not order.is_ordered:
            payment = Payment.objects.create(
                user=request.user,
                payment_id=f"stripe_{order.order_number}",
                payment_method='Stripe',
                amount_paid=order.order_total,
                status='Completed',
            )
            order.is_ordered = False  # or True if you want here
        else:
            # order.is_ordered == True, treat as Khalti
            payment = Payment.objects.create(
                user=request.user,
                payment_id=f"khalti_{order.order_number}",
                payment_method='Khalti',
                amount_paid=order.order_total,
                status='Completed',
            )
            order.is_ordered = True

        order.payment = payment
        order.save()

        # Move cart items to order products only once
        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            order_product = OrderProduct.objects.create(
                order=order,
                payment=payment,
                user=request.user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True,
            )
            order_product.variations.set(item.variations.all())

            product = item.product
            product.stock -= item.quantity
            product.save()

        cart_items.delete()

        mail_subject = 'Thank you for your order.'
        message = render_to_string('orders/order_received_email.html', {
            'user': request.user,
            'order': order,
        })
        to_email = request.user.email
        send_email = EmailMessage(mail_subject, message, to=[to_email])
        send_email.send()

    else:
        # Payment already exists, just fetch ordered products
        payment = payment

    ordered_products = OrderProduct.objects.filter(order=order)

    # Remove session var
    if 'order_id' in request.session:
        del request.session['order_id']

    # Calculate tax
    total = sum(op.product_price * op.quantity for op in ordered_products)
    tax = (2 * total) / 100

    context = {
        'order': order,
        'payment': payment,
        'ordered_products': ordered_products,
        'tax': tax,
    }

    return render(request, 'orders/paymentsuccess.html', context)


def stripe_cancel(request):
    return render(request, 'orders/stripecancel.html')





@csrf_exempt
def cod_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')

            if not order_id:
                return JsonResponse({'error': 'Order ID is missing.'}, status=400)

            order = Order.objects.get(id=order_id)

            # Create payment entry for COD, status pending
            payment = Payment.objects.create(
                user=order.user,
                payment_id=f'COD_{order_id}',
                payment_method='COD',
                amount_paid=str(order.order_total),
                status='Pending',
            )

            # Link payment to order, but DO NOT move cart or reduce stock here
            order.payment = payment
            order.payment_method = 'COD'
            order.payment_status = 'Pending'
            order.is_ordered = True
            order.save()

            # Store order ID in session for success page
            request.session['cod_order_id'] = order.id

            # Clear the user's cart after successful COD order
            from carts.models import CartItem
            CartItem.objects.filter(user=order.user).delete()

            return JsonResponse({'success': True, 'redirect_url': reverse('cod_success_page')})

        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


def cod_success_page(request):
    order_id = request.session.get('cod_order_id')
    order = None
    if order_id:
        from .models import Order
        order = Order.objects.filter(id=order_id).first()
        # Optionally, remove the session variable after use
        del request.session['cod_order_id']
    return render(request, 'orders/cod_success_page.html', {'order': order})

