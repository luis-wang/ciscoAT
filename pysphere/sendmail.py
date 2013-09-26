#coding=utf-8
#!/usr/bin/python

import smtplib
from email.header import Header
from email.mime.text import MIMEText

sender = 'lijunsong@chuwasoft.com'
psw = 're_jy'
receiver = '821090701@qq.com'
smtpserver = 'mail.chuwasoft.com'


def send_mail(sender, receiver, subject, body, smtpserver, psw):
    try:
        msg = MIMEText('<html><h2>%s</h2></html>'%body,'html','utf-8')
        msg['Subject'] = subject
        smtp = smtplib.SMTP()
        smtp.connect(smtpserver)
        smtp.login(sender, psw)
        smtp.sendmail(sender, receiver, msg.as_string())
        smtp.quit()
    except Exception,ex:
        print ex
  

if __name__ == '__main__':
    sender = 'lijunsong@chuwasoft.com'
    psw = 're_jy'
    receiver = '821090701@qq.com'
    subject = 'test'
    body = 'this is a test email - wxd'
    smtpserver = 'mail.chuwasoft.com'
    
    send_mail(sender, receiver, subject, body, smtpserver,psw) 




