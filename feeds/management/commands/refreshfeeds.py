
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from feeds.models import Source
from feeds.feed_updates import update_feed
from feeds.feed_updates.predict import due_sources


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


    def handle(self, *args, **options):

        if options['all_feeds']:
            logger.info('Updating all feeds')
            sources = Source.objects.all()

        elif options['name']:
            logger.info('Updating feed: %s', options['name'])
            sources = Source.objects.all().filter(name=options['name'])

        elif options['url']:
            logger.info('Updating feed: %s', options['url'])
            sources = Source.objects.all().filter(feed_url=options['url'])

        else:
            logger.info('Updating Due Feeds')
            sources = due_sources()

        if options['max']:
            sources = sources[:options['max']]
        
        print(sources)

        for source in sources:
            update_feed(source)

        logger.info('Finished')
