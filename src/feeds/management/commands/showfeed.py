"""
Django Command to shwo the data for a feed
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from feeds.models import Source

logger = logging.getLogger('ShowFeed')


class Command(BaseCommand):
    """
    Command to query and show the data for a feed
    """
    help = 'Print most fields for a given feed'

    def add_arguments(self, parser):
        parser.add_argument("--url", type=str)
        parser.add_argument("--name", type=str)


    def handle(self, *args, **options):

        if options['url']:
            source = Source.objects.get(feed_url=options['url'])

        elif options['name']:
            source = Source.objects.get(name=options['name'])

        else:
            raise CommandError('must supply either --name or --url')

        for key in ['name', 'title', 'subtitle', 'last_polled', 'due_poll', 'site_url', 'feed_url', 'image_url', 'icon_url', 'author', 'description']:
            value = getattr(source, key, None)
            self.stdout.write(f"{key:<11} = {value}")

        self.stdout.write(self.style.SUCCESS('Finished'))
