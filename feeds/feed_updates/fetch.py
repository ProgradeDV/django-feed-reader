"""
Fetch the feed data
"""
import feedparser


def query_source(url: str) -> feedparser.util.FeedParserDict:
    """
    Retrieve the feed data from the given url

    ### Parameters
    - url: string url of the feed

    ### Returns
    - FeedParserDict: feed data
    """
    return feedparser.parse(url)
