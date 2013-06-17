import pymarc
from PyZ3950 import zoom

from ui.records.bib import Bib
from ui.records.holding import Holding
from ui.records.item import Item


class Z3950Catalog():

    def __init__(self, ip, port, name, syntax):
        self.ip = ip
        self.port = port
        self.name = name
        self.syntax = syntax
        self.conn = self._getconn(ip, port, name, syntax)

    def _getconn(self, ip, port, name, syntax):
        conn = zoom.Connection(ip, port)
        conn.databaseName = name
        conn.preferredRecordSyntax = syntax
        return conn

    def zoom_record(self, bibid):
        query = zoom.Query('PQF', '@attr 1=12 %s' % bibid.encode('utf-8'))
        try:
            results = self.conn.search(query)
            if len(results) > 0:
                return results[0]
        except:
            raise

    def bib(self, bibid, add_holdings=True):
        try:
            zoomrec = self.zoom_record(bibid)
            marc = zoomrec.data.bibliographicRecord.encoding[1]
            bib = Bib(marc=pymarc.Record(data=marc))
            if add_holdings:
                bib.holdings = self.holdings(zoom_record=zoomrec)
            return bib
        except:
            raise

    def holdings(self, bibid=None, zoom_record=None, add_items=True):
        if bibid and not zoom_record:
            zoom_record = self.zoom_record(bibid)
        holdings = []
        for rec in zoom_record.data.holdingsData:
            holdmeta = {}
            holdmeta['callnum'] = rec[1].callNumber
            holdmeta['location'] = rec[1].localLocation
            holding = Holding(metadata=holdmeta)
            if add_items:
                itemmeta = {}
                itemmeta['callnum'] = rec[1].callNumber
                itemmeta['permloc'] = rec[1].localLocation
                itemmeta['status'] = rec[1].publicNote
                holding.items = [Item(metadata=itemmeta)]
            holdings.append(holding)
        return holdings
