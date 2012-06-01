from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect
from ui import get_bib_data, get_bibid_from_isbn, get_bibid_from_issn, get_bibid_from_oclc


def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'settings': settings,
        })

def item(request, bibid):
    bib_data = get_bib_data(bibid=bibid)
    return render(request, 'item.html', {'bib_data':bib_data})

def isbn(request, isbn):
    bibid = get_bibid_from_isbn(isbn)
    return redirect('item', bibid=bibid)

def issn(request, issn):
    bibid = get_bibid_from_issn(issn)
    return redirect('item', bibid=bibid)

def oclc(request, oclc='', ocn='', digit=''):
    bibid = get_bibid_from_oclc(oclc)
    return redirect('item', bibid=bibid)
