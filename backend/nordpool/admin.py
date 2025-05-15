from django.contrib import admin
from .models import PriceArea, ElectricityPrice, ServerData, CalculatedResult, SimulatedBattery, SimulatedSolarAndGridPower, OptimizationDecision


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


@admin.register(CalculatedResult)
class CalculatedResultAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_id_1', 'source_value_1', 'source_id_2',
                    'source_value_2', 'calculated_value', 'timestamp')
    list_filter = ('name', 'source_id_1', 'source_id_2', 'timestamp')
    search_fields = ('name', 'source_id_1', 'source_id_2')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)


@admin.register(SimulatedBattery)
class SimulatedBatteryAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'current_charge', 'charge_percentage', 'last_updated')
    search_fields = ('name',)
    list_filter = ('last_updated',)
    readonly_fields = ('last_updated',)

    def charge_percentage(self, obj):
        if obj.capacity and float(obj.capacity) > 0:
            percentage = (float(obj.current_charge) / float(obj.capacity)) * 100
            return f"{percentage:.2f}%"
        return "0.00%"

    charge_percentage.short_description = 'Poziom naładowania (%)'


@admin.register(SimulatedSolarAndGridPower)
class SimulatedSolarAndGridPowerAdmin(admin.ModelAdmin):
    list_display = ('solar_power', 'grid_power', 'usage', 'total_power', 'last_updated')
    list_filter = ('last_updated',)
    readonly_fields = ('last_updated',)

    def total_power(self, obj):
        total = float(obj.solar_power) + float(obj.grid_power)
        return f"{total:.2f}"

    total_power.short_description = 'Całkowita moc (W)'


@admin.register(OptimizationDecision)
class OptimizationDecisionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'decision', 'battery_percentage_before', 'battery_percentage_after', 'surplus', 'current_price')
    list_filter = ('timestamp', 'decision')
    search_fields = ('decision', 'decision_reason')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    fieldsets = (
        ('Informacje ogólne', {
            'fields': ('timestamp', 'decision', 'decision_reason')
        }),
        ('Stan baterii', {
            'fields': ('battery_level_before', 'battery_percentage_before', 'battery_level_after', 'battery_percentage_after')
        }),
        ('Dane energetyczne', {
            'fields': ('solar_power', 'grid_power', 'usage', 'surplus')
        }),
        ('Ceny energii', {
            'fields': ('current_price', 'avg_price')
        }),
    )

    def has_add_permission(self, request):
        return False  # Zapobiega ręcznemu dodawaniu rekordów


admin.site.register(ElectricityPrice, ElectricityPriceAdmin)