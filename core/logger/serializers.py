from rest_framework import serializers
from rest_framework_mongoengine import serializers as _serializers
from logger.models import *
from django.utils.translation import gettext as _
# from chat.models import ChatModel,STATUS_CHOICE
# from app.models import TaskModel
# from general.user.models import UserModel
# from general.user.serializers import UserSerializer
# from app.serializers import TaskSerializer
# from general.helpers import *

 

class LogSerializer(_serializers.DocumentSerializer):
    class Meta:
        model = Log
        fields = ('id', 'authorization', 'http_cookie','csrf_cookie','query_string','scheme','url','function','body','method','data','status_code','status_text','date','user','address','exception','exception_data' )
    
    authorization=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    http_cookie=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    csrf_cookie=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    query_string=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    scheme=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    url=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    address=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    function=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    body=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    method=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    data=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    date=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    user=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    status_code=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    status_text=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    exception=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    exception_data=serializers.CharField(required=False,max_length=None,allow_null=True,allow_blank=True)
    
    def validate(self, attrs):
        return super(LogSerializer, self).validate(attrs)
    
    def create(self, validated_data): 
        _new_instance = self.Meta.model(**validated_data)      
        _new_instance.save()
        return _new_instance  



   