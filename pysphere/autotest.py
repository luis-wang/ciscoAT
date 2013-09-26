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


sender = 'lijunsong@chuwasoft.com'
psw = 're_jy'
receiver = '821090701@qq.com'
smtpserver = 'mail.chuwasoft.com'


class vm_checker(threading.Thread):
    def __init__(self, isoprofile, type, interval):
        threading.Thread.__init__(self)
        self.thread_isoprofile = isoprofile
        self.thread_type    = type
        self.interval       = interval
        self.status         = -1
        self.thread_stop    = False
    
    def run(self):
        while not self.thread_stop:
            print "checking vm ......"
         
            #try:
            child, rst = Login_ssh(self.thread_isoprofile, self.thread_type)
            while True:
                index = child.expect(["admin:", "Connection refused", pexpect.EOF, pexpect.TIMEOUT])
                if index == 0:
                    self.status = 1
                    break
                else:
                    self.status = -1
                    break 
                    #except RuntimeError,ex:
                    #  print "vm statu is still poweroff! waiting..."
                    #  time.sleep(self.interval)
                     
            if self.status == 1:
                child.sendline("utitls core inactive list")
                self.thread_stop = True
                break
            elif self.status == -1:
                print "cucm is still on check!! waiting..."
                time.sleep(self.interval)

    def stop(self):
        self.thread_stop = True

class vm_upgrade_checker(threading.Thread):

    def __init__(self,isoprofile,type,interval):
        threading.Thread.__init__(self)
        self.thread_isoprofile = isoprofile
        self.thread_type = type
        self.interval = interval
        self.status = -1
        self.thread_stop = False

    def run(self):
        while True:
            print "checking vm ......"

            child,rst = Login_ssh(self.thread_isoprofile,self.thread_type)
            while True:
                index = child.expect(["admin:","closed by remote host","Connection refused",pexpect.EOF,pexpect.TIMEOUT])
                if index == 0:
                    self.status = 1
                    break
                else:
                    self.status = -1
                    break

            if self.status == 1:
                child.sendline("utils core inactive list")
                break
            elif self.status == -1:
                print "cucm is still on check!! waiting..."
                time.sleep(self.interval)

    def stop(self):
        self.thread_stop = True


def install_moudles():
    print "*"*50
    print "*"*10,"install moudles first","*"*10
    print "*"*50
    print pexpect.run("sudo pip install requests")
    print pexpect.run("sudo pip install progressbar")
    print pexpect.run("sudo pip install python-boxcar")
    print pexpect.run("sudo pip install pyscreenshot")

try:
    import requests
    from pysphere.vi_datastore import VIDatastore
    from pysphere.vi_utils import *
except:
    install_moudles()
    import requests
    from pysphere.vi_datastore import VIDatastore
    from pysphere.vi_utils import *

        
def change_cdrom_type(dev, dev_type, value):
    
    print ""
    print "*********>> changing cisco new ISO <<*********"
    if dev_type == "ISO":
        iso = VI.ns0.VirtualCdromIsoBackingInfo_Def("iso").pyclass()
        iso.set_element_fileName(value)
        dev.set_element_backing(iso)
    elif dev_type == "HOST DEVICE":
        host = VI.ns0.VirtualCdromAtapiBackingInfo_Def("host").pyclass()
        host.set_element_deviceName(value)
        dev.set_element_backing(host)
    elif dev_type == "CLIENT DEVICE":
        client = VI.ns0.VirtualCdromRemoteAtapiBackingInfo_Def("client").pyclass()
        client.set_element_deviceName("")
        dev.set_element_backing(client)
    print "*********>> changingV cisco new ISO OK! <<*********"
    print ""

def apply_changes(vm,cdrom):
    request = VI.ReconfigVM_TaskRequestMsg()
    _this = request.new__this(vm._mor)
    _this.set_attribute_type(vm._mor.get_attribute_type())
    request.set_element__this(_this)
    spec = request.new_spec()
    
    dev_change = spec.new_deviceChange()
    dev_change.set_element_device(cdrom)
    dev_change.set_element_operation("edit")
    
    spec.set_element_deviceChange([dev_change])
    request.set_element_spec(spec)
    ret = server._proxy.ReconfigVM_Task(request)._returnval
    
    task = VITask(ret,server)
    status = task.wait_for_state([task.STATE_SUCCESS,task.STATE_ERROR])
    
    if status == task.STATE_SUCCESS:
        print "*********>> %s: successfully reconfigured <<*********" % vm.properties.name
    elif status == task.STATE_ERROR:
        print "*********>> %s: Error reconfigured vm <<*********" % vm.properties.name


