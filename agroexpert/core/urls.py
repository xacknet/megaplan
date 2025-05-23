from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin_only/', views.admin_only_view, name='admin_only'),
    path('', views.home_view, name='home'), 

    # Field URLs
    path('fields/', views.field_list_view, name='field_list'),
    path('fields/create/', views.field_create_view, name='field_create'),
    path('fields/<int:pk>/', views.field_detail_view, name='field_detail'),

    # AgroOperation URLs
    path('field/<int:field_pk>/operation/new/', views.agrooperation_create_view, name='agrooperation_create'),
    path('operation/<int:pk>/edit/', views.agrooperation_update_view, name='agrooperation_update'),
    path('operation/<int:pk>/delete/', views.agrooperation_delete_view, name='agrooperation_delete'),

    # Reporting URLs
    path('reports/', views.report_dashboard_view, name='report_dashboard'),
    path('reports/field/<int:field_id>/excel/', views.download_field_operations_report_excel, name='download_field_operations_excel'),
    path('reports/field/<int:field_id>/pdf/', views.download_field_operations_report_pdf, name='download_field_operations_pdf'),
]
