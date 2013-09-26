#!/usr/bin/python
#-*-coding:utf-8-*-
import urllib, urllib2
import sys
import os
import mmap
import logging
import requests
from requests.auth import HTTPBasicAuth

from progressbar import AnimatedMarker, Bar, BouncingBar, Counter, ETA, \
                        FileTransferSpeed, FormatLabel, Percentage, \
                        ProgressBar, ReverseBar, RotatingMarker, \
                        SimpleProgress, Timer

class VIDatastore(object):
    
    def __init__(self, server_instance, datastore_name, dc_name=None):
        self._s = server_instance
        self._datastore = datastore_name
        self._datacenter = dc_name
        self.relogin()
        
    def relogin(self):
        self._handler = self._build_auth_handler()
        
    def geturl(self,remote_file_path):
        resource = "/folder/%s" % remote_file_path.lstrip("/")
        url = self._get_url(resource)
        return url


    def uploadC(self, local_file_path, remote_file_path):
        isofile = upload_in_chunks(local_file_path, chunksize=8192)
        resource = "/folder/%s" % remote_file_path.lstrip("/")
        url = self._get_url(resource)
        auth = HTTPBasicAuth('root', 'Cisc012$')
        
        #error occured**********
        """
        url= https://172.16.128.202/folder/Upgrade ISO/20130907/UCSInstall_UCOS_UNRST_9.1.2.11004-1.sgn.iso?dcPath=ha-datacenter&dsName=datastore851un
        isofile = <pysphere.vi_datastore.upload_in_chunks object at 0x54e6f10>
        """
        logging.info('\n' * 2)
        logging.info('***url= ' + str(url) + 'isofile = ' + str(isofile))
        logging.info('\n' * 2)

        #do not upload ISO file if it existed!
        resp_get = requests.head(url=url, verify=False, auth=auth)

        #upload only when the iso file not exists
        if resp_get.status_code == 404:
            resp = requests.put(url=url, verify=False, data=IterableToFileAdapter(isofile), auth=auth)
            return 200 <= resp.status_code <= 207            

        else:
           
            return True
        

    def uploadB(self, local_file_path, remote_file_path):
        fd = open(local_file_path, "rb")
        data = mmap.mmap(fd.fileno(), 0, access= mmap.ACCESS_READ)
        resource = "/folder/%s" % remote_file_path.lstrip("/")
        #print resource
        url = self._get_url(resource)
        #print url
 
        resp = self._do_request(url, data)
        data.close()
        fd.close()
        print "resp.code: %s" % resp.status_code

        return 200 <= resp.status_code <= 207
        
    def upload(self, local_file_path, remote_file_path):
        fd = open(local_file_path, "r")
        data = fd.read()
        fd.close()
        resource = "/folder/%s" % remote_file_path.lstrip("/")
        url = self._get_url(resource)
        #print url
        resp = self._do_request(url, data)
        return 200 <= resp.code <= 207

    def download(self, remote_file_path, local_file_path):
        resource = "/folder/%s" % remote_file_path.lstrip("/")
        url = self._get_url(resource)
        
        if sys.version_info >= (2, 6):
            resp = self._do_request(url)
            CHUNK = 16 * 1024
            fd = open(local_file_path, "wb")
            while True:
                chunk = resp.read(CHUNK)
                if not chunk: break
                fd.write(chunk)
            fd.close()
        else:
            urllib.urlretrieve(url, local_file_path)

    def _do_request(self, url, data=None):
        auth = HTTPBasicAuth('root', 'Cisc012$')
        return requests.post(url=url, verify=False, data=data, auth=auth)

    def _get_url(self, resource):
        if not resource.startswith("/"):
            resource = "/" + resource
        params = {"dsName":self._datastore}
        if self._datacenter:
            params["dcPath"] = self._datacenter
        params = urllib.urlencode(params)
            
        return "%s%s?%s" % (self._get_service_url(), resource, params)
    
    def _get_service_url(self):
        service_url = self._s._proxy.binding.url
        #print service_url
        rst = service_url[:service_url.rindex("/sdk")]
        #print rst 
        return rst
    
    def _build_auth_handler(self):
        service_url = self._get_service_url()
        user = self._s._VIServer__user
        password = self._s._VIServer__password
        auth_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        auth_manager.add_password(None, service_url, user, password)
        return urllib2.HTTPBasicAuthHandler(auth_manager)
        
class upload_in_chunks(object):
    def __init__(self, filename, chunksize=1 << 13):
        self.filename = filename
        self.chunksize = chunksize
        self.totalsize = os.path.getsize(filename)
        print self.totalsize
        self.readsofar = 0
        self.widgets = [' Uploading: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
        self.pbar = ProgressBar(widgets=self.widgets, maxval=self.totalsize).start()

    def __iter__(self):
        with open(self.filename, 'rb') as file:
            while True:
                data = file.read(self.chunksize)
                if not data:
                    sys.stderr.write("\n")
                    break
                self.readsofar += len(data)
                #percent = self.readsofar * 1e2 / self.totalsize
                self.pbar.update(self.readsofar)
                #sys.stderr.write("\r{percent:3.0f}%".format(percent=percent))
                yield data
            self.pbar.finish()

    def __len__(self):
        return self.totalsize
        
class IterableToFileAdapter(object):
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.length = len(iterable)

    def read(self, size=-1): # TBD: add buffer for `len(data) > size` case
        return next(self.iterator, b'')

    def __len__(self):
        return self.length
