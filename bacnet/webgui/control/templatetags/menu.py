# pylint: disable=invalid-name

"""
Menu Templatetags Module
------------------------

This module contains important descriptions for the menu.
"""


from django import template
from django.core.urlresolvers import reverse

from urllib import unquote


register = template.Library()


@register.simple_tag(takes_context=True)
def url_attr(context, label, attribute, exact=False, **kwargs):
    """
    This function marks links depending on the request's path.
    """

    request = context["request"]
    path = request.path

    if (not exact and path.lower().startswith(unquote(reverse(label, kwargs=kwargs)).lower())) or \
        path.lower() == unicode(unquote(reverse(label, kwargs=kwargs))).lower():
        return attribute

    return ""
