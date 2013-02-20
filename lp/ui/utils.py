def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj
