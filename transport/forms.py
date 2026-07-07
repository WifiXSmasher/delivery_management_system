from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import Party, Route, Stop, DeliveryVoucher, CompanyProfile


class AppUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text="Required for new users. Leave blank while editing to keep the current password.",
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_staff': 'Admin access',
            'is_active': 'Active',
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.instance.pk and not password:
            raise forms.ValidationError("Password is required for new users.")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['name', 'role', 'city', 'phone', 'address', 'gst_no', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'gst_no': forms.TextInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        qs = Party.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A party with the name '{name}' already exists.")
        return name

    def clean_gst_no(self):
        gst_no = self.cleaned_data.get('gst_no', '').strip()
        if gst_no:
            qs = Party.objects.filter(gst_no__iexact=gst_no)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"A party with GST number '{gst_no}' already exists.")
        return gst_no


class StopForm(forms.ModelForm):
    class Meta:
        model = Stop
        fields = ['name', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Stop name is required.")
        qs = Stop.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A stop with the name '{name}' already exists.")
        return name


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['name', 'from_stop', 'to_stop', 'stops', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'from_stop': forms.Select(attrs={'class': 'form-select'}),
            'to_stop': forms.Select(attrs={'class': 'form-select'}),
            'stops': forms.CheckboxSelectMultiple(),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Route name is required.")
        qs = Route.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A route with the name '{name}' already exists.")
        return name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        route_stop_ids = []
        if self.instance and self.instance.pk:
            route_stop_ids = list(self.instance.stops.values_list('pk', flat=True))
            route_stop_ids.extend([self.instance.from_stop_id, self.instance.to_stop_id])
        stops = Stop.objects.filter(Q(active=True) | Q(pk__in=route_stop_ids)).distinct()
        self.fields['from_stop'].queryset = stops
        self.fields['to_stop'].queryset = stops
        self.fields['stops'].queryset = stops
        self.fields['from_stop'].required = True
        self.fields['to_stop'].required = True
        self.fields['stops'].required = False
        self.fields['from_stop'].empty_label = "Select from location"
        self.fields['to_stop'].empty_label = "Select to location"
        self.fields['stops'].help_text = "Tick every stop covered by this route. From and To will be included automatically."

    def clean(self):
        cleaned_data = super().clean()
        from_stop = cleaned_data.get('from_stop')
        to_stop = cleaned_data.get('to_stop')
        if from_stop and to_stop and from_stop == to_stop:
            raise forms.ValidationError("From and To locations must be different stops.")
        selected_stops = list(cleaned_data.get('stops') or [])
        for stop in [from_stop, to_stop]:
            if stop and stop not in selected_stops:
                selected_stops.append(stop)
        cleaned_data['stops'] = selected_stops
        return cleaned_data


class DeliveryVoucherForm(forms.ModelForm):
    class Meta:
        model = DeliveryVoucher
        exclude = ['lr_no', 'booking_clerk', 'created_at', 'updated_at']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'consigner': forms.Select(attrs={'class': 'form-select'}),
            'consignee': forms.Select(attrs={'class': 'form-select'}),
            'from_stop': forms.Select(attrs={'class': 'form-select'}),
            'to_stop': forms.Select(attrs={'class': 'form-select'}),
            'route': forms.Select(attrs={'class': 'form-select'}),
            'invoice_no': forms.TextInput(attrs={'class': 'form-control'}),
            'no_of_boxes': forms.NumberInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'auto_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'extra_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bill_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_at': forms.TextInput(attrs={'class': 'form-control'}),
            'no_of_articles': forms.NumberInput(attrs={'class': 'form-control'}),
            'approx_weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'service_tax': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'to_pay': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'declared_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['consigner'].queryset = Party.objects.filter(active=True, role__in=[Party.CONSIGNER, Party.BOTH])
        self.fields['consignee'].queryset = Party.objects.filter(active=True, role__in=[Party.CONSIGNEE, Party.BOTH])
        self.fields['from_stop'].queryset = Stop.objects.filter(active=True)
        self.fields['to_stop'].queryset = Stop.objects.filter(active=True)
        self.fields['route'].queryset = Route.objects.filter(active=True)
        self.fields['from_stop'].required = False
        self.fields['to_stop'].required = False
        for f in ['delivery_at', 'no_of_articles', 'approx_weight_kg', 'service_tax', 'declared_value', 'remarks', 'bill_amount', 'auto_charge', 'extra_charge']:
            self.fields[f].required = False


class ReportFilterForm(forms.Form):
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
    ]
    month = forms.ChoiceField(choices=MONTH_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    year = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '2020', 'max': '2099'}))
    consigner = forms.ModelChoiceField(
        queryset=Party.objects.filter(active=True, role__in=[Party.CONSIGNER, Party.BOTH]),
        required=True,
        empty_label="Select Consigner",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class DashboardConsignerForm(forms.Form):
    consigner = forms.ModelChoiceField(
        queryset=Party.objects.filter(active=True, role__in=[Party.CONSIGNER, Party.BOTH]),
        required=False,
        empty_label="Select Consigner",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ['name', 'address_line_1', 'address_line_2', 'gst_no', 'mobile_1', 'mobile_2']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_no': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_1': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_2': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Company Name',
            'address_line_1': 'Address Line 1',
            'address_line_2': 'Address Line 2',
            'gst_no': 'GST Number',
            'mobile_1': 'Mobile Number 1',
            'mobile_2': 'Mobile Number 2',
        }
