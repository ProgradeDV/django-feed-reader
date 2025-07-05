"""
Functions for updating feeds
"""
import logging
from urllib.parse import urlencode, urlparse, parse_qs, ParseResult
from time import struct_time, strftime
import feedparser
from feeds.models import Source, Entry, Enclosure

logger = logging.getLogger('Fetch Predict')

# status codes for errors in parsing
PARSING_ERROR_STATUS_CODE = 600


SOURCE_FIELD_KEYS = {
    'title': ('title',),
    'subtitle': ('subtitle',),
    'site_url': ('href',),
    'image_url': ('image.href', 'image', 'img'),
    'icon_url': ('logo', 'icon', 'facicon'),
    'author': ('author',),
    'description': ('description'),
}

ENTRY_FIELD_KEYS = {
    'title':('title',),
    'body':('content.0.value', 'content', 'summary'),
    'link':('link',),
    'created':('updated_parsed', 'published_parsed', 'created_parsed', 'updated', 'published', 'created'),
    'guid':('id',),
    'author':('author',),
    'image_url':('image.href', 'image', 'media_thumbnail.0.url'),
}


def update_feed(source: Source, content:str):
    """
    Update the data for the given feed.

    ### Parameters
    - source (Source): the source object to update
    - content (str): the content recieved from the query step
    """
    try:
        parsed_data = parse_feed_content(content)
        update_source_attributes(source, parsed_data.feed)
        update_entries(source, parsed_data.entries)

    except Exception as exc:
        logger.exception('Failed to parse source: %s', source.feed_url)
        source.status_code = PARSING_ERROR_STATUS_CODE
        source.last_result = str(exc)

    source.save()



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
            if isinstance(value, list):
                try:
                    value = value[int(key)]
                except Exception:
                    break

            elif isinstance(value, dict):
                try:
                    value = value[key]
                except Exception:
                    break

            else:
                try:
                    value = getattr(value, key)
                except Exception:
                    break

        else: # no break
            if value is None:
                continue
            return value

    return None



def parse_feed_content(content:str) -> feedparser.util.FeedParserDict:
    """Turn the string response from the query into a searchable dict"""
    return feedparser.parse(content)



def update_source_attributes(source: Source, feed_data: feedparser.util.FeedParserDict):
    """
    Update the Source from the data

    ### Parameters
    - source (Source): the Source instance to update
    - parsed_data (FeedParserDict): the data parsed from the feed fetch
    """
    # for each field, attempt each known path to get to the data
    for field_name, paths in SOURCE_FIELD_KEYS.items():
        value = tree_atribute(feed_data, *paths)
        if value is None:
            continue

        if isinstance(value, struct_time):
            value = strftime('%Y-%m-%dT%H:%M:%SZ', value)

        setattr(source, field_name, value)

    source.save()


def update_entries(source: Source, entries_data: feedparser.util.FeedParserDict):
    """
    Create any new entries for a source

    ### Parameters
    - source (Source): the source instance we're creating entried for
    - entries_data (FeedParserDict): the raw data parsed from the fetch operation
    """
    logger.debug('Parsing %d Entries', len(entries_data))

    for entry_data in entries_data:
        entry = get_or_create_entry(source, entry_data)
        update_enclosures(entry, entry_data)


def get_or_create_entry(source: Source, entry_data: feedparser.util.FeedParserDict):
    """
    Create any new entries for a source

    ### Parameters
    - source (Source): the source instance we're creating entried for
    - entry_data (FeedParserDict): the raw data parsed from the fetch operation
    """
    try:
        entry = Entry.objects.get(source=source, guid=entry_data.id)

    except Entry.DoesNotExist:
        entry = Entry(source=source, guid=entry_data.id)

    for field_name, paths in ENTRY_FIELD_KEYS.items():
        value = tree_atribute(entry_data, *paths)
        if value is None:
            continue

        if isinstance(value, struct_time):
            value = strftime('%Y-%m-%dT%H:%M:%SZ', value)

        setattr(entry, field_name, value)

    if isinstance(entry.image_url, list) and entry.image_url:
        entry.image_url = entry.image_url[0].get('url', None)

    entry.save()
    return entry


def update_enclosures(entry: Entry, entry_data: feedparser.util.FeedParserDict):
    """
    Create enclosures for the given entry

    ### Parameters
    - entry (Entry): the netry to update
    - encloure_data (FeedParserDict): the data to parse into enclosures
    """
    # delete enclosures that don't exist
    entry.enclosures.all().delete()

    # add an enclosure for each youtube video link
    # youtube links may be in the normal 'link' attribute
    if link := entry_data.get('link', ''):
        parsed_link = urlparse(link)

        if parsed_link.netloc == 'www.youtube.com':
            create_embeded_youtube_enclosure(entry, None, parsed_link)

    # for each set of enclosure data:
    for enclosure_data in entry_data.get('enclosures', []):
        parsed_link = urlparse(link)

        if parsed_link.netloc == 'www.youtube.com':
            create_embeded_youtube_enclosure(entry, enclosure_data, parsed_link)
            continue

        create_enclosure(entry, enclosure_data)



def create_enclosure(entry: Entry, enclosure_data: feedparser.util.FeedParserDict) -> Enclosure:
    """the standard way to create an enclosure"""
    if not enclosure_data:
        return None

    return Enclosure.objects.create(
        entry = entry,
        length = enclosure_data.get('length', 0),
        href = enclosure_data.get('href', ''),
        type = enclosure_data.get('type', ''),
    )



def create_embeded_youtube_enclosure(entry: Entry, enclosure_data: feedparser.util.FeedParserDict, youtube_link:ParseResult) -> Enclosure:
    """youtube enclosures need to be modified to form an embedable link"""
    # if the link is already an embeded link
    if youtube_link.path.startswith('embed/'):
        return Enclosure.objects.create(
            entry = entry,
            length = 0,
            href = youtube_link.geturl(),
            type = 'youtube',
        )

    # check if the youtube link contains a video id
    # if no video id is present, create a normal enclosure
    query = parse_qs(youtube_link.query)
    if 'v' not in query:
        return create_enclosure(entry, enclosure_data)

    video_id = query['v'][0]
    embeded_link = f"https://www.youtube.com/embed/{video_id}"

    return Enclosure.objects.create(
        entry = entry,
        length = 0,
        href = embeded_link,
        type = 'youtube',
    )
