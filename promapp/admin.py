from django.contrib import admin
from .models import *
# Register your models here.


class LikertScaleResponseOptionInline(admin.StackedInline):
    model = LikertScaleResponseOption
    extra = 1

class RangeScaleResponseOptionInline(admin.StackedInline):
    model = RangeScaleResponseOption
    extra = 1


@admin.register(LikertScale)
class LikertScaleAdmin(admin.ModelAdmin):
    inlines = [LikertScaleResponseOptionInline]
    list_display = ('likert_scale_name',)
    search_fields = ('likert_scale_name',)
    list_filter = ('likert_scale_name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')

@admin.register(RangeScale)
class RangeScaleAdmin(admin.ModelAdmin):
    inlines = [RangeScaleResponseOptionInline]
    list_display = ('range_scale_name',)
    search_fields = ('range_scale_name',)
    list_filter = ('range_scale_name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')


admin.site.register(ConstructScale)
admin.site.register(Item)
