"""
The methods to update feeds and their entries
"""
import logging
from feeds.models import Source
from .fetch import query_source
from .parse import update_source, update_source_fields
from .predict import set_due_poll

logger = logging.getLogger('update_feed')


def init_feed(source: Source):
    """
    Query a feed source to get the title, icon and other fields, does not save changes

    ### Parameters
    - source: the Source object for the feed to update
    """
    logger.info('Initializing Feed %s', source)

    feed_data = query_source(source, False)
    update_source_fields(source, feed_data.feed)
    source.name = source.title


def update_feed(source: Source, no_cache: bool = False):
    """
    Query the feed, update theentries, and predict when to query next.

    ### Parameters
    - source: the Source object for the feed to update
    - no_cache: feed services can be told to not return posts that have already been queried, set this to true to force a complete query
    """
    logger.info('Updating Feed %s', source)

    feed_data = query_source(source, no_cache)
    if not feed_data:
        source.save()
        return

    update_source(source, feed_data)
    set_due_poll(source)

    logger.debug('polled at %s', source.last_polled)
    logger.debug('due poll set to %s', source.due_poll)

    source.save()
