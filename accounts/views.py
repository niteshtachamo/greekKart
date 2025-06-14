from django.shortcuts import render, redirect
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.http import HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from decimal import Decimal

from accounts.models import UserProfile
from accounts.forms import UserForm, UserProfileForm
import requests

from carts.models import Cart, CartItem
from carts.views import _cart_id
from orders.models import Order,OrderProduct

from .models import Account, UserProfile
from .forms import RegistrationForm, UserForm, UserProfileForm



# verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_decode,urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            password = form.cleaned_data['password']
            username = email.split('@')[0]

            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password
            )
            user.phone_number = phone_number
            user.is_active = True 
            user.save()
            
            # create user profile
            profile=UserProfile()
            profile.user_id=user.id
            profile.profile_picture='default/default-user.png'
            profile.save()
            
            # user activation
            current_site=get_current_site(request)
            mail_subject="please activate your account"
            message =render_to_string('accounts/account_verification_email.html',{
                'user':user,
                'domain':current_site,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)),
                'token':default_token_generator.make_token(user),
            })
            to_email=email
            send_email=EmailMessage(mail_subject,message,to=[to_email])
            send_email.send()
            # messages.success(request,'Thank you forregistering with us. We have sent a verification email to your email address.please verify it.')
            # Optionally redirect after registration
            return redirect('/accounts/login/?command=verification&email='+email)  # Change 'login' to your desired redirect URL name
    else:
        form = RegistrationForm()

    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)

def login(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(username=email, password=password)

        if user is not None:
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                cart_items = CartItem.objects.filter(cart=cart)

                if cart_items.exists():
                    # Get existing cart items of the logged-in user
                    user_cart_items = CartItem.objects.filter(user=user)
                    user_variation_list = []

                    for item in user_cart_items:
                        variations = item.variations.all()
                        user_variation_list.append(list(variations))

                    # Assign the cart items from session to the logged-in user
                    for item in cart_items:
                        item_variations = list(item.variations.all())
                        if item_variations in user_variation_list:
                            index = user_variation_list.index(item_variations)
                            existing_item = user_cart_items[index]
                            existing_item.quantity += item.quantity
                            existing_item.save()
                            item.delete()  # remove duplicate
                        else:
                            item.user = user
                            item.save()

            except Cart.DoesNotExist:
                pass

            auth.login(request, user)
            url=request.META.get('HTTP_REFERER')
            try:
                query=requests.utils.urlparse(url).query
                params=dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    return redirect(params['next'])
                return redirect("nextPage")
            except:
                pass
                return redirect('dashboard')

        else:
            messages.error(request, "Invalid email or password")
            return redirect('login')

    return render(request, 'accounts/login.html')

@login_required(login_url='login')
def logout(request):
    auth_logout(request)
    messages.success(request, "You are logged out")
    return redirect('home')


def activate(request,uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user=None
        
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your account has been activated successfully!!!")
        return redirect('login')
    else:
        messages.error(request, "Your account has not been activated successfully!!!")
        return redirect('register')
    
@login_required(login_url='login')
def dashboard(request):
    orders=Order.objects.order_by('-created_at').filter(user_id=request.user.id,is_ordered=True)
    orders_count=orders.count()
    userprofile=UserProfile.objects.get(user_id=request.user.id)
    context={
        'orders':orders,
        'orders_count':orders_count,
        'userprofile':userprofile,
        }
    
    return render(request,'accounts/dashboard.html',context)


def forgetpassword(request):
    if request.method == "POST":
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            current_site=get_current_site(request)
            mail_subject="Reset your Password"
            message =render_to_string('accounts/reset_password_email.html',{
                'user':user,
                'domain':current_site,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)),
                'token':default_token_generator.make_token(user),
            })
            to_email=email
            send_email=EmailMessage(mail_subject,message,to=[to_email])
            send_email.send()
            messages.success(request, "Password reset link has been sent to your email")
            return redirect('login')
        else:
            messages.error(request, "Email does not exist")
            return redirect('forgetpassword')
    return render(request, 'accounts/forgetpassword.html')
    
    
def resetpassword_validate(request,uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user=None
    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid']=uid
        messages.success(request, "Reset your password!!!")
        return redirect('resetpassword')
    else:
        messages.error(request, "Link has been expired!!!")
        return redirect('login') 
    
def resetpassword(request):
    if request.method == "POST":
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, "Password has been reset!!!")
            return redirect('login')
        else:
            messages.error(request, "Password does not match!!!")
            return redirect('resetpassword')
    else:
        return render(request, 'accounts/resetpassword.html')
    
    
@login_required

def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders': orders
        }
    return render(request, 'accounts/my_orders.html', context)


@login_required

def edit_profile(request):
    user = request.user
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=user)
        profile.save()

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('edit_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'accounts/edit_profile.html', context)




@login_required
def change_password(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')

        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return redirect('change_password')

        user.set_password(new_password)
        user.save()

        # Keeps the user logged in after password change
        # update_session_auth_hash(request, user)

        messages.success(request, 'Your password has been updated successfully.')
        return redirect('change_password')

    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=profile)
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        return render(request, 'accounts/change_password.html', context)
    
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_number=order_id)
    payment = order.payment
    order_items = OrderProduct.objects.filter(order=order)

    subtotal = 0
    quantity = 0

    for item in order_items:
        item_total = item.product_price * item.quantity
        subtotal += item_total
        quantity += item.quantity

        # Set subtotal to each item for display
        item.subtotal = round(item_total, 2)

    tax = round((2 * subtotal) / 100, 2)  # 2% flat tax
    grand_total = round(subtotal + tax, 2)

    context = {
        'order_detail': order_items,
        'order': order,
        'payment': payment,
        'subtotal': round(subtotal, 2),
        'total_tax': tax,
        'grand_total': grand_total,
    }

    return render(request, 'accounts/order_detail.html', context)
