import ee
from django.conf import settings
import os

def initialize_gee():
    """
    Initializes the Earth Engine API using service account credentials.
    Returns True if initialization is successful, False otherwise.
    """
    try:
        key_file = settings.GEE_SERVICE_ACCOUNT_KEY_FILE
        project_id = getattr(settings, 'GEE_PROJECT_ID', None)

        if not os.path.exists(key_file):
            print(f"GEE Service Account Key file not found at: {key_file}")
            print("Please ensure the GEE_SERVICE_ACCOUNT_KEY_FILE setting in settings.py points to a valid key file.")
            return False

        # For service account authentication, ee.ServiceAccountCredentials can often infer
        # the necessary details (like client_email and project_id) directly from the key file.
        # The `project` argument in ee.Initialize can be used if you need to override
        # the project associated with the credentials, or if it's not in the key file.
        
        credentials = ee.ServiceAccountCredentials(project=project_id, keyFile=key_file)
        ee.Initialize(credentials=credentials, opt_url='https://earthengine-highvolume.googleapis.com')
            
        print("Google Earth Engine initialized successfully.")
        return True
    except ee.EEException as e:
        print(f"Error initializing Earth Engine: {e}")
        print("Ensure your service account is correctly set up and has necessary permissions.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during GEE initialization: {e}")
        return False

def get_ndvi_for_field(field_geometry_geojson, start_date_str, end_date_str):
    """
    Calculates NDVI for a given field geometry and date range using Sentinel-2.

    Args:
        field_geometry_geojson (str): GeoJSON string of the field's geometry (Polygon or MultiPolygon).
        start_date_str (str): Start date in 'YYYY-MM-DD' format.
        end_date_str (str): End date in 'YYYY-MM-DD' format.

    Returns:
        dict: Containing 'tile_url' for Leaflet and 'mean_ndvi', or None if an error occurs.
              Example: {'tile_url': 'https://earthengine.googleapis.com/...', 'mean_ndvi': 0.75}
    """
    if not initialize_gee():
        return {'error': "GEE initialization failed. Check server logs and GEE settings."}

    try:
        # Convert GeoJSON string to ee.Geometry
        import json
        geometry_data = json.loads(field_geometry_geojson)
        
        # GEE expects coordinates in a specific order for Polygons.
        # Ensure the GeoJSON is correctly formatted. Leaflet draw usually provides this.
        ee_geometry = ee.Geometry(geometry_data) # Pass the whole GeoJSON geometry part

        # Image Collection: Sentinel-2 MSI: MultiSpectral Instrument, Level-2A
        s2_sr_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(ee_geometry) \
            .filterDate(ee.Date(start_date_str), ee.Date(end_date_str))

        # Cloud Masking function for Sentinel-2
        def mask_s2_clouds(image):
            QA60 = image.select('QA60')
            # Bits 10 and 11 are clouds and cirrus, respectively.
            cloud_mask = 1 << 10
            cirrus_mask = 1 << 11
            # Both flags should be set to zero, indicating clear conditions.
            mask = QA60.bitwiseAnd(cloud_mask).eq(0).And(QA60.bitwiseAnd(cirrus_mask).eq(0))
            return image.updateMask(mask).divide(10000) # Scale factor for SR

        s2_sr_masked = s2_sr_collection.map(mask_s2_clouds)

        # NDVI Calculation
        def calculate_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)

        s2_ndvi = s2_sr_masked.map(calculate_ndvi)
        
        # Check if any images are found after filtering
        collection_size = s2_ndvi.size().getInfo()
        if collection_size == 0:
            return {'error': "No cloud-free Sentinel-2 images found for the selected date range and location."}

        # Reduce to a single image (e.g., median)
        median_ndvi_image = s2_ndvi.select('NDVI').median() # Select only NDVI band for median calculation

        # Clip to the field geometry (optional, but good for visualization and stats)
        clipped_ndvi = median_ndvi_image.clip(ee_geometry)

        # Calculate mean NDVI for the field
        # Note: scale might need adjustment based on the projection of the collection.
        # For Sentinel-2, native resolution for B4, B8 is 10m.
        mean_ndvi_dict = clipped_ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee_geometry,
            scale=10, # Resolution in meters
            maxPixels=1e9
        )
        mean_ndvi = mean_ndvi_dict.get('NDVI').getInfo() # .getInfo() to get the value

        # Visualization parameters for NDVI
        ndvi_vis_params = {
            'min': -0.2, 'max': 0.9,
            'palette': ['FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
                        '74A901', '66A000', '529400', '3E8601', '207401', '056201',
                        '004C00', '023B01', '012E01', '011D01', '011301']
        }

        # Get a map ID for the NDVI layer to display in Leaflet
        map_id_dict = clipped_ndvi.getMapId(ndvi_vis_params)
        tile_url = map_id_dict['tile_fetcher'].url_format

        return {
            'tile_url': tile_url,
            'mean_ndvi': round(mean_ndvi, 2) if mean_ndvi is not None else None,
            'map_id': map_id_dict['mapid'] # Also return mapid for potential use
        }

    except ee.EEException as e:
        print(f"Earth Engine error in get_ndvi_for_field: {e}")
        # Check for common errors like "Geometry has too many vertices"
        if "Geometry has too many vertices" in str(e):
             return {'error': "The field geometry is too complex or large for direct GEE processing in this context. Consider simplifying the geometry."}
        return {'error': f"An Earth Engine error occurred: {str(e)}"}
    except json.JSONDecodeError:
        return {'error': "Invalid GeoJSON data provided for the field geometry."}
    except Exception as e:
        print(f"Unexpected error in get_ndvi_for_field: {e}")
        return {'error': f"An unexpected error occurred: {str(e)}"}

