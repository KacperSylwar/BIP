from django.contrib import admin
from .models import PriceArea, ElectricityPrice, ServerData

@admin.register(PriceArea)
class PriceAreaAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'country')
    search_fields = ('code', 'name')
    list_filter = ('country',)

class ElectricityPriceAdmin(admin.ModelAdmin):
    list_display = ('area_code', 'timestamp', 'price', 'currency')
    list_filter = ('area', 'timestamp', 'currency')
    search_fields = ('area__code', 'area__name')
    date_hierarchy = 'timestamp'

    def area_code(self, obj):
        return obj.area.code

    area_code.short_description = 'Obszar cenowy'
    area_code.admin_order_field = 'area__code'

@admin.register(ServerData)
class ServerDataAdmin(admin.ModelAdmin):
    list_display = ('server_id', 'value', 'timestamp')
    search_fields = ('server_id',)
    list_filter = ('timestamp',)

admin.site.register(ElectricityPrice, ElectricityPriceAdmin)