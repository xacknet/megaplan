# AgroExpert

## Description

AgroExpert is a web service designed for agronomists, farmers, and agricultural experts to effectively manage agricultural fields. It leverages geospatial data analysis, including satellite imagery processing via Google Earth Engine (GEE), to provide insights into field health and operations. Key functionalities include maintaining detailed agrotechnical journals, generating analytical reports, and offering a REST API for potential mobile application integration.

## Features

*   **User Authentication & Roles:** Secure user registration and login system with distinct roles (Agronomist, Farmer, Expert, Administrator) to manage permissions and access levels.
*   **Field Management:**
    *   Utilizes GeoDjango for robust geospatial data handling.
    *   Allows users to define and manage field boundaries by drawing polygons directly on an interactive Leaflet map.
    *   Stores field geometries (polygons) in a PostGIS-enabled database.
*   **Google Earth Engine (GEE) Integration:**
    *   Calculates and visualizes Normalized Difference Vegetation Index (NDVI) for user-defined fields and date ranges using Sentinel-2 satellite imagery.
    *   **Advanced GEE Features:** Implements NDVI-based zone clustering (K-Means) to identify management zones within fields and allows exporting these zones as GeoJSON.
*   **Agrotechnical Journal:**
    *   Enables users to record detailed information about agricultural operations performed on their fields (e.g., planting, fertilization, harvesting).
    *   Tracks operation dates, types, crops involved, equipment used, and material costs.
*   **Analytics and Reporting:**
    *   Dashboard displaying total cultivated area for the user (or all users for administrators).
    *   Downloadable reports of agrotechnical operations per field in Excel (`.xlsx`) and PDF formats.
*   **REST API:**
    *   Provides API endpoints built with Django REST Framework (DRF) and DRF-GIS for integration with mobile applications or other external services.
    *   Supports token-based authentication.
    *   Includes endpoints for managing fields, operations, and retrieving GEE-derived data (NDVI, NDVI zones).

## Prerequisites

*   **Python:** Version 3.8 or newer.
*   **PostgreSQL:** Version 12 or newer.
*   **PostGIS Extension:** Version 3.0 or newer for PostgreSQL (provides geospatial capabilities).
*   **Google Earth Engine (GEE) Account:**
    *   A registered GEE account.
    *   A GEE service account with its JSON key file for server-to-server authentication.
*   **GDAL:** Geospatial Data Abstraction Library.
    *   On Linux, typically installed as `libgdal-dev` (Debian/Ubuntu) or `gdal-devel` (Fedora/CentOS). This is often a dependency for `psycopg2` (if compiled with GEOS/GDAL support) and `django.contrib.gis`.
    *   On Windows, consider OSGeo4W or precompiled binaries for GDAL and Django.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url> 
    # Replace <repository_url> with the actual URL of your Git repository
    ```

2.  **Navigate to Project Directory:**
    ```bash
    cd agroexpert
    ```

3.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate    # On Windows
    ```

4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Database Setup (PostgreSQL with PostGIS):**
    *   Ensure PostgreSQL is installed and running.
    *   Create a new PostgreSQL database:
        ```sql
        CREATE DATABASE agroexpert_db; 
        -- Or your preferred database name
        ```
    *   Create a PostgreSQL user (role) with a password:
        ```sql
        CREATE USER agroexpert_user WITH PASSWORD 'your_strong_password';
        -- Replace with your desired username and a strong password
        ```
    *   Grant the user all privileges on the created database:
        ```sql
        GRANT ALL PRIVILEGES ON DATABASE agroexpert_db TO agroexpert_user;
        ```
    *   Connect to your new database (e.g., using `psql -U agroexpert_user -d agroexpert_db`) and enable the PostGIS extension (this typically requires superuser privileges or ownership of the database):
        ```sql
        CREATE EXTENSION postgis;
        ```
        If you cannot enable it as `agroexpert_user`, connect as a PostgreSQL superuser (e.g., `postgres`) to the `agroexpert_db` database and run the command.

