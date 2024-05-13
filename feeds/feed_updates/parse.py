"""
Functions for updating feeds
"""
import logging
import feedparser
from feeds.models import Source, Entry, Enclosure

logger = logging.getLogger('UpdateSources')

MAX_INTERVAL = 60*24 # 1 day
MIN_INTERVAL = 60 # 1 hour

SOURCE_FIELD_KEYS = {
    'title': ('title',),
    'subtitle': ('subtitle',),
    'site_url': ('href',),
    'image_url': tuple(),
    'icon_url': tuple(),
    'author': tuple(),
    'description': tuple(),
}

ENTRY_FIELD_KEYS = {
    'title':('title',),
    'body':('content', 'summary'),
    'link':('link',),
    'created':('created','published'),
    'guid':('id',),
    'author':('author',),
    'image_url':('media_thumbnail',)
}


def tree_atribute(parser_data: feedparser.util.FeedParserDict, *paths):
    """
    follow a tree of attributes to attempt to find a value

    ### Parameters
    - parser_data (FeedParserDict): the data retrieved from the source
    - paths: all the posible paths to go down.

    ### Returns
    the value or None
    """
    for path in paths:
        value = parser_data

        for key in path.split('.'):
            value = getattr(value, key, None)

        if value is not None:
            return value

    return None



def update_source(source: Source, parser_data: feedparser.util.FeedParserDict):
    """
    Update the data for the source.

    ### Parameters
    - source (Source): the source object to update
    """
    try:
        update_source_fields(source, parser_data.feed)
        update_entries(source, parser_data.entries)

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
    # print(entry_data.media_thumbnail)
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
