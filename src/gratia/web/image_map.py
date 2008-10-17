
import os
import types
import urllib

from threading import Condition, Thread, currentThread
from template import Template

class ImageMap(Template):

    def generate_drilldown(self, option, url):
        def drilldown(pivot, group, base_url, filter_dict):
            filter_dict[option] = pivot
            filter_url = urllib.urlencode(filter_dict)
            return os.path.join(base_url, url) + '?' + filter_url
        return drilldown

    def generate_pg_map(self, token, maps, func, kw, drilldown_url,
            drilldown_option):
        def worker(self, token, maps, func, kw, drilldown_url,
                drilldown_option):
            #print "Start worker!", currentThread().getName()
            try:
                map = self.__generate_pg_map(func, kw, drilldown_url,
                    drilldown_option)
                token['condition'].acquire()
                maps.append(map)
                token['condition'].release()
            finally:
                token['condition'].acquire()
                token['counter'] -= 1
                token['condition'].notify()
                token['condition'].release()
                #print "Finish worker!", currentThread().getName()
        try:
            token['condition'].acquire()
            token['counter'] += 1
            token['condition'].notify()
            token['condition'].release()
            args = (self, token, maps, func, kw, drilldown_url,
                    drilldown_option)
            Thread(target=worker, args=args).start()
        except:
            token['condition'].acquire()
            token['counter'] -= 1
            token['condition'].notify()
            token['condition'].release()

    def __generate_pg_map(self, func, kw, drilldown_url, drilldown_option):
        map = {}
        map['kind'] = 'pivot-group'
        results, metadata = func(**kw)
        if metadata['kind'] == 'pivot':
            return self.__generate_p_map(results, metadata, map, func, kw,
                drilldown_url, drilldown_option)
        assert metadata['kind'] == 'pivot-group'
        map['name'] = metadata['name']
        column_names = str(metadata.get('column_names',''))
        column_units = str(metadata.get('column_units',''))
        names = [ i.strip() for i in column_names.split(',') ]
        units = [ i.strip() for i in column_units.split(',') ]
        map['column_names'] = names
        map['column_units'] = units
        map['pivot_name'] = metadata['pivot_name']
        data = {}
        map['data'] = data
        map['drilldown'] = self.generate_drilldown(drilldown_option,
            drilldown_url)
        coords = metadata['grapher'].get_coords(metadata['query'], metadata,
            **metadata['given_kw'])
        for pivot, groups in results.items():
            data_groups = {}
            data[pivot] = data_groups
            if pivot in coords:
                coord_groups = coords[pivot]
                for group, val in groups.items():
                    if group in coord_groups:
                        coord = str(coord_groups[group]).replace('(', '').\
                            replace(')', '')
                        if type(val) == types.FloatType and abs(val) > 1:
                            val = "%.2f" % val
                        data_groups[group] = (coord, val)
        return map

    def __generate_p_map(self, results, metadata, map, func, kw, drilldown_url,
            drilldown_option):
        map['kind'] = 'pivot'
        map['name'] = metadata['name']
        column_names = str(metadata.get('column_names',''))
        column_units = str(metadata.get('column_units',''))
        names = [ i.strip() for i in column_names.split(',') ]
        units = [ i.strip() for i in column_units.split(',') ]
        map['column_names'] = names
        map['column_units'] = units
        map['pivot_name'] = metadata['pivot_name']
        data = {}
        map['data'] = data
        map['drilldown'] = self.generate_drilldown(drilldown_option,
            drilldown_url)
        coords = metadata['grapher'].get_coords(metadata['query'], metadata,
            **metadata['given_kw'])
        for pivot, val in results.items():
            if pivot not in coords:
                continue
            coord = coords[pivot]
            coord = str(coord).replace('(', '').replace(')', '')
            if type(val) == types.FloatType and abs(val) > 1:
                val = "%.2f" % val
            data[pivot] = (coord, val)
        return map

    def start_image_maps(self):
        return {'condition': Condition(), 'counter': 0}

    def finish_image_maps(self, token):
        c = token['condition']
        #print "Main thread waiting"
        c.acquire()
        while token['counter'] > 0:
            #print "Live image generator count:", token['counter']
            c.wait()
        c.release()

    def image_map(self, token, data, obj_name, func_name, drilldown_url,
                  drilldown_option):

        token['condition'].acquire()
        try:
            if 'csv' not in data:
                data['csv'] = self.globals['query_csv'].metadata['base_url']
            maps = data.get('maps', [])
            data['maps'] = maps
        finally:
            token['condition'].release()
        self.generate_pg_map(token, maps, getattr(self.globals[obj_name],
            func_name), data['query_kw'], drilldown_url, drilldown_option)
        token['condition'].acquire()
        if 'image_maps' not in data:
            data['image_maps'] = self.getTemplateFilename('image_map.tmpl')
        token['condition'].release()

