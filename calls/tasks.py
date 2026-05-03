import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import Room

logger = logging.getLogger(__name__)

EXPIRY_HOURS = 24


@shared_task
def delete_expired_rooms():
    expiry_threshold = timezone.now() - timedelta(hours=EXPIRY_HOURS)
    expired_rooms = Room.objects.filter(
        Q(meeting_date__isnull=False, meeting_date__lt=expiry_threshold) |
        Q(meeting_date__isnull=True, created_at__lt=expiry_threshold)
    )
    count, _ = expired_rooms.delete()
    logger.info(f"Deleted {count} expired room(s).")