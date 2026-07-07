import csv
import datetime
import json
import shutil
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.conf import settings
from .models import Party, Route, Stop, CompanyProfile, DeliveryVoucher
from .forms import AppUserForm, PartyForm, RouteForm, StopForm, DeliveryVoucherForm, ReportFilterForm, DashboardConsignerForm, CompanyProfileForm


def is_app_admin(user):
    return user.is_authenticated and user.is_staff


admin_required = user_passes_test(is_app_admin, login_url='dashboard')


# ── Auth ──────────────────────────────────────────────────────────────────────
from .models import CompanyProfile

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None

    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )

        if user:
            login(request, user)
            return redirect('dashboard')

        error = "Invalid username or password."

    current_hour = timezone.localtime().hour


    if current_hour >= 17 or current_hour < 6:
        login_bg = 'login_bg_night.jpg'
        login_theme = 'night'
    else:
        login_bg = 'login_bg.jpg'
        login_theme = 'day'

    return render(
        request,
        'transport/login.html',
        {
            'error': error,
            'login_bg': login_bg,
            'login_theme': login_theme,
            'company': CompanyProfile.load(),
        }
    )

def logout_view(request):
    logout(request)
    return redirect('login')


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = timezone.now().date()
    consigner_form = DashboardConsignerForm(request.GET or None)
    selected_consigner = None
    consigner_voucher_count = 0
    consigner_revenue = 0

    if consigner_form.is_valid():
        selected_consigner = consigner_form.cleaned_data.get('consigner')
        if selected_consigner:
            qs = DeliveryVoucher.objects.filter(consigner=selected_consigner)
            consigner_voucher_count = qs.count()
            consigner_revenue = qs.aggregate(
                total=Sum(
                    F('amount') + Coalesce(F('auto_charge'), Value(0)) + Coalesce(F('extra_charge'), Value(0)),
                    output_field=DecimalField()
                )
            )['total'] or 0

    top_consigners = list(
        DeliveryVoucher.objects.values('consigner__name')
        .annotate(total_revenue=Sum(
            F('amount') + Coalesce(F('auto_charge'), Value(0)) + Coalesce(F('extra_charge'), Value(0)),
            output_field=DecimalField()
        ))
        .order_by('-total_revenue')[:5]
    )

    # ── Daily sales (last 7 days) ───────────────────────────────────────────
    daily_labels = []
    daily_values = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        total = DeliveryVoucher.objects.filter(
            date=day
        ).aggregate(t=Sum(
            F('amount') + Coalesce(F('auto_charge'), Value(0)) + Coalesce(F('extra_charge'), Value(0)),
            output_field=DecimalField()
        ))['t'] or 0
        daily_labels.append(day.strftime('%a %d/%m'))
        daily_values.append(float(total))

    # ── Monthly sales (last 12 months) ────────────────────────────────────
    monthly_labels = []
    monthly_values = []
    for i in range(11, -1, -1):
        m_year = today.year
        m_month = today.month - i
        while m_month <= 0:
            m_month += 12
            m_year -= 1
        total = DeliveryVoucher.objects.filter(
            date__year=m_year, date__month=m_month
        ).aggregate(t=Sum(
            F('amount') + Coalesce(F('auto_charge'), Value(0)) + Coalesce(F('extra_charge'), Value(0)),
            output_field=DecimalField()
        ))['t'] or 0
        monthly_labels.append(datetime.date(m_year, m_month, 1).strftime('%b %Y'))
        monthly_values.append(float(total))

    ctx = {
        'total_vouchers': DeliveryVoucher.objects.count(),
        'this_month': DeliveryVoucher.objects.filter(date__year=today.year, date__month=today.month).count(),
        'total_consigners': Party.objects.filter(active=True, role__in=[Party.CONSIGNER, Party.BOTH]).count(),
        'total_consignees': Party.objects.filter(active=True, role__in=[Party.CONSIGNEE, Party.BOTH]).count(),
        'total_routes': Route.objects.filter(active=True).count(),
        'recent': DeliveryVoucher.objects.select_related('consigner', 'consignee', 'route', 'from_stop', 'to_stop')[:8],
        'consigner_form': consigner_form,
        'selected_consigner': selected_consigner,
        'consigner_voucher_count': consigner_voucher_count,
        'consigner_revenue': consigner_revenue,
        'top_consigner_labels': json.dumps([item['consigner__name'] or 'Unknown' for item in top_consigners]),
        'top_consigner_values': json.dumps([float(item['total_revenue'] or 0) for item in top_consigners]),
        'daily_labels': json.dumps(daily_labels),
        'daily_values': json.dumps(daily_values),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_values': json.dumps(monthly_values),
        'company': CompanyProfile.load(),
    }
    return render(request, 'transport/dashboard.html', ctx)


