"""
Fetch the feed date
"""
import feedparser


def query_source(url: str) -> feedparser.util.FeedParserDict:
    """
    Retrieve the feed data from the given url

    ### Parameters
    - url: string url of the feed

    ### Returns
    - feed data
    """
    return feedparser.parse(url)
