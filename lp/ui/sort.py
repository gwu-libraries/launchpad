from lp import settings


def splitsort(holdings_list):
    ours, theirs, shared = [], [], []
    for holding in holdings_list:
        if holding['LIBRARY_NAME'] == settings.PREF_LIB:
            ours.append(holding)
        elif holding['LIBRARY_NAME'] in (settings.SHARED_LIBRARY_NAMES):
            shared.append(holding)
        else:
            theirs.append(holding)
    return ours, theirs, shared


def libsort(holdings_list):
    return sorted(holdings_list, key=lambda holding: holding['LIBRARY_NAME'])


def holdsort(holdings_list):
    return sorted(holdings_list,
        key=lambda holding: holding.get('LOCATION_NAME', ''))


def availsort(holdings_list):
    top, remainder, bottom = [], [], []
    for holding in holdings_list:
        if holding.get('ITEMS', []):
            topitems, remainderitems = [], []
            for item in holding['ITEMS']:
                if (item.get('ITEM_STATUS', '') == 1 or
                    item.get('ITEM_STATUS_DESC', '') == 'Not Charged'):
                    topitems.append(item)
                else:
                    remainderitems.append(item)
            holding['ITEMS'] = topitems + remainderitems
        try:
            if holding.get('LIBRARY_NAME', '') in settings.INELIGIBLE_LIBRARIES:
                bottom.append(holding)
            elif (holding.get('AVAILABILITY', {}).get('ITEM_STATUS') == 1):
                top.append(holding)
            else:
                remainder.append(holding)
        except KeyError:
            remainder.append(holding)
    return top + remainder + bottom


def _is_electronic(holding):
    try:
        if holding['ELECTRONIC_DATA']['LINK856U']:
            return True
        return False
    except KeyError:
        return False


def numstrip(num):
    if num:
        newnum = ''
        for char in num:
            if char in '0123456789':
                newnum += char
            elif newnum:
                break
        if newnum:
            return int(newnum)


def enumsort(holdings_list):
    for holding in holdings_list:
        if holding.get('ITEMS', None):
            holding['ITEMS'] = sorted(holding['ITEMS'],
                key=lambda item: numstrip(item['ITEM_ENUM']))
    return holdings_list


def callnumsort(holdings_list):
    for holding in holdings_list:
        if holding.get('ITEMS', None):
            holding['ITEMS'] = sorted(holding['ITEMS'],
                key=lambda item: numstrip(item['DISPLAY_CALL_NO']))
    return holdings_list


def templocsort(holdings_list):
    for holding in holdings_list:
        if holding.get('ITEMS', None):
            holding['ITEMS'] = sorted(holding['ITEMS'],
                key=lambda item: item.get('TEMPLOCATION', ''))
    return holdings_list


def elecsort(holdings_list, rev=False):
    elec, rest = [], []
    for holding in holdings_list:
        if _is_electronic(holding):
            elec.append(holding)
        else:
            rest.append(holding)
    if not rev:
        return elec + rest
    return rest + elec


def strip_bad_holdings(holdings_list):
    goodstuff = []
    for holding in holdings_list:
        #look for online resources with no link
        if 'online' in holding.get('LOCATION_DISPLAY_NAME', '').lower():
            if holding.get('ELECTRONIC_DATA', {}):
                if not holding['ELECTRONIC_DATA'].get('LINK856U'):
                    continue
            else:
                continue
        goodstuff.append(holding)
    return goodstuff