# Example Usage (for testing, not part of the Django app flow directly here)
if __name__ == '__main__':
    # This part will not run inside Django, but can be used for standalone testing
    # if you configure settings.GEE_SERVICE_ACCOUNT_KEY_FILE appropriately
    # or use a different authentication method for local testing (e.g., ee.Authenticate()).
    
    # 1. Authenticate (if running standalone and not using service account via Django settings)
    # try:
    #    ee.Authenticate() # Opens a browser for authentication
    #    ee.Initialize()
    #    print("GEE Authenticated and Initialized for standalone test.")
    # except Exception as e:
    #    print(f"Standalone GEE authentication failed: {e}")
    #    exit()

    # Dummy GeoJSON for testing (replace with actual field geometry)
    # A small square in a known agricultural area for testing
    sample_field_geojson = """
    {
        "type": "Polygon",
        "coordinates": [[
            [-103.800, 40.700], [-103.800, 40.705],
            [-103.790, 40.705], [-103.790, 40.700],
            [-103.800, 40.700]
        ]]
    }
    """
    start_date = '2023-06-01'
    end_date = '2023-08-31'

    # To run this test, you MUST have GEE_SERVICE_ACCOUNT_KEY_FILE set in settings
    # and the key file must be valid, or use ee.Authenticate() as above.
    # For now, we assume initialize_gee() will be called from the Django view
    # which relies on Django settings.
    
    # print(f"Attempting to get NDVI for sample field from {start_date} to {end_date}...")
    # result = get_ndvi_for_field(sample_field_geojson, start_date, end_date)
    # if result and 'error' not in result:
    #    print(f"GEE NDVI Tile URL: {result['tile_url']}")
    #    print(f"Mean NDVI: {result['mean_ndvi']}")
    # else:
    #    print(f"Error or no result: {result}")
    pass # End of example usage


