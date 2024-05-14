"""
Utilities for updateing rss feeds
"""
import time
import hashlib
import logging
import json
from random import choice
import datetime

import requests
import pyrfc3339
import feedparser

from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from feeds.models import Source, Enclosure, Entry, WebProxy


FEEDS_FORCE_UPDATE_SOURCE_FIELDS = getattr(settings, "FEEDS_FORCE_UPDATE_SOURCE_FIELDS", True)
logger = logging.getLogger('RefreshFeeds')


def get_agent(source_feed) -> str:
    """return the agent string for the given source"""

    if source_feed.is_cloudflare:
        agent = random_user_agent()
        logging.error("using agent: %s", agent)
    else:
        agent = f"{settings.FEEDS_USER_AGENT} (+{settings.FEEDS_SERVER}; Updater; {source_feed.num_subs} subscribers)"

    return agent



def random_user_agent() -> str:
    """return a random user agent"""

    return choice([
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393",
        "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)",
        "Mozilla/5.0 (iPad; CPU OS 8_4_1 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12H321 Safari/600.1.4",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (Linux; Android 5.0; SAMSUNG SM-N900 Build/LRX21V) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/2.1 Chrome/34.0.1847.76 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 6.0.1; SAMSUNG SM-G570Y Build/MMB29K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/4.0 Chrome/44.0.2403.133 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0"
    ])



def fix_relative(html, url):
    """ this is fucking cheesy """
    try:
        base = "/".join(url.split("/")[:3])

        html = html.replace("src='//", "src='http://")
        html = html.replace('src="//', 'src="http://')


        html = html.replace("src='/", f"src='{base}/")
        html = html.replace('src="/', f'src="{base}/')


        html = html.replace("href='//", "href='http://")
        html = html.replace('href="//', 'href="http://')


        html = html.replace("href='/", f"href='{base}/")
        html = html.replace('href="/', f'href="{base}/')

    except Exception:
        pass

    return html



def update_due_sources(max_feeds: int = 3) -> list:
    """
    Get the list of sources due for this update.

    ### Parameters:
    - max_feeds (int): the maximum number to return

    ### Returns
    - list of sources to update
    """
    due_sources = Source.objects.filter(due_poll__lt = timezone.now(), live = True)

    return due_sources.order_by("due_poll")[:max_feeds]



def update_feeds(max_feeds: int = 3):
    """
    Fetch all feeds ready for update
    """
    due_sources = update_due_sources(max_feeds = max_feeds)

    logger.info("Queue size is %s", due_sources.count())

    for src in due_sources:
        read_feed(src)

    # kill shit proxies
    WebProxy.objects.filter(address='X').delete()



