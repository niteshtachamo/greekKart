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
    path('place_order/', place_order, name='place_order'),

    # Used by Stripe and Khalti to create payment record and finalize order
    path('payments/', payments, name='payments'),

    # Khalti integration
    path('khalti-request/', KhaltiRequestView.as_view(), name='khaltirequest'),
    path('khalti-verify/', KhaltiVerifyView.as_view(), name='khaltiverify'),

    # Finalize payment after verification (Ajax POST)
    path('payment-complete/', payment_complete, name='payment_complete'),

    # Stripe integration
    path('stripe-checkout/', StripeCheckoutRedirectView.as_view(), name='stripe-checkout'),
    path('payment-success/', views.payment_success, name='payment-success'),
    path('payment-cancel/', views.stripe_cancel, name='payment_cancel'),

    # Cash On Delivery order confirmation
    path('cod-order/', views.cod_order, name='cod_order'),
    path('cod-success/', views.cod_success_page, name='cod_success_page'),


]
