"""
Django Command to list all sources
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from feeds.models import Source

logger = logging.getLogger('ListFeeds')


class Command(BaseCommand):
    """
    Command to query and list basic data of all source objects
    """
    help = 'List all feeds'

    def handle(self, *args, **options):

        sources = Source.objects.all()

        for source in sources:
            self.stdout.write(f"{source.title} - {source.feed_url}")
