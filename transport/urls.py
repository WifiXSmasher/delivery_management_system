from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
   
    path('consigners/', views.role_party_list, {'role': 'consigner'}, name='consigner_list'),
    path('consigners/add/', views.role_party_add, {'role': 'consigner'}, name='consigner_add'),
    path('consigners/<int:pk>/edit/', views.role_party_edit, {'role': 'consigner'}, name='consigner_edit'),
    path('consigners/<int:pk>/delete/', views.role_party_delete, {'role': 'consigner'}, name='consigner_delete'),
    path('consignees/', views.role_party_list, {'role': 'consignee'}, name='consignee_list'),
    path('consignees/add/', views.role_party_add, {'role': 'consignee'}, name='consignee_add'),
    path('consignees/<int:pk>/edit/', views.role_party_edit, {'role': 'consignee'}, name='consignee_edit'),
    path('consignees/<int:pk>/delete/', views.role_party_delete, {'role': 'consignee'}, name='consignee_delete'),
    
    path('stops/', views.stop_list, name='stop_list'),
    path('stops/add/', views.stop_add, name='stop_add'),
    path('stops/<int:pk>/edit/', views.stop_edit, name='stop_edit'),
    path('stops/<int:pk>/delete/', views.stop_delete, name='stop_delete'),
    
    path('routes/', views.route_list, name='route_list'),
    path('routes/add/', views.route_add, name='route_add'),
    path('routes/<int:pk>/edit/', views.route_edit, name='route_edit'),
    path('routes/<int:pk>/delete/', views.route_delete, name='route_delete'),
    
    path('vouchers/', views.voucher_list, name='voucher_list'),
    path('vouchers/download/', views.voucher_download, name='voucher_download'),
    path('vouchers/add/', views.voucher_add, name='voucher_add'),
    path('vouchers/<int:pk>/download/', views.voucher_bill_download, name='voucher_bill_download'),
    path('vouchers/<int:pk>/', views.voucher_detail, name='voucher_detail'),
    path('vouchers/<int:pk>/edit/', views.voucher_edit, name='voucher_edit'),
    path('vouchers/<int:pk>/upload-image/', views.voucher_upload_image, name='voucher_upload_image'),
    path('vouchers/<int:pk>/delete/', views.voucher_delete, name='voucher_delete'),

    path('report/', views.monthly_report, name='monthly_report'),
    path('annual-report/', views.annual_report, name='annual_report'),
    path('backup/', views.backup_db, name='backup_db'),
    path('about/', views.company_about, name='company_about'),
]
