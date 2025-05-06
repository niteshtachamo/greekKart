from django.db import models
from store.models import Product, Variation

# Cart model stores the unique identifier and date of the cart
class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id

# CartItem model stores the product, variations, quantity, and cart relationship
class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)  # Multiple variations can be added for the same product
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def sub_total(self):
        # Returns the total cost for this cart item (product price * quantity)
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.product_name} ({self.quantity})"
