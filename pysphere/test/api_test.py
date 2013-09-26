#!/usr/bin/python/
#-*-coding:utf-8-*-
import urllib, urllib2
import sys
import os
import mmap
import logging
from multiprocessing import Process

#from requests.auth import HTTPBasicAuth
from pysphere.resources import VimService_services as VI 
from pysphere.vi_server import VIServer
from pysphere.vi_property import VIProperty
from pysphere.vi_task import VITask
from pysphere.vi_virtual_machine import VIVirtualMachine as VM
from pysphere.sendmail import send_mail

import commands
import optparse
import pexpect
import time
from time import sleep

import threading

#esx's user credential
HOST, USER, PASSWORD = '172.16.128.203', 'root', 'Cisc012$'

def testConn():
    print  'starting....'
    server = VIServer()
    server.connect(HOST, USER, PASSWORD)
    
    if server.is_connected():
        
        vm_test = server.get_vm_by_path("[datastore911re] cucm-sub/cucm-sub.vmx")
        
        """
        if vm_test.is_powered_off():
            print 'going to boot this vm'
            vm_test.power_on(sync_run=False)
            print 'vm_test.get_status(basic_status=True) = ', vm_test.get_status(basic_status=True)
            print 'vm_test.get_status()', vm_test.get_status()
        """ 
        
        print 'conn succ!'
        server.keep_session_alive()
         
        print 'server.get_api_version() = ', server.get_api_version() 
        print 'server.get_server_type() = ', server.get_server_type()
        
        #vm1 = server.get_vm_by_path("[DataStore1] Ubuntu/Ubuntu-10.vmx")
        #vm2 = server.get_vm_by_name("Windows XP Professional")        
        
        #vmlist = server.get_registered_vms(resource_pool='Windows XP', status='poweredOn')
        vmlist = server.get_registered_vms()
        
        for i in range(len(vmlist)):
            #vmlist[i] =  [datastore911re] cucm-pub/cucm-pub.vmx
            print 'vmlist[i] = ', vmlist[i]

        
        #vm_test.get_status(basic_status=True)= POWERED ON
        """
            'POWERED ON'
            'POWERED OFF'
            'SUSPENDED'
            'POWERING ON'
            'POWERING OFF'
            'SUSPENDING'
            'RESETTING'
            'BLOCKED ON MSG'
            'REVERTING TO SNAPSHOT'         
        """
        print 'vm_test.get_status(basic_status=True)=', vm_test.get_status(basic_status=True)
        
        print '----get all properties-----'
        print vm_test.get_properties()
        
        print 'vm1.get_property(\'name\') = ', vm_test.get_property('name') 
        print 'vm1.get_property(\'macAddress\') = ', vm_test.get_property('macAddress')
        print 'vm_test.get_property(\'ip_address\', from_cache=False)=', vm_test.get_property('ip_address', from_cache=False)
        #print 'vm_test.get_properties(from_cache=False) =', vm_test.get_properties(from_cache=False) 
        
        #vm1.power_on()
        #vm1.reset()
        #vm1.suspend() #since pysphere 0.1.5
        #vm1.power_off()   
        #vm_test.power_off(sync_run=False) 
        
        snapshot_list = vm_test.get_snapshots()
        
        #list all snapshots
        for snapshot in snapshot_list:
            print '-------------------------------------'
            print "Name:", snapshot.get_name()
            print "Description", snapshot.get_description()
            print "Created:", snapshot.get_create_time()
            print "State:", snapshot.get_state()
            print "Path:", snapshot.get_path()
            print "Parent:", snapshot.get_parent()
            print "Children:", snapshot.get_children()
            
        
        #To take a snapshot with the current state of the VM
        #vm_test.create_snapshot("mytest_pub_snapshot", description="just a test", sync_run=False)
        #print 'taking a snapshot....'
           
        
    else:
        print 'conn fail...'  
        
        
    server.disconnect()
    print 'disconnected..'
    

def testSnapshot():
    print 'start..'

if __name__ == '__main__':
    testConn()
    #testSnapshot()
    
    
    
    
    
    
    
    
    
    
    
    
    
    