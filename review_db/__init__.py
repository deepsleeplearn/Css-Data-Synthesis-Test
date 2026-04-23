__all__ = [
    "fetch_manual_test_reviews",
    "fetch_generated_dialogues",
    "fetch_rewrite_reviews",
]


def fetch_manual_test_reviews(*args, **kwargs):
    from .fetch_reviews import fetch_manual_test_reviews as _fetch_manual_test_reviews

    return _fetch_manual_test_reviews(*args, **kwargs)


def fetch_generated_dialogues(*args, **kwargs):
    from .fetch_generated import fetch_generated_dialogues as _fetch_generated_dialogues

    return _fetch_generated_dialogues(*args, **kwargs)


def fetch_rewrite_reviews(*args, **kwargs):
    from .fetch_rewrite_reviews import fetch_rewrite_reviews as _fetch_rewrite_reviews

    return _fetch_rewrite_reviews(*args, **kwargs)
