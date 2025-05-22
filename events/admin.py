from django.contrib import admin
from .models import Event, EventPermission, EventVersion, EventChangeLog, EventConflict

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time', 'created_by', 'is_recurring', 'version')
    list_filter = ('is_recurring', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('created_at', 'updated_at', 'version')
    date_hierarchy = 'start_time'


@admin.register(EventPermission)
class EventPermissionAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'role', 'created_at', 'updated_at')
    list_filter = ('role', 'created_at')
    search_fields = ('event__title', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EventVersion)
class EventVersionAdmin(admin.ModelAdmin):
    list_display = ('event', 'version_number', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('event__title', 'created_by__username')
    readonly_fields = ('created_at',)

@admin.register(EventChangeLog)
class EventChangeLogAdmin(admin.ModelAdmin):
    list_display = ('event', 'change_type', 'changed_by', 'changed_at')
    list_filter = ('change_type', 'changed_at')
    search_fields = ('event__title', 'changed_by__username')
    readonly_fields = ('changed_at',)

@admin.register(EventConflict)
class EventConflictAdmin(admin.ModelAdmin):
    list_display = ('event', 'conflicting_event', 'detected_at', 'resolution_status', 'resolved_by')
    list_filter = ('resolution_status', 'detected_at', 'resolved_at')
    search_fields = ('event__title', 'conflicting_event__title', 'resolved_by__username')
    readonly_fields = ('detected_at', 'resolved_at')
