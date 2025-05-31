from django.contrib import admin
from.models import Product,Variation,ReviewRating,ProductGalary
import admin_thumbnails

@admin_thumbnails.thumbnail('image')
class ProductGalleryInline(admin.TabularInline):
    model = ProductGalary
    extra = 1
    
class ProductAdmin(admin.ModelAdmin):
    list_display=('product_name','price','stock','category','created_date','modified_date','is_available')
    prepopulated_fields = {'slug': ('product_name',)} 
    inlines=[ProductGalleryInline]
    
class VariationAdmin(admin.ModelAdmin):
    list_display=('product','variation_category','variation_value','created_data','is_active') 
    list_editable=('is_active',)
    list_filter=('product','variation_category','variation_value','created_data','is_active') 
    
@admin_thumbnails.thumbnail('image')
class ProductGalleryAdmin(admin.ModelAdmin):
    list_display = ['product', 'image']


admin.site.register(Product,ProductAdmin)
admin.site.register(Variation,VariationAdmin)
admin.site.register(ReviewRating)
admin.site.register(ProductGalary)