def Get_Host_Info(server):
    hosts = server.get_hosts()
    host = [k for k,v in hosts.items() if v == hosts['ha-host']][0]
    p = VIProperty(server,host)
    
    print "#====== EXSI host info ======#"
    print "#"*80
    print "#    EXSI host name : %s" % (hosts['ha-host'])
    print "#    EXSI host IP : %s" % (p.summary.managementServerIp)
    print "#    EXSI host productor : %s" % (p.summary.hardware.vendor)                                     #(p.hardware.systemInfo.vendor)
    print "#    EXSI host model : %s" % (p.summary.hardware.model)
    print "#    EXSI host serialnumber : %s" % (p.summary.hardware.otherIdentifyingInfo[2].identifierValue) #(p.hardware.systemInfo.otherIdentifyingInfo[2].identifierValue)
    print "#    EXSI host cpuinfo : %s" % (p.summary.hardware.cpuModel)                                     #(p.hardware.cpuPkg[0].description)
    print "#    EXSI host cpucore : %s" % (p.summary.hardware.numCpuCores)                                  #(p.hardware.cpuInfo.numCpuCores)
    print "#    EXSI host cpupackage : %s" % (p.summary.hardware.numCpuPkgs)                                #(p.hardware.cpuInfo.numCpuPackages)
    print "#    EXSI host memorysize : %s" % (sizeof_fmt(p.summary.hardware.memorySize))                    #(sizeof_fmt(p.hardware.memorySize))
    print "#"*80
    
    print ""
    
    vms = server.get_registered_vms()
    print "#====== EXSI host VM list ======#"
    print "#"*80
    for (index,vm) in enumerate(vms):
        print "#    %s    %s" % (index,vms[index])
    print "#"*80
    
            
def Upload_cisco_ISO(server, datastore, datacenter, localISOpath):

    print ""
    print "*********>> Start to upload cisco ISO! <<*********"
    print ""
    
    isoname = get_name_from_path(localISOpath)
    version_date = time.strftime('%Y%m%d',time.localtime(time.time()))
    remoteISOpath = "/Upgrade ISO/" + version_date + "/" + isoname
    
    print "#====== Uploading cisco ISO info ======#"
    print "#"*80
    print "#    FileSize:    %s" % os.path.getsize(localISOpath)
    print "#    localpath:    %s" % localISOpath
    print "#    remotepath:    %s" % remoteISOpath
    print "#"*80
    print ""
    
    
    file_browser = VIDatastore(server, datastore, datacenter)
    rst1 = file_browser.uploadC(localISOpath, remoteISOpath)

    print ""
    if rst1:
        print "*********>> upload ISO %s successfully! <<*********" % isoname
        return "[%s]" % datastore + " " + remoteISOpath
    else:
        print "*********>> upload ISO %s error! <<*********" % isoname
        return None
    
    
def Mount_cisco_ISO(server,vmpath,isopath):
    
    print ""
    print "*********>> Start to mount the new cisco ISO! <<*********"
    print ""
    
    if not isopath:
        print "*********>> mount new iso error! <<*********\r\n*********>> Please check if the new ISO exist<<*********"
        return
    
    vm = server.get_vm_by_path(vmpath)
    
    if not vm:
        print "*********>> VirtualMachine get error! <<*********\r\n*********>> Please check if the VirtualMachine exist<<*********"
        return
    
    cdrom = None
    for dev in vm.properties.config.hardware.device:
        if dev._type == "VirtualCdrom":
            cdrom = dev
            break
            
    if cdrom:
        print "#====== ESTest VirtualMachine info ======#"
        print "#"*90
        print "#    VirtualMachine name:        %s" % vm.properties.config.name
        print "#    VirtualMachine version:        %s" % vm.properties.config.version
        
        print "#    VirtualMachine CPU core number:    %s" % vm.properties.config.hardware.numCPU
        print "#    VirtualMachine memory:        %s" % sizeof_fmt(vm.properties.config.hardware.memoryMB*1024*1024)
        
        print "#    VirtualMachine OS type:        %s" % vm.properties.summary.guest.guestFullName
        print "#    VirtualMachine host model:    %s" % vm.properties.config.annotation
        print "#    VirtualMachine host name:    %s" % vm.properties.summary.guest.hostName
        print "#    VirtualMachine host IP:        %s" % vm.properties.summary.guest.ipAddress
        print "#    VirtualMachine path:        %s" % vmpath
        print "#"*90
        
        print ""
        print "#====== ESTest VirtualMachine ISO mount detail ======#"
        print "#"*110
        print "#    VirtualMachine device:        %s" % cdrom.deviceInfo.label
        print "#    VirtualMachine loaded ISO:    %s" % cdrom.deviceInfo.summary
        print "#    new ISO will be mounted:    %s" % isopath
        print "#"*110
        print ""
        
    change_cdrom_type(cdrom._obj,"ISO",isopath)
    apply_changes(vm,cdrom._obj)
    
    
    
