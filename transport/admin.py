from django.contrib import admin
from .models import Party, Route, Stop, CompanyProfile, DeliveryVoucher


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'city', 'phone', 'active']
    list_filter = ['role', 'active']
    search_fields = ['name', 'city']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'from_stop', 'to_stop', 'locations_display', 'active']
    list_filter = ['active', 'from_stop', 'to_stop']
    filter_horizontal = ['stops']


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ['name', 'active']
    list_filter = ['active']
    search_fields = ['name']


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'gst_no', 'mobile_1', 'mobile_2']

    def has_add_permission(self, request):
        return not CompanyProfile.objects.exists()


@admin.register(DeliveryVoucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ['lr_no', 'date', 'consigner', 'consignee', 'invoice_no', 'no_of_boxes', 'amount']
    list_filter = ['date', 'route', 'consigner']
    search_fields = ['lr_no', 'invoice_no']
    readonly_fields = ['lr_no', 'booking_clerk']
