"""
Models to store Feed Sources, Posts, and supporting data
"""
import datetime
import logging
from urllib.parse import urlencode
from django.db import models
from django.utils.timezone import now



class Source(models.Model):
    """
    This is the data describing the source of a feed and the fetch behavior
    """
    name          = models.CharField(max_length=255, blank=True, null=True)
    title         = models.CharField(max_length=255, blank=True, null=True)
    subtitle      = models.TextField(max_length=255, blank=True, null=True)
    site_url      = models.URLField(max_length=255, blank=True, null=True) # link
    feed_url      = models.URLField(max_length=512, unique=True) # href
    image_url     = models.URLField(max_length=512, blank=True, null=True) # image.href
    icon_url      = models.URLField(max_length=512, blank=True, null=True) # icon
    author        = models.CharField(max_length=255, blank=True, null=True) # author
    description   = models.TextField(null=True, blank=True) # info

    # === due tracking ===
    # the last time it was fetched
    last_feched = models.DateTimeField(blank=True, null=True)
    # the last time there was a succsessfull query
    last_success = models.DateTimeField(blank=True, null=True)
    # the minimum seconds between queries
    min_interval = models.FloatField(default=60*60)
    # the next time to fetch, default to distant past to put new sources to front of queue
    due_fetch = models.DateTimeField(default=datetime.datetime(1900, 1, 1, tzinfo=datetime.timezone.utc))

    # === request metadata ===
    # Some feeds will only send new enties since the last query this etag was used for
    etag = models.CharField(max_length=255, blank=True, null=True)
    # the last datetime where this feed had new entries, this is not a datetime field because this value is from the fetch metadata
    last_modified = models.CharField(max_length=255, blank=True, null=True)
    # the http status, or error message of the last query
    last_result = models.CharField(max_length=255,blank=True,null=True)
    # the http status code of the last query
    status_code = models.PositiveIntegerField(default=0)
    # If the feed is not live, then the fetch routine will not query it
    live = models.BooleanField(default=True)


    def __str__(self):
        return str(self.display_name)


    @property
    def best_link(self):
        """Return a good link to the source"""
        if not self.site_url:
            return self.feed_url
        return self.site_url


    @property
    def display_name(self) -> str:
        """The best name for display to the user"""
        if self.name:
            return self.name
        if self.title:
            return self.title
        return self.best_link



class Entry(models.Model):
    """an entry in a feed"""
    # fields from feed
    source        = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='entries')
    title         = models.TextField(blank=True)
    body          = models.TextField() # content
    link          = models.CharField(max_length=512, blank=True, null=True)
    created       = models.DateTimeField(db_index=True, default=now)
    guid          = models.CharField(max_length=512, blank=True, null=True, db_index=True) # id
    author        = models.CharField(max_length=255, blank=True, null=True)
    image_url     = models.CharField(max_length=512, blank=True, null=True)
    # tracking
    found         = models.DateTimeField(auto_now_add=True)


    @property
    def title_url_encoded(self) -> str:
        """
        encoded url for title
        """
        try:
            ret = urlencode({"X":self.title})

        except Exception: # pylint: disable=broad-exception-caught
            logging.exception("Failed to url encode title of entry %s", self.id)
            return ""

        if len(ret) > 2:
            return ret[2:]
        return ret


    def __str__(self):
        return f"{self.source.display_name}: Entry {self.title}"



class Enclosure(models.Model):
    """
    What podcasts use to send their audio
    """
    entry   = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='enclosures')
    length = models.IntegerField(default=0)
    href   = models.CharField(max_length=512)
    type   = models.CharField(max_length=256)
