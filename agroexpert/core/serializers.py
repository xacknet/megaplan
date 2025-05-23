from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.auth.models import User
from .models import UserProfile, Field, Crop, OperationType, AgroOperation

class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='get_role_display') # Or just 'role' if you want the internal value
    class Meta:
        model = UserProfile
        fields = ['role']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']
        # Add 'is_staff' or 'is_superuser' if needed for client-side role checks by admin


class FieldSerializer(GeoFeatureModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True) # Or UserSerializer for nested details
    # GeoFeatureModelSerializer will handle 'geometry' automatically as GeoJSON

    class Meta:
        model = Field
        geo_field = "geometry" # Specify the geometry field
        fields = ['id', 'name', 'description', 'owner', 'geometry']
        read_only_fields = ['owner']


class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = '__all__'


class OperationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationType
        fields = '__all__'


class AgroOperationSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    # For related fields, you can choose how to represent them:
    # field = FieldSerializer() # Nested, can be verbose, might lead to circular imports if not careful
    field = serializers.PrimaryKeyRelatedField(queryset=Field.objects.all()) 
    crop = serializers.PrimaryKeyRelatedField(queryset=Crop.objects.all(), allow_null=True, required=False)
    operation_type = serializers.PrimaryKeyRelatedField(queryset=OperationType.objects.all())

    class Meta:
        model = AgroOperation
        fields = [
            'id', 'field', 'crop', 'operation_type', 'operation_date', 
            'description', 'equipment_used', 'materials_cost', 
            'user', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_field(self, value):
        """
        Check that the user (from request) owns the field or is an admin.
        This is an additional layer of validation; view-level permissions are primary.
        """
        request = self.context.get('request', None)
        if request and not (value.owner == request.user or request.user.is_staff):
            raise serializers.ValidationError("You do not have permission to assign operations to this field.")
        return value

    def create(self, validated_data):
        # Ensure user is set, even if not explicitly passed (CurrentUserDefault handles this)
        if 'user' not in validated_data and self.context.get('request'):
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
