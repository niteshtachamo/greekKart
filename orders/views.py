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
        total += (cart_item.product.price * cart_item.quantity)
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
        return render(request, "orders/khaltirequest.html", {"order": order})


class KhaltiVerifyView(View):
    def get(self, request, *args, **kwargs):
        token = request.GET.get("token")
        amount = request.GET.get("amount")
        o_id = request.GET.get("order_id")

        url = "https://khalti.com/api/v2/payment/verify/"
        payload = {"token": token, "amount": amount}
        headers = {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"}

        order = get_object_or_404(Order, id=o_id, user=request.user)
        response = requests.post(url, data=payload, headers=headers)
        resp_dict = response.json()

        if resp_dict.get("idx"):
            order.payment_completed = True
            order.save()
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})


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
def payment_success(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('store')

    order = get_object_or_404(Order, id=order_id, user=request.user, is_ordered=False)

    if not Payment.objects.filter(payment_id__startswith='stripe_', order=order).exists():
        payment = Payment.objects.create(
            user=request.user,
            payment_id=f"stripe_{order.order_number}",
            payment_method='Stripe',
            amount_paid=order.order_total,
            status='Completed',
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

        mail_subject = 'Thank you for the ordering.'
        message = render_to_string('orders/order_received_email.html', {
            'user': request.user,
            'order': order,
        })
        to_email = request.user.email
        send_email = EmailMessage(mail_subject, message, to=[to_email])
        send_email.send()

        ordered_products = OrderProduct.objects.filter(order=order)

    # Remove the session variable after successful order
    del request.session['order_id']

# Calculate tax for each ordered product (2% of product price)
    for item in ordered_products:
        item.tax = round(item.product_price * item.quantity * 0.02, 2)

# Context to pass to the template
    context = {
        'order': order,
        'payment': payment,
        'ordered_products': ordered_products,
    }

# Return the rendered template
    return render(request, 'orders/paymentsuccess.html', context)


def stripe_cancel(request):
    return render(request, 'orders/stripecancel.html')


@csrf_exempt
def cod_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')

            order = Order.objects.get(id=order_id)
            order.payment_method = 'COD'
            order.payment_status = 'Pending'
            order.is_ordered = True
            order.save()

            return JsonResponse({'message': 'Cash on Delivery order placed successfully!'}, status=200)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)