# ── Users ─────────────────────────────────────────────────────────────────────

@login_required
@admin_required
def user_list(request):
    users_all = User.objects.order_by('username')
    paginator = Paginator(users_all, 10)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    return render(request, 'transport/user_list.html', {
        'users': users,
        'company': CompanyProfile.load(),
    })


@login_required
@admin_required
def user_add(request):
    form = AppUserForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        messages.success(request, f"User {user.username} added successfully.")
        return redirect('user_list')
    return render(request, 'transport/user_form.html', {
        'form': form,
        'title': 'Add User',
        'company': CompanyProfile.load(),
    })


@login_required
@admin_required
def user_edit(request, pk):
    app_user = get_object_or_404(User, pk=pk)
    form = AppUserForm(request.POST or None, instance=app_user)
    if form.is_valid():
        will_be_staff = form.cleaned_data.get('is_staff')
        will_be_active = form.cleaned_data.get('is_active')
        if app_user == request.user and not will_be_staff:
            form.add_error('is_staff', "You cannot remove your own admin access.")
        elif app_user.is_staff and not will_be_staff and User.objects.filter(is_staff=True, is_active=True).exclude(pk=app_user.pk).count() == 0:
            form.add_error('is_staff', "At least one active admin user is required.")
        elif app_user.is_staff and not will_be_active and User.objects.filter(is_staff=True, is_active=True).exclude(pk=app_user.pk).count() == 0:
            form.add_error('is_active', "At least one active admin user is required.")
        else:
            saved_user = form.save()
            messages.success(request, f"User {saved_user.username} updated.")
            return redirect('user_list')
    return render(request, 'transport/user_form.html', {
        'form': form,
        'title': f'Edit User: {app_user.username}',
        'obj': app_user,
        'company': CompanyProfile.load(),
    })


@login_required
@admin_required
def user_delete(request, pk):
    app_user = get_object_or_404(User, pk=pk)
    if request.method != 'POST':
        return redirect('user_list')
    if app_user == request.user:
        messages.error(request, "You cannot delete your own user account.")
        return redirect('user_list')
    if app_user.is_staff and User.objects.filter(is_staff=True, is_active=True).exclude(pk=app_user.pk).count() == 0:
        messages.error(request, "At least one active admin user is required.")
        return redirect('user_list')
    username = app_user.username
    app_user.delete()
    messages.success(request, f"User {username} deleted.")
    return redirect('user_list')


# ── Parties ───────────────────────────────────────────────────────────────────

def party_queryset_for_role(role):
    if role == Party.CONSIGNER:
        return Party.objects.filter(role__in=[Party.CONSIGNER, Party.BOTH])
    return Party.objects.filter(role__in=[Party.CONSIGNEE, Party.BOTH])


def party_role_label(role):
    return 'Consigner' if role == Party.CONSIGNER else 'Consignee'


@login_required
def party_list(request):
    return redirect('consigner_list')


@login_required
def role_party_list(request, role):
    parties_all = party_queryset_for_role(role)
    paginator = Paginator(parties_all, 10)
    page_number = request.GET.get('page')
    parties = paginator.get_page(page_number)
    return render(request, 'transport/party_list.html', {
        'parties': parties,
        'role': role,
        'role_label': party_role_label(role),
        'company': CompanyProfile.load(),
    })


