from django.contrib import admin
from .models import Payment,Order,OrderProduct
from .utils import process_cod_order

# Register your models here.

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'variations', 'quantity', 'product_price', 'tax', 'ordered',)
    fields = ('payment', 'user', 'product', 'variations', 'quantity', 'product_price', 'tax', 'ordered')
    extra = 0
    
    
    
    
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name','email','phone','city','order_total', 'tax','status', 'is_ordered','created_at')
    list_filter=['status','is_ordered']
    search_fields=['order_number', 'full_name','email','phone']
    list_per_page=20
    inlines = [OrderProductInline]


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'payment_method', 'status', 'amount_paid', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('payment_id',)

    def save_model(self, request, obj, form, change):
        if change:
            old_payment = Payment.objects.get(pk=obj.pk)
            # When changing status from anything but 'Completed' to 'Completed'
            if old_payment.status != 'Completed' and obj.status == 'Completed':
                order = Order.objects.filter(payment=obj).first()
                if order:
                    process_cod_order(order)  # your custom function to move cart to order products, reduce stock, etc.
                    order.status = 'Completed'
                    order.save()
        super().save_model(request, obj, form, change)
    
admin.site.register(Payment,PaymentAdmin)
admin.site.register(Order,OrderAdmin)
admin.site.register(OrderProduct)
