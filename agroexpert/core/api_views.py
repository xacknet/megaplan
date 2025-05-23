from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile, Field, Crop, OperationType, AgroOperation
from .serializers import (
    UserSerializer, FieldSerializer, CropSerializer, 
    OperationTypeSerializer, AgroOperationSerializer
)
from rest_framework_gis.filters import InBBoxFilter # For bounding box queries if needed later

from .permissions import IsOwnerOrAdmin, IsAdminOrReadOnly
from . import gee_utils
from django.db.models import Q


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    Admins can see all users. Other authenticated users can only see their own details.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'administrator': # Check using role
            return User.objects.all().select_related('profile').order_by('id')
        return User.objects.filter(pk=self.request.user.pk).select_related('profile')

class FieldViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows fields to be viewed, created, edited or deleted.
    """
    serializer_class = FieldSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    # filter_backends = (InBBoxFilter,) # Uncomment if BBox filter is needed
    # bbox_filter_field = 'geometry'
    # bbox_filter_include_overlapping = True 

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'administrator':
            return Field.objects.all()
        return Field.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class CropViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows crops to be viewed.
    """
    queryset = Crop.objects.all().order_by('name')
    serializer_class = CropSerializer
    permission_classes = [permissions.IsAuthenticated] 

class OperationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows operation types to be viewed.
    """
    queryset = OperationType.objects.all().order_by('name')
    serializer_class = OperationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgroOperationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing agrotechnical operations.
    """
    serializer_class = AgroOperationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin] 

    def get_queryset(self):
        user = self.request.user
        field_id = self.request.query_params.get('field_id', None)
        
        base_queryset = AgroOperation.objects.all().select_related('field', 'crop', 'operation_type', 'user')

        if hasattr(user, 'profile') and user.profile.role == 'administrator':
            queryset = base_queryset
        else:
            queryset = base_queryset.filter(
                Q(field__owner=user) | Q(user=user)
            ).distinct()
        
        if field_id is not None:
            queryset = queryset.filter(field_id=field_id)
            
        return queryset.order_by('-operation_date')

    def perform_create(self, serializer):
        # User is set via CurrentUserDefault in the serializer
        # Field ownership for creation is validated in the serializer's validate_field method
        serializer.save() 
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class FieldNDVIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, field_id, format=None):
        try:
            field = Field.objects.get(pk=field_id)
        except Field.DoesNotExist:
            return Response({"error": "Field not found."}, status=status.HTTP_404_NOT_FOUND)

        if not (field.owner == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')):
            return Response({"error": "You do not have permission to view NDVI for this field."}, status=status.HTTP_403_FORBIDDEN)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response({"error": "Please provide 'start_date' and 'end_date' query parameters in YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not field.geometry:
             return Response({"error": "Field does not have geometry data."}, status=status.HTTP_400_BAD_REQUEST)

        field_geojson = field.geometry.geojson

        if not gee_utils.initialize_gee(): # GEE_SERVICE_ACCOUNT_KEY_FILE needs to be valid
            return Response({"error": "Failed to initialize Google Earth Engine. Check server configuration."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        ndvi_data = gee_utils.get_ndvi_for_field(field_geojson, start_date_str, end_date_str)

        if ndvi_data and 'error' in ndvi_data:
            return Response(ndvi_data, status=status.HTTP_400_BAD_REQUEST)
        elif ndvi_data:
            return Response(ndvi_data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to retrieve NDVI data. Unknown error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FieldNDVIZonesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, field_id, format=None):
        try:
            field = Field.objects.get(pk=field_id)
        except Field.DoesNotExist:
            return Response({"error": "Field not found."}, status=status.HTTP_404_NOT_FOUND)

        if not (field.owner == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')):
            return Response({"error": "You do not have permission to generate NDVI zones for this field."}, status=status.HTTP_403_FORBIDDEN)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        try:
            num_zones = int(request.query_params.get('num_zones', 5)) # Default to 5 zones
            if not (1 < num_zones <= 10): # Basic validation for num_zones
                 raise ValueError("Number of zones must be between 2 and 10.")
        except ValueError as e:
            return Response({"error": f"Invalid number of zones: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


        if not start_date_str or not end_date_str:
            return Response({"error": "Please provide 'start_date' and 'end_date' query parameters in YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not field.geometry:
             return Response({"error": "Field does not have geometry data."}, status=status.HTTP_400_BAD_REQUEST)

        field_geojson = field.geometry.geojson

        # GEE Initialization is already called within get_ndvi_zones
        # if not gee_utils.initialize_gee():
        #     return Response({"error": "Failed to initialize Google Earth Engine. Check server configuration."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        zones_data = gee_utils.get_ndvi_zones(field_geojson, start_date_str, end_date_str, num_zones=num_zones)

        if zones_data and 'error' in zones_data:
            # More specific error for GEE processing issues
            return Response(zones_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR if "GEE initialization failed" not in zones_data['error'] else status.HTTP_400_BAD_REQUEST)
        elif zones_data:
            return Response(zones_data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to retrieve NDVI zones. Unknown error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