def get_ISO_profile(isofilepath):
    
    #like /home/work/ISO/UCSInstall_UCOS_9.1.2.11004-1.sgn.iso
    
    # get profile path from the ISO file path
    filename = os.path.splitext(isofilepath)[0]
    isoprofilepath = filename + ".xml"
    
    # check file exists
    vp1 = os.path.exists(isofilepath)
    vp2 = os.path.exists(isoprofilepath)
    
    print ""
    print "#====== ISO file and profile check detail ======#"
    print "#"*80
    print "#    ISO filepath:    %s    %s" % (isofilepath, trans(vp1))
    print "#    ISO profile filepath:    %s    %s" % (isoprofilepath, trans(vp2))
    print "#"*80
    print ""
    
    if not (vp1 and vp2):
        print "*********>> ISO file checking error! <<*********\r\n*********>> Please check if the ISO and profile exists<<*********"
        return [False,"","","","","","","","","","","","","",""]
    
    # get profile info to json style
    jsoniso = get_json_from_xml(isoprofilepath)
    if jsoniso:
        data = json.loads(jsoniso)    
        
        ehost = str(data[u'CUCMISO'][u'hostip'][u'#text'])
        euser = str(data[u'CUCMISO'][u'hostuser'][u'#text'])
        passwd = str(data[u'CUCMISO'][u'hostpassword'][u'#text'])
        datastore = str(data[u'CUCMISO'][u'datastore'][u'#text'])
        datacenter = str(data[u'CUCMISO'][u'datacenter'][u'#text'])
        MD5 = str(data[u'CUCMISO'][u'MD5'][u'#text'])
        pubcucmvm = str(data[u'CUCMISO'][u'pubcucmvm'][u'#text'])
        pubcucmip = str(data[u'CUCMISO'][u'pubcucmip'][u'#text'])
        pubcucmuser = str(data[u'CUCMISO'][u'pubcucmuser'][u'#text'])
        pubcucmpassword = str(data[u'CUCMISO'][u'pubcucmpassword'][u'#text'])
        subcucmvm = str(data[u'CUCMISO'][u'subcucmvm'][u'#text'])
        subcucmip = str(data[u'CUCMISO'][u'subcucmip'][u'#text'])
        subcucmuser = str(data[u'CUCMISO'][u'subcucmuser'][u'#text'])
        subcucmpassword = str(data[u'CUCMISO'][u'subcucmpassword'][u'#text'])
        rst = True
        
        return [rst,ehost,euser,passwd,datastore,datacenter,MD5,pubcucmvm,pubcucmip,pubcucmuser,pubcucmpassword,subcucmvm,subcucmip,subcucmuser,subcucmpassword]
    else:
        return [False,"","","","","","","","","","","","","",""]
        
        
def Basic_Info_Check(info):
    CHECKPRO = info[0]
        
    if not (CHECKPRO):
        print ""
        print "*********>> Get CUCM ISO profile file error! <<*********\r\n*********>> Please check your ISO profile <<*********"
        print ""
        #sendNotify("2011445392@qq.com","ChuWa CUCM ES-Testing ERROR: basic info check error")
        subject = "ES-Testing Error"
        body = "chuWa CUCM ES-Testing ERROR:basic info check error" 
        send_mail(sender,receiver,subject,body,smtpserver,psw)    
    return CHECKPRO
    
def CUCM_version_check(server,pubvm,isofilename):
    # old version check
    pub_vm = server.get_vm_by_path(pubvm)
    
    if not pub_vm:
        print "*********>> VirtualMachine get error! <<*********\r\n*********>> Please check if the VirtualMachine exist<<*********"
        return [False,"",""]
        
    pub_os = pub_vm.properties.summary.config.annotation.split(' ')
    
    if not (pub_os[0] == 'CUCM'):
        print "*********>> VirtualMachine get error! <<*********\r\n*********>> the OS of VirtualMachine is not CUCM<<*********"
        return [False,"",""]
        
    old_version = pub_os[1]
    
    if old_version not in ['8.5','8.6','9.1']:
        sendNotify("2011445392@qq.com","ChuWa CUCM ES-Testing ERROR: CUCM old version error(8.5,8.6,9.1 only)")
        subject = "Version error"
        body = "ChuWa CUCM ES-Testing ERROR: CUCM old version error(8.5,8.6,9.1 only)" 
        send_mail(sender,receiver,subject,body,smtpserver,psw)    
        return [False,"",""]  
    
    # update version check    
    info = isofilename.split("_")
    deatil = info[2].split(".")
    if len(deatil)>1:
        update_version = "%s.%s" % (deatil[0],deatil[1])
    else:
        update_version = "%s.%s" %(info[2],info[3])    

    
    return [True,old_version,update_version]
    
