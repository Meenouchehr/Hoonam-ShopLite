from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
#from django.template.defaultfilters import slugify
from app.helpers import slugify
import shortuuid
from datetime import datetime, timedelta, timezone
from django.conf import settings



class AddressModel(models.Model):
    owner = models.ForeignKey(
        "UserModel", related_name="address", on_delete=models.CASCADE)
    title = models.CharField(max_length=130, blank=True)
    first_name = models.CharField(max_length=130, blank=True)
    last_name = models.CharField(max_length=130, blank=True)
    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)
    tel = models.CharField(max_length=15, blank=True)
    province = models.CharField(max_length=80)
    city = models.CharField(max_length=80)
    district = models.IntegerField(default=0)
    address = models.TextField()
    plaque = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    unit = models.IntegerField(default=0)
    postal_code = models.CharField(max_length=10, blank=True)
    comment = models.TextField(blank=True)
    is_default = models.BooleanField(default=True)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    class Meta:
        db_table = "tbl_address"
        managed = True


class AttributeModel(models.Model):
    owner = models.ForeignKey(
        'UserModel', on_delete=models.CASCADE, related_name='attributesInfo')
    feature = models.ForeignKey(
        'FeatureModel', on_delete=models.CASCADE, related_name='attributes')
    value = models.CharField(max_length=150,)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='attribute_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='attribute_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_attribute'
        managed = True
        # unique_together =['owner','feature']


def bankFile(instance, filename):
    return "".join(
        [
            "icon/bank/",
            str(instance.title),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.image.name.split('.')[-1])
        ]
    )


class BankModel(models.Model):
    title = models.CharField(max_length=130, primary_key=True)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)
    icon = models.FileField(upload_to=bankFile, blank=True)
    porsant = models.SmallIntegerField(default=0)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='bank_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='bank_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_bank'
        managed = True

    def delete(self, using=None, keep_parents=False):
        if self.icon:
            self.icon.storage.delete(self.icon.name)
        return super().delete(using=using, keep_parents=keep_parents)


def bannerFile(instance, filename):
    return "".join(
        [
            "banner_web",
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.web_image.name.split('.')[-1])
        ]
    )


def banner2File(instance, filename):
    return "".join(
        [
            "banner_mobile",
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.mobile_image.name.split('.')[-1])
        ]
    )


class BannerModel(models.Model):
    title = models.CharField(max_length=130)
    web_image = models.FileField(upload_to=bannerFile, blank=True)
    mobile_image = models.FileField(upload_to=banner2File, blank=True)
    position = models.CharField(max_length=130)
    link = models.TextField(blank=True)

    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='banner_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='banner_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_banner'
        managed = True

    def delete(self, using=None, keep_parents=False):
        if self.web_image:
            self.web_image.storage.delete(self.web_image.name)

        if self.mobile_image:
            self.mobile_image.storage.delete(self.mobile_image.name)
        return super().delete(using=using, keep_parents=keep_parents)


def productFileBlog(instance, filename):
    return "".join(
        [
            "icon/blog/",
            str(instance.title),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.image.name.split('.')[-1])
        ]
    )


class BlogModel(models.Model):

    owner = models.ForeignKey(
        "UserModel", related_name="blogs", on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=130)
    alias = models.SlugField(editable=True)
    image = models.FileField(upload_to=productFileBlog, blank=True)
    set = models.ForeignKey(
        'SetModel', on_delete=models.CASCADE, related_name='set')
    tags = models.ManyToManyField(
        'TagModel', through="BlogTagModel", related_name='blogs')
    description = models.TextField(blank=True)
    body = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True, editable=False)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)
    # status_old  = models.SmallIntegerField(choices=STATUS_CHOICE,default=1)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='blog_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='blog_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_blog'
        managed = True

    def save(self, *args, **kwargs):
        if not self.id:
            # Newly created object, so set slug
            self.alias = slugify(self.title)
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.image:
            self.image.storage.delete(self.image.name)
        return super().delete(using=using, keep_parents=keep_parents)