def read_feed(source_feed: Source):
    """
    Fetch a feed, update the management fields
    """
    logger.info('updating feed: %s', str(Source))

    old_interval = source_feed.interval
    was302 = False

    source_feed.last_polled = timezone.now()

    agent = get_agent(source_feed)

    headers = { "User-Agent": agent } #identify ourselves
    proxies = {}
    proxy = None

    feed_url = source_feed.feed_url
    if source_feed.is_cloudflare : # Fuck you !

        if settings.FEEDS_CLOUDFLARE_WORKER:
            feed_url = f"{settings.FEEDS_CLOUDFLARE_WORKER}/read/?target={feed_url}"
        else:
            try:
                proxy = get_proxy()

                if proxy.address != "X":

                    proxies = {
                      'http': proxy.address,
                      'https': proxy.address,
                    }
            except Exception:
                pass

    if source_feed.etag:
        headers["If-None-Match"] = str(source_feed.etag)
    if source_feed.last_modified:
        headers["If-Modified-Since"] = str(source_feed.last_modified)

    ret = None
    try:
        ret = requests.get(
            feed_url,
            headers=headers,
            verify=False,
            allow_redirects=False,
            timeout=20,
            proxies=proxies,
            )

        source_feed.status_code = ret.status_code
        source_feed.last_result = "Unhandled Case"
        logger.info(str(ret))

    except Exception as ex:
        source_feed.last_result = ("Fetch error:" + str(ex))[:255]
        source_feed.status_code = 0
        logger.exception("Fetch error, Burning the proxy")

        if proxy:
            source_feed.last_result = "Proxy failed. Next retry will use new proxy"
            source_feed.status_code = 1  # this will stop us increasing the interval
            source_feed.interval /= 2
            proxy.delete()

    if ret is None and source_feed.status_code == 1:   # er ??
        pass

    elif ret is None or source_feed.status_code == 0:
        source_feed.interval += 120

    elif ret.status_code < 200 or ret.status_code >= 500:
        #errors, impossible return codes
        source_feed.interval += 120
        source_feed.last_result = f"Server error fetching feed ({ret.status_code})"

    elif ret.status_code == 404:
        #not found
        source_feed.interval += 120
        source_feed.last_result = "The feed could not be found"

    elif ret.status_code == 410: # Gone
        source_feed.last_result = "Feed has gone away and says it isn't coming back."
        source_feed.live = False

    elif ret.status_code == 403:  # Forbidden
        if "Cloudflare" in ret.text or ("Server" in ret.headers and "cloudflare" in ret.headers["Server"]):

            if source_feed.is_cloudflare and proxy is not None:
                # we are already proxied - this proxy on cloudflare's shit list too?
                proxy.delete()
                logger.info("Proxy seemed to also be blocked, burning")
                source_feed.interval /= 2
                source_feed.last_result = "Proxy kind of worked but still got cloudflared."
            else:
                source_feed.is_cloudflare = True
                source_feed.last_result = "Blocked by Cloudflare (grr)"
        else:
            source_feed.last_result = "Feed is no longer accessible."
            source_feed.live = False

    elif ret.status_code >= 400 and ret.status_code < 500:
        #treat as bad request
        source_feed.live = False
        source_feed.last_result = "Bad request (%d)" % ret.status_code

    elif ret.status_code == 304:
        #not modified
        source_feed.interval += 10
        source_feed.last_result = "Not modified"
        source_feed.last_success = timezone.now()

        if source_feed.last_success and (timezone.now() - source_feed.last_success).days > 7:
            source_feed.last_result = "Clearing etag/last modified due to lack of changes"
            source_feed.etag = None
            source_feed.last_modified = None

    elif ret.status_code == 301 or ret.status_code == 308: #permenant redirect
        new_url = ""
        try:
            if "Location" in ret.headers:
                new_url = ret.headers["Location"]

                if new_url[0] == "/":
                    #find the domain from the feed

                    base = "/".join(source_feed.feed_url.split("/")[:3])

                    new_url = base + new_url

                source_feed.feed_url = new_url
                source_feed.last_result = "Moved"
                source_feed.save(update_fields=["feed_url", "last_result"])

            else:
                source_feed.last_result = "Feed has moved but no location provided"

        except Exception:
            logger.exception("Error redirecting.")
            source_feed.last_result = ("Error redirecting feed to " + new_url)[:255]

    elif ret.status_code == 302 or ret.status_code == 303 or ret.status_code == 307: #Temporary redirect
        new_url = ""
        was302 = True
        try:
            new_url = ret.headers["Location"]

            if new_url[0] == "/":
                #find the domain from the feed
                start = source_feed.feed_url[:8]
                end = source_feed.feed_url[8:]
                if end.find("/") >= 0:
                    end = end[:end.find("/")]

                new_url = start + end + new_url

            ret = requests.get(new_url, headers=headers, allow_redirects=True, timeout=20, verify=False)
            source_feed.status_code = ret.status_code
            source_feed.last_result = ("Temporary Redirect to " + new_url)[:255]

            if source_feed.last_302_url == new_url:
                #this is where we 302'd to last time
                td = timezone.now() - source_feed.last_302_start
                if td.days > 60:
                    source_feed.feed_url = new_url
                    source_feed.last_302_url = " "
                    source_feed.last_302_start = None
                    source_feed.last_result = ("Permanent Redirect to " + new_url)[:255]

                    source_feed.save(update_fields=["feed_url", "last_result", "last_302_url", "last_302_start"])

                else:
                    source_feed.last_result = ("Temporary Redirect to " + new_url + " since " + source_feed.last_302_start.strftime("%d %B"))[:255]

            else:
                source_feed.last_302_url = new_url
                source_feed.last_302_start = timezone.now()

                source_feed.last_result = ("Temporary Redirect to " + new_url + " since " + source_feed.last_302_start.strftime("%d %B"))[:255]

        except Exception as ex:
            source_feed.last_result = ("Failed Redirection to " + new_url +  " " + str(ex))[:255]
            source_feed.interval += 60

    #NOT ELIF, WE HAVE TO START THE IF AGAIN TO COPE WTIH 302
    if ret and ret.status_code >= 200 and ret.status_code < 300: #now we are not following redirects 302,303 and so forth are going to fail here, but what the hell :)

        # great!
        ok = True
        changed = False

        if was302:
            source_feed.etag = None
            source_feed.last_modified = None
        else:
            try:
                source_feed.etag = ret.headers["etag"]
            except Exception as ex:
                source_feed.etag = None
            try:
                source_feed.last_modified = ret.headers["Last-Modified"]
            except Exception as ex:
                source_feed.last_modified = None

        logger.info("\netag:%s\nLast Mod:%s\n\n", source_feed.etag, source_feed.last_modified)

        content_type = "Not Set"
        if "Content-Type" in ret.headers:
            content_type = ret.headers["Content-Type"]

        # parse and update the posts
        (ok,changed) = import_feed(source_feed=source_feed, feed_body=ret.content, content_type=content_type)

        if ok and changed:
            source_feed.interval /= 2
            source_feed.last_result = " OK (updated)" #and temporary redirects
            source_feed.last_change = timezone.now()

        elif ok:
            source_feed.last_result = " OK"
            source_feed.interval += 20 # we slow down feeds a little more that don't send headers we can use

        else: #not OK
            source_feed.interval += 120

    if source_feed.interval < 60:
        source_feed.interval = 60 # no less than 1 hour
    if source_feed.interval > (60 * 24):
        source_feed.interval = (60 * 24) # no more than a day

    logger.info("Updating source_feed.interval from %d to %d\n", old_interval, source_feed.interval)
    source_feed.due_poll = timezone.now() + datetime.timedelta(minutes=source_feed.interval)
    source_feed.save(update_fields=[
                "due_poll", "interval", "last_result",
                "last_modified", "etag", "last_302_start",
                "last_302_url", "last_success", "live",
                "status_code", "max_index", "is_cloudflare",
                "last_change",
            ])



