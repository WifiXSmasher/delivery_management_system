from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Party(models.Model):
    CONSIGNER = 'consigner'
    CONSIGNEE = 'consignee'
    BOTH = 'both'
    ROLE_CHOICES = [
        (CONSIGNER, 'Consigner'),
        (CONSIGNEE, 'Consignee'),
        (BOTH, 'Consigner & Consignee'),
    ]

    name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=BOTH)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    #gst number has to be unique 
    gst_no = models.CharField(max_length=20, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Parties"
        ordering = ['name']

    def __str__(self):
        if self.city:
            return f"{self.name} - {self.city}"
        return self.name


class Stop(models.Model):
    name = models.CharField(max_length=200, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Route(models.Model):
    name = models.CharField(max_length=200)
    from_stop = models.ForeignKey(Stop, on_delete=models.PROTECT, related_name='routes_from', null=True, blank=True)
    to_stop = models.ForeignKey(Stop, on_delete=models.PROTECT, related_name='routes_to', null=True, blank=True)
    stops = models.ManyToManyField(Stop, related_name='routes', blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        if self.from_stop_id and self.to_stop_id:
            return f"{self.name} ({self.from_stop} to {self.to_stop})"
        return self.name

    @property
    def locations_display(self):
        stops = list(self.stops.all())
        if stops:
            return ", ".join(stop.name for stop in stops)
        endpoints = [stop.name for stop in [self.from_stop, self.to_stop] if stop]
        return ", ".join(endpoints)


class CompanyProfile(models.Model):
    name = models.CharField(max_length=200, default='TRANSPORTS COMPANY_name here')
    address_line_1 = models.CharField(max_length=200, default='Address_line1_here')
    address_line_2 = models.CharField(max_length=200, default='Address_line 2_here')
    gst_no = models.CharField(max_length=30, default='gst_number_here')
    mobile_1 = models.CharField(max_length=20, default='mobile_no_1 here')
    mobile_2 = models.CharField(max_length=20, blank=True, default='mobile_number_2 here')

    class Meta:
        verbose_name = 'Company Profile'
        verbose_name_plural = 'Company Profile'

    def __str__(self):
        return self.name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def mobiles_display(self):
        mobiles = [self.mobile_1, self.mobile_2]
        return ', '.join(mobile for mobile in mobiles if mobile)


class DeliveryVoucher(models.Model):
    lr_no = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField(default=timezone.now)
    booking_clerk = models.ForeignKey(User, on_delete=models.PROTECT, editable=False)

    consigner = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='consigner_vouchers')
    consignee = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='consignee_vouchers')

    from_stop = models.ForeignKey(Stop, on_delete=models.PROTECT, related_name='departures', null=True, blank=True)
    to_stop = models.ForeignKey(Stop, on_delete=models.PROTECT, related_name='arrivals', null=True, blank=True)

    route = models.ForeignKey(Route, on_delete=models.PROTECT)
    invoice_no = models.CharField(max_length=50)
    #add mess for this also
    no_of_boxes = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # add the message also for thiis 
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    delivery_at = models.CharField(max_length=200, blank=True)
    no_of_articles = models.PositiveIntegerField(null=True, blank=True)
    approx_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    service_tax = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    to_pay = models.BooleanField(default=True, help_text="True = To Pay, False = Paid")
    declared_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)
    signed_image = models.FileField(upload_to='signed_vouchers/', blank=True, null=True, help_text="Upload signed delivery voucher image or PDF")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"LR-{self.lr_no}"

    def save(self, *args, **kwargs):
        if not self.lr_no:
            from django.db.models import Max
            max_id = DeliveryVoucher.objects.aggregate(Max('id'))['id__max'] or 0
            self.lr_no = str(max_id + 1).zfill(4)
        super().save(*args, **kwargs)