@login_required
def role_party_add(request, role):
    initial_role = role if role in [Party.CONSIGNER, Party.CONSIGNEE] else Party.BOTH
    form = PartyForm(request.POST or None, initial={'role': initial_role})
    if form.is_valid():
        form.save()
        messages.success(request, f"{party_role_label(role)} added successfully.")
        return redirect(f'{role}_list')
    return render(request, 'transport/party_form.html', {
        'form': form,
        'title': f'Add {party_role_label(role)}',
        'role': role,
        'role_label': party_role_label(role),
        'company': CompanyProfile.load(),
    })


@login_required
def role_party_edit(request, role, pk):
    party = get_object_or_404(Party, pk=pk)
    form = PartyForm(request.POST or None, instance=party)
    if form.is_valid():
        form.save()
        messages.success(request, f"{party_role_label(role)} updated.")
        return redirect(f'{role}_list')
    return render(request, 'transport/party_form.html', {
        'form': form,
        'title': f'Edit {party_role_label(role)}',
        'obj': party,
        'role': role,
        'role_label': party_role_label(role),
        'company': CompanyProfile.load(),
    })


@login_required
@admin_required
def role_party_delete(request, role, pk):
    party = get_object_or_404(Party, pk=pk)
    if request.method != 'POST':
        return redirect(f'{role}_list')
    try:
        name = party.name
        party.delete()
        messages.success(request, f"{party_role_label(role)} '{name}' deleted successfully.")
    except Exception:
        messages.error(request, f"Cannot delete '{party.name}' because it is used by vouchers.")
    return redirect(f'{role}_list')


@login_required
def party_add(request):
    return redirect('consigner_add')


@login_required
def party_edit(request, pk):
    party = get_object_or_404(Party, pk=pk)
    role = Party.CONSIGNEE if party.role == Party.CONSIGNEE else Party.CONSIGNER
    return redirect(f'{role}_edit', pk=pk)


# ── Stops ─────────────────────────────────────────────────────────────────────

@login_required
def stop_list(request):
    stops_all = Stop.objects.all()
    paginator = Paginator(stops_all, 10)
    page_number = request.GET.get('page')
    stops = paginator.get_page(page_number)
    return render(request, 'transport/stop_list.html', {'stops': stops, 'company': CompanyProfile.load()})

@login_required
def stop_add(request):
    form = StopForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Stop added successfully.")
        return redirect('stop_list')
    return render(request, 'transport/stop_form.html', {'form': form, 'title': 'Add Stop', 'company': CompanyProfile.load()})

@login_required
def stop_edit(request, pk):
    stop = get_object_or_404(Stop, pk=pk)
    form = StopForm(request.POST or None, instance=stop)
    if form.is_valid():
        form.save()
        messages.success(request, "Stop updated.")
        return redirect('stop_list')
    return render(request, 'transport/stop_form.html', {'form': form, 'title': 'Edit Stop', 'obj': stop, 'company': CompanyProfile.load()})


@login_required
@admin_required
def stop_delete(request, pk):
    stop = get_object_or_404(Stop, pk=pk)
    if request.method != 'POST':
        return redirect('stop_list')
    try:
        name = stop.name
        stop.delete()
        messages.success(request, f"Stop '{name}' deleted successfully.")
    except Exception:
        messages.error(request, f"Cannot delete stop '{stop.name}' because it is used by routes or vouchers.")
    return redirect('stop_list')


# ── Routes ────────────────────────────────────────────────────────────────────

@login_required
def route_list(request):
    routes_all = Route.objects.select_related('from_stop', 'to_stop').prefetch_related('stops')
    paginator = Paginator(routes_all, 10)
    page_number = request.GET.get('page')
    routes = paginator.get_page(page_number)
    return render(request, 'transport/route_list.html', {'routes': routes, 'company': CompanyProfile.load()})

@login_required
def route_add(request):
    form = RouteForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Route added successfully.")
        return redirect('route_list')
    return render(request, 'transport/route_form.html', {'form': form, 'title': 'Add Route', 'company': CompanyProfile.load()})

@login_required
def route_edit(request, pk):
    route = get_object_or_404(Route, pk=pk)
    form = RouteForm(request.POST or None, instance=route)
    if form.is_valid():
        form.save()
        messages.success(request, "Route updated.")
        return redirect('route_list')
    return render(request, 'transport/route_form.html', {'form': form, 'title': 'Edit Route', 'obj': route, 'company': CompanyProfile.load()})