def import_feed(source_feed, feed_body, content_type):

    ok = False
    changed = False

    if "xml" in content_type or feed_body[0:1] == b"<":
        ok, changed = parse_feed_xml(source_feed, feed_body)
    elif "json" in content_type or feed_body[0:1] == b"{":
        ok, changed = parse_feed_json(source_feed, str(feed_body, "utf-8"))
    else:
        ok = False
        source_feed.last_result = "Unknown Feed Type: " + content_type

    if ok and changed:
        source_feed.last_result = " OK (updated)" #and temporary redirects
        source_feed.last_change = timezone.now()

        idx = source_feed.max_index
        # give indices to posts based on created date
        posts = Entry.objects.filter(Q(source=source_feed) & Q(index=0)).order_by("created")
        for p in posts:
            idx += 1
            p.index = idx
            p.save(update_fields=["index"])

        source_feed.max_index = idx

    return (ok, changed)



def parse_feed_xml(source_feed: Source, feed_content) -> tuple[bool, bool]:

    ok = True
    changed = False
    is_first = not source_feed.posts.all().count()

    #output.write(ret.content)
    try:
        feed_data = feedparser.parse(feed_content) #need to start checking feed parser errors here
    except Exception:
        logger.exception('Feed Parse Error')

        source_feed.last_result = "Feed Parse Error"
        source_feed.save(update_fields=["last_result"])

        return False, False


    entries = feed_data['entries']
    if len(entries):
        source_feed.last_success = timezone.now() #in case we start auto unsubscribing long dead feeds
    else:
        source_feed.last_result = "Feed is empty"
        source_feed.save(update_fields=["last_success", "last_result"])
        return False, False

    if not source_feed.name or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
        source_feed.name = feed_data.feed.title

    if not source_feed.site_url or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
        source_feed.site_url = feed_data.feed.link

    if not source_feed.image_url or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
        source_feed.image_url = feed_data.feed.image.href

    # either of these is fine, prefer description over summary
    # also feedparser will give us itunes:summary etc if there
    if not source_feed.description or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
        source_feed.description = feed_data.feed.summary
        source_feed.description = feed_data.feed.description

    source_feed.save()

    #output.write(entries)
    entries.reverse() # Entries are typically in reverse chronological order - put them in right order
    for entry in entries:
        parse_entry_xml(source_feed, entry)


