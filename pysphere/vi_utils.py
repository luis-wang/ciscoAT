#--
# Copyright (c) 2013, vcbear
# All rights reserved.
# 
#--


import sys
import os
from hashlib import md5
from xml.dom import minidom
from boxcar import Provider

try:
	import json
except ImportError:
	import simplejson as json
	
import xml.etree.ElementTree as ET
import pyscreenshot as ImageGrab


def get_name_from_path(filepath):
	filename = filepath.split("/")[-1]
	#print filename
	return filename
	
def get_info_from_name(isoname):
	info = isoname.split("_")
	flag = info[0]
	date = info[1]
	detail = info[2]
	#print flag
	#print date
	#print detail
	return flag, date, detail
	
def check_md5(file):
	statinfo = os.stat(file)
	
	if int(statinfo.st_size)/(1024*1024) >= 1000 :
		print "File size > 1000, move to big file..."
		return check_md5_for_BigFile(file)
		
	m = md5()
	f = open(file, 'rb')
	m.update(f.read())
	f.close()
		
	return str(m.hexdigest().upper())
		
def check_md5_for_BigFile(file):
	m = md5()
	f = open(file, 'rb')
	buffer = 8192
	
	while 1:
		chunk = f.read(buffer)
		if not chunk:break
		m.update(chunk)
		
	f.close()
	return str(m.hexdigest().upper())
	
def sizeof_fmt(num):
	for x in ['bytes','KB','MB','GB','TB']:
		if num <1024.0:
			return "%3.1f %s" % (num,x)
		num/=1024.0
		
def elem_to_internal(elem,strip=1):
    d = {}
    for key, value in elem.attrib.items():
        d['@'+key] = value

    # loop over subelements to merge them
    for subelem in elem:
        v = elem_to_internal(subelem,strip=strip)
        tag = subelem.tag
        value = v[tag]
        try:
            # add to existing list for this tag
            d[tag].append(value)
        except AttributeError:
            # turn existing entry into a list
            d[tag] = [d[tag], value]
        except KeyError:
            # add a new non-list entry
            d[tag] = value
    text = elem.text
    tail = elem.tail
    if strip:
        # ignore leading and trailing whitespace
        if text: text = text.strip()
        if tail: tail = tail.strip()

    if tail:
        d['#tail'] = tail

    if d:
        # use #text element if other attributes exist
        if text: d["#text"] = text
    else:
        # text is the value if no attributes
        d = text or None
    return {elem.tag: d}


def internal_to_elem(pfsh, factory=ET.Element):
    attribs = {}
    text = None
    tail = None
    sublist = []
    tag = pfsh.keys()
    if len(tag) != 1:
        raise ValueError("Illegal structure with multiple tags: %s" % tag)
    tag = tag[0]
    value = pfsh[tag]
    if isinstance(value, dict):
        for k, v in value.items():
            if k[:1] == "@":
                attribs[k[1:]] = v
            elif k == "#text":
                text = v
            elif k == "#tail":
                tail = v
            elif isinstance(v, list):
                for v2 in v:
                    sublist.append(internal_to_elem({k:v2}, factory=factory))
            else:
                sublist.append(internal_to_elem({k:v}, factory=factory))
    else:
        text = value
    e = factory(tag, attribs)
    for sub in sublist:
        e.append(sub)
    e.text = text
    e.tail = tail
    return e


def elem2json(elem, strip=1):
	if hasattr(elem, 'getroot'):
		elem = elem.getroot()
	return json.dumps(elem_to_internal(elem, strip=strip))
	
def json2elem(json, factory=ET.Element):
	return internal_to_elem(json.loads(json), factory)
	
def xml2json(xmlstring, strip=1):
	elem = ET.fromstring(xmlstring)
	return elem2json(elem, strip=strip)
	
def json2xml(json, factory=ET.Element):
	elem = internal_to_elem(json.loads(json), factory)
	return ET.tostring(elem)
	
def get_json_from_xml(file):
	f = open(file, 'r')
	if f:
		input = f.read()
		rst = xml2json(input, strip=0)
		f.close()
		return rst
	else:
		return None
		
def trans(v):
	return "OK" if v else "ERROR"
	
def sendNotify(recvemail,msg):
	p = Provider(key='5c5mw9tk9EiLEdcCcW1g',secret='u5T1CUYzCw6cuKSEzUCJ2GBuZmaZUDXyWMMlIBH3')
	p.notify(emails=[recvemail],from_screen_name='ChuWaRobot',message=msg,source_url='',icon_url='')
	
	
def screenshot(path):
	ImageGrab.grab_to_file(path)
	
def make_mac():
	import uuid
	local_mac = uuid.uuid1().hex[-12:]
	import random 
	mac = [random.randint(0x00, 0xff), random.randint(0x00, 0xff) ] 
	s = [local_mac[0:2], local_mac[2:4],local_mac[4:6],local_mac[6:8]] 
	for item in mac: 
		s.append(hex(item)[2:])
	return ( ''.join(s) ).upper()
	