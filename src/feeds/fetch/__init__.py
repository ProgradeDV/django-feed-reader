"""
The methods to update feeds and their entries
"""
import logging
from feeds.models import Source
from .query import query_source
from .parse import update_feed, update_source_attributes, parse_feed_content
from .predict import set_next_fetch

logger = logging.getLogger('update_feed')


def init_feed(source: Source):
    """
    Query a feed source to get the title, icon and other fields, does not save changes

    ### Parameters
    - source: the Source object for the feed to update
    """
    logger.info('Initializing Feed %s', source)

    feed_content = query_source(source, False)
    feed_data = parse_feed_content(feed_content)
    update_source_attributes(source, feed_data.feed)
    source.name = source.title


def fetch_feed(source: Source, no_cache: bool = False):
    """
    Query the feed, update theentries, and predict when to query next.

    ### Parameters
    - source: the Source object for the feed to update
    - no_cache: feed services can be told to not return posts that have already been queried, set this to true to force a complete query
    """
    logger.info('Updating Feed %s', source)

    feed_content = query_source(source, no_cache)
    if feed_content is None:
        source.save()
        return

    update_feed(source, feed_content)
    set_next_fetch(source)

    logger.debug('polled at %s', source.last_feched)
    logger.debug('due fetch set to %s', source.due_fetch)

    source.save()
