
# Django Feed Reader

This is a simple Django module to allow you subscribe to RSS (and other) feeds.

This app has no UI, it just reads and stores the feeds for you to use as you see fit.

This app builds on top of the FeedParser library to provide feed management, storage, scheduling etc.

## Features

* Consumes RSS, Atom and JSONFeed feeds.  
* Parses feeds liberally to try and accomodate simple errors.
* Will attempt to bypass Cloudflare protection of feeds 
* Supports enclosure (podcast) discovery
* Automatic feed scheduling based on frequency of updates


## Installation

`django-feed-reader` is written in Python 3 and supports Django 2.2+

1. `pip install django-feed-reader`
2. Add `feeds` to your `INSTALLED_APPS`
3. Setup some values in `settings.py` so that your feed reader politely announces itself to servers:
   * Set `FEEDS_USER_AGENT` to the name and (optionally version) of your service e.g. `"ExampleFeeder/1.2"`
   * Set `FEEDS_SERVER` to preferred web address of your service so that feed hosts can locate you if required e.g. `https://example.com`
4. Set `FEEDS_FORCE_UPDATE_SOURCE_FIELDS` to False to only update source fields (like name and description) when they are empty.
5. Setup a mechanism to periodically refresh the feeds (see below)

# Models

## Source

A feed is represented by a `Source` object which has (among other things) a `feed_url`.

| Field | Type | Description |
| ----------- | ----------- |  ----------- |
| name | models.CharField(max_length=255, blank=True, null=True) | The name of the source. This gets defined on source creation and does not get updated by the rss feed query
| title | models.CharField(max_length=255, blank=True, null=True) | the title of the feed as given by the feed query
| subtitle | models.TextField(max_length=255, blank=True, null=True) |
| site_url | models.URLField(max_length=255, blank=True, null=True) | A url to the source website, not the rss feed
| feed_url | models.URLField(max_length=512, unique=True) # href | The rss feed url
| image_url | models.URLField(max_length=512, blank=True, null=True) | A url to an image for use as the feed thumbnail
| icon_url | models.URLField(max_length=512, blank=True, null=True) | A url to an image for use as the feed icon
| author | models.CharField(max_length=255, blank=True, null=True) | The author name
| description | models.TextField(null=True, blank=True) | The feed description

The above fields are the fields ment for display, many more exist for use in tracking when to query the feed next. See models.py for more information.

## Entries
`Source`s have `Entry`s which contain the content.

| Field | Type | Description |
| ----------- | ----------- |  ----------- |
| source      | models.ForeignKey(Source, on_delete=models.CASCADE, related_name='entries') | Forign key to the Source
| body        | models.TextField() | Text for the body of the entry
| title       | models.TextField(blank=True) | The entry title
| link        | models.CharField(max_length=512, blank=True, null=True) | A url to the entry on the original site
| created     | models.DateTimeField(db_index=True, default=now) | Creation timestamp
| guid        | models.CharField(max_length=512, blank=True, null=True, db_index=True) | unique entry id
| author      | models.CharField(max_length=255, blank=True, null=True) | The authors name
| image_url   | models.CharField(max_length=512, blank=True, null=True) | A url to an image to be used as the entry thumbnail
| found       | models.DateTimeField(auto_now_add=True) | A timestamp of when django_feed_reader's polling routine found it

## Enclosures

`Entry`s may have `Enclosure`s which are attached files, eg: what podcasts use to send their audio. This module does not download enclosures, if you want to do that you will need to do it in your project using the url provided.

| Field | Type | Description |
| ----------- | ----------- |  ----------- |
| entry | models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='enclosures') | Forign key to it's source Entry
| length | models.IntegerField(default=0) | how long is this media
| href | models.CharField(max_length=512) | The url link to the media
| type | models.CharField(max_length=256) | a string describing the media type: "audio", "vidio", "youtube", etc
| medium | models.CharField(max_length=25, null=True, blank=True) | file extention
| description | models.CharField(max_length=512, null= True, blank=True) | Text description of the media


## Refreshing feeds

To conserve resources with large feed lists, the app will adjust how often it polls feeds based on how often they are updated.  The fastest it will poll a feed is every hour. The slowest it will poll is every 24 hours.

Feeds that don't get updated are polled progressively more slowly until the 24 hour limit is reached.  When a feed changes, its polling frequency increases.

You will need to decided how and when to run the poller.  When the poller runs, it checks all feeds that are currently due.  The ideal frequency to run it is every 5 - 10 minutes.

### Polling with cron.

Set up a job that calls `python manage.py refreshfeeds` on your desired schedule.

Be careful to ensure you're running out of the correct directory and with the correct python environment.

### Polling with celery

Create a new celery task and schedule in your app (see the celery documentation for details).  Your `tasks.py` should look something like this:

```python

from celery import shared_task
from feeds.utils import update_feeds

@shared_task
def get_those_feeds():
    
    # the number is the max number of feeds to poll in one go
    update_feeds(30)  
    
```

## Tracking subscribers and read/unread state of feeds

The app does not (currently) track the read/unread state of posts within a feed.  That will need doing in your project according to your needs. 

The app assumes that each feed only has one subscriber that is the project itself.  If your project can allow personal subscriptions for individual users, you can let the app know on per feed basis how many subscribers it has by settings `num_subs` on a `Source` object.
The app will then report this via the user agent to the feed source for analytics purposes.


### Dealing with Cloudflare

Depending on where you run your server, you may run into problems with Cloudflare's web captcha.  Plenty of sites out there set up their Cloudflare to have default security on their RSS feed and this can block server-side RSS readers.

It's a huge pain and affects lots of self-hosted RSS readers. Seriously, Google it.

`django-feed-reader` will do it's utmost to get these feeds anyway through the judicious use of public proxy servers, but is haphazard and you cannot rely on the scheduling of such feeds.

Feeds blocked by Cloudflare will have the `is_cloudflare` flag set on their `Source` and will update on a best-efforts basis.

 




