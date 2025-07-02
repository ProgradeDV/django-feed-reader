"""
Request the feed data
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import feedparser
import requests
from requests.exceptions import RequestException
from django.conf import settings
from feeds.models import Source

logger = logging.getLogger('Fetch Query')


def query_source(source: Source, no_cache: bool) -> feedparser.util.FeedParserDict:
    """
    Retrieve the feed data from the given url

    ### Parameters
    - source (Source): the feed source to query
    - no_cache: if true, the request will be made without filtering for only new entries

    ### Returns
    - FeedParserDict: feed data
    """
    logger.info('Requesting Source: %s', source)
    now = datetime.now(tz=ZoneInfo('UTC'))

    if source.last_feched is not None:
        interval = (now - source.last_feched).total_seconds()
    else:
        interval = 0

    headers = headers={
        "Accept-Encoding": "gzip",
        "User-Agent": getattr(settings, 'FEEDS_USER_AGENT'),
        }
    if not no_cache:
        headers["If-None-Match"] = str(source.etag)
        headers["If-Modified-Since"] = str(source.last_modified)

    # query the feed
    try:
        response = requests.get(
            source.feed_url,
            timeout=10,
            headers=headers
            )

    except RequestException as exc:
        logger.exception('Error querying the source: %s', source.feed_url)
        source.last_result = str(exc)
        source.status_code = 600
        return None

    # record the feed status and codes
    logger.info('feed status: (%s) %s', response.status_code, response.reason)

    source.last_feched = now
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

    elif response.status_code == 429: # 429 means too many requests,
        if interval > source.min_cadence: # avoid doing anything if fetched early
            source.min_cadence += 1200 # add 20 minuts to minimum interval
        return None

    # turn off source if we get a 404 or any other 400 code
    elif 400 <= response.status_code < 500:
        source.live = False
        return None

    source.last_success = source.last_feched
    return response.content
