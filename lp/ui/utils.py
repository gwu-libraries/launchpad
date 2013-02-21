import urllib


def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


def openurl_dict(params):
    """Split openurl params into a useful structure"""
    p = {}
    for k, v in dict(params).items():
        p[k] = ','.join(v)
    d = {'params':  p}
    d['query_string'] = '&'.join(['%s=%s' % (k, v) for k, v
        in params.items()])
    d['query_string_encoded'] = urllib.urlencode(params)
    return d
