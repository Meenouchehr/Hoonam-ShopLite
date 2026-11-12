from rest_framework import serializers
from django.utils.translation import gettext as _

from app.models import *


class OwnerSchemaSerializer(serializers.Serializer):
    
    id          = serializers.IntegerField(read_only=True)
    avatar      = serializers.URLField(read_only=True)
    first_name  = serializers.CharField(read_only=True)
    last_name   = serializers.CharField(read_only=True)
    name        = serializers.CharField(read_only=True)
    username    = serializers.CharField(read_only=True)
    email       = serializers.EmailField(read_only=True)
    cellphone   = serializers.CharField(read_only=True)
    gender      = serializers.CharField(read_only=True)
    status      = serializers.IntegerField(read_only=True)
    is_active   = serializers.BooleanField(read_only=True)
    created     = serializers.DateTimeField(read_only=True)
    agent       = serializers.IntegerField(read_only=True)


# Address:
class AddressSchemaSerializer(serializers.Serializer):
    id          = serializers.IntegerField(read_only=True)
    owner       = serializers.IntegerField(read_only=True)
    latitude    = serializers.IntegerField(read_only=True)
    longitude   = serializers.IntegerField(read_only=True)
    province    = serializers.CharField(read_only=True)
    city        = serializers.CharField(read_only=True)
    district    = serializers.IntegerField(read_only=True)
    postal_code = serializers.CharField(read_only=True)
    address     = serializers.CharField(read_only=True)
    comment     = serializers.CharField(read_only=True)
    is_default  = serializers.BooleanField(read_only=True)
class AddressListSchemaSerializer(serializers.Serializer):
    list            = AddressSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)
  

class AttributeSchemaSerializer(serializers.Serializer):
       
    id      = serializers.IntegerField(read_only=True)
    owner   = serializers.IntegerField(read_only=True)
    feature = serializers.IntegerField(read_only=True)
    value   = serializers.CharField(read_only=True)


class BasketItemSchemaSerializer(serializers.Serializer):
    id      = serializers.IntegerField(read_only=True)
    service = serializers.IntegerField(read_only=True)
    price   = serializers.IntegerField(read_only=True)
    qty     = serializers.IntegerField(read_only=True)
    final_price = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True)
class BasketSchemaSerializer(serializers.Serializer):
    id      = serializers.IntegerField(read_only=True)
    owner   = OwnerSchemaSerializer(read_only=True)
    date    = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(read_only=True)
    items   = BasketItemSchemaSerializer(read_only=True,many=True)
class BasketListSchemaSerializer(serializers.Serializer):
    list            = BasketSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)


# Requirement Basket:
class BasketRequirementRecordInfoSerializer(serializers.Serializer):
    id              = serializers.IntegerField(read_only=True)
    evidence        = serializers.IntegerField(read_only=True)
    evidence_title  = serializers.CharField(read_only=True)
class BasketRequirementFeatureInfoSerializer(serializers.Serializer):
    id              = serializers.IntegerField(read_only=True)
    property        = serializers.IntegerField(read_only=True)
    property_title  = serializers.CharField(read_only=True)
class BasketRequirementL1Serializer(serializers.Serializer):
    service  = serializers.IntegerField(read_only=True)
    records  = BasketRequirementRecordInfoSerializer(many=True,read_only=True)
    features = BasketRequirementFeatureInfoSerializer(many=True,read_only=True)
class BasketRequirementSchemaSerializer(serializers.Serializer):
    id      = serializers.IntegerField(read_only=True)
    owner   = serializers.IntegerField(read_only=True)
    requirement = BasketRequirementL1Serializer(many=True,read_only=True)


# Blog:
class BlogTagSchemaSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField(read_only=True)
class BlogSetSchemaSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField(read_only=True)
    slug         = serializers.CharField(read_only=True)
    description  = serializers.CharField(read_only=True)
    icon         = serializers.URLField(read_only=True)
    status       = serializers.IntegerField(read_only=True)
    # status_old   = serializers.IntegerField(read_only=True)
    parent       = serializers.IntegerField(read_only=True)
    order        = serializers.IntegerField(read_only=True)
