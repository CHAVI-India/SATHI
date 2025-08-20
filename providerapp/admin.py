from django.contrib import admin
from .models import ProviderType, Provider
from allauth.account.decorators import secure_admin_login

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)

# Register your models here.

@admin.register(ProviderType)
class ProviderTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')
    
@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider_type', 'institution', 'account_expiry_date')
    search_fields = ('user__username', 'institution__name')
    list_filter = ('provider_type', 'institution', 'account_expiry_date')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('account_expiry_date',)

