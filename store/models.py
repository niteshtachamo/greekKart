from django.db import models
from category.models import Category
from django.urls import reverse
from accounts.models import Account
from django.db.models import Avg

# Create your models here.
class Product(models.Model):
    product_name=models.CharField(max_length=200,unique=True)
    slug=models.SlugField(max_length=255,unique=True)
    description =models.TextField(max_length=500,blank=True)
    price=models.IntegerField()
    images=models.ImageField(upload_to='photos/products')
    stock=models.IntegerField()
    is_available=models.BooleanField(default=True)
    category =models.ForeignKey(Category,on_delete=models.CASCADE)
    created_date=models.DateTimeField(auto_now_add=True)
    modified_date=models.DateTimeField(auto_now=True)
    rating = models.FloatField(default=0.0)  # Out of 5
    click_count = models.PositiveIntegerField(default=0)
    
    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])
    
    def __str__(self):
        return self.product_name
    

    def averageReview(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(average=Avg('rating'))
        avg = 0
        if reviews['average'] is not None:
            avg = float(reviews['average'])
        return avg


    def countReview(self):
        return ReviewRating.objects.filter(product=self, status=True).count()

    def get_recommended_products(self, user=None, limit=4):
        """
        Get recommended products using collaborative filtering
        Based on users who bought similar products
        """
        from orders.models import OrderProduct
        from django.db.models import Count, Q
        from django.contrib.auth.models import User
        
        if not user or not user.is_authenticated:
            # For non-authenticated users, return popular products
            return Product.objects.filter(is_available=True).order_by('-click_count')[:limit]
        
        # Get products this user has purchased
        user_purchases = OrderProduct.objects.filter(
            user=user, 
            ordered=True
        ).values_list('product_id', flat=True)
        
        if not user_purchases:
            # If user has no purchase history, return popular products
            return Product.objects.filter(is_available=True).order_by('-click_count')[:limit]
        
        # Find users who bought the same products as current user
        similar_users = OrderProduct.objects.filter(
            product_id__in=user_purchases,
            ordered=True
        ).exclude(user=user).values_list('user_id', flat=True).distinct()
        
        if not similar_users:
            # If no similar users, return popular products
            return Product.objects.filter(is_available=True).order_by('-click_count')[:limit]
        
        # Get products bought by similar users but not by current user
        recommended_products = OrderProduct.objects.filter(
            user_id__in=similar_users,
            ordered=True
        ).exclude(
            product_id__in=user_purchases
        ).values('product_id').annotate(
            purchase_count=Count('product_id')
        ).order_by('-purchase_count')[:limit]
        
        # Get the actual product objects
        product_ids = [item['product_id'] for item in recommended_products]
        products = Product.objects.filter(
            id__in=product_ids,
            is_available=True
        )
        
        # If we don't have enough recommendations, fill with popular products
        if products.count() < limit:
            remaining_count = limit - products.count()
            popular_products = Product.objects.filter(
                is_available=True
            ).exclude(
                id__in=product_ids
            ).order_by('-click_count')[:remaining_count]
            products = list(products) + list(popular_products)
        
        return products[:limit]
    
    
class VariationManager(models.Manager):
    def colors(self):
        return super().get_queryset().filter(variation_category='color', is_active=True)

    def sizes(self):
        return super().get_queryset().filter(variation_category='size', is_active=True)
    
variation_category_choice={
    ('color','color'),('size','size'),
}
class Variation(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    variation_category=models.CharField(max_length=100,choices=variation_category_choice)
    variation_value=models.IntegerField()
    is_active=models.BooleanField(default=True)
    created_data=models.DateTimeField(auto_now_add=True)
    
    objects=VariationManager()
    
    def __str__(self):
        return self.variation_value
    
    


class ReviewRating(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    user=models.ForeignKey(Account,on_delete=models.CASCADE)
    subject=models.CharField(max_length=100,blank=True)
    review=models.TextField(max_length=500,blank=True)
    rating=models.FloatField()
    ip=models.CharField(max_length=20,blank=True)
    status=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.subject
    

class ProductGalary(models.Model):
    product=models.ForeignKey(Product,default=None,on_delete=models.CASCADE)
    image=models.ImageField(upload_to='store/products',max_length=255)
    
    def __str__(self):
        return self.product.product_name
    
    class Meta:
        verbose_name='productgallery'
        verbose_name_plural='productgallery'
    
    