class BlogTagModel(models.Model):

    blog = models.ForeignKey(
        'BlogModel', on_delete=models.CASCADE, related_name='blog_tags')
    tag = models.ForeignKey(
        'TagModel', on_delete=models.CASCADE, related_name='tag_blogs')

    class Meta:
        db_table = 'tbl_blog_tag'
        managed = True


def productFileCategory(instance, filename):
    return "".join(
        [
            "icon/category/",
            str(instance.title),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.icon.name.split('.')[-1])
        ]
    )


class CategoryModel(models.Model):
    title = models.CharField(max_length=130)
    slug = models.SlugField(max_length=255, editable=True)
    parent = models.ForeignKey("CategoryModel", on_delete=models.CASCADE, related_name='sub_categories', null=True)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    icon = models.FileField(upload_to=productFileCategory, blank=True)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL, related_name='category_creator', editable=False, null=True)
    modified_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL, related_name='category_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_category'
        managed = True

    def save(self, *args, **kwargs):
        if not self.id:
            # Newly created object, so set slug
            # if not self.slug:
            self.slug = slugify(self.title)
        super(CategoryModel, self).save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.icon:
            self.icon.storage.delete(self.icon.name)
        return super().delete(using=using, keep_parents=keep_parents)


class ChartModel(models.Model):
    post = models.TextField()
    parent = models.ForeignKey(
        "ChartModel", on_delete=models.CASCADE, related_name="subordinates", null=True
    )
    order = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name="chart_creator", editable=False, null=True,
                                   )
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name="chart_modifier", null=True
    )
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_chart"
        managed = True


class ChartAccessModel(models.Model):
    chart = models.ForeignKey(
        "ChartModel", on_delete=models.CASCADE, related_name="chart_access"
    )
    state = models.ForeignKey("StateModel", on_delete=models.CASCADE)

    class Meta:
        db_table = "tbl_chart_access"
        managed = True
        unique_together = ["chart", "state"]


class ChartPermissionModel(models.Model):
    access = models.ForeignKey(
        "ChartAccessModel", on_delete=models.CASCADE, related_name="chart_permission"
    )
    operate = models.ForeignKey("operateModel", on_delete=models.CASCADE)

    class Meta:
        db_table = "tbl_chart_permission"
        managed = True
        unique_together = ["access", "operate"]


class CommissionModel(models.Model):
    TYPE_CHOICE = (('cash', 'cash'), ('cent', 'cent'))

    owner = models.ForeignKey(
        'UserModel', on_delete=models.CASCADE, related_name='commission_services')
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, related_name='commission_users')
    type = models.CharField(max_length=8, choices=TYPE_CHOICE)
    amount = models.IntegerField(default=0)
    porsant = models.ForeignKey(
        'PorsantModel', on_delete=models.CASCADE, related_name='commission_posant', null=True)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='commission_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='commission_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_commission'
        managed = True


def companyDocument(instance, filename):
    return "".join(
        [
            "logo/",
            str(instance.id),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.logo.name.split('.')[-1])
        ]
    )


class CompanyModel(models.Model):
    title = models.CharField(max_length=130)
    logo = models.FileField(upload_to=companyDocument, blank=True)
    slug = models.SlugField(max_length=255, editable=True, default='')
    description = models.TextField(blank=True)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='company_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='company_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_company'
        managed = True

    def save(self, *args, **kwargs):
        if not self.id:
            # Newly created object, so set slug
            # if not self.slug:
            self.slug = slugify(self.title)
        super(CompanyModel, self).save(*args, **kwargs)


class DepositModel(models.Model):
    #BANK_CHOICE     = (('mellat','mellat'),('saman','saman'),('zarinpal','zarinpal'))
    PLATFORM_CHOICE = (('android', 'android'), ('ios', 'ios'),
                       ('web', 'web'), ('portal', 'portal'))
    KIND_CHOICE = (('order', 'order'), ('increase_credit', 'decrease credit'))

    payer = models.ForeignKey(
        'UserModel', on_delete=models.CASCADE, related_name='deposits')
    shop = models.OneToOneField(
        "ShopModel", on_delete=models.CASCADE, related_name="deposit_shop", null=True)
    amount = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True, editable=False)
    platform = models.CharField(
        choices=PLATFORM_CHOICE, max_length=10, default='web')
    bank = models.ForeignKey(
        'BankModel', on_delete=models.CASCADE, related_name='deposit_bank', null=True)
    kind = models.CharField(choices=KIND_CHOICE,
                            max_length=15, default='increase_credit')
    refrence = models.TextField(blank=True)
    receipt_number = models.TextField(blank=True)
    is_deposited = models.BooleanField(default=False)
    deposit_date = models.DateTimeField(blank=True, null=True)
    callbak_url = models.TextField(blank=True)

    class Meta:
        db_table = 'tbl_deposit'
        managed = True


