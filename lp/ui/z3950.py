import pymarc
from PyZ3950 import zoom

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

    def get_holding(self, bibid=None, zoom_record=None, add_items=True):
        if bibid and not zoom_record:
            zoom_record = self.zoom_record(bibid)
        holdings = []
        for rec in zoom_record.data.holdingsData:
            holdmeta = {}
            holdmeta['item_status'] = 0
            holdmeta['callNumber'] = ''
            holdmeta['status'] = ''
            holdmeta['url'] = ''
            if hasattr(rec[1], 'callNumber'):
                holdmeta['callnum'] = rec[1].callNumber.rstrip('\x00')
            else:
                holdmeta['callnum'] = ''
            holdmeta['location'] = rec[1].localLocation.rstrip('\x00')
            if hasattr(rec[1], 'publicNote'):
                holdmeta['status'] = rec[1].publicNote.rstrip('\x00')
            if hasattr(rec[1], 'circulationData'):
                holdmeta['status'] = rec[1].circulationData[0].availableNow
            if holdmeta['status'] == True or holdmeta['status'] == 'AVAILABLE': 
                holdmeta['status'] = 'Not Charged'
                holdmeta['item_status'] = 1
            elif holdmeta['status'] == False or holdmeta['status'] == 'DUE':
                holdmeta['status'] = 'Charged'
                holdmeta['item_status'] = 0
            marc = pymarc.record.Record(zoom_record.data.bibliographicRecord.encoding[1])
            if marc['856']:
                holdmeta['url'] = marc['856']['u'] 
            holdings.append(holdmeta)
        return holdings
