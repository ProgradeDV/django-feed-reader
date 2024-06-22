"""
Fetch the feed data
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import feedparser
from feeds.models import Source

logger = logging.getLogger('SourceQuery')


def query_source(source: Source, no_cache: bool) -> feedparser.util.FeedParserDict:
    """
    Retrieve the feed data from the given url

    ### Parameters
    - source (Source): the feed source to query

    ### Returns
    - FeedParserDict: feed data
    """
    logger.info('Fetching Source: %s', source)
    source.last_polled = datetime.now(tz=ZoneInfo('UTC'))

    try:
        if no_cache:
            data = feedparser.parse(source.feed_url)
        else:
            data = feedparser.parse(source.feed_url, etag=source.etag, modified=source.last_modified)

    except Exception as exc:
        logger.exception('Error Fetching Feed: %s', source)
        source.last_result = str(exc)
        return None

    logger.info('feed status: %s', data.status)

    source.status_code = data.status
    source.etag = data.get('etag', source.etag)
    source.last_modified = data.get('modified', source.last_modified)
    source.last_result = data.get("debug_message", '')
    logger.debug('feedparser debug message: "%s"', source.last_result)

    # perminent redirect
    if data.status in (301, 308) and 'href' in data and data.href:
        source.feed_url = data.href

    # turn off source if they get a 404
    if 400 <= data.status < 500:
        source.live = False

    return data
