from django.contrib.gis.db.models.functions import Area, Transform
from django.contrib.gis.measure import A # For area measure
from .models import Field, AgroOperation, Crop

# Note on Area Calculation:
# The accuracy of area calculation depends heavily on the SRID of the geometries.
# If geometries are stored in SRID 4326 (WGS84, lat/lon), their native .area attribute 
# will be in square degrees, which is not useful for practical area measurement.
# To get areas in metric units (square meters), geometries should be transformed
# to an appropriate projected coordinate system. EPSG:3857 (Web Mercator) is a common
# global projection that gives results in meters, but it has distortions, especially
# away from the equator. For higher accuracy, a local UTM zone or an equal-area
# projection specific to the region of each field would be ideal.

# This implementation will attempt to transform to EPSG:3857 for area calculation.

def get_total_area_for_user(user):
    """
    Calculates the total area of all fields for a given user.
    If the user is an administrator, calculates for all fields in the system.
    Returns area in hectares.
    """
    total_area_sq_meters = 0
    
    if hasattr(user, 'profile') and user.profile.role == 'administrator':
        fields = Field.objects.all()
    else:
        fields = Field.objects.filter(owner=user)

    for field in fields:
        if field.geometry:
            try:
                # Ensure geometry is in a suitable projection for area calculation (e.g., EPSG:3857)
                # If geometry SRID is not set or is 4326, transform it.
                # Django's Area function by default returns area in the units of the SRID of the field.
                # If SRID is 4326, this is square degrees. We need to transform.
                
                geom_transformed = field.geometry
                if geom_transformed.srid != 3857: # If not already in Web Mercator
                    geom_transformed = Transform(field.geometry, 3857)
                
                # Area function should now use the transformed geometry implicitly if used in an annotation
                # Or, calculate area on the Python side after fetching transformed geometry:
                # current_field_area = field.geometry.transform(3857, clone=True).area # in sq meters
                
                # Using Django's Area function in an annotation is more efficient if possible
                # but requires a bit more setup if transforming within the query.
                # For simplicity here, we'll fetch and transform.
                
                # Let's refine to ensure .area gives square meters after transformation
                # Create a temporary transformed geometry object to calculate area
                temp_geom = field.geometry.transform(3857, clone=True) # Ensure transformation
                area_sq_m = temp_geom.area
                
                if area_sq_m is not None:
                    total_area_sq_meters += area_sq_m
            except Exception as e:
                print(f"Error calculating area for field {field.id} ({field.name}): {e}")
                # Optionally, handle fields with invalid geometry or transformation issues
                pass
                
    return total_area_sq_meters / 10000  # Convert sq meters to hectares

def get_material_costs_per_crop_for_field(field):
    """
    Calculates total material costs per crop for a given field.
    This is a placeholder and currently sums `materials_cost` from AgroOperation.
    """
    operations = AgroOperation.objects.filter(field=field).exclude(materials_cost__isnull=True)
    costs_by_crop = {}

    for op in operations:
        if op.crop:
            crop_name = op.crop.name
            if crop_name not in costs_by_crop:
                costs_by_crop[crop_name] = 0
            costs_by_crop[crop_name] += op.materials_cost
        else: # Operations not linked to a specific crop
            if "Unspecified Crop" not in costs_by_crop:
                costs_by_crop["Unspecified Crop"] = 0
            costs_by_crop["Unspecified Crop"] += op.materials_cost
            
    return costs_by_crop

def get_operations_for_field(field):
    """
    Retrieves all AgroOperations for a given field, ordered by date.
    """
    return AgroOperation.objects.filter(field=field).order_by('-operation_date', 'crop', 'operation_type')

# Placeholder for more advanced fertilizer usage analysis
def get_fertilizer_usage_summary(field):
    """
    Placeholder function for future fertilizer usage analysis.
    This would require more structured data on materials used.
    """
    # Example: if 'description' or a future 'materials_json' field contained structured data:
    # operations = AgroOperation.objects.filter(field=field)
    # fertilizer_summary = {}
    # for op in operations:
    #     # Parse op.description or op.materials_json for fertilizer info
    #     # e.g., if description contains "Fertilizer: Urea, Amount: 50kg"
    #     pass
    return {"message": "Fertilizer usage analysis is not yet implemented. Requires structured data for materials."}