def productFileDocument(instance, filename):
    return "".join(
        [
            "icon/document/",
            str(instance.id),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.file.name.split('.')[-1])
        ]
    )


class DocumentModel(models.Model):
    owner = models.ForeignKey(
        'UserModel', on_delete=models.CASCADE, related_name='documentsInfo')
    record = models.ForeignKey(
        'RecordModel', on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to=productFileDocument, blank=True)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='document_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='document_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_document'
        managed = True
        # unique_together =['owner','record']

    def delete(self, using=None, keep_parents=False):
        if self.file:
            self.file.storage.delete(self.file.name)
        return super().delete(using=using, keep_parents=keep_parents)


class EvidenceModel(models.Model):
    MEDIA_CHOICE = (('Image', 'Image'), ('Video', 'Video'), ('Audio', 'Audio'))

    title = models.CharField(max_length=130, unique=True)
    description = models.TextField(blank=True)
    media = models.CharField(max_length=8, choices=MEDIA_CHOICE)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='evidence_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='evidence_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_evidence'
        managed = True
        # unique_together =['title','media']


class FaqCategoryModel(models.Model):
    title = models.CharField(max_length=130)
    slug = models.SlugField(max_length=255, blank=True)
    icon = models.CharField(max_length=150, blank=True)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'tbl_faq_category'
        managed = True


class FaqModel(models.Model):
    category = models.ForeignKey("FaqCategoryModel", on_delete=models.CASCADE, related_name='faq_category', null=True)
    question = models.TextField()
    answer = models.TextField()
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'tbl_faq'
        managed = True


class FeatureModel(models.Model):
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, related_name='features')
    property = models.ForeignKey(
        'PropertyModel', on_delete=models.CASCADE, related_name='featuresInfo')

    class Meta:
        db_table = 'tbl_feature'
        managed = True
        unique_together = ['service', 'property']


class GroupModel(models.Model):

    KIND_CHOICE = (('radiobox', 'radiobox'), ('checkbox', 'checkbox'),
                   ('static', 'static'), ('boolean', 'boolean'))
    DISPLAY_CHOICE = (('none', 'none'), ('radiobox', 'radiobox'),
                      ('checkbox', 'checkbox'), ('static', 'static'), ('boolean', 'boolean'))

    title = models.CharField(max_length=130)
    description = models.TextField(blank=True)
    is_special = models.BooleanField(default=False)
    icon = models.CharField(max_length=130, blank=True)
    order = models.PositiveIntegerField(default=0)
    kind = models.CharField(
        max_length=8, choices=KIND_CHOICE, default='radiobox')
    show = models.CharField(
        max_length=8, choices=DISPLAY_CHOICE, default='radiobox')
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='group_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='group_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_group'
        managed = True


class GroupItemModel(models.Model):
    group = models.ForeignKey(
        'GroupModel', on_delete=models.CASCADE, related_name='items', default=1)
    value = models.CharField(max_length=130, blank=True)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'tbl_group_item'
        managed = True


class GroupMemberModel(models.Model):
    category = models.ForeignKey(
        "CategoryModel", on_delete=models.CASCADE, related_name="groups")
    group = models.ForeignKey(
        "GroupModel", on_delete=models.CASCADE, related_name="categories")

    class Meta:
        db_table = 'tbl_group_member'
        managed = True


class GradeModel(models.Model):
    title = models.CharField(max_length=130)
    shop_no = models.PositiveIntegerField(default=0)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='grade_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='grade_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_grade'
        managed = True