def verify_ISO_MD5(localISOpath,ciscoMd5):
    print ""
    print "*********>> Start to check cisco ISO MD5! <<*********"
    print ""
    
    calmd5 = check_md5(localISOpath)
    
    print "#====== Checking cisco ISO MD5 ======#"
    print "#"*80
    print "#    cisco provied ISO MD5:    %s" % ciscoMd5
    print "#    local upload ISO MD5:    %s" % calmd5
    print "#"*80
    print ""
    
    if calmd5 == ciscoMd5.upper():
        print "*********>> MD5 checking OK!  <<*********"
        return True
    else:
        print "*********>> MD5 checking error! <<*********\r\n*********>> Please re-download the cisco ISO <<*********"
        #sendNotify("2011445392@qq.com","ChuWa CUCM ES-Testing ERROR: ISO MD5 check error")
        subject = "ISO MD5 Error"
        body = "ChuWa CUCM ES-Testing ERROR: ISO MD5 check error" 
        send_mail(sender,receiver,subject,body,smtpserver,psw)
        return False
        
def Run_refresh_command(isoprofile,type):
    try:
        
        cucmssh,rst = Login_ssh(isoprofile, type)

        print ""
        print "#"*80
        print "*********>> Start CUCM refresh!  <<*********"
        print "#"*80
        print ""
        
        login_num = cucmssh.expect ( ['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None )
        #relogin
        if login_num != 0:
            del cucmssh
            print "=========Run_refresh_command login error, login_num = ", login_num
            cucmssh, rst = Login_ssh(isoprofile, type)         
        
        cucmssh.sendline ("utils system upgrade initiate")
        
    except Exception, e:
        body = "ChuWa CUCM ES-Testing for %s node error!" % type
        #sendNotify("2011445392@qq.com",msg)
        subject = "%s node error"%type 
        send_mail(sender,receiver,subject,body,smtpserver,psw)

       
def Login_ssh(isoprofile, type):
    if type == "PUB":
        CUCMVM = ISOprofile[7]
        CUCMIP = ISOprofile[8]
        CUCMUSER = ISOprofile[9]
        CUCMPWD = ISOprofile[10]
    elif type == "SUB":
        CUCMVM = ISOprofile[11]
        CUCMIP = ISOprofile[12]
        CUCMUSER = ISOprofile[13]
        CUCMPWD = ISOprofile[14]
        
    sshcommand = "ssh %s@%s" % (CUCMUSER, CUCMIP)
    ssh = pexpect.spawn(sshcommand)
    ssh.logfile = sys.stdout
    ssh.timeout = 180
    ssh.delaybeforesend = 0.05

    index = ssh.expect(["(yes/no)", "password:", "continue connecting (yes/no)?", pexpect.EOF, pexpect.TIMEOUT])
    

    if index == 0:
        ssh.sendline("yes")
        ssh.expect("password:") 
        ssh.sendline(CUCMPWD)  
          
    if index == 1:
        ssh.sendline(CUCMPWD)
    if index == 2:
        ssh.sendline("yes")
    if index == 3:
        return ssh, False
    if index == 4:
        return ssh, False
    
     
    return ssh, True


def vm_connect(server, isoprofile):
    if len(server.get_hosts())==0 or not server.is_connected:
        print 'server connect'
        HOST = ISOprofile[1]
        USER = ISOprofile[2]
        PASSWORD =ISOprofile[3]
        server = VIServer()
        server.connect(HOST, USER, PASSWORD)
        if server.is_connected():
            server.keep_session_alive()
    return server


def Run_upgrade_command(server, isoprofile, type):
    print '1------------start run fun Run_upgrade_command-----------'

    
    try:
        cucmssh, rst = Login_ssh(isoprofile, type)

        login_num = cucmssh.expect( ['admin:', pexpect.EOF, pexpect.TIMEOUT, 'password:'], timeout=None )
        
        if login_num == 3:
            cucmssh, rst = Login_ssh(isoprofile, type)
            login_num = cucmssh.expect( ['admin:', pexpect.EOF, pexpect.TIMEOUT, 'password:'], timeout=None )
        
        #relogin
        if login_num != 0:
            del cucmssh
            print "=========login error, login_num = ", login_num
            cucmssh, rst = Login_ssh(isoprofile, type)            

        cucmssh.sendline ("utils system upgrade initiate")
        
        print ""
        print "#"*80
        print "*********>> Start to Upgrade!  <<*********"
        print "#"*80
        print ""
        
        while True:
            #index = cucmssh.expect(['Assume control \(yes/no\):', '\(1 - 3 or "q" \):'
            index = cucmssh.expect(['\(yes/no\):', '\(1 - 3 or "q" \):', pexpect.EOF, pexpect.TIMEOUT], timeout=None )
            if index == 0:
                cucmssh.sendline("yes")
            elif index == 1:
                cucmssh.sendline ("3")
                break
        
        print '6------------utils system upgrade initiate----------'
        
        #print '=============force to end==============='
        #sys.exit(-1)
        
        while True:
            indx = cucmssh.expect(['\(optional\):','\(1 - 1 or "q" \):', pexpect.EOF, pexpect.TIMEOUT], timeout=None )
            if indx == 0:
                cucmssh.sendline("")
            elif indx == 1:
                cucmssh.sendline("1")    
                break
        
        #automatically switch? no
        i = cucmssh.expect(['\(yes/no\):', pexpect.EOF, pexpect.TIMEOUT], timeout=None )
        if i == 0 :
            cucmssh.sendline("no")
        else:
            del cucmssh
            cucmssh, rst = Login_ssh(isoprofile, type)
            print 'error expect: i = ', i
    
        #start installation? yes
        
        while True:
            i1 = cucmssh.expect(['\(yes/no\):', pexpect.EOF, pexpect.TIMEOUT], timeout=None )
            if i1 == 0 :
                cucmssh.sendline("yes")
                
            else:
                del cucmssh
                cucmssh, rst = Login_ssh(isoprofile, type)
                print 'cucmssh expect: i1 = ', i1, ', please wait...'
                break    



        #time.sleep(9000)
        #--------------------------------------------------------------------------------------------------------------------------        
        
        
        #wait until upgrade ended
        #cucmssh,rst = Login_ssh(isoprofile,type)

        index = cucmssh.expect( ['admin:', 'closed by remote host', 'Connection refused', pexpect.EOF, pexpect.TIMEOUT], timeout=None)
        
        
        while True:
            if index == 0:
                cucmssh.sendline("utils core inactive list")
                break
    
            if index == 1:
                ck_thd = vm_upgrade_checker(isoprofile, type, 10)
                while True:
                    index2 = cucmssh.expect(["reboot NOW!", pexpect.EOF, pexpect.TIMEOUT], timeout=None)
                    if index2 == 0:
                        print "reconnect now"
                        ck_thd.start() 
                        break
                    elif index2 == 1:
                        print "1"*20
                        ck_thd.start() 
                        break
                    elif index2 == 2:
                        print "2"*20
                        ck_thd.start()
                        break 
                ck_thd.join()
                
                checker_index = cucmssh.expect(['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None)            
                if checker_index != 0:
                    del cucmssh
                    print "=========checker_index =, ", checker_index
                    cucmssh, rst = Login_ssh(isoprofile, type) 
                
                cucmssh.sendline("utils core inactive list")
        
        
        #-------------------------------------------------------------------------------------------
        #after command 'utils core inactive list'
        endupgrade_index = cucmssh.expect(['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None)
        
        if endupgrade_index != 0:
            del cucmssh
            print "=========endupgrade_index =, ", endupgrade_index
            cucmssh, rst = Login_ssh(isoprofile, type)             
        
        
        cucmssh.sendline("")    
        screenshot('%s.%s-shot.png' % (time.time(), type))

        body = "ChuWa CUCM ES-Testing for %s node successfully end!" % type
        subject = "%s node successfully end"%type 
        send_mail(sender, receiver, subject, body, smtpserver, psw)
        #sendNotify("2011445392@qq.com",msg)
        cucmssh.close() 
        
    except Exception, e:
        print e
        body = "ChuWa CUCM ES-Testing for %s node error!" % type
        subject = "%s node error"%type
        send_mail(sender,receiver,subject,body,smtpserver,psw)

        #sendNotify("2011445392@qq.com",msg)
        sys.exit()    


def Run_Switch_command(server, isoprofile, type): 

    try:    
        cucmssh, rst = Login_ssh(isoprofile, type)

        login_num = cucmssh.expect( ['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None )
        
        #relogin
        if login_num != 0:
            del cucmssh
            print "=========Run_Switch_command, login_num = ", login_num
            cucmssh, rst = Login_ssh(isoprofile, type)          
        
        cucmssh.sendline("utils system switch-version")

        print ""

        print "#"*80
        print "*********>> Start to Switch [ %s ] !  <<*********" % type
        print "#"*80
        print ""

        while True:
            index = cucmssh.expect(["Enter \(yes/no\)?", "Waiting", pexpect.EOF, pexpect.TIMEOUT], timeout=None )
            if index == 0:
                print '----------switch-version-------------captured----Enter (yes/no)?------'
                cucmssh.sendline("yes")
                print 'cucmssh.before=', cucmssh.before, '|||', ' cucmssh.after=', cucmssh.after, '|||'
                
            elif index == 1:
                print '----------switch-version-------------captured----Waiting------'
                screenshot('%s.%s-shot_Before.png' % (time.time(), type))
                break
            elif index == 2:
                print '----------switch-version-------------captured----pexpect.EOF------'
                break
            elif index == 3:
                print '----------switch-version-------------captured----pexpect.TIMEOUT **Continue looping...**------'
                print 'cucmssh.before=', cucmssh.before, '||', ' cucmssh.after=', cucmssh.after, '||'
                
        print '==========loop ended, next step is vm_checker() ============'

        #cucmssh.interact()
        if index == 1: 
            print ''
            ck_thd = vm_checker(isoprofile, type, 100)
            while True:
                index2 = cucmssh.expect(["reboot NOW!", pexpect.EOF, pexpect.TIMEOUT])
                if index2 == 0:
                    print "reboot now"
                    ck_thd.start() 
                    break
                elif index2 == 1:
                    print "1"*20
                    ck_thd.start()
                    break
                elif index2 == 2:
                    print "2"*20
                    ck_thd.start()
                    break
          
            ck_thd.join() 

            cucmssh2, rst = Login_ssh(isoprofile, type)

            test_num = cucmssh2.expect( ['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None )            
            #relogin
            if test_num != 0:
                del cucmssh2
                print "=========login error, test_num = ", test_num
                cucmssh2, rst = Login_ssh(isoprofile, type)              
            
            
            cucmssh2.sendline ("utils core inactive list")
            
            test_num = cucmssh2.expect( ['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None )            
            #relogin
            if test_num != 0:
                del cucmssh2
                print "=========login error, test_num = ", test_num
                cucmssh2, rst = Login_ssh(isoprofile, type)             
            
            cucmssh2.sendline("")
            screenshot("%s.%s-shot_core_inactive_list.png"%(time.time(),type))

    except Exception,e:
        print e
        sys.exit()

def CUCM_special_update(oldversion, updateversion, server, isoprofile):
    if oldversion in ["8.5","8.6"] and updateversion == "9.1":
        refresh_isopath = isoprofile[4] + "/Upgrade ISO/ciscocm.refresh_upgrade_v1.1.cop.sgn.iso"
        Mount_cisco_ISO(server,isoprofile[7],refresh_isopath)
        #Run_refresh_command(isoprofile,"PUB")
        Mount_cisco_ISO(server,isoprofile[11],refresh_isopath)
        #Run_refresh_command(isoprofile,"SUB")
        
def Bat_test(type,version,cucmip,times):
    SENDINF = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://www.cisco.com/AXL/API/%s"><soapenv:Header/><soapenv:Body><ns:addPhone sequence="?"><phone ctiid="?"><name>SEP%s</name><description>CFTC - Lab</description><product>Cisco 7961</product><class>Phone</class><protocol>SCCP</protocol><protocolSide>User</protocolSide><devicePoolName uuid="?">Default</devicePoolName></phone></ns:addPhone></soapenv:Body></soapenv:Envelope>'''
    #print SoapMessage
    
    for i in range(0,times):
        simmac = make_mac()
        SoapMessage = "\'%s%s" % (SENDINF % (version,str(simmac.upper())),"\'")
        rst,out = commands.getstatusoutput('curl -k -u cisco:Cisc012$ -H "Content-type: text/xml;" -H "SOAPAction: CUCM:DB ver=%s" -d %s  https://%s:8443/axl/' % (version,SoapMessage,cucmip))

    body = "ChuWa CUCM ES-Testing for %s %s successful!" % (cucmip,type)
    subject = "%s %s successful"%(cucmip,type)
    send_mail(sender,receiver,subject,body,smtpserver,psw)

    #sendNotify("2011445392@qq.com",msg)    


def runtimestate(isoprofile, type):
    
    time.sleep(2000)
    
    cucmssh, rst=Login_ssh(isoprofile, type)      
    
    test_num = cucmssh.expect( ['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None )            
    #relogin
    if test_num != 0:
        del cucmssh
        print "=========login error, test_num = ", test_num
        cucmssh, rst = Login_ssh(isoprofile, type)      
    
    cucmssh.sendline("utils dbreplication runtimestate")
    
    #waiting ....
    test_num = cucmssh.expect( ['admin:', pexpect.EOF, pexpect.TIMEOUT], timeout=None )            
    #relogin
    if test_num != 0:
        del cucmssh
        print "=========login error, login_num = ", test_num
        cucmssh, rst = Login_ssh(isoprofile, type)   
        
    cucmssh.sendline("")
    screenshot("%s.%s-runtimestate.png"%(time.time(),type))



#run: python autotest_new.py /home/work/ISO/UCSInstall_UCOS_8.5.1.16109-1.sgn.iso
if __name__ == '__main__':

    ISOTIMEFORMAT = '[' + os.path.basename(sys.argv[0]) + ']%Y%m%d %H:%M:%S.log' 
    filename = time.strftime(ISOTIMEFORMAT, time.localtime())
    
    target = open (filename, 'a')
    target.close()    
         
    logging.basicConfig(filename=filename, level=logging.DEBUG)
    logging.debug('\n' * 10)
    logging.debug('------------------------   start a new test   ---------------------------')
    logging.debug('\n' * 10)
    logging.info('')
     
    try:
        p = optparse.OptionParser(
        description="######    Cisco CUCM ESTest Automation process v1.0    ######",
        prog='A2ES',
        usage='%prog -f isofile ')
        
        p.add_option('--file', '-f', help="CUCM ISO file path")
        options, arguments = p.parse_args()

        # ========  Information prepare before test  ======== #
        if len(arguments) == 1:
            if (arguments[0].split('.')[-1].lower() == "iso"):
                
                # ======== get current CUCM info ======== #
                print arguments[0]    
                ISOprofile = get_ISO_profile(arguments[0])
                LOCALISOPATH = os.path.abspath(arguments[0])
            else:
                print ""
                print "*********>> It's not CUCM ISO file! <<*********\r\n*********>> Please check your ISO path<<*********"
                print ""
                subject = "parameter error"
                body = "ChuWa CUCM ES-Testing ERROR:parmaeter error" 
                send_mail(sender,receiver,subject,body,smtpserver,psw)

                #sendNotify("2011445392@qq.com","ChuWa CUCM ES-Testing ERROR: parameter error")
                sys.exit(-1)
        else:
            p.print_help()
            sys.exit(-1)
        
        # ========  Basic Information check  ======== #
        result = Basic_Info_Check(ISOprofile)
        
        if not result:
            sys.exit(-1)
        
        HOST        =     ISOprofile[1] #172.16.128.203
        USER        =     ISOprofile[2] #root
        PASSWORD    =     ISOprofile[3] #Cisc012$
        DATASTORE   =     ISOprofile[4] #datastore911re
        DATACENTER  =     ISOprofile[5] #ha-datacenter
        MD5         =     ISOprofile[6] #78802660C49B2A2C825B1FD85F41BC50
        PUBCUCMVM   =     ISOprofile[7] #[datastore911re] cucm-pub/cucm-pub.vmx
        
        PUBCUCMIP   =     ISOprofile[8] #10.22.223.2
        PUBCUCMUSER =     ISOprofile[9] #cisco
        PUBCUCMPWD  =     ISOprofile[10]#Cisc012$
        SUBCUCMVM   =     ISOprofile[11]#[datastore911re] cucm-sub/cucm-sub.vmx
        SUBCUCMIP   =     ISOprofile[12]#10.22.223.3
        SUBCUCMUSER =     ISOprofile[13]#cisco
        SUBCUCMPWD  =     ISOprofile[14]#Cisc012$

        
        print ""
        print "*********>> ISO profile info get succesfully! <<*********"
        print ""
        
        print "#====== ISO profile info detail ======#"
        print "#"*80
        print "#    profile hostIP: %s" % HOST
        print "#    profile hostuser: %s" % USER
        print "#    profile hostpass: %s" % PASSWORD
        print "#    profile datastore: %s" % DATASTORE
        print "#    profile datacenter: %s" % DATACENTER
        print "#    profile MD5: %s" % MD5
        print "#    profile PUB vmpath: %s" % PUBCUCMVM
        print "#    profile SUB vmpath: %s" % SUBCUCMVM
        print "#"*80
        
        
        # ========  ISO MD5 Check ======== #
        #if not verify_ISO_MD5(LOCALISOPATH,MD5):
        #    sys.exit(-1)
        
        # ========  start vmware API call  ======== #
        server = VIServer()
        server.connect(HOST, USER, PASSWORD)
        if server.is_connected():
            server.keep_session_alive()
            print ""
            print "*********>> EXSI host connect succesfully! <<*********"
            print ""


            # ========  Get EXSI host info  ======== #
            Get_Host_Info(server)

            # ========  old CUCM version check  ======== #

            rst = CUCM_version_check(server, PUBCUCMVM, get_name_from_path(LOCALISOPATH))
            if not rst[0]:
                sys.exit(-1)
                
            print '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
            print 'LOCALISOPATH=', LOCALISOPATH
            print 'get_name_from_path(LOCALISOPATH)=', get_name_from_path(LOCALISOPATH)             
                
            for i in range(len(ISOprofile)):
                print  'ISOprofile[' + str(i) + ']=', ISOprofile[i]
                
            for i in range(len(rst)):
                print  'rst[' + str(i) + ']=', rst[i]               
            
            print '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'   
                
            # ========  special CUCM version preupdate  ======== #
            #1
            CUCM_special_update(rst[1], rst[2], server, ISOprofile)

            #1.5 ========  Upload ISO to the EXSI host  ======== #
            remoteisopath = Upload_cisco_ISO(server, DATASTORE, DATACENTER,LOCALISOPATH)
          
            
            #2 ========  Mount the new ISO for the PUB VM  ======== #
            Mount_cisco_ISO(server, PUBCUCMVM, remoteisopath)
            
            logging.info('+++++++++++++++++++++++++++++++++ start to upgrade PUB ......... +++++++++++++++++++++++++++++++++++')

            #3 ========  Run expect script to start cisco upgrade command for PUB ======== #
            Run_upgrade_command(server, ISOprofile, "PUB")
            
            logging.info('+++++++++++++++++++++++++++++++++ Run_upgrade_command() PUB successful +++++++++++++++++++++++++++++')
            
            #3.5
            server = vm_connect(server, ISOprofile)
            
            logging.info('+++++++++++++++++++++++++++++++++ start to mount SUB ISO file..... ++++++++++++++++++++++++++++++++++')
            
            #4 ========  Mount the new ISO for the SUB VM  ======== #
            Mount_cisco_ISO(server, SUBCUCMVM, remoteisopath)
            
            body = "Keep the connect status of the '%s' VM be connected by hand!"%ISOprofile[12]
            subject = "connect vm by hand"
            print "*"*6, body, "*"*6 
            
            logging.info('+++++++++++++++++++++++++++++++++ mount SUB ISO file successfully +++++++++++++++++++++++++++++++++++++')
            send_mail(sender, receiver, subject, body, smtpserver, psw)

            #sendNotify("2011445392@qq.com",msg) 
            time.sleep(60)
            # ========  Run expect script to start cisco upgrade command for SUB ======== #
           
            logging.info('+++++++++++++++++++++++++++++++++ start to upgrade SUB ......... +++++++++++++++++++++++++++++++++++++++')
            
            #5
            Run_upgrade_command(server, ISOprofile, "SUB")
            
            logging.info('+++++++++++++++++++++++++++++++++ Run_upgrade_command() SUB successful +++++++++++++++++++++++++++++++++')
            logging.info('+++++++++++++++++++++++++++++++++ start to switch pub ++++++++++++++++++++++++++++++++++++++++++++++++++')
            
            #6
            Run_Switch_command(server, ISOprofile, "PUB") 
            
            logging.info('+++++++++++++++++++++++++++++++++  switch pub end  ++++++++++++++++++++++++++++++++++++++++++++++++++++++')
            logging.info('+++++++++++++++++++++++++++++++++  start to switch sub ++++++++++++++++++++++++++++++++++++++++++++++++++')
                 
            #7
            Run_Switch_command(server, ISOprofile, "SUB")
            
            logging.info('+++++++++++++++++++++++++++++++++  switch sub end  ++++++++++++++++++++++++++++++++++++++++++++++++++++++')
            
            #8  
            runtimestate(ISOprofile, "PUB")
            
            logging.info('+++++++++++++++++++++++++++++++++  runtimestate(ISOprofile,"PUB") successfully +++++++++++++++++++++++++++')
            
            succ_info = "\n\n=========Congratulations, all upgrades successful done!!==========\n\n"
            
            logging.info(succ_info)
            print succ_info
            
            # ========  BAT test  ======== #
            #CUCMVERSION = '8.6'
            #PUBCUCMIP = '172.16.128.103'
            #Bat_test("addphone",CUCMVERSION,PUBCUCMIP,700)
        else:
            print ""
            print "*********>> EXSI host connect error! <<*********"
            print ""
            sys.exit(-1)
            
        subject = "all successfully end"
        logging.info('*****************' + subject + '**************************')
        body = "ChuWa CUCM ES-Testing all successfully end!" 
        send_mail(sender,receiver,subject,body,smtpserver,psw)

        #sendNotify("2011445392@qq.com","ChuWa CUCM ES-Testing successfully end!")
    except KeyboardInterrupt:
        sys.stdout('\nQuitting examples.\n')
        subject = "Testing Interrupt"
        body = "ChuWa CUCM ES-Testing Interrupt!" 
        send_mail(sender,receiver,subject,body,smtpserver,psw)

        #sendNotify("2011445392@qq.com","ChuWa CUCM ES-Testing Interrupt!")
        sys.exit(-1)

