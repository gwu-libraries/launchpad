from django.conf import settings
from django.shortcuts import render


def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'settings': settings,
        })
