"""
CLI for fetching and updating a feed
"""
import logging
from django.core.management.base import BaseCommand, CommandError

from feeds.models import Source
from feeds.fetch import fetch_feed
from feeds.fetch.predict import due_sources


logger = logging.getLogger('RefreshFeeds')

DEFAULT_MAX_FEEDS = 10


class Command(BaseCommand):
    """
    Command to request and parse all due feeds
    """
    help = 'Rrefreshes the RSS feeds'

    def add_arguments(self, parser):
        parser.add_argument("--name", type=str)
        parser.add_argument("--url", type=str)
        parser.add_argument("--max", type=int, default=DEFAULT_MAX_FEEDS)
        parser.add_argument("--all-feeds", action='store_true')
        parser.add_argument("--no-cache", action='store_true')


    def handle(self, *args, **options):

        if options['all_feeds']:
            logger.info('Updating all feeds')
            sources = Source.objects.all()

        elif options['name']:
            logger.info('Updating feed by name: %s', options['name'])
            sources = Source.objects.all().filter(name=options['name'])

        elif options['url']:
            logger.info('Updating feed by url: %s', options['url'])
            sources = Source.objects.all().filter(feed_url=options['url'])

        else:
            logger.info('Updating Due Feeds')
            sources = due_sources()

        if options['max']:
            sources = sources[:options['max']]

        logger.info('Updating %d Sources', len(sources))
        for source in sources:
            fetch_feed(source, options['no_cache'])

        logger.info('Finished')
