from rest_framework import serializers
from django.utils.translation import gettext as _
# from django_filters.filters import *
# from django_filters.rest_framework import *
from app.models import *


class BaseFilterSerializer(serializers.Serializer):
    STATUS_CHOICE = ((-1, 'trash'), (0, 'unpublish'), (1, 'publish'))
    
    search = serializers.CharField(max_length=None, required=False)
    status = serializers.ChoiceField(help_text=_("انتخاب وضعیت"),choices=STATUS_CHOICE,required=False,)


    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)

    def validate(self, attrs):
       
        return attrs  



# Address:
class AddressFilterSerializer(BaseFilterSerializer):
    
    owner  = serializers.IntegerField(required=False)
    is_default = serializers.BooleanField(required=False)
   


# Attribute:
class AttributeFilterQuerySerializer(serializers.Serializer):
    
    owner   = serializers.IntegerField(required=False)
    feature = serializers.IntegerField(required=False)
    service = serializers.IntegerField(required=False)
    
    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)


# Bank:
class BankFilterSerializer(BaseFilterSerializer):
   pass

# Banner:
class BannerFilterSerializer(BaseFilterSerializer):
    pass


# Basket:
class BasketFilterQuerySerializer(serializers.Serializer):
    
    owner   = serializers.IntegerField(required=False)
    service = serializers.IntegerField(required=False)
    
    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)


# Blog:
class BlogFilterSerializer(BaseFilterSerializer):
    alias  = serializers.CharField(max_length=None, required=False)
    set     = serializers.CharField(max_length=None,required=False)
    tag     = serializers.CharField(max_length=None,required=False)

    def validate(self, attrs):
        return attrs


# Category:
class CategoryFilterSerializer(BaseFilterSerializer):
    group = serializers.IntegerField(required=False)

# Cluster:
class ClusterFilterQuerySerializer(serializers.Serializer):
    STATUS_CHOICE = ((-1, 'trash'), (0, 'unpublish'), (1, 'publish'))
    
    search = serializers.CharField(max_length=None, required=False)
    status = serializers.MultipleChoiceField(help_text="Select object status",choices=STATUS_CHOICE,required=False,)
    cluster   = serializers.IntegerField(required=False)

    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)

    def validate(self, attrs):
        return attrs
class ClusterTrashFilterQuerySerializer(serializers.Serializer):
    search = serializers.CharField(max_length=None, required=False)

    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)

    def validate(self, attrs):
        return attrs

# Commission:
class CommissionFilterSerializer(BaseFilterSerializer):
    
    company  = serializers.IntegerField(required=False)
    category  = serializers.IntegerField(required=False)
    owner  = serializers.IntegerField(required=False)
    service  = serializers.IntegerField(required=False)
   
# Company:
class CompanyFilterSerializer(BaseFilterSerializer):
    pass


# Document:
class DocumentFilterQuerySerializer(serializers.Serializer):
    
    owner   = serializers.IntegerField(required=False)
    record  = serializers.IntegerField(required=False)
    service = serializers.IntegerField(required=False)
    
    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)


# Evidence:
class EvidenceFilterSerializer(BaseFilterSerializer): 
    media  = serializers.ChoiceField(choices=EvidenceModel.MEDIA_CHOICE,required=False)


# FaqCategory:
class FaqCategoryFilterSerializer(BaseFilterSerializer):
    pass


# Faq:
class FaqFilterSerializer(BaseFilterSerializer):
    category= serializers.IntegerField(required=False)
    cattegory_slug=serializers.CharField(required=False)


# Feature:
class FeatureFilterQuerySerializer(serializers.Serializer):
    
    service  = serializers.IntegerField(required=False)
    property = serializers.IntegerField(required=False)
    
    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)


# Group:
class GroupFilterSerializer(BaseFilterSerializer):
    pass

# Grade:
class GradeFilterSerializer(BaseFilterSerializer):
    pass

