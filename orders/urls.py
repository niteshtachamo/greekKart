from django.urls import path
from . import views
from .views import (
    place_order,
    payments,
    KhaltiRequestView,
    KhaltiVerifyView,
    StripeCheckoutRedirectView,
    payment_complete,
)

urlpatterns = [
    # Place Order
    path('place_order/', place_order, name='place_order'),

    # Payments (Generic/Stripe)
    path('payments/', payments, name='payments'),
    path('stripe-checkout/', StripeCheckoutRedirectView.as_view(), name='stripe_checkout'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.stripe_cancel, name='payment_cancel'),

    # Khalti Integration
    path('khalti-request/', KhaltiRequestView.as_view(), name='khalti_request'),
    path('khalti-verify/', KhaltiVerifyView.as_view(), name='khalti_verify'),
    path('payment-complete/', payment_complete, name='payment_complete'),

    # Cash On Delivery (COD)
    path('cod-order/', views.cod_order, name='cod_order'),
    path('cod-success/', views.cod_success_page, name='cod_success_page'),
]