def parse_entry_xml(source_feed, entry_data):
            # we are going to take the longest
            body = ""

            if hasattr(entry, "summary"):
                if len(entry.summary) > len(body):
                    body = entry.summary

            if hasattr(entry, "summary_detail"):
                if len(entry.summary_detail.value) >= len(body):
                    body = entry.summary_detail.value

            if hasattr(entry, "description"):
                if len(entry.description) >= len(body):
                    body = entry.description

            body = fix_relative(body, source_feed.site_url)

            try:
                guid = entry.guid
            except Exception:
                try:
                    guid = entry.link
                except Exception:
                    md5 = hashlib.md5()
                    md5.update(body.encode("utf-8"))
                    guid = md5.hexdigest()

            try:
                post  = Entry.objects.filter(source=source_feed).filter(guid=guid)[0]
                logger.info("EXISTING %s", guid)

            except Exception:
                logger.info("NEW %s", guid)
                post = Entry(index=0, body=" ", title="", guid=guid)
                post.found = timezone.now()
                changed = True


                try:
                    post.created  = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                except Exception:
                    try:
                        post.created  = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                    except Exception:
                        logger.exception("CREATED ERROR")
                        post.created  = timezone.now()

                post.source = source_feed
                post.save()

            try:
                post.title = entry.title
                post.save(update_fields=["title"])
            except Exception:
                logger.exception("Title error")

            try:
                post.link = entry.link
                post.save(update_fields=["link"])
            except Exception:
                logger.exception("Link error")

            try:
                post.image_url = entry.image.href
                post.save(update_fields=["image_url"])
            except Exception:
                pass

            try:
                post.author = entry.author
                post.save(update_fields=["author"])
            except Exception:
                logger.exception('Author error')
                post.author = ""

            try:
                post.body = body
                post.save(update_fields=["body"])
                # output.write(p.body)
            except Exception:
                logger.exception('Body Error')

            try:
                seen_files = []

                post_files = entry["enclosures"]
                non_dupes = []

                # find any files in media_content that aren't already declared as enclosures
                if "media_content" in entry:
                    for enclosure in entry["media_content"]:
                        found = False
                        for ff in post_files:
                            if ff["href"] == enclosure["url"]:
                                found = True
                                break
                        if not found:
                            non_dupes.append(enclosure)

                    post_files += non_dupes

                for enclosure in list(post.enclosures.all()):
                    # check existing enclosure is still there
                    found_enclosure = False
                    for post_file in post_files:

                        href = "href"
                        if href not in post_file:
                            href = "url"

                        length = "length"
                        if length not in post_file:
                            length = "filesize"

                        if post_file[href] == enclosure.href and enclosure.href not in seen_files:
                            found_enclosure = True

                            try:
                                enclosure.length = int(post_file[length])
                            except Exception:
                                enclosure.length = 0

                            try:
                                file_type = post_file["type"]
                            except Exception:
                                file_type = "audio/mpeg"  # we are assuming podcasts here but that's probably not safe

                            enclosure.type = file_type

                            if "medium" in post_file:
                                enclosure.medium = post_file["medium"]

                            if "description" in post_file:
                                enclosure.description = post_file["description"][:512]

                            enclosure.save()
                            break
                    if not found_enclosure:
                        enclosure.delete()
                    seen_files.append(enclosure.href)

                for post_file in post_files:

                    href = "href"
                    if href not in post_file:
                        href = "url"

                    length = "length"
                    if length not in post_file:
                        length = "filesize"

                    try:
                        if post_file[href] not in seen_files:

                            try:
                                length = int(post_file[length])
                            except Exception:
                                length = 0

                            try:
                                file_type = post_file["type"]
                            except Exception:
                                file_type = "audio/mpeg"

                            enclosure = Enclosure(post=post, href=post_file[href], length=length, type=file_type)

                            if "medium" in post_file:
                                enclosure.medium = post_file["medium"]

                            if "description" in post_file:
                                enclosure.description = post_file["description"][:512]

                            enclosure.save()
                    except Exception:
                        pass

            except Exception:
                logger.exception("No enclosures")

    if is_first and source_feed.posts.all().count() > 0:
        # If this is the first time we have parsed this
        # then see if it's paginated and go back through its history
        agent = get_agent(source_feed)
        headers = { "User-Agent": agent } #identify ourselves
        keep_going = True
        while keep_going:
            keep_going = False  # assume were stopping unless we find a next link
            if hasattr(feed_data.feed, 'links'):
                for link in feed_data.feed.links:
                    if 'rel' in link and link['rel'] == "next":
                        ret = requests.get(link['href'], headers=headers, verify=False, allow_redirects=True, timeout=20)
                        (pok, pchanged) = parse_feed_xml(source_feed, ret.content)
                        # print(link['href'])
                        # print((pok, pchanged))
                        feed_data = feedparser.parse(ret.content)  # rebase the loop on this feed version
                        keep_going = True

    return (ok,changed)


