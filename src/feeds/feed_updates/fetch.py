"""
Fetch the feed data
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import feedparser
import requests
from feeds.models import Source

logger = logging.getLogger('SourceQuery')

USER_AGENT = ('Django Feed Reader')


def query_source(source: Source, no_cache: bool) -> feedparser.util.FeedParserDict:
    """
    Retrieve the feed data from the given url

    ### Parameters
    - source (Source): the feed source to query
    - no_cache: if true, the request will be made without filtering for only new entries

    ### Returns
    - FeedParserDict: feed data
    """
    logger.info('Fetching Source: %s', source)
    source.last_polled = datetime.now(tz=ZoneInfo('UTC'))

    headers = headers={"Accept-Encoding": "gzip"}
    if not no_cache:
        headers["If-None-Match"] = str(source.etag)
        headers["If-Modified-Since"] = str(source.last_modified)

    # fetch the feed
    try:
        response = requests.get(
            source.feed_url,
            timeout=10,
            user_agent=USER_AGENT,
            headers=headers
            )

    except Exception as exc:
        logger.exception('Error Fetching Feed: %s', source)
        source.last_result = str(exc)
        return None

    # record the feed status and codes
    logger.info('feed status: (%s) %s', response.status_code, response.reason)

    source.status_code = response.status_code
    source.etag = response.headers.get('Etag', source.etag)
    source.last_modified = response.headers.get('Last-Modified', source.last_modified)
    source.last_result = response.reason

    # handle response codes
    if response.status_code in (301, 308): # perminent redirect
        logger.info('Feed redirected to %s', response.url)
        source.feed_url = response.url

    elif response.status_code == 304: # 304 means that there is no new content
        return None

    elif response.status_code == 429: # 429 means too many requests
        # TODO: slow down feeds that get this response
        ...

    # turn off source if we get a 404 or any other 400 code
    elif 400 <= response.status_code < 500:
        source.live = False

    # parse the data
    try:
        return feedparser.parse(response.content)

    except Exception as exc:
        logger.exception('Error Parsing Feed: %s', source)
        source.last_result = str(exc)
        return None
