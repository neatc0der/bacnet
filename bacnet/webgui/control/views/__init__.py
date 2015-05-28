"""
Views Module
------------

This module contains all descriptions of web access interfaces.
"""

from django.core.urlresolvers import resolve
from django.shortcuts import render
from django.utils.translation import ugettext as _


def get_crumb_name(link):
    """
    This function provides the breadcrumb name for a link

    :param link: link
    :return: breadcrumb name
    """

    # return breadcrumb name
    return _(resolve(link).url_name)


def breadcrumbs(path):
    """
    This function provides the breadcrumbs for a path.

    :param path: path
    :return: list of breadcrumbs
    """

    # initialize breadcrumbs
    crumbs = []

    # split the path
    steps = path.split('/')[:-1]

    # loop through split path
    for i in xrange(len(steps)):
        # create link for each step
        link = '/'.join(steps[:i+1]) + '/'

        # add links and name to each step
        crumbs.append((
            get_crumb_name(link),
            link,
            i == len(steps) - 1,
        ))

    # return breadcrumbs
    return crumbs


def control_views_render(request, template_file, arg_dict={}, local=True):
    """
    This function provides general rendering for all templates.

    :param request: Django request
    :param template_file: template filename
    :param arg_dict: arguments
    :param local: is local template
    :return: HTTP response
    """

    # initialize symbol
    symbol = '?'

    # get request path
    path = arg_dict.get('path') or request.path

    # check if path contains parameters
    if "?" in path:
        # change symbol
        symbol = '&'

    # define default arguments
    default_dict = {
        'symbol': symbol,
        'request': request,
        'breadcrumbs': breadcrumbs(request.path),
    }
    default_dict.update(arg_dict)

    # check if file is local
    if local:
        # append app path to template filename
        template_file = 'control/' + template_file

    # return rendered template
    return render(request, template_file, default_dict)


def index(request):
    """
    This function provides the index page of the project.

    :param request: Django request
    :return: HTTP response
    """

    # return rendered HTTP response
    return control_views_render(request, 'index.html')
