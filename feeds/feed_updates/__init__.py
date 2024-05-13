"""
The methods to update feeds and their entries
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from feeds.models import Source
from .fetch import query_source
from .parse import update_source
from .predict import set_due_poll

logger = logging.getLogger('update_feed')


def update_feed(source: Source):
    """
    Query the feed, update theentries, and predict when to query next.

    ### Parameters
    - source: the Source object for the feed to update
    """
    logger.info('Updating Feed %s', source)
    feed_data = query_source(source.feed_url)
    update_source(source, feed_data)
    set_due_poll(source)

    logger.debug('due poll set to %s', source.due_poll)

    source.last_polled = datetime.now(tz=ZoneInfo('UTC'))

    logger.debug('polled at %s', source.last_polled)

    source.save()