# Porsant:
class PorsantFilterSerializer(BaseFilterSerializer):
    
    category  = serializers.IntegerField(required=False)
    company  = serializers.IntegerField(required=False)        
    owner  = serializers.IntegerField(required=False)
    service  = serializers.IntegerField(required=False)


# Property:
class PropertyFilterQuerySerializer(serializers.Serializer):
    
    search = serializers.CharField(max_length=None, required=False)
    type   = serializers.ChoiceField(choices=PropertyModel.TYPE_CHOICE,required=False)

    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)


# Record:
class RecordFilterQuerySerializer(serializers.Serializer):
    
    service  = serializers.IntegerField(required=False)
    evidence = serializers.IntegerField(required=False)
    
    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)


# Service:
class ServiceFilterSerializer(BaseFilterSerializer):
    SORT_CHOICE = (('new', 'new'), ('best_sellers', 'best_sellers'),('old','old'),('high','high'),('low',('low')))
    
    search    = serializers.CharField(max_length=None, required=False)
    category  = serializers.CharField(max_length=None,required=False)
    company  = serializers.CharField(max_length=None,required=False)
    filter   = serializers.ListField(child=serializers.IntegerField(),required=False)
    sort    = serializers.ChoiceField(help_text="Select object status",choices=SORT_CHOICE,required=False,)
    price_low = serializers.IntegerField(required=False)
    price_up  = serializers.IntegerField(required=False)
    is_revival = serializers.BooleanField(required=False)
    is_special = serializers.BooleanField(required=False)


class ServiceRelatedFilterSerializer(BaseFilterSerializer):
    search=None
    status=None
# Service Dependent:
class ServiceDependentFilterSerializer(BaseFilterSerializer):
    search=None
    service= serializers.IntegerField(required=False)


# ServiceGallery:
class ServiceGalleryFilterSerializer(BaseFilterSerializer):
    search=None
    status=None
    service = serializers.IntegerField(required=False)
    
# Set
class SetFilterSerializer(BaseFilterSerializer):
    pass

# Shop:
class ShopFilterQuerySerializer(serializers.Serializer):
    
    owner   = serializers.IntegerField(required=False)
    agent   = serializers.IntegerField(required=False)
    seller = serializers.IntegerField(required=False)
    service = serializers.IntegerField(required=False)
    date_start  = serializers.CharField(help_text=" e.g. : 1400/11/23",required=False)
    date_end    = serializers.CharField(help_text=" e.g. : 1400/11/23",required=False)
    state       = serializers.CharField(required=False)

    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)


# Status:
class StatusFilterSerializer(BaseFilterSerializer):
    is_system = serializers.BooleanField(required=False)    
   

# Stock:
class StockFilterQuerySerializer(serializers.Serializer):
    KIND_CHOICE = (("input", "input"), ("output", "output"))

    product = serializers.IntegerField(required=False)
    kind    = serializers.ChoiceField(choices=KIND_CHOICE, required=False)
    
    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)

    def validate(self, attrs):
        return attrs


# Support:
class SupportFilterSerializer(BaseFilterSerializer):
   pass
   



# Tag:
class TagFilterSerializer(BaseFilterSerializer):
   pass


# User Filter:
class UserFilterSerializer(BaseFilterSerializer):
    ROLE_CHOICE = (
            ("agent", "agent"),
            ("client", "client"),
            ("seller", "seller"),
        )
    role = serializers.MultipleChoiceField(help_text="roles field", choices=ROLE_CHOICE, required=False)


# UserEvidence:
class UserEvidenceFilterSerializer(BaseFilterSerializer):
    search=None
    status=None
    media  = serializers.ChoiceField(choices=UserEvidenceModel.MEDIA_CHOICE,required=False)
   
# UserFile:
class UserFileFilterSerializer(BaseFilterSerializer):
    search=None
    status=None
    owner    = serializers.IntegerField(required=False)
    evidence = serializers.IntegerField(required=False)



# WalletFile:
class WalletFilterQuerySerializer(serializers.Serializer):
    owner    = serializers.IntegerField(required=False)
        
    page_size = serializers.IntegerField(required=False)
    page_num = serializers.IntegerField(required=False)
