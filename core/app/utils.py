from django.core.mail import send_mail, EmailMessage


class Util:
    @staticmethod
    def sendNotificationEmail(email, subject=None,message=None):
        email_message = EmailMessage(subject=subject,
                                     body=message,
                                     to=[email])
        email_message.send()

    @staticmethod
    def sendInvitationEmail(email, url,message=None):
        body = """
                Message: {0}
                Link: {1}
        """.format(message,url)
        email_message = EmailMessage(subject='Invitation to join the company',
                                     body=body,
                                     to=[email])
        email_message.send()


def sendVerificationSMS(cellphone, verification_code):
    import requests
    import json
    import re
    
    url = "https://ippanel.com/api/select"
    username = "mysms-tehran"
    password = "0073988200aA@"
    sender_one = "5000125475"
    sender_two = "3000505"
    if type(cellphone) != type([]):
        cellphone = [cellphone]
    _data = {   "op":"send",
                "uname":username,
                "pass":	password,
                "message":verification_code,
                "from":sender_one,
                "to":cellphone
            }
    _headers = {"Content-type": "application/json"}
    _response = requests.post(url, data=json.dumps(_data), headers=_headers)
    if re.match(r'^\[0,',_response.text):
        return {"result": _response.text, "status": _response.status_code}
    else:
        _data.pop('from',None)
        _data['from'] = sender_two
        _response = requests.post(url, data=json.dumps(_data), headers=_headers)
        if re.match(r'^\[0,',_response.text):
            return {"result": _response.text, "status": _response.status_code}
        else:
            return {"result": _response.text, "status": _response.status_code}
    
