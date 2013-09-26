#coding=utf-8
#!/usr/bin/python

import os
import re
import sys
import time
import string
import threading

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select,WebDriverWait
from selenium.common.exceptions import NoSuchElementException,WebDriverException
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0


def saveScreenshotImg(driver, name):   
    ISOTIMEFORMAT = name + '_%Y%m%d%H%M%S.png' 
    filename = time.strftime(ISOTIMEFORMAT, time.localtime())        
    path = os.path.join(os.path.dirname(sys.argv[0]), filename)
    
    print 'saved ' + name + ' img to the path = ', path
    
    driver.get_screenshot_as_file( path )    
    

class WaitForUpgrade(threading.Thread):
    def __init__(self,driver,timeout):
        threading.Thread.__init__(self)
        self.dr = driver 
        self.status = -1
        self.interval = timeout 
        
    def run(self):
        while True:
            print '-----[class WaitForUpgrade] upgrade is running...'
            
            status_ = self.dr.find_element_by_id("installStatus").text
            status = string.strip(status_)
            print status
            while True:
                if status.startswith("The system upgrade was successful."):
                    print 'upgrade is successful'
                    self.status = 1
                    break
                else:
                    self.status = -1	 
        
                if self.status == 1:
                    break
                elif self.status == -1:
                    print "upgrade is running..."
                    time.sleep(self.interval)


