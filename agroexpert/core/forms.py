from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class UserRegistrationForm(forms.ModelForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirm Password")
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords don't match")
        return password_confirm

class UserLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

from django.contrib.gis import forms as gis_forms
from .models import Field

class FieldForm(forms.ModelForm):
    # Geometry will be handled by a hidden input, populated by Leaflet.js
    # We expect GeoJSON string to be submitted here.
    geometry = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = Field
        fields = ['name', 'description', 'geometry']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing instance, populate the hidden geometry field
        # with its GeoJSON representation for Leaflet to use.
        if self.instance and self.instance.pk and self.instance.geometry:
            self.initial['geometry'] = self.instance.geometry.geojson

from .models import AgroOperation, Crop, OperationType

class AgroOperationForm(forms.ModelForm):
    operation_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    crop = forms.ModelChoiceField(
        queryset=Crop.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'}), 
        required=False
    )
    operation_type = forms.ModelChoiceField(
        queryset=OperationType.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    equipment_used = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}), 
        required=False
    )
    materials_cost = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), 
        required=False
    )

    class Meta:
        model = AgroOperation
        fields = ['crop', 'operation_type', 'operation_date', 'description', 'equipment_used', 'materials_cost']
        # 'field' and 'user' will be set in the view

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None) # Store request for later use if needed
        self.field_instance = kwargs.pop('field_instance', None) # Store field for pre-selection or validation
        super().__init__(*args, **kwargs)

        # Optionally, if you want to limit choices based on something (e.g. user-specific crops)
        # if self.request:
        #     self.fields['crop'].queryset = Crop.objects.filter(...) # Example
        
        # If creating a new operation and field_instance is provided,
        # you might want to set initial values or limit choices based on the field.
        # For now, the form is generic.
