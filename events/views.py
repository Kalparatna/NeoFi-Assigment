from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from .models import Event, EventPermission, EventVersion, EventChangeLog, EventConflict
from .serializers import (
    EventSerializer, EventCreateSerializer, EventUpdateSerializer,
    EventPermissionSerializer, EventVersionSerializer, EventChangeLogSerializer,
    EventConflictSerializer
)
from .permissions import IsEventOwnerOrEditor, IsEventOwner, HasEventPermission
from .utils import detect_event_conflicts, generate_diff

class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, HasEventPermission]

    def get_queryset(self):
        user = self.request.user
        return Event.objects.filter(
            permissions__user=user,
            is_deleted=False
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'create':
            return EventCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EventUpdateSerializer
        return EventSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            event = serializer.save(created_by=self.request.user)
            
            # Create changelog entry
            EventChangeLog.objects.create(
                event=event,
                version=event.versions.first(),
                change_type=EventChangeLog.ChangeType.CREATE,
                changed_by=self.request.user,
                changes={'action': 'created'},
                metadata={'initial_version': True}
            )

            # Detect conflicts
            detect_event_conflicts(event)

    def perform_update(self, serializer):
        with transaction.atomic():
            old_data = self.get_serializer(self.get_object()).data
            event = serializer.save()
            new_data = self.get_serializer(event).data

            # Create changelog entry
            EventChangeLog.objects.create(
                event=event,
                version=event.versions.latest('version_number'),
                change_type=EventChangeLog.ChangeType.UPDATE,
                changed_by=self.request.user,
                changes=generate_diff(old_data, new_data)
            )

            # Detect conflicts
            detect_event_conflicts(event)

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.is_deleted = True
            instance.save()

            # Create changelog entry
            EventChangeLog.objects.create(
                event=instance,
                version=instance.versions.latest('version_number'),
                change_type=EventChangeLog.ChangeType.DELETE,
                changed_by=self.request.user,
                changes={'action': 'deleted'}
            )

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        event = self.get_object()
        serializer = EventPermissionSerializer(data=request.data, many=True)
        
        if serializer.is_valid():
            with transaction.atomic():
                permissions = serializer.save(event=event)
                
                # Create changelog entry
                EventChangeLog.objects.create(
                    event=event,
                    version=event.versions.latest('version_number'),
                    change_type=EventChangeLog.ChangeType.SHARE,
                    changed_by=request.user,
                    changes={'permissions': serializer.data},
                    metadata={'shared_with': [p.user_id for p in permissions]}
                )
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        event = self.get_object()
        permissions = event.permissions.all()
        serializer = EventPermissionSerializer(permissions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        event = self.get_object()
        versions = event.versions.all()
        serializer = EventVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def changelog(self, request, pk=None):
        event = self.get_object()
        changelog = event.changelog.all()
        serializer = EventChangeLogSerializer(changelog, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def diff(self, request, pk=None):
        event = self.get_object()
        version1_id = request.query_params.get('version1')
        version2_id = request.query_params.get('version2')

        if not version1_id or not version2_id:
            return Response(
                {'error': 'Both version1 and version2 parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            version1 = event.versions.get(version_number=version1_id)
            version2 = event.versions.get(version_number=version2_id)
        except EventVersion.DoesNotExist:
            return Response(
                {'error': 'One or both versions not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        diff = generate_diff(version1.data, version2.data)
        return Response(diff)

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        event = self.get_object()
        version_id = request.data.get('version_id')

        if not version_id:
            return Response(
                {'error': 'version_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            version = event.versions.get(version_number=version_id)
        except EventVersion.DoesNotExist:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            # Create new version with rolled back data
            new_version = EventVersion.objects.create(
                event=event,
                version_number=event.version + 1,
                data=version.data,
                created_by=request.user,
                change_reason=f'Rolled back to version {version_id}'
            )

            # Update event with rolled back data
            for key, value in version.data.items():
                if key not in ['id', 'created_by', 'created_at', 'updated_at', 'version']:
                    setattr(event, key, value)
            event.version += 1
            event.save()

            # Create changelog entry
            EventChangeLog.objects.create(
                event=event,
                version=new_version,
                change_type=EventChangeLog.ChangeType.UPDATE,
                changed_by=request.user,
                changes={'action': 'rollback', 'to_version': version_id}
            )

        return Response(EventSerializer(event).data)

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        serializer = EventCreateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            events = serializer.save(created_by=request.user)
            return Response(
                EventSerializer(events, many=True).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