class BlogSchemaSerializer(serializers.Serializer):
    id          = serializers.IntegerField(read_only=True)
    title       = serializers.CharField(read_only=True)
    alias       = serializers.CharField(read_only=True)
    owner       = serializers.IntegerField(read_only=True)
    image       = serializers.URLField(read_only=True)
    body        = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    status      = serializers.IntegerField(read_only=True)
    date        = serializers.DateField(read_only=True)
    set         = BlogSetSchemaSerializer(read_only=True)
    tags        = BlogTagSchemaSerializer(read_only=True,many=True)
class BlogListSchemaSerializer(serializers.Serializer):
    list            = BlogSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)


class CategoryServiceSchemaSerializer(serializers.Serializer):
    
    id          = serializers.IntegerField(read_only=True)
    title       = serializers.CharField(read_only=True)
    slug        = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    image       = serializers.URLField(read_only=True)
    price       = serializers.IntegerField(read_only=True)
    vat         = serializers.IntegerField(read_only=True)
    discount    = serializers.IntegerField(read_only=True)
    status      = serializers.IntegerField(read_only=True)
class CategoryChildSchemaSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField(read_only=True)
    slug         = serializers.CharField(read_only=True)
    description  = serializers.CharField(read_only=True)
    icon         = serializers.URLField(read_only=True)
    status       = serializers.IntegerField(read_only=True)
    # status_old   = serializers.IntegerField(read_only=True)
    parent       = serializers.IntegerField(read_only=True)
    order        = serializers.IntegerField(read_only=True)
    # servicesInfo = CategoryServiceSchemaSerializer(read_only=True,many=True)
class CategorySchemaSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField(read_only=True)
    slug         = serializers.CharField(read_only=True)
    description  = serializers.CharField(read_only=True)
    icon         = serializers.URLField(read_only=True)
    status       = serializers.IntegerField(read_only=True)
    # status_old   = serializers.IntegerField(read_only=True)
    parent       = serializers.IntegerField(read_only=True)
    order        = serializers.IntegerField(read_only=True)
    sub_categories = CategoryChildSchemaSerializer(read_only=True,many=True)
    # servicesInfo = CategoryServiceSchemaSerializer(read_only=True,many=True)
class CategoryListSchemaSerializer(serializers.Serializer):
    list            = CategorySchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)
    
    
class DocumentSchemaSerializer(serializers.Serializer):
       
    id      = serializers.IntegerField(read_only=True)
    owner   = serializers.IntegerField(read_only=True)
    record  = serializers.IntegerField(read_only=True)
    file    = serializers.URLField(read_only=True)


class EvidenceSchemaSerializer(serializers.Serializer):
    id          = serializers.IntegerField(read_only=True) 
    title       = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    media       = serializers.CharField(read_only=True)


class FeatureSchemaSerializer(serializers.Serializer):
    id              = serializers.IntegerField(read_only=True)
    service         = serializers.IntegerField(read_only=True)
    service_title   = serializers.CharField(read_only=True)
    property        = serializers.IntegerField(read_only=True)
    property_title  = serializers.CharField(read_only=True)


#Login ???



class ProfileSchemaSerializer(serializers.Serializer):
    owner         = serializers.IntegerField(read_only=True)
    father_name   = serializers.CharField(read_only=True)
    id_no         = serializers.IntegerField(read_only=True)
    national_code = serializers.CharField(read_only=True)
    birthday      = serializers.CharField(read_only=True)
    age           = serializers.IntegerField(read_only=True)
    birthplace    = serializers.CharField(read_only=True)
    married       = serializers.BooleanField(read_only=True)
    children      = serializers.IntegerField(read_only=True)
    latitude      = serializers.IntegerField(read_only=True)
    longitude     = serializers.IntegerField(read_only=True)
    province      = serializers.CharField(read_only=True)
    city          = serializers.CharField(read_only=True)
    district      = serializers.IntegerField(read_only=True)
    address       = serializers.CharField(read_only=True)
    comment       = serializers.CharField(read_only=True)
    tel           = serializers.CharField(read_only=True)


