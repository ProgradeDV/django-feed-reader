"""
Django Command to import a feed source
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from feeds.models import Source
from feeds.fetch import fetch_feed
from feeds.url_converters import get_rss_url
from urllib.parse import  urlparse, ParseResult

logger = logging.getLogger('ImportFeed')


class Command(BaseCommand):
    """
    Command to create a new soure object
    """
    help = 'Inport an RSS feed'

    def add_arguments(self, parser):
        parser.add_argument("feed_url", type=str)
        parser.add_argument("-n", "--name", dest='name', type=str)


    def handle(self, *args, **options):

        feed_url = options['feed_url']

        parsed_url = urlparse(feed_url)
        if not parsed_url.scheme:
            raise ValueError(f'Not a url: {feed_url}')

        feed_url = get_rss_url(parsed_url)
        logger.info('feed_url = %s', feed_url)

        source, _ = Source.objects.get_or_create(feed_url=feed_url)
        logger.debug('source = %s', source)

        if options['name']:
            logger.info('name = %s', options['name'])
            source.name = options['name']

        fetch_feed(source)