class TestPhone():
    def __init__(self, host):
        self.base_host = host
        self.base_url = 'https://%s' % self.base_host
        
    
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.verificationErrors = []
        self.accept_next_alert = True  
         
             
    def clearData(self):
        self.driver.close()    

        
    def insertPhone(self):
        self.setUp()
        
        driver = self.driver    
        driver.get(self.base_url + "/ccmadmin/showHome.do")
        print '--opened the home page---'
        
        driver.maximize_window()       

        driver.find_element_by_name("j_username").send_keys("cisco")
        driver.find_element_by_name("j_password").send_keys("Cisc012$")         
        
        driver.find_element_by_css_selector("button.cuesLoginButton").click() 
        print '--login successfully ' 

        
        driver.get(self.base_url + '/ccmadmin/bulkphoneinsertEdit.do')

        filename = driver.find_element(By.NAME, "filename")
        allOptions = filename.find_elements_by_tag_name("OPTION")
        for option in allOptions:
            if option.get_attribute("value") != '':
                option.click()
                
        time.sleep(1)

        phonetemplate = driver.find_element(By.NAME,"phonetemplate")
        allOptions = phonetemplate.find_elements_by_tag_name("OPTION")
        for option in allOptions:
            if option.get_attribute("value") != '':
                option.click()
                break
            
        time.sleep(1)
        
        #runimmediately  
        inputs = driver.find_elements(By.XPATH, "//input")
        for input in inputs:
            if input.get_attribute("name") == 'runimmediately' and input.get_attribute("value") == 'true':
                input.click()
                break
            
        time.sleep(2)

        driver.find_element(By.NAME,"Submit").click()
        
        print '*' * 80
        print 'insert phone successful, wait for screenshot....'
        print '*' * 80
        
        #saveScreenshotImg(driver, 'insert_phone_successful')
        time.sleep(3)
        print '===================start to check the insert job status================'
        
        self.checkJobScheduler()
        
        print '===================end checking the insert job status================'
        time.sleep(2) 

        driver.close()

   
    def checkJobScheduler(self):

        driver = self.driver  
        job_url = self.base_url + "/ccmadmin/showHome.do"
        driver.get(job_url)
        print '--opened the job schedule page---'    
        
        #check into job scheduler page
        #driver.find_element_by_link_text("Job Scheduler").click()        
        driver.get(self.base_url + "/ccmadmin/bulkjobFindList.do")
        
        # ERROR: Caught exception [ReferenceError: selectLocator is not defined]
        driver.find_element_by_css_selector("option[value=\"batjob.Jobid\"]").click()
        driver.find_element_by_name("findButton").click()
        
        time.sleep(10)
        
        #find the last jobid, then click it
        #driver.find_element_by_link_text("1379838026").click()
        """              
        try:
            element = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "myDynamicElement")))
        finally:
            print '----errors when WebDriverWait(ff, 30)'
            pass
            #driver.quit()
        """
        
        
        #++++++++++++++++++++++++++++++++++++++++++++++=
        
        jobid_table = None        
        find_tables = driver.find_elements_by_tag_name("table")
        
        for table in find_tables:
            if table.get_attribute("class") == 'cuesTableBg':
                print 'yes , got the correct table'
                jobid_table = table
               
        trs = jobid_table.find_elements_by_tag_name("tr")
                
        last_tr = trs[-1]
        
        #find the tds in last tr
        tds = last_tr.find_elements_by_tag_name('td')
        for td in tds:
            a_links = td.find_elements_by_tag_name('a')
            if len(a_links) > 0:
                #bulkjobEdit.do?key=d226227e-5083-8b45-c65b-4181cc985000
                newest_job_href = a_links[0].get_attribute('href')                
                print '-----going to the job page :', newest_job_href
                break
            else:
                newest_job_href = job_url
                print '-----the page is not valid----'
        

        all_links = driver.find_elements_by_tag_name('a')
        for link in all_links:
            if link.get_attribute('href') == newest_job_href:
                link.click()
                break
            
        time.sleep(10)
        
        #analyze the job schedule page
        while True:
            tr = driver.find_element(By.CSS_SELECTOR, ".content-grid-stripe-dark")
            results_tds = tr.find_elements_by_tag_name("td")    
        
            """
            09/22/2013 16:20:27
            Success
            125
            0
            780
            1379838026#09222013162027.txt
            """    
            results_status      = results_tds[1].text
            processed_number    = int(results_tds[2].text)
            failed_number       = int(results_tds[3].text)
            total_Number        = int(results_tds[4].text)
            
            if results_status == 'Success' and processed_number == total_Number:
                saveScreenshotImg(driver, 'job_ended_successful')
                print 'results_status = ', results_status, 'total_Number = ', total_Number, 'processed_number = ', processed_number
                print '----------the job ended-------'                
                break
            elif results_status != 'Success' and processed_number == total_Number:
                saveScreenshotImg(driver, 'job_ended_error')
                print 'results_status = ', results_status, 'total_Number = ', total_Number, 'processed_number = ', processed_number
                print '----------the job ended with error-------'                
                break                
            else:
                print 'total_Number = ', total_Number, 'processed_number = ', processed_number
                print '----------refresh to wait for the job end-------'   
                driver.refresh()
                time.sleep(15)           
                
        
        
                           
        
    def deletePhones(self):
        
        self.setUp()
        driver = self.driver  
        driver.get(self.base_url + "/ccmadmin/showHome.do")
        print '--opened the home page---'       

        driver.find_element_by_name("j_username").send_keys("cisco")
        driver.find_element_by_name("j_password").send_keys("Cisc012$")         
        
        driver.find_element_by_css_selector("button.cuesLoginButton").click() 
        print '--login successfully ' 
        
        driver.maximize_window()  
        
        driver.get(self.base_url + '/ccmadmin/bulkphonedeleteFindList.do')
        driver.find_element_by_id("searchString0").send_keys("SEP000903000")
        
        #step 1: search
        driver.find_element_by_name("findButton").click()
        
        #step 2: runimmediately
        inputs = driver.find_elements(By.XPATH, "//input")
        for input in inputs:
            if input.get_attribute("name") == 'runimmediately' and input.get_attribute("value") == 'true':
                input.click()
                break 
            
        #step 3: submit
        driver.find_element_by_id("1tblcenter").click()  

        
        """
        while True:            
            driver.find_element_by_name("findButton").click()
            time.sleep(6)
            try:            
                driver.execute_script('alert(document.getElementById("status-info-txt").innerHTML);')
            except WebDriverException:
                print 'continue running delete, please wait......'
                continue
            
            try:
                alert = driver.switch_to_alert()
                status_text = alert.text
                print 'status_text = ', status_text
                time.sleep(2)
                alert.accept()
            except:
                print "no alert to accept"            
            
        
            if status_text.startswith('0 records found'):
                print '----phone delete complete----'
                break
            else:
                print'----phone delete not complete----'
                time.sleep(10)        
        """
        
        time.sleep(3)
        print '===================start to check the delete job status================'
        
        self.checkJobScheduler()
        
        print '===================end checking the delete job status================'
        time.sleep(2)  
        
        #saveScreenshotImg(driver, 'delete_phone_successful')

        driver.close()
        
            

