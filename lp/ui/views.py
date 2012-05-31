from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from ui import get_bib_data


def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'settings': settings,
        })

def item(request, bibid):
    try:
        bib_data = get_bib_data(bibid=bibid)
        return render(request, 'item.html', {'bib_data':bib_data})
    except Exception, e:
        raise Http404('Exception: %s' %e)