class NotificationModel(models.Model):
    owner = models.ForeignKey("UserModel", on_delete=models.CASCADE)
    title = models.TextField()
    body = models.TextField(blank=True, null=True)
    # blank=True,null=True default=settings.NOTIFICATION_ICON,
    icon = models.TextField(default=settings.NOTIFICATION_ICON)
    data = models.JSONField(default=dict)
    sound = models.TextField(blank=True, null=True)
    badge = models.TextField(blank=True, null=True)

    date = models.DateTimeField(auto_now_add=True, editable=False)
    seen = models.BooleanField(default=False)
    sent = models.BooleanField(default=False)
    received = models.BooleanField(default=False)

    send_date = models.DateTimeField(null=True)

    class Meta:
        db_table = "tbl_notification"
        managed = True


class OperateModel(models.Model):
    title = models.CharField(max_length=130, primary_key=True)

    created_by = models.ForeignKey('UserModel',
                                   on_delete=models.SET_NULL,
                                   related_name='operate_creator',
                                   null=True,
                                   editable=False)
    modified_by = models.ForeignKey('UserModel',
                                    on_delete=models.SET_NULL,
                                    related_name='operate_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_operate'
        managed = True


class PorsantModel(models.Model):
    TYPE_CHOICE = (('cash', 'cash'), ('cent', 'cent'))

    title = models.CharField(max_length=130)
    owner = models.ForeignKey('UserModel', on_delete=models.CASCADE, null=True)
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, null=True)
    category = models.ForeignKey(
        'CategoryModel', on_delete=models.CASCADE, null=True)
    company = models.ForeignKey(
        'CompanyModel', on_delete=models.CASCADE, null=True)
    grade = models.ForeignKey(
        'GradeModel', on_delete=models.CASCADE, null=True)
    type = models.CharField(choices=TYPE_CHOICE, max_length=4, default='cent')
    amount = models.IntegerField()
    role = models.ForeignKey('RoleModel', on_delete=models.CASCADE, null=True)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='porsant_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='porsant_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_porsant'
        managed = True


class PriceModel(models.Model):
    STATE_CHOICE = (('pendding', 'pendding'), ('compelete', 'compelete'))
    OPERATE_CHOICE = (('grather', 'grather'), ('less', 'less'))

    title = models.CharField(max_length=130)
    owner = models.ForeignKey('UserModel', on_delete=models.CASCADE, null=True)
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, null=True)
    category = models.ForeignKey(
        'CategoryModel', on_delete=models.CASCADE, null=True)
    company = models.ForeignKey(
        'CompanyModel', on_delete=models.CASCADE, null=True)
    amount = models.IntegerField()
    role = models.ForeignKey('RoleModel', on_delete=models.CASCADE, null=True)
    state = models.CharField(choices=STATE_CHOICE,
                             max_length=10, default='pendding')
    operate = models.CharField(choices=OPERATE_CHOICE, max_length=7)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='price_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='price_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_price'
        managed = True


class PriceHistoryModel(models.Model):
    service = models.ForeignKey(
        "ServiceModel", on_delete=models.CASCADE, related_name='price_history')
    price = models.PositiveIntegerField(default=0)
    vat = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField(default=0)
    date = models.DateTimeField(auto_now_add=True, editable=False)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='price_history_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='price_history_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_price_history'
        managed = True


class ProfileModel(models.Model):
    owner = models.OneToOneField(
        "UserModel", related_name="profile", on_delete=models.CASCADE, primary_key=True)
    father_name = models.CharField(max_length=80, blank=True)
    id_no = models.PositiveIntegerField(default=0)
    birthday = models.DateField(auto_now=False, auto_now_add=False, null=True)
    birthplace = models.CharField(max_length=70, blank=True)
    married = models.BooleanField(default=False)
    children = models.PositiveIntegerField(default=0)
    national_code = models.CharField(max_length=10, blank=True)
    tel = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        db_table = "tbl_profile"
        managed = True


class PropertyModel(models.Model):
    TYPE_CHOICE = (('int', 'int'), ('str', 'str'), ('bool', 'bool'))

    title = models.CharField(max_length=130, unique=True)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=8, choices=TYPE_CHOICE)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='property_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='property_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_property'
        managed = True
        # unique_together =['title','type']


