from __future__ import annotations

from ...tools.web_search import do_search, get_search_message
from ...Provider.search.CachedSearch import search, SearchResults

__all__ = ["SearchResults", "search", "do_search", "get_search_message"]