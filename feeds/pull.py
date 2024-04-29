"""
Functions for querying and decoding rss feeds using feedparser
"""
import logging
from datetime import datetime
import feedparser
from .models import Source, Entry, Enclosure
from .fetch import query_source

logger = logging.getLogger('UpdateSources')

MAX_INTERVAL = 60*24 # 1 day
MIN_INTERVAL = 60 # 1 hour

SOURCE_FIELD_KEYS = {
    'title': ('title',),
    'subtitle': ('subtitle',),
    'site_url': ('href',),
    'image_url': tuple(),
    'author': tuple(),
    'description': tuple(),
}

ENTRY_FIELD_KEYS = {
    'guid':('id',),
    'title':('title',),
    'link':('link',),
    'created':('created','published'),
    'author':('author',),
    'body':('content', 'summary'),
    'image_url':('media_thumbnail',)
}


def tree_atribute(data, *paths):
    for path in paths:
        value = data

        for key in path.split('.'):
            value = getattr(value, key, None)

        if value is not None:
            return value


def pull_sources(sources: list[Source]):
    """
    Update all of the given sources

    ### Parameters
    - sources (list): a list of sources to update
    """
    logger.info('Updating %s sources', len(sources))
    for source in sources:
        pull_source(source)


def pull_source(source: Source):
    """
    Update the data for the source.

    ### Parameters
    - source (Source): the source object to update
    """
    logger.info('Updating Source: %s', Source)
    try:
        data = query_source(source.feed_url)

    except Exception as exc:
        logger.exception('Failed to request source: %s', source.feed_url)
        source.last_result = str(exc)
        source.save()
        return

    try:
        update_source_fields(source, data.feed)
        update_entries(source, data.entries)

    except Exception as exc:
        logger.exception('Failed to parse source: %s', source.feed_url)
        source.last_result = str(exc)

    source.save()


def update_source_fields(source: Source, parser_data: feedparser.util.FeedParserDict):
    """
    Update the Source from the data

    ### Parameters
    - source (Source): the Source instance to update
    - parser_data (FeedParserDict): the data parsed from the feed fetch
    """
    # for each field, attempt each known path to get to the data
    for field_name, paths in SOURCE_FIELD_KEYS.items():
        setattr(source, field_name, tree_atribute(parser_data, *paths))


def update_entries(source: Source, parser_data: feedparser.util.FeedParserDict):
    """
    Create any new entries for a source

    ### Parameters
    - source (Source): the source instance we're creating entried for
    - parser_data (FeedParserDict): the raw data parsed from the fetch operation
    """
    for entry_data in parser_data:
        get_or_create_entry(source, entry_data)


def get_or_create_entry(source: Source, entry_data: feedparser.util.FeedParserDict):
    """
    Create any new entries for a source

    ### Parameters
    - source (Source): the source instance we're creating entried for
    - entry_data (FeedParserDict): the raw data parsed from the fetch operation
    """
    print(entry_data.media_thumbnail)
    try:
        entry = Entry.objects.get(source=source, guid=entry_data.id)

    except Entry.DoesNotExist:
        entry = Entry(source=source, guid=entry_data.id)

    for field_name, paths in ENTRY_FIELD_KEYS.items():
        value = tree_atribute(entry_data, *paths)
        setattr(entry, field_name, value)

    if isinstance(entry.image_url, list) and entry.image_url:
        entry.image_url = entry.image_url[0].get('url', None)

    entry.save()
