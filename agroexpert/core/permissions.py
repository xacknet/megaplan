from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit/delete it.
    Read is allowed for authenticated users if the object is public or they have specific access.
    For this project, we'll assume list views in ViewSets will handle filtering by owner.
    Detail views (retrieve, update, destroy) will use this permission.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request if the list view is already filtered,
        # so we'll always allow GET, HEAD or OPTIONS requests at the object level.
        # For list views, filtering should be done in get_queryset().
        if request.method in permissions.SAFE_METHODS:
            # For detail view, check if user is owner or admin for safe methods too,
            # if you want to restrict who can even view details.
            # Let's assume the queryset in the view already handled basic visibility.
            # If obj is a Field, check ownership.
            if hasattr(obj, 'owner') and obj.owner is not None: # Check if obj.owner exists and is not None
                return obj.owner == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')
            # If obj is an AgroOperation, check ownership via its field or direct user.
            if hasattr(obj, 'user') and obj.user is not None: # AgroOperation has a 'user' field (creator)
                return obj.user == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')
            if hasattr(obj, 'field') and hasattr(obj.field, 'owner') and obj.field.owner is not None: # AgroOperation linked to Field
                return obj.field.owner == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')
            # If none of the above, and it's a safe method, let's be cautious.
            # If an object doesn't have a clear owner, only admins should see details unless explicitly public.
            # However, for this iteration, we assume views filter lists, and detail view implies some access.
            # For objects without explicit ownership (like Crop, OperationType), access is typically broader or admin-only for writes.
            # This permission is primarily for owner-centric models like Field and AgroOperation.
            if not (hasattr(obj, 'owner') or hasattr(obj, 'user') or hasattr(obj, 'field')):
                 return True # Allow GET for objects without specific ownership like Crop, OperationType for now.
            return request.user.is_staff # Fallback for safe methods on ownable objects without clear owner match

        # Write permissions are only allowed to the owner of the snippet or admin.
        if hasattr(obj, 'owner') and obj.owner is not None: # For Field model
            return obj.owner == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')
        if hasattr(obj, 'user') and obj.user is not None: # For AgroOperation model (creator)
            return obj.user == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')
        # If an AgroOperation is being checked, and it doesn't have a 'user' but has a 'field'
        if hasattr(obj, 'field') and hasattr(obj.field, 'owner') and obj.field.owner is not None:
             return obj.field.owner == request.user or (hasattr(request.user, 'profile') and request.user.profile.role == 'administrator')
             
        return False # Default to deny for safety for write operations

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access for everyone, but write access only for admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
