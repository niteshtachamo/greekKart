from django import forms
from .models import Account


class RegistrationForm(forms.ModelForm):
    password=forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder':"Enter your Password",
        'class':'form-control'
    }))
    confirm_password=forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder':"Enter your Password Again",
        'class':'form-control'

    }))
    
    
    class Meta:
        model=Account
        fields=['first_name','last_name','phone_number','email','password']
        
    def clean(self):
        cleaned_data=super(RegistrationForm,self).clean()
        password=cleaned_data.get('password')
        confirm_password=cleaned_data.get('confirm_password')
        
        if password != confirm_password:
            raise forms.ValidationError(
                "password doesnot match!!!"
            )
            
            
    def __init__(self,*args,**kwargs):
        super(RegistrationForm,self).__init__(*args,**kwargs)
        self.fields['first_name'].widget.attrs['placeholder']='Enter your Fiest name'
        self.fields['last_name'].widget.attrs['placeholder']='Enter your Last Name'
        self.fields['email'].widget.attrs['placeholder']='Enter your Email'
        self.fields['phone_number'].widget.attrs['placeholder']='Enter your Phone Number'
        for field in self.fields:
            self.fields[field].widget.attrs['class']='form-control'
            
    

from django import forms
from .models import Account, UserProfile

class UserForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'phone_number']

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['address_line_1', 'address_line_2', 'profile_picture', 'city', 'state', 'country']

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # For file input, use different class to keep default style
            if field_name == 'profile_picture':
                field.widget.attrs['class'] = 'form-control-file'
            else:
                field.widget.attrs['class'] = 'form-control'