class PropertySchemaSerializer(serializers.Serializer):
    id          = serializers.IntegerField(read_only=True) 
    title       = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    type        = serializers.CharField(read_only=True)


class RecordSchemaSerializer(serializers.Serializer):
    id              = serializers.IntegerField(read_only=True)
    service         = serializers.IntegerField(read_only=True)
    service_title   = serializers.CharField(read_only=True)
    evidence        = serializers.IntegerField(read_only=True)
    evidence_title  = serializers.CharField(read_only=True)

class ServiceCategorySchemaSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField(read_only=True)
    slug         = serializers.CharField(read_only=True)
    description  = serializers.CharField(read_only=True)
    icon         = serializers.URLField(read_only=True)
    status       = serializers.IntegerField(read_only=True)
    # status_old   = serializers.IntegerField(read_only=True)
    parent       = serializers.IntegerField(read_only=True)
    order        = serializers.IntegerField(read_only=True)
class ServiceGalleryInfoSchemaSerializer(serializers.Serializer):
    id      = serializers.IntegerField(read_only=True)
    file    = serializers.IntegerField(read_only=True)
class ServiceSchemaSerializer(serializers.Serializer):
    id          = serializers.IntegerField(read_only=True)
    title       = serializers.CharField(read_only=True)
    slug        = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    image       = serializers.URLField(read_only=True)
    status      = serializers.IntegerField(read_only=True)
    price       = serializers.IntegerField(read_only=True)
    vat         = serializers.IntegerField(read_only=True)
    discount    = serializers.IntegerField(read_only=True)
    final_price = serializers.IntegerField(read_only=True)
    # qty          = serializers.IntegerField(read_only=True)
    category    = ServiceCategorySchemaSerializer(read_only=True)
    galery      = ServiceGalleryInfoSchemaSerializer(read_only=True,many=True)
class ServiceListSchemaSerializer(serializers.Serializer):
    list            = ServiceSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)


class ServiceGallerySchemaSerializer(serializers.Serializer):
    id      = serializers.IntegerField(read_only=True)
    service = serializers.IntegerField(read_only=True)
    file    = serializers.IntegerField(read_only=True)
class ServiceGalleryListSchemaSerializer(serializers.Serializer):
    list            = ServiceGallerySchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)
      

# Shop for respose schema:
class ShopItemSchemaSerializer(serializers.Serializer):
    id      = serializers.IntegerField(read_only=True)
    service = serializers.IntegerField(read_only=True)
    price   = serializers.IntegerField(read_only=True)
    qty     = serializers.IntegerField(read_only=True)
    final_price = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True)
class ShopSchemaSerializer(serializers.Serializer):
    id      = serializers.IntegerField(read_only=True)
    owner   = OwnerSchemaSerializer(read_only=True)
    date    = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(read_only=True)
    address = AddressSchemaSerializer(read_only=True)
    items   = ShopItemSchemaSerializer(read_only=True,many=True)


class TagSchemaSerializer(serializers.Serializer):
    
    id          = serializers.IntegerField(read_only=True)
    title       = serializers.CharField(read_only=True)
class TagListSchemaSerializer(serializers.Serializer):
    list            = TagSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)
      

class SetBlogSchemaSerializer(serializers.Serializer):
    
    id          = serializers.IntegerField(read_only=True)
    title       = serializers.CharField(read_only=True)
    alias       = serializers.CharField(read_only=True)
    owner       = serializers.IntegerField(read_only=True)
    image       = serializers.URLField(read_only=True)
    body        = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    status      = serializers.IntegerField(read_only=True)
    date        = serializers.DateField(read_only=True)
    tags        = TagSchemaSerializer(read_only=True)

class SetChildSchemaSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField(read_only=True)
    slug         = serializers.CharField(read_only=True)
    description  = serializers.CharField(read_only=True)
    icon         = serializers.URLField(read_only=True)
    status       = serializers.IntegerField(read_only=True)
    # status_old   = serializers.IntegerField(read_only=True)
    parent       = serializers.IntegerField(read_only=True)
    order        = serializers.IntegerField(read_only=True)
    # blogsInfo = SetBlogSchemaSerializer(read_only=True,many=True)
class SetSchemaSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField(read_only=True)
    slug         = serializers.CharField(read_only=True)
    description  = serializers.CharField(read_only=True)
    icon         = serializers.URLField(read_only=True)
    status       = serializers.IntegerField(read_only=True)
    # status_old   = serializers.IntegerField(read_only=True)
    parent       = serializers.IntegerField(read_only=True)
    order        = serializers.IntegerField(read_only=True)
    sub_sets = SetChildSchemaSerializer(read_only=True,many=True)
    # blogsInfo = SetBlogSchemaSerializer(read_only=True,many=True)
class SetListSchemaSerializer(serializers.Serializer):
    list            = SetSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)



class UserPermissionSchemaSerializer(serializers.Serializer):
    pass
class UserInfoEvidenceSchemaSerializer(serializers.Serializer):
    id          = serializers.IntegerField(read_only=True) 
    title       = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    media       = serializers.CharField(read_only=True)

class UserInfoFileSchemaSerializer(serializers.Serializer):
    id       = serializers.IntegerField(read_only=True) 
    owner    = serializers.IntegerField(read_only=True)
    evidence = UserInfoEvidenceSchemaSerializer(read_only=True)
    file     = serializers.URLField(read_only=True)
class UserSchemaSerializer(serializers.Serializer):

    id          = serializers.IntegerField(read_only=True)
    avatar      = serializers.URLField(read_only=True)
    first_name  = serializers.CharField(read_only=True)
    last_name   = serializers.CharField(read_only=True)
    name        = serializers.CharField(read_only=True)
    username    = serializers.CharField(read_only=True)
    email       = serializers.EmailField(read_only=True)
    cellphone   = serializers.CharField(read_only=True)
    gender      = serializers.CharField(read_only=True)
    status      = serializers.IntegerField(read_only=True)
    is_active   = serializers.BooleanField(read_only=True)
    created     = serializers.DateTimeField(read_only=True)
    user_permissions = UserPermissionSchemaSerializer(read_only=True,many=True)
    role        = serializers.CharField(read_only=True)
    agent       = serializers.IntegerField(read_only=True)
    profile     = ProfileSchemaSerializer(read_only=True)
    address     = AddressSchemaSerializer(read_only=True,many=True)
    evidences   = UserInfoFileSchemaSerializer(read_only=True,many=True)
class UserListSchemaSerializer(serializers.Serializer):
    list            = UserSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)



class UserEvidenceSchemaSerializer(serializers.Serializer):
    id          = serializers.IntegerField(read_only=True) 
    title       = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    media       = serializers.CharField(read_only=True)
class UserEvidenceListSchemaSerializer(serializers.Serializer):
    list            = UserEvidenceSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)


class UserFileSchemaSerializer(serializers.Serializer):
    id       = serializers.IntegerField(read_only=True) 
    owner    = serializers.IntegerField(read_only=True)
    evidence = serializers.IntegerField(read_only=True)
    file     = serializers.URLField(read_only=True)
class UserFileListSchemaSerializer(serializers.Serializer):
    list            = UserFileSchemaSerializer(read_only=True,many=True)
    total_page_num  = serializers.IntegerField(read_only=True)
    total_row       = serializers.IntegerField(read_only=True)