def get_ndvi_zones(field_geometry_geojson, start_date_str, end_date_str, num_zones=5):
    """
    Calculates NDVI, clusters it into zones, and returns tile URL and GeoJSON for the zones.

    Args:
        field_geometry_geojson (str): GeoJSON string of the field's geometry.
        start_date_str (str): Start date in 'YYYY-MM-DD' format.
        end_date_str (str): End date in 'YYYY-MM-DD' format.
        num_zones (int): Number of zones for K-Means clustering.

    Returns:
        dict: Containing 'zones_tile_url', 'zones_geojson', or an 'error' message.
    """
    if not initialize_gee():
        return {'error': "GEE initialization failed. Check server logs and GEE settings."}

    try:
        import json
        geometry_data = json.loads(field_geometry_geojson)
        ee_geometry = ee.Geometry(geometry_data)

        # 1. Get Median NDVI Image (similar to get_ndvi_for_field)
        s2_sr_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(ee_geometry) \
            .filterDate(ee.Date(start_date_str), ee.Date(end_date_str))

        def mask_s2_clouds(image):
            QA60 = image.select('QA60')
            cloud_mask = 1 << 10
            cirrus_mask = 1 << 11
            mask = QA60.bitwiseAnd(cloud_mask).eq(0).And(QA60.bitwiseAnd(cirrus_mask).eq(0))
            return image.updateMask(mask).divide(10000)

        s2_sr_masked = s2_sr_collection.map(mask_s2_clouds)

        def calculate_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)

        s2_ndvi = s2_sr_masked.map(calculate_ndvi)
        
        collection_size = s2_ndvi.size().getInfo()
        if collection_size == 0:
            return {'error': "No cloud-free Sentinel-2 images found for the selected date range and location."}

        median_ndvi_image = s2_ndvi.select('NDVI').median().clip(ee_geometry)

        # 2. K-Means Clustering
        # The training data for clustering is the NDVI values within the field.
        # GEE needs a FeatureCollection for training. We can sample the NDVI image.
        # For K-Means, it's better to operate on an image with just the band to cluster.
        
        # Create training data by sampling the NDVI image.
        # Ensure the band name 'NDVI' is present for training.
        training_data = median_ndvi_image.sample(
            region=ee_geometry,
            scale=30, # Scale for sampling, can be coarser than final vectorization
            numPixels=1000, # Number of pixels to sample for training
            tileScale=4 # Increase tileScale to avoid "Too many concurrent aggregations"
        )
        
        if training_data.size().getInfo() == 0:
            return {'error': "No data available for NDVI clustering after sampling. The field might be too small or there is no valid NDVI data."}


        clusterer = ee.Clusterer.wekaKMeans(num_zones).train(training_data, ['NDVI'])
        
        # Apply the clusterer to the NDVI image.
        clustered_result = median_ndvi_image.cluster(clusterer) # This will have a 'cluster' band

        # Visualization for clustered image (random colors for zones)
        # We can use a random visualizer for distinct colors per cluster ID
        # The 'cluster' band contains values from 0 to num_zones-1.
        clustered_vis_params = {'min': 0, 'max': num_zones - 1, 'palette': ['FF0000', '00FF00', '0000FF', 'FFFF00', 'FF00FF', '00FFFF', 'FFA500', '800080', '008000', 'A52A2A'][:num_zones]}
        
        zones_map_id_dict = clustered_result.getMapId(clustered_vis_params)
        zones_tile_url = zones_map_id_dict['tile_fetcher'].url_format

        # 3. Vectorize Clustered Image
        # Ensure 'cluster' band is used for vectorization
        # reduceToVectors is memory intensive. Scale needs to be chosen carefully.
        # Using a scale of 10m (Sentinel-2 NDVI resolution) can be very heavy.
        # Consider a slightly coarser scale for vectorization if performance is an issue,
        # or if the zones are expected to be relatively large.
        vector_scale = 20 # meters; adjust based on performance and desired detail
        
        # Ensure the image being vectorized has the 'cluster' band and is projected.
        # It's good practice to reproject to a known CRS before vectorization if issues arise.
        # Default projection of reduceToVectors is WGS84 (EPSG:4326).
        vectorized_zones = clustered_result.select('cluster').reduceToVectors(
            geometry=ee_geometry,
            scale=vector_scale,
            geometryType='polygon',
            eightConnected=False, # Use four-connected to reduce complexity
            labelProperty='cluster_id', # Name of the property storing the cluster ID
            reducer=ee.Reducer.first(), # Keeps the first value of the cluster ID
            maxPixels=1e10, # Increased maxPixels, but be cautious
            tileScale=4 # Helps with large computations
        )
        
        # Get GeoJSON. This can be very slow or fail for large/complex results.
        try:
            zones_geojson = vectorized_zones.getInfo() # This is a blocking call
        except ee.EEException as e:
            if "Too many features" in str(e) or "Too many pixels" in str(e) or "User memory limit exceeded" in str(e):
                return {'error': f"The field geometry is too complex or the number of zones resulted in too many vector features for direct GeoJSON export. Try reducing num_zones or simplifying the field boundary. (Details: {str(e)})", 'zones_tile_url': zones_tile_url}
            raise e # Re-raise other GEE errors

        return {
            'zones_tile_url': zones_tile_url,
            'zones_geojson': zones_geojson, # This is a FeatureCollection GeoJSON
            'zones_map_id': zones_map_id_dict['mapid']
        }

    except ee.EEException as e:
        error_message = f"An Earth Engine error occurred: {str(e)}"
        if "Invalid band name: NDVI" in str(e) and collection_size == 0:
             error_message = "No cloud-free Sentinel-2 images found for the selected date range and location. Cannot compute NDVI."
        elif "training_data.size().getInfo() == 0" in str(e): # This check is now earlier
             error_message = "No data available for NDVI clustering after sampling. The field might be too small or there is no valid NDVI data."
        elif "clusterer.train" in str(e):
             error_message = f"Error during GEE K-Means training: {str(e)}. This might be due to insufficient distinct NDVI values for clustering or too few pixels in the training sample."
        print(f"Earth Engine error in get_ndvi_zones: {e}")
        return {'error': error_message}
    except json.JSONDecodeError:
        return {'error': "Invalid GeoJSON data provided for the field geometry."}
    except Exception as e:
        print(f"Unexpected error in get_ndvi_zones: {e}")
        return {'error': f"An unexpected error occurred: {str(e)}"}
