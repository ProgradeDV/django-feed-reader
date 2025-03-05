
import os
from django.test import TestCase, Client
from django.conf import settings
from django.utils import timezone
from feeds.models import Source, Entry, Enclosure, WebProxy
from feeds.fetch import parse

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')


def construct_feed(file_name:str) -> Source:
    """reusable function to construct a feed from a file"""
    test_source = Source()
    test_source.save()

    with open(os.path.join(TEST_DATA_DIR, file_name), 'r', encoding='utf-8') as file:
        content = file.read()

    parse.update_feed(test_source, content)

    return test_source




class TestParsing(TestCase):

    def test_parse_podcast_xml(self):
        test_source = construct_feed('podcast.xml')

        self.assertIsNone(test_source.name)
        self.assertEqual(test_source.title, 'Accidental Tech Podcast')
        self.assertEqual(test_source.subtitle, 'ST: Three nerds discussing tech, Apple, programming, and loosely related matters.')
        self.assertIsNone(test_source.site_url)
        self.assertEqual(test_source.feed_url, '')
        self.assertEqual(test_source.image_url, 'https://images.squarespace-cdn.com/content/513abd71e4b0fe58c655c105/1388599863457-1KVWSYSYVIGDBNVHKXDU/Artwork.jpg?content-type=image%2Fjpeg')
        self.assertIsNone(test_source.icon_url, '')
        self.assertEqual(test_source.author, 'atp@marco.org')
        self.assertIsNone(test_source.description, '')

    def test_youtube_parse(self):
        test_source = construct_feed('youtube.html')

        self.assertIsNone(test_source.name)
        self.assertEqual(test_source.title, 'Brandon Sanderson')
        self.assertIsNone(test_source.subtitle)
        self.assertEqual(test_source.site_url, 'https://www.youtube.com/channel/UC3g-w83Cb5pEAu5UmRrge-A')
        self.assertEqual(test_source.feed_url, '')
        self.assertIsNone(test_source.image_url)
        self.assertIsNone(test_source.icon_url)
        self.assertEqual(test_source.author, 'Brandon Sanderson')
        self.assertIsNone(test_source.description, '')

        self.assertEqual(test_source.entries.count(), 1)

        test_entry = test_source.entries.first()

        self.assertEqual(test_entry.title, 'Every Chapter is Flirting')
        self.assertEqual(test_entry.body, 'Want to send me something to open?')
        self.assertEqual(test_entry.link, 'https://www.youtube.com/watch?v=sWvHHM_4Eiw')

        self.assertEqual(test_entry.enclosures.count(), 1)

        test_enclosure = test_entry.enclosures.first()

        self.assertEqual(test_enclosure.type, 'youtube')
        self.assertEqual(test_enclosure.href, 'https://www.youtube.com/embed/?v=sWvHHM_4Eiw')
