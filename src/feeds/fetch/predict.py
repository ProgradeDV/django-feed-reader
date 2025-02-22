"""
This module contains the functions that predict when the next feed entry will be posted based on past data
"""
from statistics import stdev, mean
from datetime import datetime, timedelta, time, date
from zoneinfo import ZoneInfo
from django.db.models import Q
from feeds.models import Source, Entry

MAX_ENTRIES = 50


def set_next_fetch(source: Source) -> datetime:
    """Calculate and set when the given source should next be polled

    ### Parameters
    - source: the feed source to set the poll date on
    """
    entries = list(Entry.objects.all()[:MAX_ENTRIES])

    mean_time, std_dev = predict_time(entries)
    predicted_date = predict_day(entries)
    now = datetime.now(tz=ZoneInfo('UTC'))

    tomarrow = (now + timedelta(days=1)).date()

    # if predicted to be beyond tomarrow, set to check tomarrow anyway, at the end of the curve
    if predicted_date > tomarrow:
        source.due_fetch = datetime.combine(tomarrow, mean_time, tzinfo=ZoneInfo('UTC')) + std_dev
        return

    # if predicted for today, do minimum steps untill the end of the curve
    if predicted_date < tomarrow:
        zone_end = datetime.combine(now.date(), mean_time, tzinfo=ZoneInfo('UTC')) + std_dev
        if now < zone_end:
            source.due_fetch = now + timedelta(seconds=source.min_interval)
            return

    # if predicted to be tommarrow, or beyond the zone today, set to poll tomarrow at the begining of the predicted zone
    source.due_fetch = datetime.combine(tomarrow, mean_time, tzinfo=ZoneInfo('UTC')) - std_dev



def predict_time(entries: list[Entry]) -> tuple[time, timedelta]:
    """Predicts the time of day and standard deviation from it of the next entry

    ### Parameters
    - entries, a list of feed entries

    ### Returns
    - time: the of day predicted
    - timedelta: the standard defiation
    """
    if not entries:
        return time(hour=12), timedelta(seconds=0)

    # convert all created times to seconds since midnight
    seconds = [seconds_since_midnight(entry.created) for entry in entries]
    mean_value, deviation = circled_mean(seconds, 0, 86400)

    deviation_dt = timedelta(seconds=deviation)
    predicted_time = (datetime.min + timedelta(seconds=mean_value)).time()

    return predicted_time, deviation_dt



def circled_mean(data: list, min_value, max_value) -> tuple:
    """Find the mean of data that wraps around a circle

    ### Parameters
    - data (list): the data to find the mean of
    - min: the minimum value
    - max: the maximum value

    ### Returns
    - the average
    - the standard deviation
    """
    middle = (min_value + max_value)/2
    range_length = max_value - min_value
    sorted_data = sorted(data)

    # find the index of the first data point above the middle
    for middle_index, value in enumerate(sorted_data):
        if value >= middle:
            break

    unswapped_mean = mean(data)
    unswapped_deviation = stdev(data, unswapped_mean)

    # shift the data below the middle to above the range by one length
    swapped_data = sorted_data[middle_index:] + [range_length + value for value in sorted_data[:middle_index]]
    swapped_mean = mean(swapped_data)
    swapped_deviation = stdev(swapped_data, swapped_mean)

    # if the shifted data is more tightly packed than the unshifted data then the return the shifted result
    if swapped_deviation < unswapped_deviation:
        # un-shift the mean
        if swapped_mean >= max_value:
            swapped_mean -= range_length
        return swapped_mean, swapped_deviation

    return unswapped_mean, unswapped_deviation



def seconds_since_midnight(date_time: datetime) -> float:
    """Convert a datetime object into a float representing the total seconds since midnight

    ### Parameters
    - date_time (datetime): the object to convert

    ### Returns
    - float: the total seconds sonce midnight
    """
    return (date_time - datetime.combine(date_time.date(), time.min, tzinfo=date_time.tzinfo)).total_seconds()



def predict_day(entries: list[Entry]) -> date:
    """Predict the next day that there will be a new entry. It does this by tallying what days of the week new
    entries happen and finding the next one where an entry was posted.

    This does not take into account time of day. so a feed that regularly posts around midnight UTC will get the tally
    split over many weekdays
    
    ### Parameters
    - entries: list of entries

    ### Returns
    date of next predicted entry
    """
    # if less than a week of entries present, assume dayly
    if len(entries) == 0 or (entries[-1].created).date() > date.today() - timedelta(days=7):
        return date.today()

    # count by weekday and determine days with entries
    weekday_tally = [0]*7
    for entry in entries:
        weekday_tally[entry.created.weekday()] += 1

    today_weekday = datetime.now().weekday()

    # shift the week tally to start on todays weekday
    reordered_weekdays = weekday_tally[today_weekday:] + weekday_tally[:today_weekday]

    for i, tally in enumerate(reordered_weekdays):
        if tally > 0:
            return date.today() + timedelta(days=i)

    return date.today() + timedelta(days=1)



def due_sources() -> list:
    """Get the list of sources due for a fetch.

    ### Returns
    - list of sources to update
    """
    sources = Source.objects.filter(Q(due_fetch__lt = datetime.now()) & Q(live = True))
    return sources.order_by("due_fetch")
