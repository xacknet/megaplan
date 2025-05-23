from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as authtoken_views
from . import api_views

router = DefaultRouter()
router.register(r'users', api_views.UserViewSet, basename='user')
router.register(r'fields', api_views.FieldViewSet, basename='field')
router.register(r'crops', api_views.CropViewSet, basename='crop')
router.register(r'operation-types', api_views.OperationTypeViewSet, basename='operationtype')
router.register(r'operations', api_views.AgroOperationViewSet, basename='agrooperation')

urlpatterns = [
    path('', include(router.urls)),
    path('fields/<int:field_id>/ndvi/', api_views.FieldNDVIView.as_view(), name='field-ndvi'),
    path('api-token-auth/', authtoken_views.obtain_auth_token, name='api_token_auth'), # For obtaining a token
]
