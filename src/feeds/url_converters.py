"""functions for converting links related to a feed to the feed url"""
from urllib.parse import parse_qs, ParseResult
import re
import requests
from bs4 import BeautifulSoup


def get_rss_url(parsed_url:ParseResult) -> str:
    """convert the given url into the corisponding rss url"""
    if parsed_url.netloc == 'www.youtube.com':
        return convert_youtube_channel(parsed_url)

    if parsed_url.netloc == 'bsky.app':
        return convert_bluesky_account(parsed_url)

    if parsed_url.netloc == 'www.reddit.com':
        return convert_subreddit(parsed_url)

    return parsed_url.geturl()


def convert_youtube_channel(parsed_url:ParseResult) -> str:
    """find the rss feed link for a given youtube channel"""
    if re.match(r"^/@\w+$", parsed_url.path): # mathces "/@{channelname_name}..."
        # remove any parameters
        parsed_url._replace(query='')

        # pull the url
        page = requests.get(parsed_url.geturl(), timeout=5)
        soup = BeautifulSoup(page.content, "html.parser")
        link = soup.find(title='RSS')
        return link['href']

    if 'list' in (query := parse_qs(parsed_url.query)):
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={query['list'][0]}"

    raise ValueError('Unreconized link')


def convert_bluesky_account(parsed_url:ParseResult) -> str:
    """find the rss link for a given bluesky account"""
    assert re.match(r"^/profile/\w+\.\w+\.\w+$", parsed_url.path) # mathces "/profile/{profile_name}"

    new_path = parsed_url.path + '/rss'

    return parsed_url._replace(path=new_path).geturl()


def convert_subreddit(parsed_url:ParseResult) -> str:
    """find the rss link for a given subredit"""
    assert re.match(r"^/r/\w+/$", parsed_url.path) # mathces "/r/{subreddit_name}/"

    new_path = parsed_url.path[:-1] + '.rss'

    return parsed_url._replace(path=new_path).geturl()
