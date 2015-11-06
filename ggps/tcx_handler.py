__author__ = 'cjoakim'

import sys
import xml.sax

import m26

from ggps.trackpoint import Trackpoint


class TcxHandler(xml.sax.ContentHandler):

    tkpt_path = "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint"
    tkpt_path_len = len(tkpt_path)

    @classmethod
    def parse(cls, filename, augment=False):
        handler = TcxHandler(augment)
        none_result =  xml.sax.parse(open(filename), handler)
        return handler

    def __init__(self, augment=False):
        xml.sax.ContentHandler.__init__(self)
        self.augment = augment
        self.heirarchy = list()
        self.trackpoints = list()
        self.curr_tkpt = Trackpoint()
        self.current_text = ''
        self.end_reached = False
        self.first_time = None
        self.first_etime = None
        self.first_time_secs_to_midnight = 0

    def startElement(self, tag_name, attrs):
        self.heirarchy.append(tag_name)
        self.reset_curr_text()
        path = self.current_path()

        if path == self.tkpt_path:
            self.curr_tkpt = Trackpoint()
            self.trackpoints.append(self.curr_tkpt)
            return

    def endElement(self, tag_name):
        path = self.current_path()

        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|AltitudeMeters": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|DistanceMeters": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Extensions": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Extensions|TPX": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Extensions|TPX@xmlns": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Extensions|TPX|RunCadence": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Extensions|TPX|Speed": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|HeartRateBpm": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|HeartRateBpm|Value": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Position": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Position|LatitudeDegrees": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Position|LongitudeDegrees": 2256,
        # "TrainingCenterDatabase|Activities|Activity|Lap|Track|Trackpoint|Time": 2256,

        if self.tkpt_path in path:
            if len(path) > self.tkpt_path_len:
                retain = True
                if tag_name == 'Extensions':
                    retain = False
                elif tag_name == 'Position':
                    retain = False
                elif tag_name == 'TPX':
                    retain = False
                elif tag_name == 'HeartRateBpm':
                    retain = False
                elif tag_name == 'Value':
                    tag_name = 'HeartRateBpm'

                if retain:
                    self.curr_tkpt.set(tag_name, self.current_text)

        self.heirarchy.pop()
        self.reset_curr_text()

    def endDocument(self):
        self.end_reached = True

        if self.augment:
            for idx, t in enumerate(self.trackpoints):
                if idx == 0:
                    self.set_first_trackpoint(t)
                self.augment_with_calculations(idx, t)

    def set_first_trackpoint(self, t):
        self.first_time = self.parse_hhmmss(t.get('time'))
        self.first_etime = m26.ElapsedTime(self.first_etime)

    def reset_curr_text(self):
        self.current_text = ''

    def characters(self, chars):
        self.current_text = self.current_text + chars

    def current_depth(self):
        return len(self.heirarchy)

    def current_path(self):
        return '|'.join(self.heirarchy)

    def trackpoint_count(self):
        return len(self.trackpoints)

    def augment_with_calculations(self, idx, t):
        t.set('seq', "{0}".format(idx + 1))
        self.meters_to_feet(t, 'altitudemeters', 'altitudefeet')
        self.meters_to_miles(t, 'distancemeters', 'distancemiles')
        self.meters_to_km(t, 'distancemeters', 'distancekilometers')
        self.cadence_x2(t)

        self.calculate_elapsed_time(t)

    def meters_to_feet(self, t, meters_key, new_key):
        m = t.get(meters_key)
        if m:
            km = float(m) / 1000.0
            d_km = m26.Distance(km, m26.Constants.uom_kilometers())
            yds = d_km.as_yards()
            t.set(new_key, str(yds * 3.000000))

    def meters_to_km(self, t, meters_key, new_key):
        m = t.get(meters_key)
        if m:
            km = float(m) / 1000.0
            t.set(new_key, str(km))

    def meters_to_miles(self, t, meters_key, new_key):
        m = t.get(meters_key)
        if m:
            km = float(m) / 1000.0
            d_km = m26.Distance(km, m26.Constants.uom_kilometers())
            t.set(new_key, str(d_km.as_miles()))

    def meters_to_miles(self, t, meters_key, new_key):
        m = t.get(meters_key)
        if m:
            km = float(m) / 1000.0
            d_km = m26.Distance(km, m26.Constants.uom_kilometers())
            t.set(new_key, str(d_km.as_miles()))

    def cadence_x2(self, t):
        c = t.get('runcadence')
        if c:
            i = int(c)
            t.set('runcadencex2', str(i * 2))

    def calculate_elapsed_time(self, t):
        new_key = 'elapsedtime'
        time_str = t.get('time')
        if time_str == self.first_time:
            t.set(new_key, '00:00:00')
        else:
            t.set(new_key, self.parse_hhmmss(time_str))

    def parse_hhmmss(self, time_str):
        """
        For a given value like '2014-10-05T17:22:17.000Z' return the hhmmss '17:22:17' part.
        """
        if len(time_str) == 24:
            return time_str.split('T')[1][:9]
        else:
            return ''

if __name__ == "__main__":
    filename = sys.argv[1]
    print(filename)
    handler = TcxHandler.parse(filename, True)
    print("{0} trackpoints parsed".format(handler.trackpoint_count()))
    for t in handler.trackpoints:
        print(repr(t))
