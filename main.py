import os
import datetime

from lxml import etree

# Use https://overpass-turbo.eu/ to export to gpx

gpx_header = """
<?xml version="1.0" encoding="UTF-8" ?>
<gpx version="1.1" 
creator="Memory-Map 6.4.3.1278 https://memory-map.com"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns="http://www.topografix.com/GPX/1/1"
 xmlns:xstyle="http://www.topografix.com/GPX/gpx_style/0/2"
 xmlns:xgarmin="http://www.garmin.com/xmlschemas/GpxExtensions/v3"
 xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.topografix.com/GPX/gpx_style/0/2 http://www.topografix.com/GPX/gpx_style/0/2/gpx_style.xsd http://www.garmin.com/xmlschemas/GpxExtensions/v3 https://www8.garmin.com/xmlschemas/GpxExtensionsv3.xsd">
"""
gpx_waypoint = """
<wpt lat="{lat}" lon="{long}">
<time>{time}</time>
<name>{name}</name>
<desc>{desc}</desc>
<link href="{href}"></link>
<sym>{sym}</sym>
<type>Marks</type>
<extensions>
<xstyle:fill>
<xstyle:color>{color}</xstyle:color>
</xstyle:fill>
</extensions>
</wpt>
"""
gpx_footer = """
</gpx>
"""

types_to_process = ['buoy', 'beacon', 'wreck', 'mooring']
ignored_types = []
used_symbols = []


def get_xpath_value(result, default=''):
    if len(result) > 0:
        return result[0]
    return default


def get_color(data_dict, symbol):
    if symbol in ['wreck']:
        return '000000'
    for key, value in data_dict.items():
        if 'colour' in key and 'light' not in key:
            if value == 'red':
                return 'FF0000'
            if value == 'green':
                return '008000'
            if value == 'yellow':
                return 'FFFF00'
    return ''


def get_symbol(data_dict):
    if data_dict['seamark:type'] == 'buoy_special_purpose':
        return 'buoy_round'
    if 'cardinal' in data_dict['seamark:type']:
        return f'buoy_cardinal_{data_dict["seamark:buoy_cardinal:category"]}'
    if data_dict['seamark:type'] in ['beacon_lateral', 'buoy_lateral']:
        if 'can' in data_dict.values():
            return 'buoy_can'
        if 'conical' in data_dict.values():
            return 'buoy_conical'
        if 'spherical' in data_dict.values():
            return 'buoy_round'
        if 'pillar' in data_dict.values():
            return 'pillar'
    return data_dict['seamark:type']


def get_waypoint_xml(name, lat, long, time, data_dict, link=''):
    if 'seamark:type' not in data_dict.keys():
        return ''
    process = False
    seamark_type = data_dict['seamark:type']
    for prefix in types_to_process:
        if seamark_type.startswith(prefix):
            process = True
    if not process:
        print(f'Ignoring {name} type {seamark_type}')
        if seamark_type not in ignored_types:
            ignored_types.append(seamark_type)
        return ''
    if 'seamark:name' in data_dict.keys():
        name = data_dict["seamark:name"]
    desc = ''
    for key in data_dict:
        desc += f'{key}={data_dict[key]}\n'
    href = link
    sym = get_symbol(data_dict)
    if sym not in used_symbols:
        used_symbols.append(sym)
    color = get_color(data_dict, sym)
    return gpx_waypoint.format(lat=lat, long=long, time=time,
                               name=name, desc=desc, href=href, sym=sym, color=color)


def process_gpx(input_path, output_path):
    tree = etree.parse(input_path)
    namespaces = {'ns': tree.getroot().nsmap[None]}
    with open(output_path, 'w') as writer:
        time = datetime.datetime.now().isoformat()
        writer.write(gpx_header)
        for x in tree.xpath('//ns:wpt', namespaces=namespaces):
            name = get_xpath_value(x.xpath('.//ns:name/text()', namespaces=namespaces))
            lat = get_xpath_value(x.xpath('.//@lat', namespaces=namespaces))
            long = get_xpath_value(x.xpath('.//@lon', namespaces=namespaces))
            desc = get_xpath_value(x.xpath('.//ns:desc/text()', namespaces=namespaces))
            link = get_xpath_value(x.xpath('.//ns:link/@href', namespaces=namespaces))
            items = desc.split(f'\n')
            data_dict = {}
            for item in items:
                key_value = item.split('=')
                data_dict[key_value[0]] = key_value[1]
            waypoint_xml = get_waypoint_xml(name, lat, long, time, data_dict, link=link)
            if waypoint_xml:
                writer.write(waypoint_xml)
        writer.write(gpx_footer)


def process_kml(input_path, output_path):
    tree = etree.parse(input_path)
    namespaces = {'ns': tree.getroot().nsmap[None]}
    with open(output_path, 'w') as writer:
        time = datetime.datetime.now().isoformat()
        writer.write(gpx_header)
        for x in tree.xpath('//ns:Placemark[.//ns:Point]', namespaces=namespaces):
            coordinates = get_xpath_value(x.xpath('.//ns:coordinates/text()', namespaces=namespaces))
            coordinates = coordinates.split(',')
            keys = x.xpath('.//ns:Data/@name', namespaces=namespaces)
            values = x.xpath('.//ns:Data/ns:value/text()', namespaces=namespaces)
            key_value_pairs = zip(keys, values)
            data_dict = dict(key_value_pairs)
            name = get_xpath_value(x.xpath('.//ns:name/text()', namespaces=namespaces), default=data_dict['@id'])
            waypoint_xml = get_waypoint_xml(name, coordinates[1], coordinates[0], time, data_dict, link='')
            if waypoint_xml:
                writer.write(waypoint_xml)
        writer.write(gpx_footer)


if __name__ == '__main__':
    data_dir = os.path.join(os.getcwd(), 'data')
    results_dir = os.path.join(os.getcwd(), 'results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    process_gpx(os.path.join(data_dir, 'export.gpx'),
                os.path.join(results_dir, 'osm2mm.gpx'))
    ignored_types.sort()
    used_symbols.sort()
    print(f'Ignored types: {ignored_types}')
    print(f'Used Symbols: {used_symbols}')