class RecordModel(models.Model):
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, related_name='records')
    evidence = models.ForeignKey(
        'EvidenceModel', on_delete=models.CASCADE, related_name='recordsInfo')

    class Meta:
        db_table = 'tbl_record'
        managed = True
        unique_together = ['service', 'evidence']


class RoleModel(models.Model):
    title = models.CharField(max_length=130, primary_key=True)
    parent = models.ForeignKey('RoleModel', on_delete=models.SET_NULL,
                               related_name='subordinates', editable=False, null=True)
    order = models.SmallIntegerField(default=0)
    priority = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey('UserModel',
                                   on_delete=models.SET_NULL,
                                   related_name='role_creator',
                                   editable=False,
                                   null=True)
    modified_by = models.ForeignKey('UserModel',
                                    on_delete=models.SET_NULL,
                                    related_name='role_modifier',
                                    null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_role'
        managed = True


class RoleAccessModel(models.Model):
    role = models.ForeignKey(
        "RoleModel", on_delete=models.CASCADE, related_name="role_accesses"
    )
    state = models.ForeignKey(
        "StateModel", on_delete=models.CASCADE, related_name="role_state")

    class Meta:
        db_table = "tbl_role_access"
        managed = True
        unique_together = ["role", "state"]


class RolePermissionModel(models.Model):
    access = models.ForeignKey(
        "RoleAccessModel", on_delete=models.CASCADE, related_name="role_permissions"
    )
    operate = models.ForeignKey("operateModel", on_delete=models.CASCADE)

    class Meta:
        db_table = "tbl_role_permission"
        managed = True
        unique_together = ["access", "operate"]


def productFileService(instance, filename):
    return "".join(
        [
            "icon/service/",
            str(instance.title),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.image.name.split('.')[-1])
        ]
    )


class ServiceModel(models.Model):
    TYPE_CHOICE = (('virtual', 'virtual'), ('physical', 'physical'))
    title = models.CharField(max_length=130, unique=True)
    sku = models.CharField(max_length=130, unique=True, null=True)
    slug = models.SlugField(max_length=255, editable=True)
    image = models.FileField(upload_to=productFileService, blank=True)
    category = models.ForeignKey(
        'CategoryModel', on_delete=models.CASCADE, related_name='services')
    company = models.ForeignKey(
        'CompanyModel', on_delete=models.CASCADE, related_name='comany_services', null=True)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(default=0)
    vat = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField(default=0)
    qty = models.IntegerField(default=0)
    rebate = models.PositiveIntegerField(default=0)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)
    is_saleable = models.BooleanField(default=True)
    type = models.CharField(max_length=8, choices=TYPE_CHOICE, default='virtual')

    is_installation = models.BooleanField(default=False)
    is_revival = models.BooleanField(default=False)
    revival_days = models.IntegerField(default=0)
    is_special= models.BooleanField(default=False)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='service_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='service_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_service'
        managed = True

    def save(self, *args, **kwargs):
        if not self.id:
            # Newly created object, so set slug
            self.slug = slugify(self.title)
        super(ServiceModel, self).save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.image:
            self.image.storage.delete(self.image.name)
        return super().delete(using=using, keep_parents=keep_parents)


class ServiceClassificationModel(models.Model):
    service = models.ForeignKey(
        "ServiceModel", on_delete=models.CASCADE, related_name="properties")
    property = models.ForeignKey(
        "GroupItemModel", on_delete=models.CASCADE, related_name="classifications", null=True)

    class Meta:
        db_table = 'tbl_classification'
        managed = True


class ServiceClassificationStaticModel(models.Model):
    classification = models.OneToOneField(
        "ServiceClassificationModel", on_delete=models.CASCADE, related_name="static", primary_key=True, default=1)
    value = models.TextField(blank=True)

    class Meta:
        db_table = 'tbl_classification_static'
        managed = True


