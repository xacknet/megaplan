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
            # For this iteration, if they get to has_object_permission, they can view.
            # However, specific model access (like Field.owner) should be checked.
            # Let's assume the queryset in the view already handled basic visibility.
            # If obj is a Field, check ownership.
            if hasattr(obj, 'owner'):
                return obj.owner == request.user or request.user.is_staff
            # If obj is an AgroOperation, check ownership via its field or direct user.
            if hasattr(obj, 'user'): # AgroOperation has a 'user' field (creator)
                return obj.user == request.user or request.user.is_staff
            if hasattr(obj, 'field') and hasattr(obj.field, 'owner'): # AgroOperation linked to Field
                return obj.field.owner == request.user or request.user.is_staff
            return True # Fallback for other objects or if no specific owner attribute

        # Write permissions are only allowed to the owner of the snippet or admin.
        if hasattr(obj, 'owner'): # For Field model
            return obj.owner == request.user or request.user.is_staff
        if hasattr(obj, 'user'): # For AgroOperation model (creator)
            return obj.user == request.user or request.user.is_staff
        # If an AgroOperation is being checked, and it doesn't have a 'user' but has a 'field'
        if hasattr(obj, 'field') and hasattr(obj.field, 'owner'):
             return obj.field.owner == request.user or request.user.is_staff
             
        return False # Default to deny for safety

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access for everyone, but write access only for admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
