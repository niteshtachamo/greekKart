from django.db import models
from store.models import Product, Variation
from accounts.models import Account

# Cart model stores the unique identifier and date of the cart
class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id

# CartItem model stores the product, variations, quantity, and cart relationship
class CartItem(models.Model):
    user=models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)  # Multiple variations can be added for the same product
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE,null=True)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def sub_total(self):
        # Returns the total cost for this cart item (product price * size * quantity)
        size = 1
        size_variation = self.variations.filter(variation_category__iexact='size').first()
        if size_variation:
            try:
                size = int(size_variation.variation_value)
            except (ValueError, TypeError):
                size = 1  # fallback if not an integer
        return self.product.price * size * self.quantity

    @property
    def unit_price_with_size(self):
        size = 1
        size_variation = self.variations.filter(variation_category__iexact='size').first()
        if size_variation:
            try:
                size = int(size_variation.variation_value)
            except (ValueError, TypeError):
                size = 1
        return self.product.price * size

    def __unicode__(self):
        return self.product
