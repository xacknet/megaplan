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

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    Admins can see all users. Other authenticated users can only see their own details.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all().select_related('profile').order_by('id')
        return User.objects.filter(pk=self.request.user.pk).select_related('profile')

class FieldViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows fields to be viewed, created, edited or deleted.
    """
    serializer_class = FieldSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    # Example of how to use a BBox filter if you want to query fields by location later:
    # filter_backends = (InBBoxFilter,)
    # bbox_filter_field = 'geometry' # The geometry field to filter on
    # bbox_filter_include_overlapping = True # Optional

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or (hasattr(user, 'profile') and user.profile.role == 'administrator'):
            return Field.objects.all()
        return Field.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class CropViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows crops to be viewed.
    Managed by administrators.
    """
    queryset = Crop.objects.all().order_by('name')
    serializer_class = CropSerializer
    permission_classes = [permissions.IsAuthenticated] # Read-only for authenticated users

class OperationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows operation types to be viewed.
    Managed by administrators.
    """
    queryset = OperationType.objects.all().order_by('name')
    serializer_class = OperationTypeSerializer
    permission_classes = [permissions.IsAuthenticated] # Read-only for authenticated users

class AgroOperationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing agrotechnical operations.
    """
    serializer_class = AgroOperationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin] # Custom permission checks object-level field ownership

    def get_queryset(self):
        user = self.request.user
        # Allow query parameter filtering, e.g., /api/v1/operations/?field_id=X
        field_id = self.request.query_params.get('field_id', None)

        if user.is_staff or (hasattr(user, 'profile') and user.profile.role == 'administrator'):
            queryset = AgroOperation.objects.all()
        else:
            # Users can only see operations for fields they own or operations they created
            queryset = AgroOperation.objects.filter(
                Q(field__owner=user) | Q(user=user)
            ).distinct() # Use Q objects for OR conditions
        
        if field_id is not None:
            queryset = queryset.filter(field_id=field_id)
            
        return queryset.select_related('field', 'crop', 'operation_type', 'user').order_by('-operation_date')

    def perform_create(self, serializer):
        # serializer.save(user=self.request.user) is handled by CurrentUserDefault in serializer
        # and field validation is also in serializer.
        serializer.save() # user will be set by CurrentUserDefault
        
    def get_serializer_context(self):
        """
        Extra context provided to the serializer.
        """
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

# Need to import Q for AgroOperationViewSet queryset
from django.db.models import Q

# GEE NDVI Data Endpoint
class FieldNDVIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, field_id, format=None):
        try:
            field = Field.objects.get(pk=field_id)
        except Field.DoesNotExist:
            return Response({"error": "Field not found."}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Ensure the user owns the field or is an admin
        if not (field.owner == request.user or request.user.is_staff):
            return Response({"error": "You do not have permission to view NDVI for this field."}, status=status.HTTP_403_FORBIDDEN)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response({"error": "Please provide 'start_date' and 'end_date' query parameters in YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not field.geometry:
             return Response({"error": "Field does not have geometry data."}, status=status.HTTP_400_BAD_REQUEST)

        field_geojson = field.geometry.geojson # Get GeoJSON string

        # Initialize GEE (ensure your key file is correctly configured in settings.py)
        if not gee_utils.initialize_gee():
            return Response({"error": "Failed to initialize Google Earth Engine. Check server logs and GEE configuration."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        ndvi_data = gee_utils.get_ndvi_for_field(field_geojson, start_date_str, end_date_str)

        if ndvi_data and 'error' in ndvi_data:
            return Response(ndvi_data, status=status.HTTP_400_BAD_REQUEST) # GEE specific errors
        elif ndvi_data:
            return Response(ndvi_data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to retrieve NDVI data. Unknown error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
