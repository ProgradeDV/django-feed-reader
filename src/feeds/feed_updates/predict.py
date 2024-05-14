"""
This module contins the functions that predict when the next feed entry will be posted based on past performance
"""
from statistics import stdev, median, mean
from datetime import datetime, timedelta, time, date
from zoneinfo import ZoneInfo
from django.db.models import Q
from feeds.models import Source, Entry

MIN_TIME_STEP = timedelta(hours=1)
MAX_ENTRIES = 50


def set_due_poll(source: Source) -> datetime:
    """
    Sets when the given feed should net be shecked

    ### Parameters
    - source: the feed source to set the poll date
    """
    entries = list(Entry.objects.all()[:MAX_ENTRIES])

    mean_time, std_dev = predict_time(entries)
    predicted_date = predict_day(entries)
    now = datetime.now(tz=ZoneInfo('UTC'))

    tomarrow = (now + timedelta(days=1)).date()

    # if predicted to be beyond tomarrow, set to check tomarrow anyway, at the end of the curve
    if predicted_date > tomarrow:
        source.due_poll = datetime.combine(tomarrow, mean_time, tzinfo=ZoneInfo('UTC')) + std_dev
        return

    # if predicted for today, do minimum steps untill the end of the curve
    if predicted_date < tomarrow:
        zone_end = datetime.combine(now.date(), mean_time, tzinfo=ZoneInfo('UTC')) + std_dev
        if now < zone_end:
            source.due_poll = now + MIN_TIME_STEP
            return

    # if predicted to be tommarrow, or beyond the zone today, set to poll tomarrow at the begining of the predicted zone
    source.due_poll = datetime.combine(tomarrow, mean_time, tzinfo=ZoneInfo('UTC')) - std_dev



def predict_time(entries: list[Entry]) -> tuple[time, timedelta]:
    """
    Predicts the time of day, and standard deviation, of the next entry

    ### Parameters
    - entries, a list of feed entries

    ### Returns
    - time: the time of day predicted
    - timedelta: the standard defiation
    """
    # convert all created times to seconds since midnight
    seconds = [delta_since_midnight(entry.created) for entry in entries]
    mean_value, deviation = circled_mean(seconds, 0, 86400)

    deviation_dt = timedelta(seconds=deviation)
    predicted_time = (datetime.min + timedelta(seconds=mean_value)).time()

    return predicted_time, deviation_dt



def circled_mean(data: list, min_value, max_value) -> tuple:
    """
    Find the mean of data that wraps around

    ### Parameters
    - data (list): the data to find the mean of
    - min: the minimum value
    - max: the maximum value

    ### Returns
    - the average
    - the standard deviation
    """
    middle = (min_value + max_value)/2
    gap = max_value - min_value
    sorted_data = sorted(data)

    for i, value in enumerate(sorted_data):
        if value >= middle:
            break

    base_mean = mean(data)
    base_dev = stdev(data, base_mean)

    swapped_data = sorted_data[i:] + [gap + value for value in sorted_data[:i]]
    swapped_mean = mean(swapped_data)
    swapped_dev = stdev(swapped_data, swapped_mean)

    if swapped_dev < base_dev:
        if swapped_mean >= max_value:
            swapped_mean -= gap
        return swapped_mean, swapped_dev

    return base_mean, base_dev



def delta_since_midnight(date_time: datetime) -> float:
    """
    converta a datetime object into a float representing the total seconds since midnight

    ### Parameters
    - date_time (datetime): the object to convert

    ### Returns
    - float: the total seconds sonce midnight
    """
    return (date_time - datetime.combine(date_time.date(), time.min, tzinfo=date_time.tzinfo)).total_seconds()



def predict_day(entries: list[Entry]) -> date:
    """
    Predicts the next day that there will be a new entry
    
    ### Parameters
    - entries: list of entries

    ### Returns
    date of next predicted entry
    """
    # if less than a week of entries present, assume dayly
    if len(entries) == 0 or (entries[-1].created).date() > date.today() - timedelta(days=7):
        return date.today()

    # count by weekday and determine days with entries
    weekdays = [0]*7
    for entry in entries:
        weekdays[entry.created.weekday()] += 1

    this_weekday = datetime.now().weekday()

    reordered_weekdays = weekdays[this_weekday:] + weekdays[:this_weekday]

    for i, weekday in enumerate(reordered_weekdays):
        if weekday > 0:
            return date.today() + timedelta(days=i)

    return date.today() + timedelta(days=1)



def due_sources() -> list:
    """
    Get the list of sources due for this update.

    ### Returns
    - list of sources to update
    """
    sources = Source.objects.filter(Q(due_poll__lt = datetime.now()) & Q(live = True))
    return sources.order_by("due_poll")
