#coding=utf-8
#!/usr/bin/python
'''
Created on Sep 6, 2013

@author: root
'''


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