class ServiceDependentModel(models.Model):
    TYPE_CHOICE=((0,'every shop'),(1,'once for this service'),(2,'once for this service category'),(3,'once qty'),(4,'once'))

    primary = models.ForeignKey("ServiceModel", on_delete=models.CASCADE, related_name="dependents")
    dependent = models.ForeignKey("ServiceModel", on_delete=models.CASCADE)
    type=models.IntegerField(choices=TYPE_CHOICE,default=0)
    
    qty=models.PositiveIntegerField(default=1)
    price = models.PositiveIntegerField(default=0)
    vat = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField(default=0)

    expire_date=models.DateField(null=True, blank=True)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)



    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='service_dependent_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='service_dependent_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_service_dependent'
        managed = True


class ServiceGalleryModel(models.Model):
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, related_name='gallery')
    file = models.FileField(upload_to='gallery/', blank=True)
    is_default = models.BooleanField(default=False)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='gallery_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='gallery_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_service_gallery'
        managed = True


class ServiceHistoryModel(models.Model):
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, related_name='history')
    price = models.PositiveIntegerField(default=0)
    vat = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        db_table = 'tbl_service_history'
        managed = True


class SettingModel(models.Model):
    key = models.CharField(max_length=130, primary_key=True)
    value = models.CharField(max_length=130)

    class Meta:
        db_table = 'tbl_setting'
        managed = True


def productFileSet(instance, filename):
    return "".join(
        [
            "icon/set/",
            str(instance.title),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.icon.name.split('.')[-1])
        ]
    )


class SetModel(models.Model):
    title = models.CharField(max_length=130, unique=True)
    slug = models.SlugField(editable=True)
    parent = models.ForeignKey(
        "SetModel", on_delete=models.CASCADE, related_name='sub_sets', null=True)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    icon = models.FileField(upload_to=productFileSet, blank=True)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='set_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='set_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_set'
        managed = True

    def save(self, *args, **kwargs):
        if not self.id:
            # Newly created object, so set slug
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.icon:
            self.icon.storage.delete(self.icon.name)
        return super().delete(using=using, keep_parents=keep_parents)


class ShopModel(models.Model):

    owner = models.ForeignKey(
        'UserModel', on_delete=models.CASCADE, related_name='shops')
    address = models.ForeignKey(
        'AddressModel', on_delete=models.CASCADE, related_name='shopsInfo',null=True,blank=True)
    date = models.DateTimeField(auto_now_add=True, editable=False)
    description = models.TextField(blank=True)
    state = models.ForeignKey(
        'StatusModel', on_delete=models.CASCADE, related_name='shop_status', default='cart')
    pending_expire = models.DateTimeField(null=True)

    created_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='shop_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='shop_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_shop'
        managed = True


class ShopItemModel(models.Model):
    shop = models.ForeignKey('ShopModel', on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey('ServiceModel', on_delete=models.CASCADE, related_name='shopsInfo')
    state = models.ForeignKey('StatusModel', on_delete=models.CASCADE,related_name='shop_item_status', default='bought')
    qty = models.PositiveSmallIntegerField(default=1)
    price = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    is_dependent = models.BooleanField(default=False)
    dependent = models.ForeignKey('ServiceModel', on_delete=models.CASCADE, related_name='shop_dependent',null=True)

    is_installation = models.BooleanField(default=False)
    is_revival = models.BooleanField(default=False)
    revival_days = models.IntegerField(default=0)

    class Meta:
        db_table = 'tbl_shop_item'
        managed = True
        unique_together = ['service', 'shop']


class StateModel(models.Model):
    title = models.CharField(max_length=130, primary_key=True)

    created_by = models.ForeignKey('UserModel',
                                   on_delete=models.SET_NULL,
                                   related_name='state_creator',
                                   null=True,
                                   editable=False)
    modified_by = models.ForeignKey('UserModel',
                                    on_delete=models.SET_NULL,
                                    related_name='state_modifier', null=True,)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_state'
        managed = True


class StatusModel(models.Model):
    title = models.CharField(max_length=130, primary_key=True)
    description = models.TextField(blank=True)
    client_message = models.CharField(max_length=150, blank=True)
    seller_message = models.CharField(max_length=150, blank=True)
    agent_message = models.CharField(max_length=150, blank=True)
    admin_message = models.CharField(max_length=150, blank=True)
    is_system = models.BooleanField(default=False)
    is_client_message = models.BooleanField(default=False)
    is_seller_message = models.BooleanField(default=False)
    is_agent_message = models.BooleanField(default=False)
    is_admin_message = models.BooleanField(default=False)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)
    is_shop_item = models.BooleanField(default=True)

    system_status = models.ForeignKey('StatusModel',
                                      on_delete=models.SET_NULL,
                                      null=True,
                                      editable=False)

    created_by = models.ForeignKey('UserModel',
                                   on_delete=models.SET_NULL,
                                   related_name='status_creator',
                                   null=True,
                                   editable=False)
    modified_by = models.ForeignKey('UserModel',
                                    on_delete=models.SET_NULL,
                                    related_name='status_modifier', null=True,)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_status'
        managed = True