@login_required
@admin_required
def route_delete(request, pk):
    route = get_object_or_404(Route, pk=pk)
    if request.method != 'POST':
        return redirect('route_list')
    try:
        name = route.name
        route.delete()
        messages.success(request, f"Route '{name}' deleted successfully.")
    except Exception:
        messages.error(request, f"Cannot delete route '{route.name}' because it is used by vouchers.")
    return redirect('route_list')


# ── Vouchers ──────────────────────────────────────────────────────────────────

def filtered_vouchers(params):
    vouchers = DeliveryVoucher.objects.select_related(
        'consigner', 'consignee', 'route', 'from_stop', 'to_stop', 'booking_clerk'
    )
    q_consigner = params.get('consigner', '')
    q_consignee = params.get('consignee', '')
    q_booking_clerk = params.get('booking_clerk', '')
    q_from_date = params.get('from_date', '')
    q_to_date = params.get('to_date', '')
    q_lr = params.get('lr', '')
    q_invoice_no = params.get('invoice_no', '')
    q_payment_status = params.get('payment_status', '')
    q_has_auto = params.get('has_auto', '')
    q_has_extra = params.get('has_extra', '')
    q_has_bill = params.get('has_bill', '')
    if q_consigner:
        try:
            vouchers = vouchers.filter(consigner_id=int(q_consigner))
        except (ValueError, TypeError):
            pass
    if q_consignee:
        try:
            vouchers = vouchers.filter(consignee_id=int(q_consignee))
        except (ValueError, TypeError):
            pass
    if q_booking_clerk:
        try:
            vouchers = vouchers.filter(booking_clerk_id=int(q_booking_clerk))
        except (ValueError, TypeError):
            pass
    if q_from_date:
        vouchers = vouchers.filter(date__gte=q_from_date)
    if q_to_date:
        vouchers = vouchers.filter(date__lte=q_to_date)
    if q_lr:
        vouchers = vouchers.filter(lr_no__icontains=q_lr)
    if q_invoice_no:
        vouchers = vouchers.filter(invoice_no__icontains=q_invoice_no)
    if q_payment_status == 'paid':
        vouchers = vouchers.filter(to_pay=False)
    elif q_payment_status == 'to_pay':
        vouchers = vouchers.filter(to_pay=True)
    if q_has_auto:
        vouchers = vouchers.filter(auto_charge__gt=0)
    if q_has_extra:
        vouchers = vouchers.filter(extra_charge__gt=0)
    if q_has_bill:
        vouchers = vouchers.filter(bill_amount__gt=0)
    return vouchers, {
        'q_consigner': q_consigner,
        'q_consignee': q_consignee,
        'q_booking_clerk': q_booking_clerk,
        'q_from_date': q_from_date,
        'q_to_date': q_to_date,
        'q_lr': q_lr,
        'q_invoice_no': q_invoice_no,
        'q_payment_status': q_payment_status,
        'q_has_auto': q_has_auto,
        'q_has_extra': q_has_extra,
        'q_has_bill': q_has_bill,
    }

@login_required
def voucher_list(request):
    vouchers_qs, filters = filtered_vouchers(request.GET)
    paginator = Paginator(vouchers_qs, 10)
    page_number = request.GET.get('page')
    vouchers = paginator.get_page(page_number)
    consigner_parties = Party.objects.filter(active=True, role__in=[Party.CONSIGNER, Party.BOTH])
    consignee_parties = Party.objects.filter(active=True, role__in=[Party.CONSIGNEE, Party.BOTH])
    booking_clerks = User.objects.filter(is_active=True).order_by('username')
    return render(request, 'transport/voucher_list.html', {
        'vouchers': vouchers,
        'consigner_parties': consigner_parties,
        'consignee_parties': consignee_parties,
        'booking_clerks': booking_clerks,
        **filters,
        'company': CompanyProfile.load(),
    })