def parse_feed_json(source_feed: Source, feed_content) -> tuple[bool, bool]:

    ok = True
    changed = False

    try:
        content = json.loads(feed_content)
        entries = content['items']
        if len(entries):
            source_feed.last_success = timezone.now() #in case we start auto unsubscribing long dead feeds
        else:
            source_feed.last_result = "Feed is empty"
            source_feed.interval += 120
            ok = False

        source_feed.save(update_fields=["last_success", "last_result"])

    except Exception:
        source_feed.last_result = "Feed Parse Error"
        entries = []
        source_feed.interval += 120
        ok = False

    if ok:

        if "expired" in content and content["expired"]:
            # This feed says it is done
            # TODO: permanently disable
            # for now source_feed.interval to max
            source_feed.interval = 24 * 3 * 60
            source_feed.last_result = "This feed has expired"
            return (False, False)

        if not source_feed.name or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
            try:
                source_feed.name = feedparser.sanitizer._sanitize_html(content['title'], "utf-8", 'text/html')
                source_feed.save(update_fields=["name"])
            except Exception:
                pass

        if not source_feed.site_url or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
            try:
                source_feed.site_url = content["home_page_url"]
                source_feed.save(update_fields=["site_url"])
            except Exception:
                pass

        if not source_feed.description or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
            try:
                if "description" in content:
                    source_feed.description = feedparser.sanitizer._sanitize_html(content["description"], "utf-8", 'text/html')
                    source_feed.save(update_fields=["description"])
            except Exception:
                pass

        if not source_feed.image_url or FEEDS_FORCE_UPDATE_SOURCE_FIELDS:
            try:
                if "icon" in content:
                    source_feed.image_url = content["icon"]
                    source_feed.save(update_fields=["image_url"])
            except Exception:
                pass

        #output.write(entries)
        entries.reverse() # Entries are typically in reverse chronological order - put them in right order
        for entry in entries:
            body = " "
            if "content_text" in entry:
                body = entry["content_text"]
            if "content_html" in entry:
                body = entry["content_html"] # prefer html over text

            body = fix_relative(body,source_feed.site_url)

            try:
                guid = entry["id"]
            except Exception:
                try:
                    guid = entry["url"]
                except Exception:
                    md5 = hashlib.md5()
                    md5.update(body.encode("utf-8"))
                    guid = md5.hexdigest()

            try:
                post  = Entry.objects.filter(source=source_feed).filter(guid=guid)[0]
                logger.info("EXISTING %s", guid)

            except Exception:
                logger.info("NEW %s", guid)
                post = Entry(index=0, body=' ')
                post.found = timezone.now()
                changed = True
                post.source = source_feed

            try:
                title = entry["title"]
            except Exception:
                title = ""

            # borrow the RSS parser's sanitizer
            body = feedparser.sanitizer._sanitize_html(body, "utf-8", 'text/html') # TODO: validate charset ??
            title = feedparser.sanitizer._sanitize_html(title, "utf-8", 'text/html') # TODO: validate charset ??
            # no other fields are ever marked as |safe in the templates

            if "banner_image" in entry:
                post.image_url = entry["banner_image"]

            if "image" in entry:
                post.image_url = entry["image"]

            try:
                post.link = entry["url"]
            except Exception:
                logger.exception('Link Error')
                post.link = ''

            post.title = title

            try:
                post.created  = pyrfc3339.parse(entry["date_published"])
            except Exception:
                logger.exception("CREATED ERROR")
                post.created  = timezone.now()

            post.guid = guid
            try:
                post.author = entry["author"]
            except Exception:
                logger.exception('Author Error')
                post.author = ""

            post.save()

            try:
                seen_files = []
                for enclosure in list(post.enclosures.all()):
                    # check existing enclosure is still there
                    found_enclosure = False
                    if "attachments" in entry:
                        for pe in entry["attachments"]:

                            if pe["url"] == enclosure.href and enclosure.href not in seen_files:
                                found_enclosure = True

                                try:
                                    enclosure.length = int(pe["size_in_bytes"])
                                except:
                                    enclosure.length = 0

                                try:
                                    type = pe["mime_type"]
                                except:
                                    type = "audio/mpeg"  # we are assuming podcasts here but that's probably not safe

                                enclosure.type = type
                                enclosure.save()
                                break
                    if not found_enclosure:
                        enclosure.delete()
                    seen_files.append(enclosure.href)

                if "attachments" in entry:
                    for pe in entry["attachments"]:

                        try:
                            if pe["url"] not in seen_files:

                                try:
                                    length = int(pe["size_in_bytes"])
                                except Exception:
                                    length = 0

                                try:
                                    type = pe["mime_type"]
                                except Exception:
                                    type = "audio/mpeg"

                                enclosure = Enclosure(post=post , href=pe["url"], length=length, type=type)
                                enclosure.save()
                        except Exception:
                            pass

            except Exception:
                logger.exception('')

            try:
                post.body = body
                post.save()
                # output.write(p.body)

            except Exception:
                logger.exception('')

    return (ok,changed)