class Support(models.Model):
    owner = models.ForeignKey(
        "UserModel", on_delete=models.CASCADE, related_name='support')
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, related_name='supportInfo')
    shop_item = models.ForeignKey('ShopItemModel', on_delete=models.CASCADE,
                                  related_name='support_shop_item_supportInfo', null=True)
    serries = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    state = models.ForeignKey('StatusModel', on_delete=models.CASCADE,
                              related_name='support_shop_item_status', null=True)
    revival_date = models.DateField(null=True)
    installation_date = models.DateField(null=True)

    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='support_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='support_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_support'


class TagModel(models.Model):
    title = models.CharField(max_length=130, unique=True)

    created_by = models.ForeignKey('UserModel',
                                   on_delete=models.SET_NULL,
                                   related_name='tag_creator',
                                   null=True,
                                   editable=False)
    modified_by = models.ForeignKey('UserModel',
                                    on_delete=models.SET_NULL,
                                    related_name='tag_modifier', null=True,)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_tag'
        managed = True


class TokenModel(models.Model):
    user = models.ForeignKey(
        'UserModel', on_delete=models.CASCADE, related_name='bearer_token',)
    key = models.TextField(unique=True)
    # access_token  = models.TextField(unique=True)
    refresh_token = models.TextField(unique=True)
    remote_addr = models.TextField()
    user_agent = models.TextField()
    player_id = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tbl_token'
        unique_together = ('user', 'player_id',)
        managed = True