@login_required
def voucher_download(request):
    vouchers, _ = filtered_vouchers(request.GET)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vouchers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'LR No', 'Consigner', 'Consignee', 'From', 'To', 'Route', 'Invoice No', 'Boxes', 'Articles', 'Approx Weight Kg', 'Amount', 'Auto Charge', 'Extra Charge', 'Total Amount', 'Bill Amount', 'Delivery At', 'Payment Status', 'Declared Value', 'Remarks'])
    for voucher in vouchers:
        writer.writerow([voucher.date.strftime('%d-%m-%Y'), voucher.lr_no, voucher.consigner, voucher.consignee, voucher.from_stop or '', voucher.to_stop or '', voucher.route, voucher.invoice_no, voucher.no_of_boxes, voucher.no_of_articles or '', voucher.approx_weight_kg or '', voucher.amount, voucher.auto_charge or 0, voucher.extra_charge or 0, voucher.total_amount, voucher.bill_amount or '', voucher.delivery_at, 'To Pay' if voucher.to_pay else 'Paid', voucher.declared_value or '', voucher.remarks])
    return response

@login_required
def voucher_add(request):
    form = DeliveryVoucherForm(request.POST or None)
    if form.is_valid():
        v = form.save(commit=False)
        v.booking_clerk = request.user
        v.save()
        messages.success(request, f"Voucher LR-{v.lr_no} created successfully.")
        return redirect('voucher_list')
    return render(request, 'transport/voucher_form.html', {'form': form, 'title': 'New Delivery Voucher', 'company': CompanyProfile.load()})

@login_required
def voucher_edit(request, pk):
    voucher = get_object_or_404(DeliveryVoucher, pk=pk)
    form = DeliveryVoucherForm(request.POST or None, instance=voucher)
    if form.is_valid():
        form.save()
        messages.success(request, "Voucher updated.")
        return redirect('voucher_list')
    return render(request, 'transport/voucher_form.html', {'form': form, 'title': f'Edit Voucher LR-{voucher.lr_no}', 'obj': voucher, 'company': CompanyProfile.load()})

@login_required
def voucher_detail(request, pk):
    voucher = get_object_or_404(DeliveryVoucher, pk=pk)
    return render(request, 'transport/voucher_detail.html', {'voucher': voucher, 'company': CompanyProfile.load()})

@login_required
def voucher_bill_download(request, pk):
    voucher = get_object_or_404(DeliveryVoucher.objects.select_related('consigner', 'consignee', 'route', 'from_stop', 'to_stop', 'booking_clerk'), pk=pk)
    return render(request, 'transport/voucher_bill.html', {'voucher': voucher, 'company': CompanyProfile.load()})


@login_required
@admin_required
def voucher_delete(request, pk):
    voucher = get_object_or_404(DeliveryVoucher, pk=pk)
    if request.method != 'POST':
        return redirect('voucher_list')
    lr_no = voucher.lr_no
    voucher.delete()
    messages.success(request, f"Voucher LR-{lr_no} deleted successfully.")
    return redirect('voucher_list')


@login_required
def voucher_upload_image(request, pk):
    voucher = get_object_or_404(DeliveryVoucher, pk=pk)
    if request.method == 'POST' and request.FILES.get('signed_image'):
        uploaded_file = request.FILES['signed_image']
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'application/pdf']
        if uploaded_file.content_type not in allowed_types:
            messages.error(request, "Invalid file type. Please upload a JPEG, PNG, WebP, GIF, or PDF file.")
            return redirect('voucher_detail', pk=pk)
        # Delete old image if replacing
        if voucher.signed_image:
            voucher.signed_image.delete(save=False)
        # Rename file to LRNO_CONSIGNER_CONSIGNEE.ext
        import os, re
        ext = os.path.splitext(uploaded_file.name)[1]  # e.g. .jpg, .pdf
        safe_consigner = re.sub(r'[^\w]+', '-', str(voucher.consigner)).strip('-')
        safe_consignee = re.sub(r'[^\w]+', '-', str(voucher.consignee)).strip('-')
        uploaded_file.name = f"{voucher.lr_no}_{safe_consigner}_{safe_consignee}{ext}"
        voucher.signed_image = uploaded_file
        voucher.save()
        messages.success(request, f"Signed delivery image uploaded for LR-{voucher.lr_no}.")
    else:
        messages.error(request, "No image file was provided.")
    return redirect('voucher_detail', pk=pk)


