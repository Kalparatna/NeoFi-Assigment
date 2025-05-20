from datetime import datetime
from django.utils import timezone
from .models import Event, EventConflict

def detect_event_conflicts(event):
    """
    Detect conflicts between the given event and other events.
    A conflict occurs when two events overlap in time.
    """
    # Get all events that could potentially conflict
    potential_conflicts = Event.objects.filter(
        start_time__lt=event.end_time,
        end_time__gt=event.start_time,
        is_deleted=False
    ).exclude(id=event.id)

    # Check each potential conflict
    for other_event in potential_conflicts:
        # Check if there's already a conflict record
        if not EventConflict.objects.filter(
            event=event,
            conflicting_event=other_event
        ).exists():
            # Create new conflict record
            EventConflict.objects.create(
                event=event,
                conflicting_event=other_event,
                resolution_status=EventConflict.ResolutionStatus.PENDING
            )

def generate_diff(old_data, new_data):
    """
    Generate a diff between two versions of event data.
    Returns a dictionary with added, modified, and removed fields.
    """
    diff = {
        'added': {},
        'modified': {},
        'removed': {}
    }

    # Find added and modified fields
    for key, new_value in new_data.items():
        if key not in old_data:
            diff['added'][key] = new_value
        elif old_data[key] != new_value:
            diff['modified'][key] = {
                'old': old_data[key],
                'new': new_value
            }

    # Find removed fields
    for key, old_value in old_data.items():
        if key not in new_data:
            diff['removed'][key] = old_value

    return diff

def parse_recurrence_pattern(pattern):
    """
    Parse a recurrence pattern string into a structured format.
    Example pattern: "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE,FR"
    """
    if not pattern:
        return None

    result = {}
    parts = pattern.split(';')

    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            if ',' in value:
                result[key] = value.split(',')
            else:
                result[key] = value

    return result

def generate_recurring_events(event, start_date, end_date):
    """
    Generate recurring events based on the event's recurrence pattern.
    Returns a list of event instances between start_date and end_date.
    """
    if not event.is_recurring or not event.recurrence_pattern:
        return []

    pattern = parse_recurrence_pattern(event.recurrence_pattern)
    if not pattern:
        return []

    events = []
    current_date = max(event.start_time, start_date)
    end = min(event.end_time, end_date)

    while current_date <= end:
        # Create a new event instance
        new_event = Event(
            title=event.title,
            description=event.description,
            start_time=current_date,
            end_time=current_date + (event.end_time - event.start_time),
            location=event.location,
            created_by=event.created_by,
            is_recurring=True,
            recurrence_pattern=event.recurrence_pattern
        )
        events.append(new_event)

        # Calculate next occurrence based on pattern
        if pattern['FREQ'] == 'DAILY':
            current_date += timezone.timedelta(days=int(pattern.get('INTERVAL', 1)))
        elif pattern['FREQ'] == 'WEEKLY':
            current_date += timezone.timedelta(weeks=int(pattern.get('INTERVAL', 1)))
        elif pattern['FREQ'] == 'MONTHLY':
            # Add months to current_date
            month = current_date.month - 1 + int(pattern.get('INTERVAL', 1))
            year = current_date.year + month // 12
            month = month % 12 + 1
            current_date = current_date.replace(year=year, month=month)
        elif pattern['FREQ'] == 'YEARLY':
            current_date = current_date.replace(year=current_date.year + int(pattern.get('INTERVAL', 1)))

    return events 