class UserRoleModel(models.Model):
    user = models.ForeignKey(
        "UserModel", on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(
        "RoleModel", on_delete=models.CASCADE, related_name="role_user")

    class Meta:
        db_table = "tbl_user_role"
        managed = True
        unique_together = ["user", "role"]


def productFileUser(instance, filename):
    return "".join(
        [
            "user/avatar/",
            str(instance.username),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".jpg",
        ]
    )


class UserModel(AbstractUser):
    groups = None
    user_permissions = None
    GENDER_CHOICE = (('none', 'none'), ('male', 'male'), ('female', 'female'))

    avatar = models.ImageField(upload_to=productFileUser, null=True)
    gender = models.CharField(choices=GENDER_CHOICE,
                              max_length=8, default='male')
    cellphone = models.CharField(max_length=15, blank=True, null=True)
    email = models.CharField(max_length=130, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    status = models.SmallIntegerField(default=1)
    is_delete = models.SmallIntegerField(default=0)
    verification_code = models.CharField(max_length=15, blank=True)

    login_error = models.IntegerField(default=0)
    deactive_expire = models.DateTimeField(null=True)

    owner = models.ForeignKey(
        'UserModel', on_delete=models.SET_NULL, related_name='user_owner', null=True)
    created_by = models.ForeignKey('UserModel',
                                   on_delete=models.SET_NULL,
                                   related_name='user_creator',
                                   null=True,
                                   editable=False)
    modified_by = models.ForeignKey('UserModel',
                                    on_delete=models.SET_NULL,
                                    related_name='user_modifier',
                                    null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_user'
        managed = True

    def save(self, *args, **kwargs):
        if not self.is_staff:
            # self.expire = datetime.now().date() + timedelta(days=365)
            pass
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.avatar:
            self.avatar.storage.delete(self.avatar.name)
        return super().delete(using=using, keep_parents=keep_parents)


class UserSubordinateModel(models.Model):
    user = models.ForeignKey(
        "UserModel", on_delete=models.CASCADE, related_name="parent")
    parent = models.ForeignKey(
        "UserModel", on_delete=models.CASCADE, related_name="subordinates")
    order = models.SmallIntegerField(default=0)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name="userchart_creator", editable=False, null=True,)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name="userchart_modifier", null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_user_subordinate"
        managed = True
        unique_together = ["user", "parent"]


class UserAccessModel(models.Model):
    user = models.ForeignKey(
        "UserModel", on_delete=models.CASCADE, related_name="permissions"
    )  # user_accesses
    state = models.ForeignKey("StateModel", on_delete=models.CASCADE)

    class Meta:
        db_table = "tbl_user_access"
        managed = True
        unique_together = ["user", "state"]


class UserEvidenceModel(models.Model):
    MEDIA_CHOICE = (('Image', 'Image'), ('Video', 'Video'), ('Audio', 'Audio'))

    title = models.CharField(max_length=130, unique=True)
    description = models.TextField(blank=True)
    media = models.CharField(max_length=8, choices=MEDIA_CHOICE)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='userevidence_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='userevidence_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_userevidence'
        managed = True
        # unique_together =['title','media']


def productFileEvidence(instance, filename):
    return "".join(
        [
            "user/evidence/",
            str(instance.id),
            "_",
            str(shortuuid.ShortUUID().random(length=10)),
            ".", str(instance.file.name.split('.')[-1])
        ]
    )


class UserFileModel(models.Model):
    address = models.ForeignKey(
        'AddressModel', on_delete=models.CASCADE, related_name='evidences', null=True)
    evidence = models.ForeignKey(
        'UserEvidenceModel', on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=productFileEvidence, blank=True)
    # description = models.TextField(blank=True)

    created_by = models.ForeignKey("UserModel", on_delete=models.SET_NULL,
                                   related_name='userfile_creator', editable=False, null=True)
    modified_by = models.ForeignKey(
        "UserModel", on_delete=models.SET_NULL, related_name='userfile_modifier', null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_userfile'
        managed = True
        #unique_together =['owner','evidence']

    def delete(self, using=None, keep_parents=False):
        if self.file:
            self.file.storage.delete(self.file.name)
        return super().delete(using=using, keep_parents=keep_parents)


class UserPermissionModel(models.Model):
    access = models.ForeignKey(
        "UserAccessModel", on_delete=models.CASCADE, related_name="user_permissions"
    )
    operate = models.ForeignKey("operateModel", on_delete=models.CASCADE)

    class Meta:
        db_table = "tbl_user_permission"
        managed = True
        unique_together = ["access", "operate"]


class UserChartModel(models.Model):
    user = models.ForeignKey(
        "UserModel", on_delete=models.CASCADE, related_name="positions")
    chart = models.ForeignKey("ChartModel", on_delete=models.CASCADE)

    class Meta:
        db_table = "tbl_user_position"
        managed = True
        unique_together = ["user", "chart"]


class WalletModel(models.Model):
    KIND_CHOICE = (('none', 'none'), ('deposit', 'deposit'),
                   ('withdraw', 'withdraw'))
    TYPE_CHOICE = (('charge', 'charge'), ('credit', 'credit'), ('reward', 'reward'),
                   ('porsant', 'porsant'), ('order', 'order'), ('checkout', 'checkout'))

    owner = models.ForeignKey(
        'UserModel', on_delete=models.CASCADE, related_name='accounts')
    amount = models.IntegerField(default=0)
    comment = models.TextField(blank=True)
    kind = models.CharField(choices=KIND_CHOICE, max_length=15)
    type = models.CharField(choices=TYPE_CHOICE, max_length=15)
    deposit = models.OneToOneField(
        'DepositModel', on_delete=models.CASCADE, related_name='account_deposit', null=True)
    shop = models.ForeignKey(
        'ShopModel', on_delete=models.CASCADE, related_name='wallet_shop', null=True)
    service = models.ForeignKey(
        'ServiceModel', on_delete=models.CASCADE, related_name='wallet_service', null=True)
    date = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        db_table = 'tbl_wallet'
        managed = True
