"""
The methods to update feeds and their entries
"""
import logging
from feeds.models import Source
from .query import query_source
from .parse import update_feed
from .predict import set_next_fetch

logger = logging.getLogger('update_feed')


def new_feed(source: Source):
    """query, parse, and save a new source. If the query fails then it will not be saved and return false."""
    logger.info('creating a new feed: %s', source)

    feed_content = query_source(source, False)
    if source.status_code >= 400:
        logger.error('Error querying the source, changes will not be saved: %s', source)
        return

    set_next_fetch(source)
    source.save() # first save is to give the source model an id
    update_feed(source, feed_content)



def fetch_feed(source: Source, no_cache: bool = False):
    """
    Query the feed, update the entries, and predict when to query next. The given source must already exist.

    ### Parameters
    - source: the Source object for the feed to update
    - no_cache: feed services can be told to not return posts that have already been queried, set this to true to force a complete query
    """
    logger.info('Updating Feed %s', source)

    feed_content = query_source(source, no_cache)
    set_next_fetch(source)
    logger.debug('polled at %s', source.last_feched)
    logger.debug('due fetch set to %s', source.due_fetch)

    if not feed_content:
        source.save()
        return

    update_feed(source, feed_content) # update feed will also save
