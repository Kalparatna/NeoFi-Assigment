from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Event, EventPermission, EventVersion, EventChangeLog, EventConflict

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)

class EventPermissionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = EventPermission
        fields = ('id', 'user', 'user_id', 'role', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class EventVersionSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = EventVersion
        fields = ('id', 'version_number', 'data', 'created_by', 'created_at', 'change_reason')
        read_only_fields = ('id', 'version_number', 'created_by', 'created_at')

class EventChangeLogSerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)
    version = EventVersionSerializer(read_only=True)

    class Meta:
        model = EventChangeLog
        fields = ('id', 'change_type', 'changed_by', 'changed_at', 'changes', 'metadata', 'version')
        read_only_fields = ('id', 'changed_by', 'changed_at', 'version')

class EventConflictSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    conflicting_event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    resolved_by = UserSerializer(read_only=True)

    class Meta:
        model = EventConflict
        fields = ('id', 'event', 'conflicting_event', 'detected_at', 'resolved_at',
                 'resolution_status', 'resolution_notes', 'resolved_by')
        read_only_fields = ('id', 'detected_at', 'resolved_at', 'resolved_by')

class EventSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    permissions = EventPermissionSerializer(many=True, read_only=True)
    current_version = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ('id', 'title', 'description', 'start_time', 'end_time', 'location',
                 'created_by', 'created_at', 'updated_at', 'is_recurring', 'recurrence_pattern',
                 'version', 'permissions', 'current_version')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at', 'version')

    def get_current_version(self, obj):
        try:
            version = obj.versions.latest('version_number')
            return EventVersionSerializer(version).data
        except EventVersion.DoesNotExist:
            return None

    def validate(self, data):
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError("End time must be after start time")
        return data

class EventCreateSerializer(EventSerializer):
    permissions = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ('permissions',)

    def create(self, validated_data):
        permissions_data = validated_data.pop('permissions', [])
        event = super().create(validated_data)
        
        # Create owner permission
        EventPermission.objects.create(
            event=event,
            user=self.context['request'].user,
            role=EventPermission.Role.OWNER
        )

        # Create additional permissions
        for perm_data in permissions_data:
            EventPermission.objects.create(
                event=event,
                user_id=perm_data['user_id'],
                role=perm_data.get('role', EventPermission.Role.VIEWER)
            )
        return event

class EventUpdateSerializer(EventSerializer):
    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields

    def update(self, instance, validated_data):
        # Create a new version before updating
        EventVersion.objects.create(
            event=instance,
            version_number=instance.version + 1,
            data=self.to_representation(instance),
            created_by=self.context['request'].user,
            change_reason=validated_data.get('change_reason', '')
        )

        # Update the event
        instance = super().update(instance, validated_data)
        instance.version += 1
        instance.save()

        return instance 
