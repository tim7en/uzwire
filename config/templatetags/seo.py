from __future__ import annotations

from django import template
from django.urls import translate_url


register = template.Library()


@register.simple_tag
def lang_url(request, lang_code: str) -> str:
    """Return absolute URL for the current path in a different language."""
    path = request.get_full_path() if request else "/"
    translated = translate_url(path, lang_code)
    if request:
        return request.build_absolute_uri(translated)
    return translated
