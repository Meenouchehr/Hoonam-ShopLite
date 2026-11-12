from django.db import models
from mongoengine import Document, EmbeddedDocument, fields
# Create your models here.

class Log(Document):
    authorization=fields.StringField(null=True,blank=True)
    http_cookie=fields.StringField(null=True,blank=True)
    csrf_cookie=fields.StringField(null=True,blank=True)
    query_string=fields.StringField(null=True,blank=True)
    scheme=fields.StringField(null=True,blank=True)
    url=fields.StringField(null=True,blank=True)
    address=fields.StringField(null=True,blank=True)
    method=fields.StringField(null=True,blank=True)
    function=fields.StringField(null=True,blank=True)
    body=fields.StringField(null=True,blank=True)
    data=fields.StringField(null=True,blank=True)
    user=fields.StringField(null=True,blank=True)
    date=fields.StringField(null=True,blank=True)
    status_code=fields.StringField(null=True,blank=True)
    status_text=fields.StringField(null=True,blank=True)
    exception=fields.StringField(null=True,blank=True)
    exception_data=fields.StringField(null=True,blank=True)

