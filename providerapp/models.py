from django.db import models
from django.contrib.auth.models import User
from patientapp.models import Institution



# Create your models here.
class ProviderType(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    

class Provider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, help_text="Select the user for the provider")
    provider_type = models.ForeignKey(ProviderType, on_delete=models.CASCADE, help_text="Select the provider type")
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, help_text="Select the institution for the provider")
    employee_id = models.CharField(max_length=255, null=True, blank=True, help_text="Employee ID. Optional")
    account_expiry_date = models.DateField(null=True, blank=True, help_text="Account expiry date. Optional")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.username
    
    