"""
This module contins the functions that predict when the next feed entry will be posted based on past performance
"""
from datetime import datetime, timedelta, time, date
from zoneinfo import ZoneInfo
from django.db.models import Q
from ..models import Source, Entry

MIN_TIME_STEP = timedelta(hours=1)
MAX_TIME_STEP = timedelta(days=1)
MAX_ENTRIES = 50


def set_due_poll(source: Source) -> datetime:
    """
    Sets when the given feed should net be shecked

    ### Parameters
    - source: the feed source to set the poll date
    """

    entries = Entry.objects.all()[:MAX_ENTRIES]

    predicted_time, std = predict_time(entries)
    predicted_date = predict_day(entries)

    source.due_poll = datetime.combine(predicted_date, predicted_time, tzinfo=ZoneInfo('UTC'))



def predict_time(entries: list[Entry]) -> tuple[time, timedelta]:
    """
    Predicts the time of day, and standard deviation, of the next entry

    ### Parameters
    - entries, a list of feed entries

    ### Returns
    - time: the time of day predicted
    - timedelta: the standard defiation
    """
    return time(hour=12), timedelta(hours=1)


def predict_day(entries: list[Entry]) -> date:
    """
    Predicts the next day that there will be a new entry
    
    ### Parameters
    - entries: list of entries

    ### Returns
    date of next predicted entry
    """
    return date.today() + timedelta(days=1)


def due_sources() -> list:
    """
    Get the list of sources due for this update.

    ### Returns
    - list of sources to update
    """
    sources = Source.objects.filter(Q(due_poll__lt = datetime.now()) & Q(live = True))
    return sources.order_by("due_poll")