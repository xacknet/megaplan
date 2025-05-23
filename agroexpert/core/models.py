from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('agronomist', 'Agronomist'),
        ('farmer', 'Farmer'),
        ('expert', 'Expert'),
        ('administrator', 'Administrator'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True) # Allow blank/null initially

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # This ensures the profile is saved whenever the User object is saved
    # It's important if other parts of the code might update User and expect Profile to be in sync
    # However, for simple role assignment, this might not be strictly necessary if role is set separately
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        # This can happen if the profile wasn't created for some reason (e.g. existing users before this signal)
        UserProfile.objects.create(user=instance)

from django.contrib.gis.db import models as gis_models

class Field(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fields')
    geometry = gis_models.PolygonField()

    def __str__(self):
        return self.name

class Crop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    scientific_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class OperationType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class AgroOperation(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='agro_operations')
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True)
    operation_type = models.ForeignKey(OperationType, on_delete=models.PROTECT) # PROTECT to prevent deletion of type if in use
    operation_date = models.DateField()
    description = models.TextField()
    equipment_used = models.CharField(max_length=255, blank=True, null=True)
    materials_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, editable=False) # Set editable=False
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # photos = models.ImageField(upload_to='agro_operations_photos/', blank=True, null=True) # Optional for now

    def __str__(self):
        return f"{self.operation_type} on {self.field} - {self.operation_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-operation_date', '-created_at']
