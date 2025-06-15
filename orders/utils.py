# orders/utils.py
from .models import OrderProduct
from carts.models import CartItem

def process_cod_order(order):
    payment = order.payment
    cart_items = CartItem.objects.filter(user=order.user)

    for item in cart_items:
        order_product = OrderProduct.objects.create(
            order=order,
            payment=payment,
            user=order.user,
            product=item.product,
            quantity=item.quantity,
            product_price=item.product.price,
            ordered=True,
            tax=float(order.tax)
        )
        order_product.variations.set(item.variations.all())
        order_product.save()

        # Reduce stock
        item.product.stock -= item.quantity
        item.product.save()

    # Clear the cart
    cart_items.delete()