class Cucmweb():
    def __init__(self, host):
        self.base_host = host
        self.base_url = 'https://%s' % self.base_host
        #self.TC = TestCase
        self.setUp()
        
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.verificationErrors = []
        self.accept_next_alert = True
        
    def clearData(self):
        #self.driver.close()
        self.driver.quit()
        
    def upgrade(self):
        driver = self.driver
               
        driver.get(self.base_url + "/cmplatform/showHome.do")
        print '--opened the home page'
        
        
        driver.find_element_by_name("j_username").send_keys("cisco")
        driver.find_element_by_name("j_password").send_keys("Cisc012$")        
        
        driver.find_element_by_css_selector("button.cuesLoginButton").click()
        print '--login successfully '
        driver.find_element_by_id("SoftwareUpgradesButton").click()
        
        #driver.find_element_by_link_text("Install/Upgrade").click()
        
        driver.get(self.base_url+"/cmplatform/install.do")
        
        time.sleep(1) 
        elem = driver.find_element_by_id("DIRECTORY").get_attribute("disabled")
        print elem	
        
        if elem:
            driver.execute_script('document.getElementById("DIRECTORY").disabled=false;')
        
        driver.find_element_by_id("DIRECTORY").send_keys("/")
        driver.find_element_by_name("Next").click()
        driver.find_element_by_name("Next").click()
        driver.find_element_by_name("Next").click()
        
        print '22', '-------to accept an alert-------'
        
        try:
            art1 =driver.switch_to_alert()
            art1.accept()
        except:
            print '=========there is no alert prompt=========art1 = ', art1
        
        try:
            art2 =driver.switch_to_alert()
            art2.accept()
        except:
            print '=========there is no alert prompt=========art2 = ', art2
        
        print '33',''
        
        #if driver.is_confirmation_present():
        #print driver.get_confirmation()
      
        while True:
            #this step will occur err
            try:
                sta = driver.find_element_by_id("installStatus").text
                
            except NoSuchElementException:
                print '\n' * 3
                print '*' * 80
                print 'Please browse into the datastore in VM setting, the status of CD/DVD drive SHOULD be connected!'
                print '*' * 80
                print '\n' * 3
                sys.exit(-1)

            status = string.strip(sta)
            print '------------- status = %s-------------' % status
            
            if status.startswith("The system upgrade was successful."):
                up_status = True
                print '************upgrade was successful************'
                break
            
            else:
                up_status = False
                print 'please wait.....'
                time.sleep(60)
    
    def switch(self):
        driver = self.driver
        driver.get(self.base_url + "/")
        driver.find_element_by_link_text("Cisco Unified Communications Manager").click()
        # ERROR: Caught exception [ReferenceError: selectLocator is not defined]
        driver.find_element_by_name("go").click()
        driver.find_element_by_name("j_username").clear()
        driver.find_element_by_name("j_username").send_keys("cisco")
        driver.find_element_by_name("j_password").clear()
        driver.find_element_by_name("j_password").send_keys("Cisc012$")
        driver.find_element_by_css_selector("button.cuesLoginButton").click()
        driver.find_element_by_id("SettingsButton").click()
        driver.find_element_by_link_text("Version").click()
        
        
if __name__ == "__main__":
    #w = Cucmweb('10.22.221.4')
    #w.upgrade()
    tp = TestPhone('10.22.221.4')
    tp.insertPhone()
    tp.deletePhones()
    #tp.checkJobScheduler()

