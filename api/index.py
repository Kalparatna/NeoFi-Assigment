import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_scheduler.settings')

from django.core.asgi import get_asgi_application
app = get_asgi_application()
