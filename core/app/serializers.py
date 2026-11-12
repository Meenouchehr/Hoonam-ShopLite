import contextlib
from rest_framework import serializers
from rest_framework import status
from django.utils.translation import gettext as _
from datetime import datetime, timedelta, timezone, tzinfo
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, F, CharField, Value as V, Count, Sum, Avg

from django.conf import settings
from app.helpers import *
from app.models import *
from .exceptions import ProjectException
from app.fields import *

STATUS_CHOICE = ((-1, 'trash'), (0, 'unpublish'), (1, 'publish'))


def execute_create(model, validated_data, ex_fields=None):
    extra_fileds = []
    if ex_fields:
        for f in ex_fields:
            if attr := validated_data.pop(f, None):
                extra_fileds.append({f: attr})

    new_instance = model(** validated_data)
    if extra_fileds:
        for f in extra_fileds:
            for k, v in f.items():
                setattr(new_instance, k, v)

    new_instance.save()
    return new_instance


def execute_update(instance, validated_data, ex_fields=None):
    extra_fileds = []
    if ex_fields:
        for f in ex_fields:
            if attr := validated_data.pop(f, None):
                extra_fileds.append({f: attr})
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    if extra_fileds:
        for f in extra_fileds:
            for k, v in f.items():
                setattr(instance, k, v)
    instance.save()
    return instance


def execute_delete(validated_data):
    if 'id' not in validated_data or not validated_data['id']:
        return
    objects = validated_data['id']
    is_delete = True
    delete = True
    for obj in objects:
        if hasattr(obj, 'is_delete') and obj.is_delete:
            is_delete = False
        elif hasattr(obj, 'is_delete'):
            delete = False
            obj.is_delete = True

    if objects and delete:
        [obj.delete() for obj in objects]
    elif objects and is_delete:
        [obj.save() for obj in objects]
    else:
        raise ProjectException(8001, _('خطای راستی آزمایی'),
                               _("ایتم های حذفی ناهمگن هستند"),
                               status.HTTP_400_BAD_REQUEST)


def execute_recycle(validated_data):
    if 'id' in validated_data and validated_data['id']:
        objects = validated_data['id']
        is_delete = 1
        for obj in objects:
            if hasattr(obj, 'is_delete') and obj.is_delete==0:
                raise ProjectException(8002, _('خطای راستی آزمایی'),
                                       _('همه داده های ارسالی در سطل زباله نمی باشند'),
                                       status.HTTP_400_BAD_REQUEST)

            obj.is_delete = 0
        if objects:
            type(objects[0]).objects.bulk_update(objects,['is_delete'])


def execute_access(validated_data):
    status = None
    if 'status' in validated_data and validated_data['status'] is not None:
        status = validated_data['status']

    # if status not in [0,1]:
    #     raise ProjectException(4007, _('خطای راستی آزمایی'), _('مقدار status نادرست است'), 400)


    if 'id' in validated_data and validated_data['id'] and status is not None:
        if objects := validated_data['id']:
            for obj in objects:
                if status in [0,1]:
                    obj.status=status
                    obj.is_delete=0
                elif status==-1:
                    obj.is_delete=1

            type(objects[0]).objects.bulk_update(objects,['status','is_delete'])


def get_user(request):
    if not request.user:
        raise ProjectException(4001, _('خطا'),
                               _("کاربر شناخته نشد"),
                               status.HTTP_404_NOT_FOUND)
    return request.user

def get_status(obj):
    if obj and hasattr(obj,'is_delete') and obj.is_delete:
        return -1
    elif obj and hasattr(obj,'status') and obj.status is not None:
        return obj.status
    return -2

def set_status(attrs):
    status = attrs.get('status', None)
    if status and status == -1:
        attrs.pop('status')
        attrs['is_delete'] = 1
    elif status is not None:
        attrs['is_delete'] = 0

def set_image_file(attrs,field_name):
    image = attrs.pop(field_name, None)
    if image:
            base64ImageField = Base64ImageField()
            image = base64ImageField.to_internal_value(image)
            attrs[field_name] = image

def set_create_user(attrs,request):
    attrs['created_by'] = get_user(request)
    attrs['modified_by'] = get_user(request)

def set_update_user(attrs,request):
    attrs.pop('created_by',None)
    attrs['modified_by'] = get_user(request)




# ----------Address:----------


class AddressSerializer(serializers.Serializer):
    class Meta:
        model = AddressModel

    id=serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("کاربر موجود نیست"),
        "invalid": _("داده معتبر نیست"),
    },
    )
    title = serializers.CharField(required=False, max_length=130, allow_blank=True)
    first_name = serializers.CharField(
        required=False, max_length=130, allow_blank=True)
    last_name = serializers.CharField(
        required=False, max_length=130, allow_blank=True)
    latitude = serializers.FloatField(default=0.0, required=False)
    longitude = serializers.FloatField(default=0.0, required=False)
    province = serializers.CharField(max_length=80, required=False)
    city = serializers.CharField(max_length=80, required=False)
    district = serializers.IntegerField(default=0, required=False)
    postal_code = serializers.CharField(
        max_length=10, allow_blank=True, required=False)
    address = serializers.CharField(max_length=None)
    tel = serializers.CharField(
        required=False, max_length=15, allow_blank=True)
    plaque = serializers.IntegerField(default=0)
    level = serializers.IntegerField(default=0)
    unit = serializers.IntegerField(default=0)
    comment = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    is_default = serializers.BooleanField(default=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICE, default=1)

    def validate(self, attrs):
        set_status(attrs)
        user=get_user(self.request)
        owner = attrs.get('owner', None)
        if owner and owner.pk != user.pk:
            if not user.is_staff:
                try:
                    UserModel.objects.get(Q(owner=user,owner__is_delete=0,owner__status=1) | Q(owner__owner=user,owner__owner__is_delete=0,owner__owner__status=1))
                except ObjectDoesNotExist as e:
                    raise ProjectException(808, 'خطای راستی آزمایی', "کاربر شناخته نشد", status.HTTP_404_NOT_FOUND) from e

                except UserModel.MultipleObjectsReturned:
                    pass

        elif owner is None:
            attrs['owner'] = user
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class AddressAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=AddressModel.objects.all(),
        error_messages={'not_exist': _(
            'آدرس موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class AddressDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=AddressModel.objects.all(),
        error_messages={'not_exist': _('آدرس موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        addresses= attrs.get('id',None)
        if addresses:
            for add in addresses:
                if add.is_default:
                    raise ProjectException(4002,_('خطای راستی آزمایی'),('آدرس پیش فرض قابل حذف نیست'),status_code=status.HTTP_400_BAD_REQUEST)
                    
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class AddressInformationSerializer(AddressSerializer):
    owner= serializers.SerializerMethodField(read_only=True)
    evidences = serializers.SerializerMethodField(read_only=True)
    def get_owner(self, obj):
        if obj and hasattr(obj, 'owner') and obj.owner:
            return OwnerInformationSerializer(obj.owner).data
        return {}

    def get_evidences(self,obj):
        if obj and hasattr(obj, 'evidences') and obj.evidences:
            return UserFileInformation_AddressInformation(obj.evidences,many=True).data
        return []


class AddressUpdateSerializer(AddressSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    status = serializers.ChoiceField(choices=STATUS_CHOICE, required=False)

    def validate(self, attrs):
        super().validate(attrs)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Attribute:----------


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeModel
        fields = ('id', 'owner', 'feature', 'value',)

    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    feature = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=FeatureModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Feature does not exist"),
        "invalid": _("invalid value"),
    },
    )
    value = serializers.CharField(required=True, max_length=150)

    def validate(self, attrs):
        self.user = get_user(self.request)
        _owner = attrs.get('owner', None)
        if (_owner != self.user) and (not has_access(user=_owner, instance=self.user)):
            raise ProjectException(821, _('Forbidden'),
                                   _('You do not have permission to perform this action.'),
                                   status.HTTP_403_FORBIDDEN)
        return attrs

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance


class AttributeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeModel
        fields = ('id', 'owner', 'feature', 'value',)

    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    feature = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=FeatureModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Feature does not exist"),
        "invalid": _("invalid value"),
    },
    )
    value = serializers.CharField(required=False, max_length=150)

    def validate(self, attrs):
        self.user = get_user(self.request)
        _owner = attrs.get('owner', None)
        if _owner is None:
            _owner = self.instance.owner
        if (_owner != self.user) and (not has_access(user=_owner, instance=self.user)):
            raise ProjectException(821, _('Forbidden'),
                                   _('You do not have permission to perform this action.'),
                                   status.HTTP_403_FORBIDDEN)
        return attrs

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AttributeInfoSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)
    owner = serializers.SerializerMethodField(read_only=True)
    feature = serializers.SerializerMethodField(read_only=True)
    value = serializers.CharField(read_only=True)

    def get_owner(self, obj):
        return obj.owner.pk

    def get_feature(self, obj):
        return obj.feature.pk


# ----------Bank:----------

class BankSerializer(serializers.Serializer):
    class Meta:
        model = BankModel

    title = serializers.CharField(max_length=130)
    value = serializers.CharField(max_length=130)
    porsant = serializers.IntegerField(default=0)
    description = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    icon = serializers.CharField(max_length=None, required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICE, default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_status(attrs)
        set_image_file(attrs,'icon')

        title=attrs.get('title',None)
        try:
            BankModel.objects.get(title=title)
            raise ProjectException(4002,_("خطای راستی آزمایی"),("بانک وجود دارد"),status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            pass

        return attrs

   

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class BankAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BankModel.objects.all(),
        error_messages={'not_exist': _(
            'بانک موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class BankDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BankModel.objects.all(),
        error_messages={'not_exist': _('بانک موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class BankInformationSerializer(BankSerializer):
    icon= serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    def get_icon(self, obj):
        if obj and hasattr(obj,'icon') and obj.icon:
            return obj.icon.url
        return ''
    def get_status(self,obj):
        return get_status(obj)

class BankUpdateSerializer(BankSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    status = serializers.ChoiceField(choices=STATUS_CHOICE, required=False)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        title=instance.title
        resp=execute_update(instance, validated_data)
        BankModel.objects.get(title=title).delete()
        return resp


# ----------Banner:----------

class BannerSerializer(serializers.Serializer):
    class Meta:
        model = BannerModel

    id = serializers.IntegerField(read_only=True)    
    title = serializers.CharField(max_length=130)
    link = serializers.CharField(max_length=None, allow_blank=True, required=False)
    web_image = serializers.CharField(max_length=None, required=False)
    mobile_image = serializers.CharField(max_length=None, required=False)
    position = serializers.CharField(max_length=130)
    status = serializers.ChoiceField(choices=STATUS_CHOICE, default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_status(attrs)
        set_image_file(attrs,'web_image')
        set_image_file(attrs,'mobile_image')
        
        return attrs

    def create(self, validated_data):
          return execute_create(self.Meta.model, validated_data)

class BannerAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BannerModel.objects.all(),
        error_messages={'not_exist': _(
            'بنر موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class BannerDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BannerModel.objects.all(),
        error_messages={'not_exist': _(
            'بنر موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class BannerInformationSerializer(BannerSerializer):
    web_image = serializers.SerializerMethodField(read_only=True)
    mobile_image = serializers.SerializerMethodField(read_only=True)
    status= serializers.SerializerMethodField(read_only=True)

    def get_web_image(self, obj):
        if obj and hasattr(obj,'web_image') and obj.web_image:
            return obj.web_image.url
        return ''
    def get_mobile_image(self, obj):
        if obj and hasattr(obj,'mobile_image') and obj.mobile_image:
            return obj.mobile_image.url
        return ''
    def get_status(self,obj):
        return get_status(obj)

class BannerRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BannerModel.objects.all(),
        error_messages={'not_exist': _(
            'بنر موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class BannerUpdateSerializer(BannerSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    status = serializers.ChoiceField(choices=STATUS_CHOICE, required=False)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

class BannerWebUploadSerializer(serializers.Serializer):
    id=serializers.IntegerField(read_only=True)
    web_image = serializers.CharField(max_length=None, required=False)
    
    def validate(self, attrs):
        super().validate(attrs)
        set_image_file(attrs,'web_image')
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

class BannerMobileUploadSerializer(BannerSerializer):
    id=serializers.IntegerField(read_only=True)
    mobile_image = serializers.CharField(max_length=None, required=False)
    
    def validate(self, attrs):
        super().validate(attrs)
        set_image_file(attrs,'mobile_image')
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Blog:----------
class BlogSerializer(serializers.Serializer):
    class Meta:
        model = BlogModel

    id= serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    title = serializers.CharField(max_length=130)
    alias = serializers.CharField(max_length=130, required=False)
    image = serializers.CharField(max_length=None, required=False)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    body = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    set = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=SetModel.objects.all(),
                                             error_messages={
        "does_not_exist": _("Set does not exist"),
        "invalid": _("invalid value"),
    },
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=130), required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        owner = attrs.get('owner', None)
        if owner is None:
            attrs['owner'] = get_user(self.request)
        set_create_user(attrs,self.request)
        set_image_file(attrs,'image')
        set_status(attrs)
        if tags := attrs.pop('tags', None):
            attrs['temp_tags']=tags
        return attrs
    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data, ['temp_tags'])
    
class BlogAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BlogModel.objects.all(),
        error_messages={'not_exist': _(
            'بلاگ موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class BlogDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BlogModel.objects.all(),
        error_messages={'not_exist': _('بلاگ موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class BlogInformationSerializer(BlogSerializer):
    owner = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(read_only=True)
    status= serializers.SerializerMethodField(read_only=True)
    date  = serializers.SerializerMethodField(read_only=True)
    tags  = serializers.SerializerMethodField(read_only=True)
    set   = serializers.SerializerMethodField(read_only=True)

    def get_owner(self, obj):
        if obj and hasattr(obj,'owner') and  obj.owner:
            return OwnerInformationSerializer(obj.owner).data
        return {}
    
    def get_image(self, obj):
        if obj and hasattr(obj,'image') and obj.image:
            return obj.image.url
        return ''
    
    def get_status(self,obj):
        return get_status(obj)

    def get_tags(self, obj):
        if obj and hasattr(obj, 'tags') and obj.tags:
            return TagSerializer(obj.tags, many=True).data
        return []

    def get_date(self, obj):
        if obj and hasattr(obj,'date') and obj.date:
            return convert_gregorian_to_jalali_string_datetime(obj.date)
        return ''

    def get_set(self,obj):
        if obj and hasattr(obj,'set') and obj.set:
            return SetSerializer(obj.set).data
        return {}

class BlogRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=BannerModel.objects.all(),
        error_messages={'not_exist': _(
            'بلاگ موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class BlogUpdateSerializer(BlogSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,required=False)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

class BlogUploadSerializer(serializers.Serializer):
    id=serializers.IntegerField(read_only=True)
    image = serializers.CharField(max_length=None, required=False)

    def validate(self, attrs):
        set_update_user(attrs)
        set_image_file(attrs,'image')
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

# ----------Category:----------
class CategorySerializer(serializers.Serializer):
    class Meta:
        model = CategoryModel

    id    = serializers.IntegerField(read_only=True)   
    title = serializers.CharField(max_length=130)
    slug = serializers.CharField(required=False, max_length=130)
    icon = serializers.CharField(max_length=None, required=False)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    parent = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=CategoryModel.objects.all(),
                                                error_messages={
        "does_not_exist": _("Category does not exist"),
        "invalid": _("invalid value"),
    },
    )
    groups = serializers.PrimaryKeyRelatedField(required=False, many=True, queryset=GroupModel.objects.all(),
                                                error_messages={
        "does_not_exist": _("Group does not exist"),
        "invalid": _("invalid value"),
    },
    )
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)
    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_image_file(attrs,'icon')
        set_status(attrs)

        if groups:=attrs.get('groups',None):
            for grp in groups:
                if grp.is_delete==1:
                    raise ProjectException(806, _('خطای راستی آزمایی'),
                                   _('گروه {0} وجود ندارد.'.format(grp.pk)),
                                   status.HTTP_400_BAD_REQUEST)

        title=attrs.get('title', None)
        with contextlib.suppress(ObjectDoesNotExist):
            CategoryModel.objects.get(title=title)
            raise ProjectException(805, _('خطای راستی آزمایی'),
                                   _('این عنوان دسته موجود است'),
                                   status.HTTP_400_BAD_REQUEST)
        if groups:=attrs.pop('groups',None):
            attrs['temp_groups']=groups
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data, ['temp_groups'])

class CategoryAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CategoryModel.objects.all(),
        error_messages={'not_exist': _(
            'دسته موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class CategoryDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CategoryModel.objects.all(),
        error_messages={'not_exist': _('دسته موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class CategoryInformationSerializer(CategorySerializer):
    icon   = serializers.SerializerMethodField(read_only=True)
    parent = serializers.SerializerMethodField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    sub_categories = serializers.SerializerMethodField(read_only=True)
    groups = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)

    def get_icon(self, obj):
        if obj and hasattr(obj,'icon') and obj.icon:
            return obj.icon.url
        return ''

    def get_parent(self, obj):
        if obj and hasattr(obj,'parent') and obj.parent:
            return CategorySerializer(obj.parent).data
        return {}

    def get_sub_categories(self, obj):
        if obj and hasattr(obj,'sub_categories') and obj.sub_categories:
            sub_categories=list(obj.sub_categories.select_related('parent').prefetch_related('groups'))
            if sub_categories:
                return CategoryInformationSerializer(sub_categories,many=True).data
        return []

    def get_groups(self, obj):
        if obj and hasattr(obj,'groups') and obj.groups:
            groups=[i.group for i in obj.groups.filter(group__status=1,group__is_delete=0)]
            if groups:
                return GroupInformation_CategoryInformationSerializer(groups,many=True).data
        return []
  
    def get_status(self, obj):
        return get_status(obj)

class CategoryInformation_SubCategoryInformationSerializer(CategoryInformationSerializer):
    title = serializers.CharField(read_only=True)
    groups=None

class CategoryInformation_GroupInformationSerializer(serializers.Serializer):
    id    = serializers.IntegerField(read_only=True)   
    title = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    icon = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)

class CategoryRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CategoryModel.objects.all(),
        error_messages={'not_exist': _(
            'دسته موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class CategoryUpdateSerializer(CategorySerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

class CategoryUploadSerializer(serializers.Serializer):
    
    id = serializers.IntegerField(read_only=True)
    icon = serializers.CharField(max_length=None, required=False)
    def validate(self, attrs):
        set_update_user(attrs,self.request)
        set_image_file(attrs,'icon')
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)
        
class CategoryGroupSerializer(serializers.Serializer):
    groups = serializers.ListField(required=False, child=serializers.PrimaryKeyRelatedField(many=False, queryset=GroupModel.objects.all(),
                                                                                            error_messages={
        "does_not_exist": _("Group does not exist"),
        "invalid": _("invalid value"),
    },
    ))

# ----------Commission:----------


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionModel
        fields = ('id', 'owner', 'service', 'category',
                  'company', 'type', 'amount', 'status', 'role')
        read_only_fields = ('status',)
    ROLE_CHOICE = (('agent', 'agent'), ('seller', 'seller'))

    owner = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserModel.objects.all(),
        error_messages={
            'does_not_exist': _("User does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    service = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceModel.objects.all(),
        error_messages={
            'does_not_exist': _("service does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    category = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CategoryModel.objects.all(),
        error_messages={
            'does_not_exist': _("category does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    company = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CompanyModel.objects.all(),
        error_messages={
            'does_not_exist': _("company does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    type = serializers.ChoiceField(
        choices=CommissionModel.TYPE_CHOICE, default='cent')
    amount = serializers.IntegerField()
    role = serializers.ChoiceField(choices=ROLE_CHOICE, required=False)

    status = serializers.IntegerField(read_only=True)

    def validate(self, attrs):
        self.user = get_user(self.request)
        self.role_list = get_user_roles(self.user)
        _role = attrs.get('role', None)
        if self.user.is_staff or (_role and (_role == 'admin' or (_role == 'agent' and 'agent' in self.role_list))):
            pass

        else:
            raise ProjectException(805, 'forbidden',
                                   'forbidden',
                                   status.HTTP_403_FORBIDDEN)

        _owner = attrs.get('owner', None)
        _category = attrs.get('category', None)
        _company = attrs.get('company', None)
        _service = attrs.get('service', None)
        _role = attrs.get('role', None)

        if not _owner and not _category and not _company and not _service and not _role:
            raise ProjectException(805, 'validation error',
                                   'owner or category or company or service or role no exist',
                                   status.HTTP_400_BAD_REQUEST)
        elif _owner and _role:
            raise ProjectException(806, 'validation error',
                                   'owner and role confilict',
                                   status.HTTP_400_BAD_REQUEST)
        elif _service and _company:
            raise ProjectException(807, 'validation error',
                                   'service and company confilict',
                                   status.HTTP_400_BAD_REQUEST)
        elif _service and _category:
            raise ProjectException(808, 'validation error',
                                   'service and category confilict',
                                   status.HTTP_400_BAD_REQUEST)
        elif _company and _category:
            raise ProjectException(809, 'validation error',
                                   'company and category confilict',
                                   status.HTTP_400_BAD_REQUEST)

        _type = attrs.get('type', None)
        _amount = attrs.get('amount', None)
        if _type == 'cent':
            if _amount < 1 and _amount > 100:
                raise ProjectException(810, 'validation error',
                                       'amount between 1 .. 100',
                                       status.HTTP_400_BAD_REQUEST)
        else:
            if _amount < 1:
                raise ProjectException(811, 'validation error',
                                       'amount must gratter than 1',
                                       status.HTTP_400_BAD_REQUEST)

        return attrs

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        # new_instance = self.Meta.model(**validated_data)
        # new_instance.save()
        _type = validated_data.get('type', None)
        _amount = validated_data.get('amount', None)
        _owner = validated_data.get('owner', None)
        self.insert = []
        self.update = []
        if _owner:
            _service = validated_data.get('service', None)
            _category = validated_data.get('category', None)
            _company = validated_data.get('company', None)
            if _service:
                self.prepare(_owner, _service, _type, _amount)
            elif _category:
                _services = ServiceModel.objects.filter(category=_category)
                for srv in _services:
                    self.prepare(_owner, srv, _type, _amount)
            elif _company:
                _services = ServiceModel.objects.filter(company=_company)
                for srv in _services:
                    self.prepare(_owner, srv, _type, _amount)
            else:
                _services = ServiceModel.objects.all()
                for srv in _services:
                    self.prepare(_owner, srv, _type, _amount)
        else:
            _role = validated_data.get('role', None)
            if self.user.is_staff:
                _users = UserModel.objects.filter(roles__role__title=_role)
            else:
                _users = UserModel.objects.filter(
                    owner=self.user, roles__role__title=_role)

            _service = validated_data.get('service', None)
            _category = validated_data.get('category', None)
            _company = validated_data.get('company', None)
            for usr in _users:
                _owner = usr
                if _service:
                    self.prepare(_owner, _service, _type, _amount)
                elif _category:
                    _services = ServiceModel.objects.filter(category=_category)
                    for srv in _services:
                        self.prepare(_owner, srv, _type, _amount)
                elif _company:
                    _services = ServiceModel.objects.filter(company=_company)
                    for srv in _services:
                        self.prepare(_owner, srv, _type, _amount)
                else:
                    _services = ServiceModel.objects.all()
                    for srv in _services:
                        self.prepare(_owner, srv, _type, _amount)

        if self.insert:
            CommissionModel.objects.bulk_create(self.insert)
        if self.update:
            CommissionModel.objects.bulk_update(
                self.update, ['amount', 'type'])

        return {}

    def prepare(self, owner, service, type, amount):
        _data = {'owner': owner, 'service': service,
                 'type': type, 'amount': amount}
        try:
            _object = CommissionModel.objects.get(owner=owner, service=service)
            _object.amount = amount
            _object.type = type
            _object.modified_by = self.user
            self.update.append(_object)
        except ObjectDoesNotExist:
            _object = CommissionModel(** _data)
            _object.modified_by = self.user
            _object.created_by = self.user
            self.insert.append(_object)

class CommissionAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CommissionModel.objects.all(),
        error_messages={'not_exist': _(
            'کمسیون موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class CommissionDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CommissionModel.objects.all(),
        error_messages={'not_exist': _('کمسیون موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class CommissionInformationSerializer(CommissionSerializer):
    pass

class CommissionUpdateSerializer(CommissionSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)




class CommissionInfoSerializer(serializers.Serializer):
    class CommissionOwnerInfoSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        avatar = serializers.SerializerMethodField(read_only=True)
        name = serializers.SerializerMethodField(read_only=True)

        def get_avatar(self, obj):
            avatar = None
            if obj.avatar:
                avatar = obj.avatar.url
            return avatar

        def get_name(self, obj):
            _name = "".join([obj.first_name, ' ', obj.last_name])
            return _name

    class CommissionServiceInfoSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        title = serializers.CharField(read_only=True)
        slug = serializers.CharField(read_only=True)
        description = serializers.CharField(read_only=True)
        image = serializers.SerializerMethodField(read_only=True)
        status = serializers.IntegerField(read_only=True)
        #parent       = serializers.SerializerMethodField(read_only=True)
        order = serializers.IntegerField(read_only=True)

        def get_image(self, obj):
            if obj.image:
                return obj.image.url
            return None

        def get_parent(self, obj):
            id = serializers.IntegerField(read_only=True)
            title = serializers.CharField(read_only=True)
            slug = serializers.CharField(read_only=True)
            description = serializers.CharField(read_only=True)
            icon = serializers.SerializerMethodField(read_only=True)

            def get_icon(self, obj):
                if obj.icon:
                    return obj.icon.url
                return None
    id = serializers.IntegerField(read_only=True)
    owner = CommissionOwnerInfoSerializer(read_only=True)
    service = CommissionServiceInfoSerializer(read_only=True)
    type = serializers.CharField(read_only=True)
    amount = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True)
    status = serializers.IntegerField(read_only=True)


class CommissionStatusSerializer(serializers.Serializer):
    STATUS_CHOICE = ((-1, 'trash'), (0, 'unpublish'), (1, 'publish'))

    id = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CommissionModel.objects.all(),
        error_messages={
            'does_not_exist': _("Commission does not exist"),
            'invalid': _('invalid data')
        },)
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        status = attrs.get('status', None)
        if (status is None) and (status not in [-1, 0, 1]):
            raise ProjectException(827, _('validation error'),
                                   _('Status field is Invalid.'),
                                   status.HTTP_400_BAD_REQUEST)
        return attrs


class CommissionSomeSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CommissionModel.objects.all(),
        error_messages={
            'does_not_exist': _("Commission does not exist"),
            'invalid': _('invalid data')
        },)

    def validate(self, attrs):
        return attrs

# ----------Company:----------

class CompanySerializer(serializers.Serializer):
    class Meta:
        model = CompanyModel

    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    logo = serializers.CharField(max_length=None, required=False)
    slug = serializers.CharField(required=False, max_length=130)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_image_file(attrs,'logo')
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class CompanyAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CompanyModel.objects.all(),
        error_messages={'not_exist': _(
            'شرکت موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class CompanyDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CompanyModel.objects.all(),
        error_messages={'not_exist': _('شرکت موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class CompanyRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CompanyModel.objects.all(),
        error_messages={'not_exist': _(
            'شرکت موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class CompanyInformationSerializer(CompanySerializer):
    logo   = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)

    def get_logo(self, obj):
        if obj and hasattr(obj,'logo') and obj.logo:
            return obj.logo.url
        return ''

    def get_status(self, obj):
        return get_status(obj)

class CompanyUpdateSerializer(CompanySerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,required=False)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

# ----------Deposit:----------
class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositModel
        fields = ('id', 'amount', 'comment', 'bank',
                  'platform', 'url', 'token')
    amount = serializers.IntegerField()
    comment = serializers.CharField(required=False, max_length=None)
    bank = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=BankModel.objects.all(),
                                              error_messages={
        "does_not_exist": _("Bank does not exist"),
        "invalid": _("invalid value"),
    },
    )
    platform = serializers.ChoiceField(
        choices=DepositModel.PLATFORM_CHOICE, default='web')
    token = serializers.CharField(read_only=True, max_length=None)
    url = serializers.CharField(read_only=True, max_length=None)

    def validate(self, attrs):
        self.user = get_user(self.request)
        return attrs

    def create(self, validated_data):

        _kind = 'increase_credit'
        if self.user and self.user.pk:
            validated_data['payer'] = self.user
        #     validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.request = self.context['request']
        new_instance.kind = _kind
        new_instance.save()
        return new_instance



# ----------Document:----------
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentModel
        fields = ('id', 'owner', 'record', 'file',)

    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    record = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=RecordModel.objects.all(),
                                                error_messages={
        "does_not_exist": _("Record does not exist"),
        "invalid": _("invalid value"),
    },
    )
    file = serializers.FileField(required=True, max_length=None, use_url=True)

    def validate(self, attrs):
        self.user = get_user(self.request)
        _owner = attrs.get('owner', None)
        if (_owner != self.user) and (not has_access(user=_owner, instance=self.user)):
            raise ProjectException(821, _('Forbidden'),
                                   _('You do not have permission to perform this action.'),
                                   status.HTTP_403_FORBIDDEN)
        return attrs

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance

class DocumentAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=DocumentModel.objects.all(),
        error_messages={'not_exist': _(
            'مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class DocumentDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=DocumentModel.objects.all(),
        error_messages={'not_exist': _('مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class DocumentInformationSerializer(DocumentSerializer):
    pass

class DocumentUpdateSerializer(DocumentSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)



class DocumentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentModel
        fields = ('id', 'owner', 'record', 'file',)

    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    record = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=RecordModel.objects.all(),
                                                error_messages={
        "does_not_exist": _("Record does not exist"),
        "invalid": _("invalid value"),
    },
    )
    file = serializers.FileField(required=False, max_length=None, use_url=True)

    def validate(self, attrs):
        self.user = get_user(self.request)
        _owner = attrs.get('owner', None)
        if _owner is None:
            _owner = self.instance.owner
        if (_owner != self.user) and (not has_access(user=_owner, instance=self.user)):
            raise ProjectException(821, _('Forbidden'),
                                   _('You do not have permission to perform this action.'),
                                   status.HTTP_403_FORBIDDEN)
        return attrs

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class DocumentInfoSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)
    owner = serializers.SerializerMethodField(read_only=True)
    record = serializers.SerializerMethodField(read_only=True)
    file = serializers.SerializerMethodField(read_only=True)

    def get_owner(self, obj):
        return obj.owner.pk

    def get_record(self, obj):
        return obj.record.pk

    def get_file(self, obj):
        if obj.file:
            return obj.file.url
        return None


# ----------Evidence:----------
class EvidenceSerializer(serializers.Serializer):
    class Meta:
        model = EvidenceModel
        
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    media = serializers.ChoiceField(choices=EvidenceModel.MEDIA_CHOICE)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class EvidenceAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=EvidenceModel.objects.all(),
        error_messages={'not_exist': _(
            'مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class EvidenceDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=EvidenceModel.objects.all(),
        error_messages={'not_exist': _('مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class EvidenceInformationSerializer(EvidenceSerializer):
    pass

class EvidenceRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=EvidenceModel.objects.all(),
        error_messages={'not_exist': _(
            'مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class EvidenceUpdateSerializer(EvidenceSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    status = serializers.ChoiceField(required=False,choices=STATUS_CHOICE)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Faq Category:----------

class FaqCategorySerializer(serializers.Serializer):
    class Meta:
        model = FaqCategoryModel
       

    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    slug = serializers.CharField(required=False, max_length=130)
    icon = serializers.CharField(max_length=130)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        #set_create_user(attrs,self.request)
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class FaqCategoryAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=FaqCategoryModel.objects.all(),
        error_messages={'not_exist': _(
            'دسته موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class FaqCategoryDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=FaqCategoryModel.objects.all(),
        error_messages={'not_exist': _('دسته موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class FaqCategoryInformationSerializer(FaqCategorySerializer):
    status = serializers.SerializerMethodField(read_only=True)

    def get_status(self, obj):
        return get_status(obj)

class FaqCategoryRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=FaqCategoryModel.objects.all(),
        error_messages={'not_exist': _(
            'دسته موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class FaqCategoryUpdateSerializer(FaqCategorySerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    icon = serializers.CharField(required=False, max_length=130)
    status = serializers.ChoiceField(required=False, choices=STATUS_CHOICE)
    

    def validate(self, attrs):
        super().validate(attrs)
        #set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

# ----------Faq:----------


class FaqSerializer(serializers.Serializer):
    class Meta:
        model = FaqModel
      

    id = serializers.IntegerField(read_only=True)
    question = serializers.CharField(max_length=None)
    answer = serializers.CharField(max_length=None)
    category = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=FaqCategoryModel.objects.all(),
                                                  error_messages={
        "does_not_exist": _("دسته وجود ندارد"),
        "invalid": _("داده ها نامعتبر است"),
    },
    )

    status= serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        #set_create_user(attrs,self.request)
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance

class FaqAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=FaqModel.objects.all(),
        error_messages={'not_exist': _(
            'سئوال پرتکرار موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class FaqDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=FaqModel.objects.all(),
        error_messages={'not_exist': _('سئوال پرتکرار موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class FaqInformationSerializer(FaqSerializer):
    category= serializers.SerializerMethodField(read_only=True)
    status= serializers.SerializerMethodField(read_only=True)

    def get_category(self,obj):
        if obj and hasattr(obj, 'category') and obj.category:
            return FaqCategoryInformationSerializer(obj.category).data
        return {}
    
    def get_status(self, obj):
        return get_status(obj)

class FaqRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=FaqModel.objects.all(),
        error_messages={'not_exist': _(
            'سئوال پرتکرار موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class FaqUpdateSerializer(FaqSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
    question = serializers.CharField(required=False,max_length=None)
    answer = serializers.CharField(required=False,max_length=None)
    status = serializers.ChoiceField(required=False, choices=STATUS_CHOICE)

    def validate(self, attrs):
        super().validate(attrs)
        #set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Feature:----------


class FeatureInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    service = serializers.SerializerMethodField(read_only=True)
    service_title = serializers.SerializerMethodField(read_only=True)
    property = serializers.SerializerMethodField(read_only=True)
    property_title = serializers.SerializerMethodField(read_only=True)

    def get_service(self, obj):
        return obj.service.pk

    def get_service_title(self, obj):
        return obj.service.title

    def get_property(self, obj):
        return obj.property.pk

    def get_property_title(self, obj):
        return obj.property.title


# ----------Group:----------
class GroupSerializer(serializers.Serializer):
    class Meta:
        model = GroupModel
       
    class GroupItemSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        value = serializers.CharField(max_length=130)
        order = serializers.IntegerField(default=0)
        description = serializers.CharField(max_length=None, allow_blank=True, required=False)

        
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    is_special = serializers.BooleanField(required=False, default=False)
    icon = serializers.CharField(required=False, max_length=130, allow_blank=True)
    order = serializers.IntegerField(default=0)
    kind = serializers.ChoiceField(choices=GroupModel.KIND_CHOICE)
    show = serializers.ChoiceField(choices=GroupModel.DISPLAY_CHOICE)
    items = GroupItemSerializer(required=False, many=True)
    categories = serializers.ListField(required=False, child=serializers.PrimaryKeyRelatedField(many=False, queryset=CategoryModel.objects.all(),
                                                                                                error_messages={
        "does_not_exist": _("دسته وجود ندارد"),
        "invalid": _("داده ها نامعتبر است"),
    },
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        group_items = attrs.pop('items', None)
        temp_categories=attrs.pop('categories', None)
        if not group_items:
            raise ProjectException(823, 'Validation error',
                                        'Group items is not required',
                                 status.HTTP_400_BAD_REQUEST)

        
        attrs['group_items']=group_items
        attrs['temp_categories']=temp_categories
        set_create_user(attrs,self.request)
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data, ['group_items','temp_categories'])

class GroupAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=GroupModel.objects.all(),
        error_messages={'not_exist': _(
            'گروه موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class GroupDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=GroupModel.objects.all(),
        error_messages={'not_exist': _('گروه موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class GroupInformationSerializer(GroupSerializer):
    status = serializers.SerializerMethodField(read_only=True)
    categories = serializers.SerializerMethodField(read_only=True)


    def get_categories(self, obj):
        if obj and hasattr(obj, 'categories') and obj.categories:
            categories= [i.category for i in obj.categories.filter(category__status=1,category__is_delete=0)]
            return CategoryInformation_GroupInformationSerializer(obj.categories, many=True).data
        return []

    def get_status(self, obj):
       return get_status(obj)

class GroupRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=GroupModel.objects.all(),
        error_messages={'not_exist': _(
            'گروه موجود نیست'), 'invalid': _('داده ها نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class GroupInformation_CategoryInformationSerializer(GroupInformationSerializer):
    categories=None
class GroupInformation_ServiceInformationSerializer(GroupInformationSerializer):
    categories=None
    items=None

class GroupUpdateSerializer(GroupSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Grade:----------


class GradeSerializer(serializers.Serializer):
    class Meta:
        model = GradeModel

    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    shop_no = serializers.IntegerField(default=0)
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        attrs['created_by'] = get_user(self.request)
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class GradeAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=GradeModel.objects.all(),
        error_messages={'not_exist': _(
            'رده موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class GradeDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=GradeModel.objects.all(),
        error_messages={'not_exist': _('رده موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class GradeInformationSerializer(GradeSerializer):
    pass

class GradeRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=GradeModel.objects.all(),
        error_messages={'not_exist': _(
            'رده موجود نیست'), 'invalid': _('داده ها نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class GradeUpdateSerializer(GradeSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# Login
class LoginSerializer(serializers.Serializer):
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)
    # firebase = serializers.CharField(max_length=None,required=False,write_only=True)
    avatar = serializers.SerializerMethodField(
        read_only=True, method_name="get_avatar")
    cellphone = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True,
                                             method_name="get_name")
    gender = serializers.CharField(read_only=True)
    status = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    roles = serializers.SerializerMethodField(
        read_only=True, method_name="get_roles")

    address = serializers.SerializerMethodField(
        read_only=True, method_name="get_address")

    wallet = serializers.SerializerMethodField(read_only=True)

    def get_avatar(self, obj):
        avatar = None
        if obj.avatar:
            avatar = obj.avatar.url
        return avatar

    def get_name(self, obj):
        _name = "".join([obj.first_name, ' ', obj.last_name])
        return _name

    def get_roles(self, obj):
        if obj.is_superuser:
            roles = {
                "title": "superuser",
                "states": {"all": ["manage"]}
            }
            return [roles]
        else:
            list_role = UserRoleModel.objects.filter(user=obj)
            roles = [obj.role for obj in list_role]
            _serializer = RoleInfoGetSerializer(roles, many=True)
            return _serializer.data

    def get_address(self, obj):
        if obj:
            address = AddressModel.objects.filter(owner=obj, is_default=True).first()
            if address:
                return AddressInformationSerializer(address, many=False).data
        return {}

    def get_wallet(self, obj):
        wallet = 0
        wallets = WalletModel.objects.filter(owner=obj)
        if wallets:
            wallet = wallets.aggregate(Sum("amount"))["amount__sum"]

        return wallet

    def validate(self, attrs):
        username = attrs.pop("username", None)
        password = attrs.get("password", None)

        if username:
            username = username.lower()
            obj = None
            try:
                obj = UserModel.objects.get(username=username, status=1,is_delete=0 ,is_active=True)
                attrs["username"] = username
            except:
                try:
                    obj = UserModel.objects.get(cellphone=username,status=1,is_delete=0 ,is_active=True)
                    attrs["username"] = obj.username
                except:
                    try:
                        obj = UserModel.objects.get(email=username, status=1,is_delete=0 ,is_active=True)
                        attrs["username"] = obj.username
                    except:
                        pass
            
            if obj:
                if obj.deactive_expire and (obj.deactive_expire > datetime.now(timezone.utc)):
                    raise ProjectException(
                        803,
                        _("authentication error"),
                        _("You will not be able to access the system until {0}.".format(
                            _object.deactive_expire)),
                        status.HTTP_401_UNAUTHORIZED,
                    )
                if obj.login_error == settings.DEACTIVE_COUNT:
                    raise ProjectException(
                        804,
                        _("authentication error"),
                        _("You have been disabled by the system for security reasons."),
                        status.HTTP_401_UNAUTHORIZED,
                    )
                if not obj.check_password(password):
                    login_error = obj.login_error + 1
                    obj.login_error = login_error
                    if login_error == settings.LOGIN_ERROR:
                        obj.deactive_expire = datetime.now() + timedelta(minutes=settings.DEACTIVE_EXPIRE)
                    elif login_error == settings.DEACTIVE_COUNT:
                        if obj.is_active:
                            obj.is_active = False
                            obj.save()
                        raise ProjectException(
                            804,
                            _("authentication error"),
                            _("You have been disabled by the system for security reasons."),
                            status.HTTP_401_UNAUTHORIZED,
                        )
                    obj.save()
                    raise ProjectException(
                        801,
                        _("authentication error"),
                        _("Authentication error"),
                        status.HTTP_401_UNAUTHORIZED,
                    )
                elif not obj.is_active:
                    raise ProjectException(802, _('authentication error'),
                                           _('You are not active on the system.'),
                                           status.HTTP_400_BAD_REQUEST)

        return attrs


# ----------None:----------
class NoneSerializer(serializers.Serializer):
    pass


# ----------Operate:----------
class OperateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperateModel
        fields = (
            'title',
        )

    title = serializers.CharField(max_length=130)

    def validate(self, attrs):
        self.user = self.context['request'].user
        return attrs

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance


# ----------Owner:----------
class OwnerInformationSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)
    avatar = serializers.SerializerMethodField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    cellphone = serializers.CharField(read_only=True)
    gender = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    agent = serializers.SerializerMethodField(
        read_only=True, method_name="get_agent")

    def get_avatar(self, obj):
        avatar = None
        if obj.avatar:
            avatar = obj.avatar.url
        return avatar

    def get_name(self, obj):
        name=''
        if obj and hasattr(obj, 'first_name') and obj.first_name:
            name=obj.first_name

        if obj and hasattr(obj,'last_name') and obj.last_name and name:
            name='{0} {1}'.format(name,obj.last_name)
        elif obj and hasattr(obj,'last_name') and obj.last_name:
            name=obj.last_name
        return name

    def get_agent(self, obj):
        try:
            chart = UserSubordinateModel.objects.get(user=obj)
            return chart.parent.pk
        except:
            pass
        return None
    
    def get_status(self, obj):
        return get_status(obj)


# ----------Porsant:----------
class PorsantSerializer(serializers.Serializer):
    class Meta:
        model = PorsantModel

    ROLE_CHOICE = (('agent', 'agent'), ('seller', 'seller'))

    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    owner = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserModel.objects.all(),
        error_messages={
            'does_not_exist': _("user does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    service = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceModel.objects.all(),
        error_messages={
            'does_not_exist': _("service does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    category = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CategoryModel.objects.all(),
        error_messages={
            'does_not_exist': _("category does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    company = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=CompanyModel.objects.all(),
        error_messages={
            'does_not_exist': _("company does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    grade = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=GradeModel.objects.all(),
        error_messages={
            'does_not_exist': _("grade does not exist"),
            'invalid': _('invalid data')
        }, required=False)
    type = serializers.ChoiceField(
        choices=PorsantModel.TYPE_CHOICE, default='cent')
    amount = serializers.IntegerField()
    role = serializers.ChoiceField(choices=ROLE_CHOICE, required=False)

    def validate(self, attrs):
        self.user = get_user(self.request)
        self.role_list = get_user_roles(self.user)
        _role = attrs.get('role', None)
        if self.user.is_staff or (_role and (_role == 'admin' or (_role == 'agent' and 'agent' in self.role_list))):
            pass

        else:
            raise ProjectException(805, 'forbidden',
                                   'forbidden',
                                   status.HTTP_403_FORBIDDEN)

        _owner = attrs.get('owner', None)
        _category = attrs.get('category', None)
        _company = attrs.get('company', None)
        _service = attrs.get('service', None)
        _role = attrs.pop('role', None)

        if not _owner and not _category and not _company and not _service and not _role:
            raise ProjectException(805, 'validation error',
                                   'owner or category or company or service or role no exist',
                                   status.HTTP_400_BAD_REQUEST)
        elif _owner and _role:
            raise ProjectException(806, 'validation error',
                                   'owner and role confilict',
                                   status.HTTP_400_BAD_REQUEST)
        elif _service and _company:
            raise ProjectException(807, 'validation error',
                                   'service and company confilict',
                                   status.HTTP_400_BAD_REQUEST)
        elif _service and _category:
            raise ProjectException(808, 'validation error',
                                   'service and category confilict',
                                   status.HTTP_400_BAD_REQUEST)
        # elif _company and _category:
        #     raise ProjectException(809, 'validation error',
        #                            'company and category confilict',
        #                            status.HTTP_400_BAD_REQUEST)

        _type = attrs.get('type', None)
        _amount = attrs.get('amount', None)
        if _type == 'cent':
            if _amount < 1 or _amount > 100:
                raise ProjectException(810, 'validation error',
                                       'amount between 1 .. 100',
                                       status.HTTP_400_BAD_REQUEST)
        else:
            if _amount < 1:
                raise ProjectException(811, 'validation error',
                                       'amount must gratter than 1',
                                       status.HTTP_400_BAD_REQUEST)

        if _role:
            try:
                _object = RoleModel.objects.get(title=_role)
                attrs['role'] = _object
            except RoleModel.DoesNotExist:
                pass

        return attrs

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class PorsantAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=PorsantModel.objects.all(),
        error_messages={'not_exist': _(
            'پورسانت موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class PorsantDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=PorsantModel.objects.all(),
        error_messages={'not_exist': _('پورسانت موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class PorsantInformationSerializer(PorsantSerializer):
    owner = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    def get_owner(self, obj):
        if obj and hasattr(obj, 'owner') and obj.owner:
            return OwnerInfoSerializer(obj.owner).data
        return {}

    def get_service(self, obj):
        if obj and hasattr(obj, 'service') and obj.service:
            return ServiceSerializer(obj.service).data
        return {}

    def get_category(self, obj):
        if obj and hasattr(obj, 'category') and obj.category:
            return CategorySerializer(obj.category).data
        return {}

    def get_company(self, obj):
        if obj and hasattr(obj, 'company') and obj.company:
            return CompanySerializer(obj.company).data
        return {}

    def get_grade(self, obj):
        if obj and hasattr(obj, 'grade') and obj.grade:
            return GradeSerializer(obj.grade).data
        return {}

    def get_role(self, obj):
        if obj and hasattr(obj, 'role') and obj.role:
            return obj.role.title
        return None

class PorsantRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=PorsantModel.objects.all(),
        error_messages={'not_exist': _(
            'پورسانت موجود نیست'), 'invalid': _('داده ها نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class PorsantUpdateSerializer(PorsantSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Profile:----------
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileModel
        fields = ("owner", "father_name", "id_no", "national_code", "birthday", "birthplace",
                  "married", "children", "tel"
                  )

    owner = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    father_name = serializers.CharField(
        max_length=30, allow_blank=True, required=False)
    id_no = serializers.IntegerField(default=0, required=False)
    national_code = serializers.CharField(
        max_length=80, allow_blank=True, required=False)
    birthday = serializers.DateField(required=False)
    birthplace = serializers.CharField(
        max_length=70, allow_blank=True, required=False)
    married = serializers.BooleanField(default=False, required=False)
    children = serializers.IntegerField(default=0, required=False)
    tel = serializers.CharField(max_length=15, required=False)

    def validate(self, attrs):
        owner = attrs.get('owner', None)
        # Check national code with is_national_code_verify():

        return attrs

    def create(self, validated_data):
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileModel
        fields = ("owner", "father_name", "id_no", "national_code", "old_national_code", "birthday",
                  "birthplace", "married", "children", "tel"
                  )

    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    father_name = serializers.CharField(
        max_length=30, allow_blank=True, required=False)
    id_no = serializers.IntegerField(default=0, required=False)
    national_code = serializers.CharField(
        max_length=80, allow_blank=True, required=False)
    old_national_code = serializers.CharField(
        max_length=80, allow_blank=True, required=False)
    birthday = serializers.DateField(required=False)
    birthplace = serializers.CharField(
        max_length=70, allow_blank=True, required=False)
    married = serializers.BooleanField(default=False, required=False)
    children = serializers.IntegerField(default=0, required=False)
    tel = serializers.CharField(max_length=15, required=False)

    def validate(self, attrs):
        # Check national code with is_national_code_verify():

        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class ProfileInfoSerializer(serializers.Serializer):
    owner = serializers.SerializerMethodField(read_only=True)
    father_name = serializers.CharField(read_only=True)
    id_no = serializers.IntegerField(read_only=True)
    national_code = serializers.CharField(read_only=True)
    birthday = serializers.SerializerMethodField(read_only=True)
    age = serializers.SerializerMethodField(
        read_only=True, method_name="get_user_age")
    birthplace = serializers.CharField(read_only=True)
    married = serializers.BooleanField(read_only=True)
    children = serializers.IntegerField(read_only=True)
    latitude = serializers.IntegerField(read_only=True)
    longitude = serializers.IntegerField(read_only=True)
    province = serializers.CharField(read_only=True)
    city = serializers.CharField(read_only=True)
    district = serializers.IntegerField(read_only=True)
    address = serializers.CharField(read_only=True)
    comment = serializers.CharField(read_only=True)
    tel = serializers.CharField(read_only=True)

    def get_owner(self, obj):
        return obj.owner.pk

    def get_birthday(self, obj):
        if obj.birthday:
            return convert_gregorian_to_jalali_string_date(obj.birthday)
        return None

    def get_user_age(self, obj):
        if obj.birthday:
            _date = datetime.now().date()
            _diff = _date - obj.birthday
            _age = int(_diff.days / 365)
            return _age
        return None


# ----------Property:----------
class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyModel
        fields = ('id', 'title', 'description', 'type',)

    title = serializers.CharField(max_length=130)
    description = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    type = serializers.ChoiceField(choices=PropertyModel.TYPE_CHOICE)

    def validate(self, attrs):
        self.user = get_user(self.request)
        return attrs

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance

class PropertyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyModel
        fields = ('id', 'title', 'description', 'type',)

    title = serializers.CharField(max_length=130, required=False)
    description = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    type = serializers.ChoiceField(
        choices=PropertyModel.TYPE_CHOICE, required=False)

    def validate(self, attrs):
        self.user = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class PropertyInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)


# ----------Record:----------
class RecordInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    service = serializers.SerializerMethodField(read_only=True)
    service_title = serializers.SerializerMethodField(read_only=True)
    evidence = serializers.SerializerMethodField(read_only=True)
    evidence_title = serializers.SerializerMethodField(read_only=True)

    def get_service(self, obj):
        return obj.service.pk

    def get_service_title(self, obj):
        return obj.service.title

    def get_evidence(self, obj):
        return obj.evidence.pk

    def get_evidence_title(self, obj):
        return obj.evidence.title


# Role:
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleModel
        fields = ('title', 'parent')

    title = serializers.CharField(max_length=130)
    parent = serializers.PrimaryKeyRelatedField(many=False, required=False,
                                                queryset=RoleModel.objects.all(),
                                                error_messages={
                                                    'does_not_exist':
                                                    "role does not exist",
                                                    'invalid': "invalid value"
                                                })

    def validate(self, attrs):
        self.user = self.context['request'].user
        return attrs

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save
        return instance

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance
# For UserInfo


class RoleInfoGetSerializer(serializers.Serializer):
    title = serializers.CharField(read_only=True)
    states = serializers.SerializerMethodField(
        read_only=True, method_name="get_state_list")

    def get_state_list(self, obj):
        _state_list = {}
        _accesses = RoleAccessModel.objects.filter(role=obj)
        if _accesses:
            for _access in _accesses:
                _key = _access.state.pk
                _state_list[_key] = []
                _operate_list = []
                _permissions = RolePermissionModel.objects.filter(
                    access=_access)
                if _permissions:
                    for _permission in _permissions:
                        _operate = _permission.operate.pk
                        _state_list[_key].append(_operate)

        return _state_list
# Role Access:


class RoleAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleModel
        fields = ('id', 'role', 'state',)

    role = serializers.PrimaryKeyRelatedField(many=False,
                                              queryset=RoleModel.objects.all(),
                                              error_messages={
                                                  'does_not_exist':
                                                  "role does not exist",
                                                  'invalid': "invalid value"
                                              })
    state = serializers.PrimaryKeyRelatedField(many=False,
                                               queryset=StateModel.objects.all(),
                                               error_messages={
                                                   'does_not_exist':
                                                   "state does not exist",
                                                   'invalid': "invalid value"
                                               })

    def validate(self, attrs):
        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save
        return instance

    def create(self, validated_data):
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance


# Role permissions create
class RolesOperatessSerializer(serializers.Serializer):
    state = serializers.PrimaryKeyRelatedField(many=False,
                                               queryset=StateModel.objects.all(),
                                               error_messages={
                                                   'does_not_exist':
                                                   "state does not exist",
                                                   'invalid': "invalid value"
                                               })
    operates = serializers.ListSerializer(child=serializers.PrimaryKeyRelatedField(many=False,
                                                                                   queryset=OperateModel.objects.all(),
                                                                                   error_messages={
                                                                                       'does_not_exist':
                                                                                       "operate does not exist",
                                                                                       'invalid': "invalid value"
                                                                                   }))


class RolesStatesSerializer(serializers.Serializer):
    role = serializers.PrimaryKeyRelatedField(many=False,
                                              queryset=RoleModel.objects.all(),
                                              error_messages={
                                                  'does_not_exist':
                                                  "role does not exist",
                                                  'invalid': "invalid value"
                                              })
    states = serializers.ListSerializer(child=RolesOperatessSerializer())


class RolesPermissionsSerializer(serializers.Serializer):

    permissions = serializers.ListSerializer(child=RolesStatesSerializer())

    def validate(self, attrs):
        _user = self.context['request'].user
        permissions = attrs.get('permissions', None)
        if permissions:
            for permission in permissions:
                role = permission['role']
                if role.parent:
                    role_states = permission['states']
                    if role_states:
                        for obj in role_states:
                            state = obj['state']
                            operates = obj['operates']
                            if operates:
                                for operate in operates:
                                    parent_permission = RolePermissionModel.objects.filter(operate=operate,
                                                                                           role_permissions__role=role.parent, role_permissions__state=state)
                                    if not parent_permission:
                                        raise ProjectException(814,
                                                               _('validation error'),
                                                               _('The parent role does not have this permission.'),
                                                               status.HTTP_400_BAD_REQUEST)
                            else:
                                raise ProjectException(815,
                                                       _('validation error'),
                                                       _("The operate does not exist"),
                                                       status.HTTP_400_BAD_REQUEST)
                    else:
                        raise ProjectException(816,
                                               _('validation error'),
                                               _("The state does not exist"),
                                               status.HTTP_400_BAD_REQUEST)

        return super(RolesPermissionsSerializer, self).validate(attrs)
# Role Info Read


class RolePermissionInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    operate_id = serializers.CharField(read_only=True)


class RoleAccessInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    state_id = serializers.CharField(read_only=True)
    role_permissions = RolePermissionInfoSerializer(many=True)


class RoleInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    parent_id = serializers.IntegerField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    role_accesses = RoleAccessInfoSerializer(many=True)
# Checked ............


class RoleInfoFullSerializer(serializers.Serializer):
    roles = serializers.SerializerMethodField(
        read_only=True, method_name="get_roles")

    def get_roles(self, obj):
        roles = {}
        role_dict = {}
        state_list = []
        if obj.is_superuser:
            roles = {
                "system": {
                    "superuser": {
                        "all": ["manage", ]
                    }
                }
            }
        else:
            roles = {"system": {}}
            user_roles = UserRoleModel.objects.filter(user=obj)
            for user_role in user_roles:
                role = user_role.role
                role_dict[role.pk] = {}
                role_accesses = RoleAccessModel.objects.filter(role=role)
                if role_accesses:
                    for role_access in role_accesses:
                        state = role_access.state
                        role_permissions = RolePermissionModel.objects.filter(
                            access=role_access)
                        if role_permissions:
                            for role_permission in role_permissions:
                                state_list.append(role_permission.operate.pk)
                        role_dict[role.pk][state.pk] = state_list
            roles["system"] = role_dict
        return roles


# Sample for responses schema:
class SampleResponseSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=None, required=False)
    code = serializers.IntegerField(required=False)
    message = serializers.CharField(max_length=None, required=False)
    detail = serializers.CharField(max_length=None, required=False)
    # data    = serializers.DictField(child=serializers.CharField(), allow_empty=True)


class SampleSomeResponseSerializer(serializers.Serializer):
    status = serializers.CharField(required=False)
    code = serializers.IntegerField(required=False)
    deletes = serializers.ListField(
        child=serializers.CharField(max_length=None), required=False)
    virtual_delete = serializers.ListField(
        child=serializers.CharField(max_length=None), required=False)
    # data    = serializers.DictField(child=serializers.CharField(), allow_empty=True)


class SampleSomeVirResponseSerializer(serializers.Serializer):
    virtual_delete = serializers.ListField(
        child=serializers.CharField(max_length=None), required=False)


class SampleForgetPasswordResponseSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    token = serializers.CharField(read_only=True)


# ----------Service:----------

class ServiceSerializer(serializers.Serializer):
    class Meta:
        model = ServiceModel

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        group_id = serializers.IntegerField()
        static = serializers.CharField(
            max_length=130, required=False, allow_blank=True)
    id= serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    sku = serializers.CharField(required=False, max_length=130, allow_null=True)
    slug = serializers.CharField(max_length=130)
    image = serializers.CharField(max_length=None, required=False)
    description = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    category = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=CategoryModel.objects.all(),
                                                  error_messages={
        "does_not_exist": _("Category does not exist"),
        "invalid": _("invalid value"),
    },
    )
    company = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=CompanyModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Company does not exist"),
        "invalid": _("invalid value"),
    },
    )
    price = serializers.IntegerField(default=0)
    vat = serializers.IntegerField(default=0)
    discount = serializers.IntegerField(default=0)
    rebate = serializers.IntegerField(default=0)
    filters = FilterSerializer(required=False, many=True)

    is_installation = serializers.BooleanField(default=False)
    is_revival = serializers.BooleanField(default=False)
    revival_days = serializers.IntegerField(default=0)
    is_saleable=serializers.BooleanField(default=True)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)
    is_special = serializers.BooleanField(default=False)

    def validate(self, attrs):
       
        category = attrs.get('category', None)
        filters = attrs.get('filters', None)
        if filters:
            filters = [dict(i) for i in filters if i]
        if category and filters:
            items = [i.pk for i in GroupItemModel.objects.filter(group__categories__category=category)]
            for fil in filters:
                ret = [i for i in items if i == fil['id']]
                if not ret:
                    raise ProjectException(840, 'validation error',
                                           'filter not found',
                                           status.HTTP_400_BAD_REQUEST)
        set_create_user(attrs,self.request)
        set_image_file(attrs,'image')
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data, ['filters'])

class ServiceAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceModel.objects.all(),
        error_messages={'not_exist': _(
            'سرویس موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class ServiceDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceModel.objects.all(),
        error_messages={'not_exist': _('سرویس موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class ServiceInformationSerializer(ServiceSerializer):
    
    class FilterSerializer(GroupSerializer.GroupItemSerializer):
        group=serializers.SerializerMethodField()
        static_val=serializers.CharField(read_only=True)

        def get_group(self,obj):
            if obj and hasattr(obj, 'group') and obj.group:
                return GroupInformation_ServiceInformationSerializer(obj.group).data
            return {}
       

    image = serializers.SerializerMethodField(read_only=True)
    discount_price = serializers.SerializerMethodField(read_only=True)
    discounted_price = serializers.SerializerMethodField(read_only=True)
    vat_price = serializers.SerializerMethodField(read_only=True)
    final_price = serializers.SerializerMethodField(read_only=True)
    company = serializers.SerializerMethodField(read_only=True)
    category = serializers.SerializerMethodField(read_only=True)
    gallery = serializers.SerializerMethodField(read_only=True)
    filters = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)


    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_category(self, obj):
        if obj and hasattr(obj, 'category') and obj.category:
            return CategoryInformationSerializer(instance=obj.category).data
        return {}

    def get_company(self, obj):
        if obj and hasattr(obj, 'company') and obj.company:
            return CompanyInformationSerializer(instance=obj.company).data
        return {}

    def get_gallery(self, obj):
        if obj and hasattr(obj, 'gallery') and obj.gallery:
            return ServiceGalleryInformationSerializer(obj.gallery, many=True).data
        return []

    def get_discount_price(self, obj):
        orginal_price = obj.price
        discount = obj.discount
        discounted_price = orginal_price*(discount/100)
        discounted_price = int(discounted_price)
        return discounted_price

    def get_discounted_price(self, obj):
        orginal_price = obj.price
        discounted_price = self.get_discount_price(obj)
        price = orginal_price-discounted_price
        return price

    def get_vat_price(self, obj):
        orginal_price = obj.price
        vat = obj.vat
        discounted_price = self.get_discounted_price(obj)
        vat_price = discounted_price*(vat/100)
        vat_price = int(vat_price)
        return vat_price

    def get_final_price(self, obj):
        orginal_price = obj.price
        vat_price = self.get_vat_price(obj)
        price = orginal_price + vat_price
        return price

    def get_filters(self, obj):

        if obj and hasattr(obj, 'properties') and obj.properties:
            properties = [i.property for i in obj.properties.annotate(static_val=F('static__value')).select_related('static')]
            serializer = self.FilterSerializer(properties, many=True)
            #data = serializer.data.copy()
            # _statics = [(i.property, i.static.value)
            #             for i in _objects if hasattr(i, 'static') and i.static]
            # for item in _data:
            #     if item['group_kind'] == 'static':
            #         for st in _statics:
            #             if item['id'] == st[0].pk:
            #                 item['static'] = st[1]
            #                 break
            #         else:
            #             item['static'] = ''
            #     else:
            #         item['static'] = ''
            return serializer.data
        return []

    def get_status(self, obj):
        return get_status(obj)

class ServiceInformation_ShopInformationSerializer(ServiceInformationSerializer):
    category = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=CategoryModel.objects.all(),
                                                  error_messages={
        "does_not_exist": _("Category does not exist"),
        "invalid": _("invalid value"),
    },
    )
    company = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=CompanyModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Company does not exist"),
        "invalid": _("invalid value"),
    },
    )
   
    filters=None

class ServiceRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceModel.objects.all(),
        error_messages={'not_exist': _(
            'خدمت موجود نیست'), 'invalid': _('داده ها نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}    

class ServiceUpdateSerializer(ServiceSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,required=False)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data,['filters'])

class ServiceUploadSerializer(serializers.Serializer):
    id= serializers.IntegerField(read_only=True)
    image = serializers.CharField(max_length=None, required=False)
    def validate(self, attrs):
        set_update_user(attrs,self.request)
        set_image_file(attrs,'image')
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)
        
# ----------ServiceDependent:----------

def set_type(attrs,type_value):
    if type_value:
        type_choices=list(ServiceDependentSerializer.TYPE_CHOICE)
        type_value = [i for i in type_choices if type_value in i]
        if type_value:
            type_value=type_value[0]
    if type_value:
        attrs['type']=type_value[1]

def get_type(type_value):
    if type_value is not None:
        type_choices=list(ServiceDependentModel.TYPE_CHOICE)
        type_value = [i for i in type_choices if type_value in i]
        if type_value:
            type_value=type_value[0]
    if type_value:
        return type_value[1]
    return ''

class ServiceDependentSerializer(serializers.Serializer):
    class Meta:
        model = ServiceDependentModel
    
    TYPE_CHOICE=(('every shop',0),('once for this service',1),('once for this service category',2),('once qty',3),('once',4))

    id = serializers.IntegerField(read_only=True)
    primary=serializers.PrimaryKeyRelatedField(
        required=True, many=False, queryset=ServiceModel.objects.all(),
        error_messages={
        "does_not_exist": _("سرویس موجود نیست"),
        "invalid": _("داده نامعتبر است"),
        },
    )
    dependent=serializers.PrimaryKeyRelatedField(
        required=True, many=False, queryset=ServiceModel.objects.all(),
        error_messages={
        "does_not_exist": _("سرویس موجود نیست"),
        "invalid": _("داده نامعتبر است"),
        },
    )
    type = serializers.ChoiceField(choices=TYPE_CHOICE)
    qty=serializers.IntegerField(default=1)
    price=serializers.IntegerField(required=False)
    vat=serializers.IntegerField(required=False)
    discount= serializers.IntegerField(required=False)
    status= serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_status(attrs)
        primary= attrs.get('primary')
        dependent=attrs.get('dependent')
        with contextlib.suppress(ObjectDoesNotExist):
            ServiceDependentModel.objects.get(Q(primary=primary,dependent=dependent) | Q(primary=dependent,dependent=primary))
            raise ProjectException(820, 'خطای راستی آزمایی','این محصول اصلی و وابسته وجود دارد',status.HTTP_400_BAD_REQUEST)
        price= attrs.pop('price', None)
        vat= attrs.pop('vat',None)
        discount= attrs.pop('discount', None)

        if dependent:= attrs.get('dependent',None):
            if price is None:
                price=dependent.price
            if discount is None:
                discount=dependent.discount
            if vat is None:
                vat=dependent.vat
        attrs['price']=price
        attrs['vat']=vat
        attrs['discount']=discount
        type_value=attrs.pop('type')
        set_type(attrs,type_value)

        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class ServiceDependentAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceDependentModel.objects.all(),
        error_messages={'not_exist': _(
            'سرویس وابسته موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class ServiceDependentDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceDependentModel.objects.all(),
        error_messages={'not_exist': _('سرویس وابسته موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):
        if 'id' not in self.validated_data or not self.validated_data['id']:
            return
        objects = self.validated_data['id']
        [obj.delete() for obj in objects]

       

class ServiceDependentInformationSerializer(ServiceDependentSerializer):

    class servicenformationSerializer(serializers.Serializer):
        id=serializers.IntegerField(read_only=True)
        title=serializers.CharField(read_only=True)


    primary=serializers.SerializerMethodField(read_only=True)
    dependent=serializers.SerializerMethodField(read_only=True)
    status= serializers.SerializerMethodField(read_only=True)
    type = serializers.SerializerMethodField(read_only=True)
    discount_price = serializers.SerializerMethodField(read_only=True)
    discounted_price = serializers.SerializerMethodField(read_only=True)
    vat_price = serializers.SerializerMethodField(read_only=True)
    final_price = serializers.SerializerMethodField(read_only=True)
   

    def get_primary(self, obj):
        return self.servicenformationSerializer(obj.primary,many=False).data

    def get_dependent(self,obj):
        return self.servicenformationSerializer(obj.dependent,many=False).data

    def get_type(self, obj):
        return get_type(obj.type)
   
    def get_status(self, obj):
        return get_status(obj)

    def get_discount_price(self, obj):
        orginal_price = obj.price
        discount = obj.discount
        discounted_price = orginal_price*(discount/100)
        discounted_price = int(discounted_price)
        return discounted_price

    def get_discounted_price(self, obj):
        orginal_price = obj.price
        discounted_price = self.get_discount_price(obj)
        price = orginal_price-discounted_price
        return price

    def get_vat_price(self, obj):
        orginal_price = obj.price
        vat = obj.vat
        discounted_price = self.get_discounted_price(obj)
        vat_price = discounted_price*(vat/100)
        vat_price = int(vat_price)
        return vat_price

    def get_final_price(self, obj):
        orginal_price = obj.price
        vat_price = self.get_vat_price(obj)
        price = orginal_price + vat_price
        return price

class ServiceDependentRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceDependentModel.objects.all(),
        error_messages={'not_exist': _(
            'سرویس وابسته موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class ServiceDependentUpdateSerializer(ServiceDependentSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
    question = serializers.CharField(required=False,max_length=None)
    answer = serializers.CharField(required=False,max_length=None)
    status = serializers.ChoiceField(required=False, choices=STATUS_CHOICE)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------ServiceGallery:----------

class ServiceGallerySerializer(serializers.Serializer):
    class Meta:
        model = ServiceGalleryModel
     
    id   = serializers.IntegerField(read_only=True)
    file = serializers.CharField(max_length=None)
    service = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=ServiceModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("سرویس موجود نیست"),
        "invalid": _("داده ها نامعتبر است"),
    },
    )

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_image_file(attrs,'file')
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class ServiceGalleryDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=ServiceGalleryModel.objects.all(),
        error_messages={'not_exist': _('گالری موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class ServiceGalleryInformationSerializer(ServiceGallerySerializer):
    service = serializers.SerializerMethodField(read_only=True)
    file = serializers.SerializerMethodField(read_only=True)

    def get_service(self, obj):
        if obj and hasattr(obj,'service') and obj.service:
            return ServiceSerializer(obj.service).data
        return {}

    def get_file(self, obj):
        if obj and hasattr(obj,'file') and obj.file:
            return obj.file.url
        return None


# ----------Setting:----------


class SettingAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettingModel
        fields = ('value',)
    value = serializers.IntegerField()

    def validate(self, attrs):
        self.user = get_user(self.request)
        _value = attrs.get('value', None)
        if _value and (_value < 1 or _value > 100):
            raise ProjectException(810, 'validation error',
                                   'amount between 1 .. 100',
                                   status.HTTP_400_BAD_REQUEST)
        return attrs

    def create(self, validated_data):

        _value = str(validated_data.get('value'))
        _key = settings.AGENT_COMMISSION_TAG
        try:
            _object = self.Meta.model.objects.get(key=_key)
            _object.value = _value
            _object.save()
        except ObjectDoesNotExist:
            _data = {'key': _key, 'value': _value}
            _object = self.Meta.model.objects.create(** _data)
        return _object


class SettingSellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettingModel
        fields = ('value',)
    value = serializers.IntegerField()

    def validate(self, attrs):
        self.user = get_user(self.request)
        _value = attrs.get('value', None)
        if _value and (_value < 1 or _value > 100):
            raise ProjectException(810, 'validation error',
                                   'amount between 1 .. 100',
                                   status.HTTP_400_BAD_REQUEST)
        return attrs

    def create(self, validated_data):

        _value = validated_data.get('value')
        _key = _key = settings.SELLER_COMMISSION_TAG
        try:
            _object = self.Meta.model.objects.get(key=_key)
            _object.value = str(_value)
            _object.save()
        except ObjectDoesNotExist:
            _data = {'key': _key, 'value': _value}
            _object = self.Meta.model.objects.create(** _data)
        return _object


class SettingInfoSerializer(serializers.Serializer):
    key = serializers.CharField(read_only=True)
    value = serializers.CharField(read_only=True)


# ----------Set:For Blog----------
class SetSerializer(serializers.Serializer):
    class Meta:
        model = SetModel

    id=serializers.IntegerField(read_only=True)    
    title = serializers.CharField(max_length=130)
    icon = serializers.CharField(max_length=None, required=False)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    parent = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=SetModel.objects.all(),
                                                error_messages={
        "does_not_exist": _("Set does not exist"),
        "invalid": _("invalid value"),
    },
    )
    status= serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_image_file(attrs,'icon')
        set_status(attrs)
        return attrs

    def create(self, validated_data):
         return execute_create(self.Meta.model, validated_data)

class SetAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=SetModel.objects.all(),
        error_messages={'not_exist': _(
            'مجموعه موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class SetDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=SetModel.objects.all(),
        error_messages={'not_exist': _('مجموعه موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class SetInformationSerializer(SetSerializer):
    slug = serializers.CharField(read_only=True)
    parent = serializers.SerializerMethodField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    icon = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    sub_sets = serializers.SerializerMethodField(read_only=True)

    def get_icon(self, obj):
        if obj and hasattr(obj,'icon') and obj.icon:
            return obj.icon.url
        return ''

    def get_parent(self, obj):
        if obj and hasattr(obj,'parnet') and obj.parent:
            return SetSerializer(obj.parent).data
        return {}

    def sub_sets(self, obj):
        if obj and hasattr(obj, 'sub_sets') and obj.sub_sets:
            return  SetInformationSerializer(obj.sub_sets,many=True).data
        return []

    def get_status(self, obj):
        return get_status(obj)

class SetRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=SetModel.objects.all(),
        error_messages={'not_exist': _(
            'دسته موجود نیست'), 'invalid': _('داده ها نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class SetUpdateSerializer(SetSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

# ----------SMS:----------

class SmsSerializer(serializers.Serializer):
    cellphone = serializers.CharField(max_length=15)
    msg = serializers.CharField(max_length=None)

# ----------Shop:----------


def shop_validate(user, attrs,add_address=False):
    owner = attrs.get('owner', None)
    if owner and owner.pk != user.pk:
        if not user.is_staff:
            try:
                UserModel.objects.get(owner=user.pk)
            except ObjectDoesNotExist as e:
                raise ProjectException(808, 'validation error', "select owner forbidden", status.HTTP_403_FORBIDDEN) from e
            except UserModel.MultipleObjectsReturned:
                pass

    elif not owner:
        owner = user
        attrs['owner'] = user
    if add_address:
        address = attrs.get('address', None)
        if address is None:
            try:
                attrs['address'] = AddressModel.objects.get(owner=owner, is_default=True)
            except ObjectDoesNotExist as e:
                raise ProjectException(807, _('validation error'), "{'address': ['This field is required.']}", status.HTTP_400_BAD_REQUEST) from e
            except AddressModel.MultipleObjectsReturned:
                attrs['address'] = AddressModel.objects.filter(owner=owner, is_default=True)[0]


    return attrs

def shop(user, model, validated_data, state):
    items = validated_data.pop('items') if 'items' in validated_data else None
    owner = validated_data.get('owner')
    try:
        validated_data['modified_by'] = user
        instance = model.objects.get(owner=owner, state=state)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
    except ObjectDoesNotExist:
        validated_data['created_by'] = user
        instance = model(**validated_data)

    instance.shopItems = items
    instance.save()
    return instance


class ShopItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    service = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=ServiceModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Service does not exist"),
        "invalid": _("invalid value"),
    },
    )
    price = serializers.IntegerField(read_only=True)
    qty = serializers.IntegerField(min_value=1, default=1)
    
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    
class ShopItemInformationSerializer(ShopItemSerializer):
    service=serializers.SerializerMethodField(read_only=True)
    is_dependent = serializers.BooleanField(read_only=True)
    dependent=serializers.SerializerMethodField(read_only=True)
    final_price = serializers.SerializerMethodField(read_only=True)

    def get_service(self,obj):
        if obj and hasattr(obj,'service') and obj.service:
            return ServiceInformation_ShopInformationSerializer(obj.service).data
        return {}

    def get_dependent(self,obj):
        if obj and hasattr(obj,'dependent') and obj.dependent:
            return ServiceSerializer(obj.dependent).data
        return {}
    
    def get_final_price(self, obj):
        return obj.qty * obj.price

class ShopSerializer(serializers.Serializer):
    class Meta:
        model = ShopModel
       
    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    date = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    address = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=AddressModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Address does not exist"),
        "invalid": _("invalid value"),
    },
    )
    items = ShopItemSerializer(required=False, many=True)
    bank = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=BankModel.objects.all(),
                                              error_messages={
        "does_not_exist": _("Bank does not exist"),
        "invalid": _("invalid value"),
    },
    )
    platform = serializers.ChoiceField(
        choices=DepositModel.PLATFORM_CHOICE, default='web')
    is_wallet = serializers.BooleanField(default=False)
    callback_url = serializers.CharField(max_length=None)

    def validate(self, attrs):
        self.user = get_user(self.request)
        return shop_validate(self.user, attrs)

    def create(self, validated_data):
        items = validated_data.pop('items') if 'items' in validated_data else None
        bank = validated_data.pop('bank')
        platform = validated_data.pop('platform')
        owner = validated_data.get('owner')
        is_wallet = validated_data.pop('is_wallet')
        callbak_url = validated_data.pop('callback_url')
        try:
            validated_data['modified_by'] = self.user
            instance = self.Meta.model.objects.get(owner=owner, state_id='cart')
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
        except ObjectDoesNotExist as e:
            if not items:
                raise ProjectException(811,"runtime error","shop cart is empty",status.HTTP_400_BAD_REQUEST) from e

            validated_data['state_id'] = 'cart'
            validated_data['created_by'] = self.user
            instance = self.Meta.model(**validated_data)
            instance.save()
        instance.shopItems = items
        instance.state_id = 'pendding'
        instance.pending_expired = datetime.now()+settings.EXPIRE_DEPOSITE
        instance.request = self.request
        instance.bank = bank
        instance.platform = platform
        instance.is_wallet = is_wallet
        instance.callback_url = callbak_url
        instance.save()
        return instance

class ShopUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopModel
        fields = ('id', 'address')
    id = serializers.IntegerField(read_only=True)
    address = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=AddressModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Address does not exist"),
        "invalid": _("invalid value"),
    },
    )

    def validate(self, attrs):
        self.user = get_user(self.request)
        return shop_validate(self.user, attrs)

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class ShopPaymentSerializer(serializers.Serializer):
    class Meta:
        model = ShopModel
       

    bank = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=BankModel.objects.all(),
                                              error_messages={
        "does_not_exist": _("Bank does not exist"),
        "invalid": _("invalid value"),
    },
    )
    platform = serializers.ChoiceField(choices=DepositModel.PLATFORM_CHOICE, default='web')
    is_wallet = serializers.BooleanField(default=False)
    callback_url = serializers.CharField(max_length=None)

    def validate(self, attrs):
        attrs['owner'] = self.context['owner']
        self.user = get_user(self.request)
        return shop_validate(self.user, attrs)


    def update(self, instance, validated_data):
        
        bank = validated_data.pop('bank')
        platform = validated_data.pop('platform')
        is_wallet = validated_data.pop('is_wallet')
        callback_url = validated_data.pop('callback_url')

        instance.bank = bank
        instance.request = self.request
        instance.platform = platform
        instance.is_wallet = is_wallet
        instance.callback_url = callback_url
        instance.is_payment = True
        instance.shopItems = ShopItemSerializer(instance.items.select_related('service').filter(is_dependent=False),many=True).data
        instance.save()
        return instance

class ShopCartSerializer(serializers.Serializer):
    class Meta:
        model = ShopModel
      
    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
        error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    date = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    # #address = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=AddressModel.objects.all(),
    #                                              #error_messages={
    #     "does_not_exist": _("Address does not exist"),
    #     "invalid": _("invalid value"),
    # },
    # )
    items = ShopItemSerializer(required=False, many=True)

    def validate(self, attrs):
        self.user = get_user(self.request)
        return shop_validate(self.user, attrs,False)

    def create(self, validated_data):
        return shop(self.user, self.Meta.model, validated_data, 'cart')

class ShopNextSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopModel
        fields = ('id', 'owner', 'date', 'description', 'address', 'items')
    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("User does not exist"),
        "invalid": _("invalid value"),
    },
    )
    date = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    address = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=AddressModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Address does not exist"),
        "invalid": _("invalid value"),
    },
    )
    items = ShopItemSerializer(required=False, many=True)

    def validate(self, attrs):
        self.user = get_user(self.request)
        return shop_validate(self.user, attrs)

    def create(self, validated_data):
        return shop(self.user, self.Meta.model, validated_data, 'next')

class ShopInformationSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)
    owner = OwnerInformationSerializer(read_only=True)
    date = serializers.SerializerMethodField(read_only=True)
    description = serializers.CharField(read_only=True)
    #address = AddressInforSerializer(read_only=True)
    address = AddressInformationSerializer(read_only=True)
    items = serializers.SerializerMethodField(read_only=True)
    state = serializers.SerializerMethodField(read_only=True)
    token = serializers.CharField(read_only=True, max_length=None)
    url = serializers.CharField(read_only=True, max_length=None)
    callback_url = serializers.CharField(read_only=True, max_length=None)
    deposit = serializers.SerializerMethodField(read_only=True)

    def get_date(self, obj):
        if obj.date:
            return convert_gregorian_to_jalali_string_datetime(obj.date)
        return None

    def get_items(self, obj):
        if items := ShopItemModel.objects.filter(shop=obj):
            serializer = ShopItemInformationSerializer(items, many=True)
            return serializer.data
        return []

    def get_owner(self, obj):
        return obj.owner.pk

    def get_address(self, obj):
        return obj.address.pk if obj.address else None

    def get_deposit(self, obj):
        if hasattr(obj, 'deposit_shop') and obj.deposit_shop:
            deposit = obj.deposit_shop
            date = ''
            if deposit.date:
                date = deposit.date.strftime("%Y-%m-%d %H:%M:%S")

            deposit_date = ''
            if deposit.deposit_date:
                deposit_date = deposit.deposit_date.strftime("%Y-%m-%d %H:%M:%S")

            return {'platform': deposit.platform, 'date': date, 'bank': deposit.bank.title, 'receipt_number': deposit.receipt_number, 'is_deposited': deposit.is_deposited, 'deposit_date': deposit_date}
        return {}

    def get_state(self, obj):
        if hasattr(obj, 'state') and obj.state:
            return obj.state.title
        return ''


# State:

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StateModel
        fields = ('title',)

    title = serializers.CharField(max_length=130)

    def validate(self, attrs):
        self.user = self.context['request'].user
        return attrs

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data['modified_by'] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def create(self, validated_data):
        if self.user and self.user.pk:
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        new_instance.save()
        return new_instance

# ----------Status:----------

class StatusSerializer(serializers.Serializer):
    class Meta:
        model = StatusModel
    
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    description = serializers.CharField(required=False, max_length=None, allow_blank=True)
    client_message = serializers.CharField(required=False, max_length=150, allow_blank=True)
    seller_message = serializers.CharField(required=False, max_length=150, allow_blank=True)
    agent_message = serializers.CharField(required=False, max_length=150, allow_blank=True)
    admin_message = serializers.CharField(required=False, max_length=150, allow_blank=True)
    is_client_message = serializers.BooleanField(default=False)
    is_seller_message = serializers.BooleanField(default=False)
    is_agent_message = serializers.BooleanField(default=False)
    is_admin_message = serializers.BooleanField(default=False)
    system_status = serializers.PrimaryKeyRelatedField(required=False, many=False, queryset=StatusModel.objects.all(),
        error_messages={
        "does_not_exist": _("status does not exist"),
        "invalid": _("invalid value"),
    },
        allow_null=True
    )

    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class StatusAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=StatusModel.objects.all(),
        error_messages={'not_exist': _(
            'وضعیت موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class StatusDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=StatusModel.objects.all(),
        error_messages={'not_exist': _('وضعیت موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class StatusInformationSerializer(StatusSerializer):
    system_status = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    is_system = serializers.BooleanField(read_only=True)

    def get_status(self, obj):
        return get_status(obj)

    def get_system_status(self, obj):
        if obj and hasattr(obj, 'system_status') and obj.system_status:
            return StatusInformationSerializer(obj.system_status).data
        return {}

class StatusRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=StatusModel.objects.all(),
        error_messages={'not_exist': _(
            'وضعیت موجود نیست'), 'invalid': _('داده ها نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class StatusUpdateSerializer(StatusSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = None

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Support:----------
class SupportSerializer(serializers.Serializer):
    class Meta:
        model = Support
    
    id = serializers.IntegerField(read_only=True)
    owner = serializers.PrimaryKeyRelatedField(many=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("کاربر وجود ندارد"),
        "invalid": _("داده ها نامعتبر است"),
    },
    )
    service = serializers.PrimaryKeyRelatedField(many=False, queryset=ServiceModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("سرویس وجود ندارد"),
        "invalid": _("داده ها نامعتبر است"),
    },
    )
    description = serializers.CharField(required=False, max_length=None, allow_blank=True)
    serries = serializers.CharField(required=False, max_length=150, allow_blank=True)
    state = serializers.PrimaryKeyRelatedField(many=False, queryset=StatusModel.objects.all(),
        error_messages={
        "does_not_exist": _("وضعیت وجود ندارد"),
        "invalid": _("داده های نامعتبر است"),
    },
    )
    revival_date = serializers.DateField(required=False, allow_null=True)
    installation_date = serializers.DateField(required=False, allow_null=True)

    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        set_status(attrs)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class SupportAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=Support.objects.all(),
        error_messages={'not_exist': _(
            'وضعیت موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class SupportDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=Support.objects.all(),
        error_messages={'not_exist': _('وضعیت موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class SupportInformationSerializer(SupportSerializer):

    class MyShopInformationSerializer(ShopInformationSerializer):
        items=None
        address=None


    owner = serializers.SerializerMethodField(read_only=True)
    service = serializers.SerializerMethodField(read_only=True)
    shop = serializers.SerializerMethodField(read_only=True)
    shop_item = serializers.SerializerMethodField(read_only=True)
    installation_date = serializers.SerializerMethodField(read_only=True)
    revival_date = serializers.SerializerMethodField(read_only=True)
    state = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)


    def get_owner(self, obj):
        if obj and hasattr(obj, 'owner') and obj.owner:
            return OwnerInformationSerializer(obj.owner).data
        return {}

    def get_service(self, obj):
        if obj and hasattr(obj, 'service') and obj.service:
            return ServiceSerializer(obj.service).data
        return {}

    def get_state(self, obj):
        if obj and hasattr(obj, 'state') and obj.state:
            return SupportInformationSerializer(obj.state).data
        return {}

    def get_shop(self, obj):
        if obj and hasattr(obj, 'shop_item') and obj.shop_item and hasattr(obj.shop_item, 'shop') and obj.shop_item.shop:
            return self.MyShopInformationSerializer(obj.shop_item.shop).data
        return {}

    def get_installation_date(self,obj):
        if obj and hasattr(obj, 'installation_date') and obj.installation_date:
            return convert_gregorian_to_jalali_string_datetime(obj.installation_date)
        return ''      
    
    def get_revival_date(self,obj):
        if obj and hasattr(obj, 'revival_date') and obj.revival_date:
            return convert_gregorian_to_jalali_string_datetime(obj.revival_date)
        return ''

    def get_shop_item(self, obj):
        if obj and hasattr(obj, 'shop_item') and obj.shop_item:
            return ShopItemSerializer(obj.shop_item).data
        return {}

    def get_status(self, obj):
        return get_status(obj)

class SupportRecycleSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=Support.objects.all(),
        error_messages={'not_exist': _(
            'وضعیت موجود نیست'), 'invalid': _('داده ها نامعتبر است')},
    ))
    def validate(self, attrs):
        return attrs

    def recycle(self):
        execute_recycle(self.validated_data)
        return {}

class SupportUpdateSerializer(SupportSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        attrs.pop('created_by')
        attrs['modified_by'] = get_user(self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)


# ----------Tag: for blog----------
class TagSerializer(serializers.Serializer):
    class Meta:
        model = TagModel
     
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)

    def validate(self, attrs):
        title = attrs.get('title', None)
        try:
            self.instance = TagModel.objects.get(title=title)
        except ObjectDoesNotExist:
            pass
        return attrs
    
    def update(self, instance, validated_data):
        return execute_update(instance, validated_data) 
    
    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)


# Token:
class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenModel
        fields = ('key', 'refresh_token', 'user',
                  'remote_addr', 'user_agent', 'player_id')

    key = serializers.CharField(max_length=None)
    refresh_token = serializers.CharField(max_length=None)
    remote_addr = serializers.CharField(max_length=None)
    player_id = serializers.CharField(max_length=None)
    user_agent = serializers.CharField(max_length=None)
    user = serializers.PrimaryKeyRelatedField(many=False,
                                              queryset=UserModel.objects.all(),
                                              error_messages={
                                                  'does_not_exist':
                                                  "user does not exist",
                                                  'invalid': "invalid value"
                                              })

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        _player_id = validated_data['player_id']
        _remote_addr = validated_data['remote_addr']
        _user_agent = validated_data['user_agent']
        _user = validated_data['user']
        _user_id = _user.id
        if _player_id:
            try:
                _object = TokenModel.objects.get(player_id=_player_id)
                _object.delete()
            except TokenModel.DoesNotExist:
                pass
        _new_instance = self.Meta.model(**validated_data)
        _new_instance.save()
        return _new_instance
# Refresh Token:


class RefreshTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenModel
        fields = ('access_token', 'refresh_token',)

    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(max_length=None)

    def validate(self, attrs):
        import jwt
        from app.player import get_player_id

        _request = self.context['request']
        refresh_token = attrs.pop('refresh_token', None)
        try:
            refresh_token_decode = jwt.decode(
                refresh_token, key=settings.SECRET_KEY, algorithms=[settings.SECRET_ALGORITM])
            if refresh_token_decode['grant_type'] != 'refresh_token':
                raise ProjectException(
                    440, _('Unauthorized'), 'The token is invalid.', status.HTTP_401_UNAUTHORIZED)
            _player_id = refresh_token_decode['player_id']
            _user_id = refresh_token_decode['user_id']
            _user_name = refresh_token_decode['user_name']
            _unlimited = refresh_token_decode['unlimited']
            _expires_at = refresh_token_decode['expires_at']
            date_time_exp = datetime.strptime(
                _expires_at, '%B %d %Y - %H:%M:%S')
            date_time_now = datetime.strptime(datetime.utcnow().strftime(
                '%B %d %Y - %H:%M:%S'), '%B %d %Y - %H:%M:%S')
            _req_player_id = get_player_id(request=_request)[0]
            if _player_id != _req_player_id:
                raise ProjectException(441, _('Unauthorized'), _('The token is invalid for this system.'),
                                       status.HTTP_401_UNAUTHORIZED)
            elif not (_unlimited) and (date_time_exp < date_time_now):
                raise ProjectException(443, _('Unauthorized'), _('The refresh token has expired.'),
                                       status.HTTP_401_UNAUTHORIZED)
            try:
                self.instance = TokenModel.objects.get(
                    refresh_token=refresh_token, player_id=_player_id)
                access_expires_in = settings.ACCESS_TOKEN_LIFETIME
                new_access_token = jwt.encode({
                    'grant_type': 'access_token',
                    'user_id': _user_id,
                    'user_name': _user_name,
                    'player_id': _player_id,
                    'unlimited': False,
                    'created_at': datetime.utcnow().strftime('%B %d %Y - %H:%M:%S'),
                    'expires_at': (datetime.utcnow() + access_expires_in).strftime('%B %d %Y - %H:%M:%S'),
                }, key=settings.SECRET_KEY, algorithm=settings.SECRET_ALGORITM)
                attrs['key'] = new_access_token
                refresh_expires_in = settings.REFRESH_TOKEN_LIFETIME
                unlimited = settings.REFRESH_TOKEN_UNLIMITED
                new_refresh_token = jwt.encode({
                    'grant_type': 'refresh_token',
                    'user_id': _user_id,
                    'user_name': _user_name,
                    'player_id': _player_id,
                    'unlimited': unlimited,
                    'created_at': datetime.utcnow().strftime('%B %d %Y - %H:%M:%S'),
                    'expires_at': (datetime.utcnow() + refresh_expires_in).strftime('%B %d %Y - %H:%M:%S'),
                }, key=settings.SECRET_KEY, algorithm=settings.SECRET_ALGORITM)
                attrs['refresh_token'] = new_refresh_token
            except:
                raise ProjectException(445, _('Unauthorized'), _('The refresh token is invalid.'),
                                       status.HTTP_401_UNAUTHORIZED)
        except:
            raise ProjectException(445, _('Unauthorized'), _('The refresh token is invalid.'),
                                   status.HTTP_401_UNAUTHORIZED)
        return attrs

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.access_token = instance.key
        return instance


# User:
class UserRegisterSerializer(serializers.Serializer):
    class Meta:
        model = UserModel
        

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=130, required=False)
    cellphone = serializers.CharField(max_length=15, required=True)
    email = serializers.EmailField(required=False)
    gender = serializers.ChoiceField(
        choices=UserModel.GENDER_CHOICE, required=False)
    avatar = serializers.ImageField(
        max_length=None, use_url=True, allow_empty_file=True, required=False)
  

    def validate(self, attrs):

       

        cellphone = attrs.get('cellphone', None)
        email = attrs.get('email', None)

        # Check unique Field:
        if email:
            try:
                UserModel.objects.get(email=email)
                raise ProjectException(
                    809, 'validation error', 'There is a user with this email in this system.', status_code=status.HTTP_400_BAD_REQUEST)
            except UserModel.DoesNotExist:
                pass
        if cellphone:
            if not validate_phone_number(cellphone, "IR"):
                raise ProjectException(807,
                                       _("validation error"), _(
                                           "'Cellphone': this field is invalid"),
                                       status.HTTP_400_BAD_REQUEST)
            try:
                UserModel.objects.get(cellphone=cellphone)
                raise ProjectException(808,
                                       'validation error', 'There is a user with this cellphone in this system.',
                                       status_code=status.HTTP_400_BAD_REQUEST)
            except UserModel.DoesNotExist:
                pass
        # --------Address Fields:---------------
       
        return attrs

    def create(self, validated_data):
      
        #_password = str(get_verfication_code(8))
        _password = validated_data.get('password', '')
        if not _password:
            _password = str(get_verfication_code(8))

        # Create Username:
        first = validated_data.get('first_name', '')
        last = validated_data.get('last_name', '')
        _name = "".join([first, last])
        validated_data['username'] = generate_username(_name)
        new_instance = self.Meta.model(**validated_data)
        if _password:
            new_instance.set_password(_password)
            new_instance.verification_code = _password

        new_instance.status = 1
        new_instance.is_active = True
        try:
            new_instance.role = RoleModel.objects.get(title='client')
        except ObjectDoesNotExist:
            raise ProjectException(852, _("runtime error"), _(
                "role error"), status.HTTP_400_BAD_REQUEST,)
    
        new_instance.save()
        return new_instance

class UserSerializer(serializers.Serializer):
    class Meta:
        model = UserModel
       
    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=130, required=False)
    cellphone = serializers.CharField(max_length=15, required=True)
    email = serializers.EmailField(required=False)
    gender = serializers.ChoiceField(
        choices=UserModel.GENDER_CHOICE, required=False)
    avatar = serializers.ImageField(
        max_length=None, use_url=True, allow_empty_file=True, required=False)
    role = serializers.PrimaryKeyRelatedField(many=False, required=True, queryset=RoleModel.objects.all(),
                                              error_messages={
        "does_not_exist": _("role does not exist"),
        "invalid": _("invalid value"),
    },
    )
    agent = serializers.PrimaryKeyRelatedField(many=False, required=False, queryset=UserModel.objects.all(),
                                               error_messages={
        "does_not_exist": _("user does not exist"),
        "invalid": _("invalid value"),
    },
    )
    latitude = serializers.FloatField(default=0.0, required=False)
    longitude = serializers.FloatField(default=0.0, required=False)
    address = serializers.CharField(max_length=None, required=False)
    plaque = serializers.IntegerField(default=0, required=False)
    level = serializers.IntegerField(default=0, required=False)
    unit = serializers.IntegerField(default=0, required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICE,default=1)

    def validate(self, attrs):
        self.user = get_user(self.request)
        _cellphone = attrs.get('cellphone', None)
        _email = attrs.get('email', None)
        _role = attrs.pop('role', None)
        _agent = attrs.pop('agent', None)

        if not self.user or not self.user.pk:
            raise ProjectException(801, _('authentication error'),
                                   _('Authentication error'),
                                   status.HTTP_401_UNAUTHORIZED)

        if _role:
            _forbidden = False
            user_roles = get_user_roles(self.user)
            if 'client' in user_roles:
                _forbidden = True
            elif _role.title == 'seller':
                if self.user.is_staff and 'agent' in user_roles or not self.user.is_staff and 'agent' in user_roles:
                    attrs['agent'] = self.user
                elif self.user.is_staff and _agent is None:
                    raise ProjectException(807,
                                           _('validation error'), "{'agent': ['This field is required.']}",
                                           status.HTTP_400_BAD_REQUEST)
                elif self.user.is_staff:
                    agent_roles = get_user_roles(_agent)
                    if 'agent' in agent_roles:
                        attrs['agent'] = _agent
                    else:
                        raise ProjectException(855,
                                               _('validation error'), "{'agent': ['This field must be a user with an agent role.']}",
                                               status.HTTP_400_BAD_REQUEST)
                else:
                    _forbidden = True
            elif _role.title == 'agent':
                if not (self.user.is_staff):
                    _forbidden = True
            elif _role.title == 'admin':
                if not self.user.is_superuser:
                    _forbidden = True
            if _forbidden:
                raise ProjectException(821, _('Forbidden'),
                                       _('You do not have permission to perform this action.'),
                                       status.HTTP_403_FORBIDDEN)
            attrs['role'] = _role
        # Check unique Field:
        if _email:
            try:
                UserModel.objects.get(email=_email)
                raise ProjectException(
                    809, 'validation error', 'There is a user with this email in this system.', status_code=status.HTTP_400_BAD_REQUEST)
            except UserModel.DoesNotExist:
                pass
        if _cellphone:
            if not validate_phone_number(_cellphone, "IR"):
                raise ProjectException(807,
                                       _("validation error"), _(
                                           "'Cellphone': this field is invalid"),
                                       status.HTTP_400_BAD_REQUEST)
            try:
                UserModel.objects.get(cellphone=_cellphone)
                raise ProjectException(808,
                                       'validation error', 'There is a user with this cellphone in this system.',
                                       status_code=status.HTTP_400_BAD_REQUEST)
            except UserModel.DoesNotExist:
                pass
        # --------Address Fields:---------------
        address_fields = ["address", "latitude",
                          "longitude", "plaque", "level", "unit"]
        address = {}
        for attr in address_fields:
            value = attrs.pop(attr, None)
            if value:
                address.update({attr: value})
        attrs['address'] = address
        return attrs

    def create(self, validated_data):
        _address = validated_data.pop('address')
        _role = validated_data.pop('role', None)
        _agent = validated_data.pop('agent', None)
        #_password = str(get_verfication_code(8))
        _password = validated_data.get('password', '')
        if not _password:
            _password = str(get_verfication_code(8))

        # Create Username:
        first = validated_data.get('first_name', '')
        last = validated_data.get('last_name', '')
        _name = "".join([first, last])
        validated_data['username'] = generate_username(_name)
        if self.user and self.user.pk:
            validated_data['owner'] = self.user
            validated_data['created_by'] = self.user
            validated_data['modified_by'] = self.user
        new_instance = self.Meta.model(**validated_data)
        if _password:
            new_instance.set_password(_password)
            new_instance.verification_code = _password
        new_instance.status = 1
        new_instance.is_active = True
        if _role and (_role.title == 'admin'):
            new_instance.is_staff = True
        new_instance.role = _role
        new_instance.agent = _agent
        new_instance.address_fields = _address
        new_instance.save()
        return new_instance

class UserAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserModel.objects.all(),
        error_messages={'not_exist': _(
            'کاربر موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class UserDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserModel.objects.all(),
        error_messages={'not_exist': _('کاربر موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class UserInformationSerializer(UserSerializer):
    password=None
    name = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    user_permissions = serializers.SerializerMethodField(read_only=True) 
    role = serializers.SerializerMethodField(read_only=True)
    agent = serializers.SerializerMethodField(read_only=True)
    profile = ProfileInfoSerializer()
    address = serializers.SerializerMethodField(read_only=True)

    def get_name(self,obj):
        name=''
        if obj and hasattr(obj, 'first_name') and obj.first_name:
            name=obj.first_name

        if obj and hasattr(obj,'last_name') and obj.last_name and name:
            name='{0} {1}'.format(name,obj.last_name)
        elif obj and hasattr(obj,'last_name') and obj.last_name:
            name=obj.last_name
        return name


    def get_user_permissions(self,obj):
        if obj and hasattr(obj, 'user_permissions') and obj.user_permissions:
            return UserPermissionInfoSerializer(obj.user_permissions,many=True).data
        return {}

    def get_avatar(self, obj):
        avatar = None
        if obj.avatar:
            avatar = obj.avatar.url
        return avatar


    def get_role(self, obj):
        user_role = get_user_roles(obj)
        if user_role:
            return user_role[0]
        return 'superuser'

    def get_agent(self, obj):
        try:
            chart = UserSubordinateModel.objects.get(user=obj)
            return chart.parent.pk
        except:
            pass
        return None

    def get_address(self, obj):
        address = obj.address
        if address:
            _serializer = AddressInformationSerializer(address, many=True)
            return _serializer.data
        return []

    def get_roles_for_test(self, obj):
        if obj.is_superuser:
            roles = {
                "title": "superuser",
                "states": {"all": ["manage"]}
            }
            return [roles]
        else:
            list_role = UserRoleModel.objects.filter(user=obj)
            roles = [obj.role for obj in list_role]
            serializer = RoleInfoGetSerializer(roles, many=True)
            return serializer.data

    def get_status(self, obj):
        return get_status(obj)

class UserUpdateSerializer(UserSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)
    latitude = None
    longitude = None
    address = None
    plaque = None
    level = None
    unit = None

    def validate(self, attrs):
        attrs.pop('created_by',None)
        attrs['modified_by'] = get_user(self.request)


        return attrs

    def update(self, instance, validated_data):
        password=validated_data.pop('password',None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
            instance.verification_code = password

        instance.save()
        return instance

# Avatar
class UserUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ("id", "avatar",)
        # read_only_fields = ()

    avatar = Base64ImageField(required=True, max_length=None, use_url=True, validators=[
                              validate_image_file_extension])

    def validate(self, attrs):
        self.user = self.context["request"].user
        _owner = self.instance
        if (_owner != self.user) and (not has_access(user=_owner, instance=self.user)):
            raise ProjectException(821, _('Forbidden'),
                                   _('You do not have permission to perform this action.'),
                                   status.HTTP_403_FORBIDDEN)
        return attrs

    def update(self, instance, validated_data):
        if self.user and self.user.pk:
            validated_data["modified_by"] = self.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# User Resend Password:
# ----------User Change Password:----------

class UserChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=128)
    new_password = serializers.CharField(max_length=128)

    def validate(self, attrs):
        self.instance = self.context['request'].user
        if not (current_password := attrs.get('current_password', None)):
            raise ProjectException(806, _('خطای راستی آزمایی'),_('کلمه عبور اشتباه است'),status.HTTP_400_BAD_REQUEST)

        if not self.instance.check_password(current_password):
            raise ProjectException(806, _('خطای راستی آزمایی'),_('کلمه عبور اشتباه است'),status.HTTP_400_BAD_REQUEST)
        if new_password := attrs.get('new_password', None):
            if len(new_password) < 8:
                raise ProjectException(812, _('validation error'),
                                       _("password cannot less than 8 digit"),
                                       status.HTTP_400_BAD_REQUEST)
            if current_password == new_password:
                raise ProjectException(805, _('validation error'),
                                       _("The new password cannot be the same as the current one."),
                                       status.HTTP_400_BAD_REQUEST)
        return attrs

    def update(self, instance, validated_data):
        new_password=validated_data.get('new_password')
        instance.set_password(new_password)
        instance.verification_code = new_password
        instance.save()
        return instance
        
class UserResendPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('id', 'cellphone')
    cellphone = serializers.CharField(max_length=15, required=True)

    def validate(self, attrs):
        self.user = self.context['request'].user
        cellphone = attrs.get('cellphone', None)

        # --------Check Unique Fields:-----------
        if _cellphone:
            if not validate_phone_number(_cellphone, "IR"):
                raise ProjectException(807,
                                       _("validation error"), _(
                                           "'Cellphone': this field is invalid"),
                                       status.HTTP_400_BAD_REQUEST)
            try:
                self.instance = UserModel.objects.get(cellphone=_cellphone)
            except UserModel.DoesNotExist:
                pass

        return attrs

    def update(self, instance, validated_data):
        password = str(get_verfication_code())
        if password is not None:
            new_instance = self.Meta.model()
            validated_data['verification_code'] = password
            new_instance.set_password(password)
            validated_data['password'] = new_instance.password
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class UserResetPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('cellphone', 'verification_code')
    cellphone = serializers.CharField(max_length=15, required=True)
    verification_code = serializers.CharField(read_only=True)

    def validate(self, attrs):
        self.user = self.context['request'].user
        cellphone = attrs.get('cellphone', None)

        # --------Check Unique Fields:-----------
        if cellphone:
            if not validate_phone_number(cellphone, "IR"):
                raise ProjectException(807,
                                       _("validation error"), _(
                                           "'Cellphone': this field is invalid"),
                                       status.HTTP_400_BAD_REQUEST)
            try:
                self.instance = UserModel.objects.get(cellphone=cellphone)
            except UserModel.DoesNotExist:
                pass

        return attrs

    def update(self, instance, validated_data):
        password = str(get_verfication_code(6))
        if password is not None:
            validated_data['verification_code'] = password
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.reset_password=True
        instance.save()
        return instance

class UserResetSerializer(serializers.Serializer):
    reset_token = serializers.CharField(max_length=15)
    new_password = serializers.CharField(max_length=128)

    def validate(self, attrs):
        reset_token=attrs.get('reset_token',None)
        try:
            self.instance = UserModel.objects.get(verification_code=reset_token)
        except UserModel.DoesNotExist:
            raise ProjectException(808,_("خطای راستی آزمایی"), _("توکن پیدا نشد"),status.HTTP_403_FORBIDDEN)
        return attrs
    def update(self, instance, validated_data):
        password = validated_data['new_password']
        if password is not None:
            validated_data['verification_code'] = password
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

# ----------User Role:----------
class UserRoleInSerializer(serializers.Serializer):
    role = serializers.PrimaryKeyRelatedField(
        many=False, queryset=RoleModel.objects.all(),
        error_messages={
            "does_not_exist": _("role does not exist"),
            "invalid": _("invalid value"),
        },
    )

class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoleModel
        fields = ("id", "user", "role",)

    user = serializers.PrimaryKeyRelatedField(
        many=False, queryset=UserModel.objects.all(),
        error_messages={
            "does_not_exist": _("user does not exist"),
            "invalid": _("invalid value"),
        },
    )
    role = serializers.PrimaryKeyRelatedField(
        many=False, queryset=RoleModel.objects.all(),
        error_messages={
            "does_not_exist": _("role does not exist"),
            "invalid": _("invalid value"),
        },
    )

    def validate(self, attrs):

        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def create(self, validated_data):
        _new_instance = self.Meta.model(**validated_data)
        _new_instance.save()
        return _new_instance


# ----------User Evidence:----------
class UserEvidenceSerializer(serializers.Serializer):
    class Meta:
        model = UserEvidenceModel
      
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=130)
    description = serializers.CharField(max_length=None, allow_blank=True, required=False)
    media = serializers.ChoiceField(choices=UserEvidenceModel.MEDIA_CHOICE)

    def validate(self, attrs):
        set_create_user(attrs,self.request)
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class UserEvidenceAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserEvidenceModel.objects.all(),
        error_messages={'not_exist': _(
            'مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class UserEvidenceDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserEvidenceModel.objects.all(),
        error_messages={'not_exist': _('مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class UserEvidenceInformationSerializer(UserEvidenceSerializer):
    pass
    
class UserEvidenceUpdateSerializer(UserSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    title = serializers.CharField(required=False, max_length=130)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)

# ----------User File:----------
class UserFileSerializer(serializers.Serializer):
    class Meta:
        model = UserFileModel
       

    id = serializers.IntegerField(read_only=True)
    address = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=AddressModel.objects.all(),
                                                 error_messages={
        "does_not_exist": _("Address does not exist"),
        "invalid": _("invalid value"),
    },
    )
    evidence = serializers.PrimaryKeyRelatedField(required=True, many=False, queryset=UserEvidenceModel.objects.all(),
                                                  error_messages={
        "does_not_exist": _("evidence does not exist"),
        "invalid": _("invalid value"),
    },
    )
    file = Base64ImageField(required=True, max_length=None, use_url=True)

    def validate(self, attrs):
        self.user = get_user(self.request)
        _evidence = attrs.get('evidence', None)
        if _address := attrs.get('address', None):
            _owner = _address.owner
            if (_owner != self.user) and (not has_access(user=self.user, instance=_owner)):
                raise ProjectException(821, _('Forbidden'),
                                       _('You do not have permission to perform this action.'),
                                       status.HTTP_403_FORBIDDEN)
            try:
                self.instance = UserFileModel.objects.get(
                    address=_address, evidence=_evidence)
            except:
                pass
        return attrs

    def create(self, validated_data):
        return execute_create(self.Meta.model, validated_data)

class UserFileAccessSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserFileModel.objects.all(),
        error_messages={'not_exist': _(
            'مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},
    ))
    status = serializers.ChoiceField(choices=STATUS_CHOICE)

    def validate(self, attrs):
        return attrs

    def access_execute(self):
        execute_access(self.validated_data)
        return {}

class UserFileDeleteSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=UserFileModel.objects.all(),
        error_messages={'not_exist': _('مدرک موجود نیست'), 'invalid': _('داده نامعتبر است')},))

    def validate(self, attrs):
        return attrs

    def delete(self):

        execute_delete(self.validated_data)
        return {}

class UserFileInformationSerializer(UserFileSerializer):
    address = serializers.SerializerMethodField(read_only=True)
    evidence = serializers.SerializerMethodField(read_only=True)
    file = serializers.SerializerMethodField(read_only=True)

    def get_address(self, obj):
        if obj and hasattr(obj,'address' ) and obj.address:
            return AddressInformationSerializer(obj.address).data
        return {}

    def get_evidence(self, obj):
        if obj and hasattr(obj,'evidence' ) and obj.evidence:

            return EvidenceInformationSerializer(obj.evidence).data
        return {}
        

    def get_file(self, obj):
        if obj and hasattr(obj,'file' ) and obj.file:
            return obj.file.url
        return ''

class UserFileInformation_AddressInformation(UserFileInformationSerializer):
    address=None

class UserFileUpdateSerializer(UserFileSerializer):
    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)

    def validate(self, attrs):
        super().validate(attrs)
        set_update_user(attrs,self.request)
        return attrs

    def update(self, instance, validated_data):
        return execute_update(instance, validated_data)



# Wallet:
class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletModel
        fields = ("id", "owner", "amount", "comment", "kind", "deposit")

    owner = serializers.PrimaryKeyRelatedField(
        required=True,
        many=False,
        queryset=UserModel.objects.all(),
        error_messages={
            "does_not_exist": _("user does not exist"),
            "invalid": _("invalid value"),
        },
    )
    amount = serializers.IntegerField(default=0)
    comment = serializers.CharField(
        max_length=None, allow_blank=True, required=False)
    kind = serializers.ChoiceField(
        choices=WalletModel.KIND_CHOICE, required=True)
    deposit = serializers.PrimaryKeyRelatedField(
        required=False,
        many=False,
        queryset=DepositModel.objects.all(),
        error_messages={
            "does_not_exist": _("deposit does not exist"),
            "invalid": _("invalid value"),
        },
    )

    def validate(self, attrs):

        return super(WalletSerializer, self).validate(attrs)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def create(self, validated_data):

        _new_instance = self.Meta.model(**validated_data)
        _new_instance.save()

        return _new_instance

class WalletInformationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    shop_id = serializers.IntegerField(read_only=True)
    owner_id = serializers.IntegerField(read_only=True)
    owner_first_name = serializers.SerializerMethodField(
        read_only=True, method_name="get_first_name")
    owner_last_name = serializers.SerializerMethodField(
        read_only=True, method_name="get_last_name")

    owner_name = serializers.CharField(read_only=True)
    amount = serializers.IntegerField(read_only=True)
    comment = serializers.CharField(read_only=True)
    kind = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    deposit_id = serializers.IntegerField(read_only=True)
    deposit_kind = serializers.CharField(read_only=True)
    receipt_number = serializers.SerializerMethodField(
        read_only=True, method_name="get_receipt_number")
    date = serializers.SerializerMethodField(
        read_only=True, method_name="get_date")

    def get_first_name(self, obj):
        return obj.owner.first_name

    def get_last_name(self, obj):
        return obj.owner.last_name

    def get_receipt_number(self, obj):
        receipt_number = None
        if obj.deposit:
            receipt_number = obj.deposit.receipt_number
        return receipt_number

    def get_date(self, obj):
        return convert_gregorian_to_jalali_string_datetime(obj.date)

class WalletChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletModel
        fields = ("id", "owner", "amount", "comment",)

    owner = serializers.PrimaryKeyRelatedField(
        required=True,
        many=False,
        queryset=UserModel.objects.all(),
        error_messages={
            "does_not_exist": _("user does not exist"),
            "invalid": _("invalid value"),
        },
    )
    amount = serializers.IntegerField(default=0)
    comment = serializers.CharField(
        max_length=None, allow_blank=True, required=False)

    def validate(self, attrs):
        return super(WalletSerializer, self).validate(attrs)

    def create(self, validated_data):

        _new_instance = self.Meta.model(**validated_data)
        _new_instance.kind = 'deposit'
        _new_instance.kind = 'charge'
        _new_instance.save()

        return _new_instance
