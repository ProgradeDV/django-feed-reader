"""
Models to store Feed Sources, Posts, and supporting data
"""
import datetime
import logging
from urllib.parse import urlencode

from django.db import models
import django.utils as django_utils
from django.utils.deconstruct import deconstructible


@deconstructible
class ExpiresGenerator():
    """
    Callable Key Generator that returns a random keystring.
    """

    def __call__(self):
        return django_utils.timezone.now() - datetime.timedelta(days=1)



class Source(models.Model):
    """
    This is an actual feed that we poll
    """
    name          = models.CharField(max_length=255, blank=True, null=True)
    site_url      = models.CharField(max_length=255, blank=True, null=True)
    feed_url      = models.CharField(max_length=512)
    image_url     = models.CharField(max_length=512, blank=True, null=True)

    description   = models.TextField(null=True, blank=True)

    last_polled   = models.DateTimeField(blank=True, null=True)
    due_poll      = models.DateTimeField(default=datetime.datetime(1900, 1, 1)) # default to distant past to put new sources to front of queue
    etag          = models.CharField(max_length=255, blank=True, null=True)
    last_modified = models.CharField(max_length=255, blank=True, null=True) # just pass this back and forward between server and me , no need to parse

    last_result    = models.CharField(max_length=255,blank=True,null=True)
    interval       = models.PositiveIntegerField(default=400)
    last_success   = models.DateTimeField(blank=True, null=True)
    last_change    = models.DateTimeField(blank=True, null=True)
    live           = models.BooleanField(default=True)
    status_code    = models.PositiveIntegerField(default=0)
    last_302_url   = models.CharField(max_length=512, null=True, blank=True)
    last_302_start = models.DateTimeField(null=True, blank=True)

    max_index      = models.IntegerField(default=0)
    num_subs       = models.IntegerField(default=1)

    is_cloudflare  = models.BooleanField(default=False)


    def __str__(self):
        return str(self.display_name)


    @property
    def best_link(self):
        """the html link else hte feed link"""
        if not self.site_url:
            return self.feed_url
        return self.site_url


    @property
    def display_name(self) -> str:
        """The name to render"""
        if not self.name:
            return self.best_link
        return self.name


    @property
    def garden_style(self) -> str:
        """garden style css"""

        if not self.live:
            return "background-color:#ccc;"

        if self.last_change is None or self.last_success is None:
            return "background-color:#D00;color:white"

        dd = datetime.datetime.utcnow() - self.last_change

        days = int (dd.days / 2)
        col = max(255 - days, 0)

        css = f"background-color:#ff{col:02x}{col:02x}"

        if col < 128:
            css += ";color:white"

        return css


    @property
    def health_box(self) -> str:
        """health box css"""

        if not self.live:
            return "#ccc;"

        if self.last_change is None or self.last_success is None:
            return "#F00;"

        dd = datetime.datetime.utcnow() - self.last_change

        days = int(dd.days / 2)
        red = min(days, 255)
        green = max(0, 255 - days)

        return f"#{red:02x}{green:02x}00"



class Post(models.Model):
    """an entry in a feed"""

    source        = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='posts')
    title         = models.TextField(blank=True)
    body          = models.TextField()
    link          = models.CharField(max_length=512, blank=True, null=True)
    found         = models.DateTimeField(auto_now_add=True)
    created       = models.DateTimeField(db_index=True)
    guid          = models.CharField(max_length=512, blank=True, null=True, db_index=True)
    author        = models.CharField(max_length=255, blank=True, null=True)
    index         = models.IntegerField(db_index=True)
    image_url     = models.CharField(max_length=512, blank=True,null=True)


    @property
    def title_url_encoded(self) -> str:
        """
        encoded url for title
        """
        try:
            ret = urlencode({"X":self.title})

        except Exception: # pylint: disable=broad-exception-caught
            logging.exception("Failed to url encode title of post %s", self.id)
            return ""

        if len(ret) > 2:
            return ret[2:]
        return ret


    def __str__(self):
        return f"{self.source.display_name}: post {self.index}, {self.title}"


    class Meta:
        ordering = ["index"]



class Enclosure(models.Model):
    """
    What podcasts use to send their audio
    """

    post   = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='enclosures')
    length = models.IntegerField(default=0)
    href   = models.CharField(max_length=512)
    type   = models.CharField(max_length=256)
    medium = models.CharField(max_length=25, null=True, blank=True)
    description = models.CharField(max_length=512, null= True, blank=True)



class WebProxy(models.Model):
    """
    This class if for Cloudflare avoidance and contains a list of potential
    Web proxies that we can try, scraped from the internet
    """
    address = models.CharField(max_length=255)

    def __str__(self):
        return f"Proxy:{self.address}"
