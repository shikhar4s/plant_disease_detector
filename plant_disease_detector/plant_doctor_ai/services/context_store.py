import secrets
from django.core.cache import cache


def store_context(user_id, kind, payload, ttl=900):
    context_id = secrets.token_urlsafe(18)
    cache.set(f'plantdoc-context:{user_id}:{kind}:{context_id}', payload, ttl)
    return context_id


def load_context(user_id, kind, context_id):
    if not context_id:
        return None
    return cache.get(f'plantdoc-context:{user_id}:{kind}:{context_id}')