6.  **Application Configuration:**
    Edit the `agroexpert/settings.py` file:
    *   **`DATABASES`:** Update the `default` database connection settings with your PostgreSQL details:
        ```python
        DATABASES = {
            'default': {
                'ENGINE': 'django.contrib.gis.db.backends.postgis',
                'NAME': 'agroexpert_db',        # Your database name
                'USER': 'agroexpert_user',      # Your PostgreSQL username
                'PASSWORD': 'your_strong_password', # Your PostgreSQL password
                'HOST': 'localhost',            # Or your DB host
                'PORT': '5432',                 # Default PostgreSQL port
            }
        }
        ```
    *   **`GEE_SERVICE_ACCOUNT_KEY_FILE`:** Set the *absolute path* to your Google Earth Engine service account JSON key file.
        ```python
        GEE_SERVICE_ACCOUNT_KEY_FILE = '/path/to/your/service_account_key.json' 
        # Example: '/home/user/secrets/agroexpert-gee-key.json'
        ```
        **Important:** Do NOT commit this key file to your repository. Ensure it's listed in your `.gitignore` file.
    *   **`GEE_PROJECT_ID`:** (Optional, but recommended) Set your GEE project ID if it's not automatically inferred from the service account key.
        ```python
        GEE_PROJECT_ID = 'your-google-earth-engine-project-id'
        ```
    *   **`SECRET_KEY`:** Django generates a default `SECRET_KEY`. For production, ensure this is a unique, long, and random string and kept secret.
    *   **`DEBUG`:** Set to `False` for production environments.
        ```python
        DEBUG = False # For production
        ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com'] # For production
        ```

7.  **Apply Database Migrations:**
    This command creates the necessary tables in your database based on the project's models.
    ```bash
    python manage.py migrate
    ```

8.  **Create a Superuser:**
    This allows you to access the Django admin interface.
    ```bash
    python manage.py createsuperuser
    ```
    Follow the prompts to set a username, email, and password.

## Running the Development Server

1.  **Start the Server:**
    ```bash
    python manage.py runserver
    ```

2.  **Access the Application:**
    *   Open your web browser and go to: `http://127.0.0.1:8000/`
    *   **Admin Interface:** `http://127.0.0.1:8000/admin/` (Log in with your superuser credentials).

## API Endpoints (Brief Overview)

The REST API is available under the `/api/v1/` namespace. Authentication is token-based.
If `DEBUG=True`, the API is browsable via DRF's interface.

*   **Get Auth Token:** `POST /api/v1/api-token-auth/`
    *   Provide `username` and `password` to receive an authentication token.
*   **Users:** `GET /api/v1/users/` (List/details - admin/self only)
*   **Fields:** `GET, POST /api/v1/fields/` (List, Create)
    *   `GET, PUT, PATCH, DELETE /api/v1/fields/<id>/` (Retrieve, Update, Delete)
*   **Crops:** `GET /api/v1/crops/` (List)
*   **Operation Types:** `GET /api/v1/operation-types/` (List)
*   **Agrotechnical Operations:** `GET, POST /api/v1/operations/` (List, Create)
    *   `GET, PUT, PATCH, DELETE /api/v1/operations/<id>/` (Retrieve, Update, Delete)
    *   Can be filtered by `field_id` (e.g., `/api/v1/operations/?field_id=<id>`)
*   **NDVI Data:** `GET /api/v1/fields/<id>/ndvi/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
*   **NDVI Zones:** `GET /api/v1/fields/<id>/ndvi-zones/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&num_zones=<N>`

## (Optional) Running Tests

Tests are yet to be implemented for this project. Future work will include adding a comprehensive test suite.
(To run tests once available: `python manage.py test`)

---

This README provides a starting point. You may need to adjust paths, URLs, or specific commands based on your final project structure and deployment environment.