# ── Monthly Report ────────────────────────────────────────────────────────────

@login_required
def monthly_report(request):
    today = timezone.now().date()
    form = ReportFilterForm(request.GET or None, initial={'month': today.month, 'year': today.year})
    vouchers, total_amount, total_boxes, total_bill_amount, total_auto_charge, total_extra_charge, month_label, selected_consigner = [], 0, 0, 0, 0, 0, '', None
    report_requested = False
    if request.GET and form.is_valid():
        report_requested = True
        month = int(form.cleaned_data['month'])
        year = int(form.cleaned_data['year'])
        selected_consigner = form.cleaned_data['consigner']
        qs = DeliveryVoucher.objects.filter(date__year=year, date__month=month, consigner=selected_consigner).select_related('consigner', 'consignee', 'route', 'from_stop', 'to_stop', 'booking_clerk').order_by('date', 'lr_no')
        vouchers = qs
        agg = qs.aggregate(
            ta=Sum(
                F('amount') + Coalesce(F('auto_charge'), Value(0)) + Coalesce(F('extra_charge'), Value(0)),
                output_field=DecimalField()
            ),
            tb=Sum('no_of_boxes'),
            tba=Sum('bill_amount'),
            t_auto=Sum('auto_charge'),
            t_extra=Sum('extra_charge'),
        )
        total_amount = agg['ta'] or 0
        total_boxes = agg['tb'] or 0
        total_bill_amount = agg['tba'] or 0
        total_auto_charge = agg['t_auto'] or 0
        total_extra_charge = agg['t_extra'] or 0
        month_label = datetime.date(year, month, 1).strftime('%B %Y')
    return render(request, 'transport/report.html', {'form': form, 'vouchers': vouchers, 'total_amount': total_amount, 'total_boxes': total_boxes, 'total_bill_amount': total_bill_amount, 'total_auto_charge': total_auto_charge, 'total_extra_charge': total_extra_charge, 'month_label': month_label, 'selected_consigner': selected_consigner, 'report_requested': report_requested, 'company': CompanyProfile.load()})

# ── Annual Report ─────────────────────────────────────────────────────────────

@login_required
def annual_report(request):
    today = timezone.now().date()
    selected_year = request.GET.get('year', '')
    try:
        selected_year = int(selected_year)
    except (ValueError, TypeError):
        selected_year = today.year

    # Build list of available years from voucher data
    years_qs = DeliveryVoucher.objects.dates('date', 'year')
    available_years = sorted(set([d.year for d in years_qs] + [today.year]), reverse=True)

    # Monthly breakdown for the selected year
    annual_labels = []
    annual_values = []
    annual_total = 0
    for m in range(1, 13):
        total = DeliveryVoucher.objects.filter(
            date__year=selected_year, date__month=m
        ).aggregate(t=Sum(
            F('amount') + Coalesce(F('auto_charge'), Value(0)) + Coalesce(F('extra_charge'), Value(0)),
            output_field=DecimalField()
        ))['t'] or 0
        annual_labels.append(datetime.date(selected_year, m, 1).strftime('%b'))
        annual_values.append(float(total))
        annual_total += float(total)

    ctx = {
        'selected_year': selected_year,
        'available_years': available_years,
        'annual_labels': json.dumps(annual_labels),
        'annual_values': json.dumps(annual_values),
        'annual_total': annual_total,
        'company': CompanyProfile.load(),
    }
    return render(request, 'transport/annual_report.html', ctx)


# ── Backup ────────────────────────────────────────────────────────────────────

@login_required
def backup_db(request):
    db_path = settings.DATABASES['default']['NAME']
    backup_dir = settings.BASE_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = backup_dir / f'kap_transport_{ts}.db'
    shutil.copy2(db_path, dest)
    messages.success(request, f"Backup saved: backups/kap_transport_{ts}.db")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# ── Company About ─────────────────────────────────────────────────────────────

@login_required
@admin_required
def company_about(request):
    company = CompanyProfile.load()
    form = CompanyProfileForm(request.POST or None, instance=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Company details updated successfully.")
        return redirect('company_about')
    return render(request, 'transport/company_about.html', {
        'form': form,
        'company': company,
    })
