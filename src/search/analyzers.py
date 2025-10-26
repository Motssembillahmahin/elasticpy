"""
Analyzers control text processing:
1. Character filters: Clean text (remove HTML, patterns)
2. Tokenizer: Split text into tokens
3. Token filters: Modify tokens (lowercase, stemming, synonyms)
"""

CUSTOM_ANALYZERS = {
    "autocomplete_analyzer": {
        "type": "custom",
        "tokenizer": "standard",
        "filter": ["lowercase", "autocomplete_filter"],
    },
    "autocomplete_search_analyzer": {
        "type": "custom",
        "tokenizer": "standard",
        "filter": ["lowercase"],
    },
}

CUSTOM_FILTERS = {
    "autocomplete_filter": {"type": "edge_ngram", "min_gram": 2, "max_gram": 20}
}
