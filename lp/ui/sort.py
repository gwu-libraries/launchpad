from lp import settings


def libsort(holdings_list):
    top, middle, bottom = [],[],[]
    for holding in holdings_list:
        if holding['LIBRARY_NAME'] == settings.PREF_LIB:
            top.append(holding)
        elif holding['LIBRARY_NAME'] in settings.BOTTOM_LIBS:
            bottom.append(holding)
        else:
            middle.append(holding)
    return top + middle + bottom
	

def libsort_bottom_only(holdings_list):
    bottom, remainder = [], []
    for holding in holdings_list:
        if holding['LIBRARY_NAME'] in settings.BOTTOM_LIBS:
            bottom.append(holding)
        else:
            remainder.append(holding)
    return remainder + bottom


def libsort_top_only(holdings_list):
    top, remainder = [],[]
    for holding in holdings_list:
        if holdings['LIBRARY_NAME'] == settings.PREF_LIB:
            top.append(holding)
        else:
            remainder.append(holding)
    return top + remainder