def test_feed(source, cache=False):

    headers = { "User-Agent": get_agent(source)  } #identify ourselves and also stop our requests getting picked up by any cache

    if cache:
        if source.etag:
            headers["If-None-Match"] = str(source.etag)
        if source.last_modified:
            headers["If-Modified-Since"] = str(source.last_modified)
    else:
        headers["Cache-Control"] = "no-cache,max-age=0"
        headers["Pragma"] = "no-cache"

    logger.info(str(headers))

    ret = requests.get(source.feed_url, headers=headers, allow_redirects=False, verify=False, timeout=20)

    logger.info(str(ret))

    logger.info(ret.text)



def get_proxy():

    proxy = WebProxy.objects.first()

    if proxy is None:
        find_proxies()
        proxy = WebProxy.objects.first()

    logger.info("Proxy: %s", proxy)

    return proxy



def find_proxies():

    logger.info("Looking for proxies")

    try:
        req = requests.get("https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list.txt", timeout=30)
        if req.status_code == 200:
            text = req.text

            text = text.split("\n")

            # remove header
            text = text[4:]

            for item in text:
                if ":" in item:
                    item = item.split(" ")[0]
                    WebProxy(address=item).save()

    except Exception:
        logging.exception("Proxy scrape error")

    if WebProxy.objects.count() == 0:
        # something went wrong.
        # to stop infinite loops we will insert duff proxys now
        for _ in range(20):
            WebProxy(address="X").save()
        logger.info("No proxies found.")
