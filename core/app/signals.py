from django.db.models.signals import pre_delete,post_delete,pre_save,post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _
from django.conf import settings
from app.serializers import *
import datetime
import os

import pytz
import requests
import rsa
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad
import time



# Address:---------------------------------------------------
@receiver(pre_save, sender=AddressModel)
def pre_save_address(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_is_default = instance.__class__.objects.get(id=instance.id).is_default
        if instance.is_default:
            try:
                defaul_add = AddressModel.objects.exclude(pk=instance.pk).get(owner=instance.owner,is_default=True)
                defaul_add.is_default = False
                defaul_add.save()
            except ObjectDoesNotExist:
                pass
            except MultipleObjectsReturned:
                objects=AddressModel.objects.exclude(pk=instance.pk).filter(owner=instance.owner,is_default=True)
                for obj in objects:
                    obj.is_default=False
                AddressModel.objects.bulk_update(objects,['is_default'])


    else:
        try:
            defaul_add = AddressModel.objects.get(owner=instance.owner,is_default=True)
            defaul_add.is_default = False
            defaul_add.no_change = True
            defaul_add.save()
        except ObjectDoesNotExist:
            pass

@receiver(post_save, sender=AddressModel)
def post_save_address(sender, instance=None, created=False, **kwargs):
    old_is_default = None
    if hasattr(instance, "old_is_default") and instance.old_is_default:
        old_is_default = instance.old_is_default
    if old_is_default and (not instance.is_default):
        if hasattr(instance, "no_change") and instance.no_change:
            pass
        else:
            try:
                defaul_add = AddressModel.objects.get(owner=instance.owner,is_default=True)
            except ObjectDoesNotExist:
                defaul_add = AddressModel.objects.filter(owner=instance.owner).exclude(pk=instance.pk)
                if defaul_add:
                    defaul_add = defaul_add.last()
                    defaul_add.is_default = True
                    defaul_add.save()

@receiver(post_delete, sender=AddressModel)
def pre_delete_address(sender, instance=None, **kargs):
    if instance.is_default:
        try:
            user_profile = ProfileModel.objects.get(owner=instance)
            user_profile.delete()
        except:
            try:
                defaul_add = AddressModel.objects.exclude(pk=instance.pk).get(owner=instance.owner,is_default=True)
            except ObjectDoesNotExist:
                defaul_add = AddressModel.objects.filter(owner=instance.owner).exclude(pk=instance.pk)
                if defaul_add:
                    defaul_add = defaul_add.last()
                    defaul_add.is_default = True
                    defaul_add.save()


# Banner:---------------------------------------------------
@receiver(pre_save, sender=BannerModel)
def pre_save_banner(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_web_image = instance.__class__.objects.get(id=instance.id).web_image
        instance.old_mobile_image = instance.__class__.objects.get(id=instance.id).mobile_image

@receiver(post_save, sender=BannerModel)
def post_save_banner(sender, instance=None, created=False, **kwargs):
    # Delete Image of local storage:
    web_image = None
    old_web_image = None

    mobile_image = None
    old_mobile_image = None
    
    if hasattr(instance, "old_web_image") and instance.old_web_image:
        old_web_image = instance.old_web_image
    if hasattr(instance, "web_image") and instance.web_image:
        web_image = instance.web_image
    if old_web_image and (old_web_image != web_image):
        instance.image.storage.delete(old_web_image.name)


    if hasattr(instance, "old_mobile_image") and instance.old_mobile_image:
        old_mobile_image = instance.old_mobile_image
    if hasattr(instance, "mobile_image") and instance.mobile_image:
        mobile_image = instance.mobile_image
    if old_mobile_image and (old_mobile_image != mobile_image):
        instance.image.storage.delete(old_mobile_image.name)






# Blog:---------------------------------------------------
@receiver(pre_save, sender=BlogModel)
def pre_save_blog(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_image = instance.__class__.objects.get(id=instance.id).image

@receiver(post_save, sender=BlogModel)
def post_save_blog(sender, instance=None, created=False, **kwargs):
    # Add Tag:
    if hasattr(instance, "temp_tags") and instance.temp_tags is not None:
        tags=instance.temp_tags.copy()
        instance.tags.exclude(tag_blogs__tag__title__in=tags).delete()
        for tg in tags:
            try:
                tag = TagModel.objects.get(title=tg)
            except ObjectDoesNotExist:
                tag = TagModel.objects.create(title=tg)
            try:
                BlogTagModel.objects.get(blog=instance,tag=tag)
            except ObjectDoesNotExist:
                BlogTagModel.objects.create(blog=instance,tag=tag)     
         
        

    # Delete Image of local storage:
    image =  instance.image if hasattr(instance, "image") and instance.image else None
    old_image = instance.old_image if hasattr(instance, "old_image") and instance.old_image else None
    if old_image and (old_image != image):
        instance.image.storage.delete(old_image.name)



# Category:---------------------------------------------------
@receiver(pre_save, sender=CategoryModel)
def pre_save_category(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_icon = instance.__class__.objects.get(id=instance.id).icon
    else:
        instance.order = parent.order + 1 if (parent := instance.parent) else 0

@receiver(post_save, sender=CategoryModel)
def post_save_category(sender, instance=None, created=False, **kwargs):
    old_icon = instance.old_icon if hasattr(instance, "old_icon") and instance.old_icon else None
    icon = instance.icon if hasattr(instance, "icon") and instance.icon else None
    if old_icon and (old_icon != icon):
        instance.icon.storage.delete(old_icon.name)

    if hasattr(instance, 'temp_groups') and instance.temp_groups:
        GroupMemberModel.objects.filter(category=instance).delete()
        if groups := instance.temp_groups:
            models=[]
            for grp in groups:
                data={'category':instance,'group':grp}
                models.append(GroupMemberModel(** data))

            if models:
                GroupMemberModel.objects.bulk_create(models)



@receiver(post_save, sender=DepositModel)
def post_save_deposit(sender, instance=None, created=False, **kwargs):
    if created:
        request = instance.request
        amount = instance.amount
        bank_portal = instance.bank.title
        cellphone = instance.payer.cellphone
        data_payment = payment(request,amount,bank_portal,cellphone,deposit_id=instance.pk)
        _token = data_payment.get('token',None)
        _url = data_payment.get('url',None)
       
        if _token:
            instance.refrence = _token
            instance.save()
            instance.token=_token
            instance.url=_url
        else: 
            raise ProjectException(811,"runtime error","bank token empty",status.HTTP_400_BAD_REQUEST,)

    if instance.is_deposited:
        
        instance.shop.state_id ='paid'
        instance.shop.save()

        # change Address Default
        if instance.shop.address:
            instance.shop.address.is_default = True
            instance.shop.address.save()

        # insert shop item to support
        shop_items=instance.shop.items.filter(is_dependent=False)
        supports=[]
        for item in shop_items:
            data={'owner':instance.payer,'service':item.service,'shop_item':item}
            supports.append(Support(** data))
        if supports:
            Support.objects.bulk_create(supports)


       
        data=calculate_commission(instance.payer,instance.shop,instance.amount,instance.pk)
        WalletModel.objects.bulk_create(data)

@receiver(post_save, sender=GroupModel)
def post_save_group(sender, instance=None, created=False, **kwargs):
    if hasattr(instance, 'group_items') and created:
        _group_items=instance.group_items
        _items=[]
        for item in _group_items:
            item['group_id']=instance.pk
            _items.append(GroupItemModel(** item))
        if _items:
            GroupItemModel.objects.bulk_create(_items)
    elif hasattr(instance, 'group_items'):
        _group_items=instance.group_items
        _appends=[]
        _updates=[]
        _exists=[]
        for item in _group_items:
            if ('id' not in item) or  ('id' in item and item['id']==0):
                item['group_id']=instance.pk
                _appends.append(GroupItemModel(** item))

            elif 'id' in item and item['id']:
                try:
                    _exists.append(item['id'])
                    _object=GroupItemModel.objects.get(id=item['id'])
                    _object.value=item['value']
                    _object.order=item['order']
                    _object.description=item['description']
                    _updates.append(_object)
                except ObjectDoesNotExist:
                    pass

        GroupItemModel.objects.filter(group_id=instance.pk).exclude(pk__in=_exists).delete()

        if _appends:
            GroupItemModel.objects.bulk_create(_appends)
        if _updates:
            [item.save() for item in _updates]

    if  hasattr(instance, 'temp_categories') and created:
        _categories=instance.temp_categories
        if _categories:
            _models=[]
            for cat in _categories:
                _data={'group_id':instance.pk,'category_id':cat.pk}
                _models.append(GroupMemberModel(** _data))

            if _models:
                GroupMemberModel.objects.bulk_create(_models)



# Porsant:---------------------------------------------------

def prepare(porsant,owner,service,type,amount,user,insert,update):
        _data={'porsant':porsant,'owner':owner,'service':service,'type':type,'amount':amount}
        try:
            _object=CommissionModel.objects.get(owner=owner,service=service)
            _object.amount=amount
            _object.type=type
            _object.porsant=porsant
            _object.modified_by=user
            update.append(_object)
        except ObjectDoesNotExist:
            _object=CommissionModel(** _data)
            _object.modified_by=user
            _object.created_by=user
            insert.append(_object)

@receiver(post_save, sender=PorsantModel)
def post_save_porsant(sender, instance=None, created=False, **kwargs):
    if created:
        _user=instance.created_by
        _type=instance.type
        _amount=instance.amount
        _owner=instance.owner
        _service=instance.service
        _category=instance.category
        _company=instance.company
        _posant=instance
        insert=[]
        update=[]
        if _owner:
            if _service:
                prepare(_posant,_owner,_service,_type,_amount,_user,insert,update)
            elif _category:
               _services= ServiceModel.objects.filter(category=_category)
               for srv in _services:
                   prepare(_posant,_owner,srv,_type,_amount,_user,insert,update)
            elif _company:
               _services= ServiceModel.objects.filter(company=_company)
               for srv in _services:
                   prepare(_posant,_owner,srv,_type,_amount,_user,insert,update)
            else:
                _services= ServiceModel.objects.all()
                for srv in _services:
                    prepare(_posant,_owner,srv,_type,_amount,_user,insert,update)
        else:
            _role=instance.role
            if _user.is_staff:
                _users=UserModel.objects.filter(roles__role=_role)
            else:
                _users=UserModel.objects.filter(owner=_user,roles__role=_role)                
                
            for usr in _users:
                _owner=usr
                if _service:
                    prepare(_posant,_owner,_service,_type,_amount,_user,insert,update)
                elif _category:
                    _services= ServiceModel.objects.filter(category=_category)
                    for srv in _services:
                        prepare(_posant,_owner,srv,_type,_amount,_user,insert,update)
                elif _company:
                    _services= ServiceModel.objects.filter(company=_company)
                    for srv in _services:
                        prepare(_posant,_owner,srv,_type,_amount,_user,insert,update)
                else:
                    _services= ServiceModel.objects.all()
                    for srv in _services:
                        prepare(_posant,_owner,srv,_type,_amount,_user,insert,update)

        if insert:
            CommissionModel.objects.bulk_create(insert)
        if update:
            CommissionModel.objects.bulk_update(update,['porsant_id','amount','type'])


@receiver(pre_delete, sender=PorsantModel)
def pre_delete_porsant(sender, instance=None, **kargs):
    from django.db.models import Q
    
    objects=[obj for obj in CommissionModel.objects.filter(porsant_id=instance.pk)] 
    for obj in objects:
        owner=obj.owner
        service=obj.service
        try:
            porsant=PorsantModel.objects.filter(Q(owner=owner,service=service)
            | Q(owner=owner,category__services=service)
            | Q(owner=owner,company__comany_services=service)
            | Q(role__role_user__user=owner,service=service)
            | Q(role__role_user__user=owner,category__services=service)
            | Q(role__role_user__user=owner,company__comany_services=service)).exclude(pk=instance.pk).distinct().order_by('-id').first()
            
            if porsant:
                obj.porsant=porsant
                obj.amount=porsant.amount
                obj.type=porsant.type
                
            
        except ObjectDoesNotExist:
            roles = [item.role.title for item in UserRoleModel.objects.filter(user_id=obj.owner.id)]
            if 'agent' in roles:
                try:
                    setting=SettingModel.objects.get(key=settings.AGENT_COMMISSION_TAG)
                    obj.porsant=None
                    obj.amount=setting.value
                    obj.type='cent'
                   
                except ObjectDoesNotExist:
                    obj.porsant=None
                    obj.amount=0
                    obj.type='none'
                   

            elif 'seller' in roles:
                try:
                    setting=SettingModel.objects.get(key=settings.SELLER_COMMISSION_TAG)
                    obj.porsant=None
                    obj.amount=setting.value
                    obj.type='cent'
                   
                except ObjectDoesNotExist:
                    obj.porsant=None
                    obj.amount=0
                    obj.type='none'
                    
           
    #CommissionModel.objects.bulk_update(objects,['porsant','amount','type'])
    instance.commissions=objects 

@receiver(post_delete, sender=PorsantModel)
def post_delete_porsant(sender, instance=None, **kwargs):
    if instance.commissions:
        CommissionModel.objects.bulk_update(instance.commissions,['porsant','amount','type'])
        



# Profile:---------------------------------------------------
@receiver(post_save, sender=ProfileModel)
def post_save_profile(sender, instance=None, created=False, **kwargs):
    pass


# Role:---------------------------------------------------
@receiver(pre_save, sender=RoleModel)
def pre_save_role(sender, instance, *args, **kwargs):
    if not instance.pk:
        _parent = instance.parent
        if _parent:
            instance.order = _parent.order + 1

@receiver(post_save, sender=RoleModel)
def post_save_role(sender, instance=None, created=False, **kwargs):
    pass


# Service:---------------------------------------------------
@receiver(pre_save, sender=ServiceModel)
def pre_save_service(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_image = instance.__class__.objects.get(id=instance.id).image
        old_price    = instance.__class__.objects.get(id=instance.id).price
        old_vat      = instance.__class__.objects.get(id=instance.id).vat
        old_discount = instance.__class__.objects.get(id=instance.id).discount
        discounted_price = old_price*(1 - old_discount/100)
        vat_price        = discounted_price*(1 + old_vat/100)
        instance.old_total_price = int(vat_price)


@receiver(post_save, sender=ServiceModel)
def post_save_service(sender, instance=None, created=False, **kwargs):
    # Add Recored:
    if hasattr(instance, "evidence") and instance.evidence:
        _evidences = instance.evidence
        _records = RecordModel.objects.filter(service=instance).exclude(evidence__in=_evidences)
        if _records:
            _records.delete()
        for obj in _evidences:
            try:
                RecordModel.objects.get(service=instance,evidence=obj)
            except ObjectDoesNotExist:
                RecordModel.objects.create(service=instance,evidence=obj)
    else:
        if hasattr(instance, "handle") and instance.handle:
            _records = RecordModel.objects.filter(service=instance)
            if _records:
                _records.delete()

    # Add Feature:
    if hasattr(instance, "property") and instance.property:
        _properties = instance.property
        _features = FeatureModel.objects.filter(service=instance).exclude(property__in=_properties)
        if _features:
            _features.delete()
        for obj in _properties:
            try:
                FeatureModel.objects.get(service=instance,property=obj)
            except ObjectDoesNotExist:
                FeatureModel.objects.create(service=instance,property=obj)
    else:
        if hasattr(instance, "handle") and instance.handle:
            _features = FeatureModel.objects.filter(service=instance)
            if _features:
                _features.delete()
    
    # Delete Image of local storage:
    _image = None
    _old_image = None
    if hasattr(instance, "old_image") and instance.old_image:
        _old_image = instance.old_image
    if hasattr(instance, "image") and instance.image:
        _image = instance.image
    if _old_image and (_old_image != _image):
        instance.image.storage.delete(_old_image.name)
    
    # Add history price:-----------------------------------
    _total_price = None
    _old_total_price = None
    if hasattr(instance, "old_total_price") and instance.old_total_price:
        _old_total_price = instance.old_total_price
    discounted_price = instance.price*(1 - instance.discount/100)
    vat_price        = discounted_price*(1 + instance.vat/100)
    _total_price     = int(vat_price)
    if created or (_old_total_price and (_old_total_price != _total_price)):
        try:
            PriceHistoryModel.objects.create(service=instance,price=instance.price,
                                            vat=instance.vat,discount=instance.discount)
        except:
            pass

    if hasattr(instance,'filters'):
        if instance.filters and not created:
            ServiceClassificationModel.objects.filter(service=instance).delete()
        
        _models=[]
        for fil in instance.filters:
            _data={'service_id':instance.pk,'property_id':fil['id']}
            if 'static' in fil and fil['static']:
                _classification=ServiceClassificationModel.objects.create(** _data)
                _data={'classification':_classification,'value':fil['static']}
                ServiceClassificationStaticModel.objects.create(** _data)
            else:  
                _models.append(ServiceClassificationModel(** _data))
        if _models:
            ServiceClassificationModel.objects.bulk_create(_models)
    
    

# Set:---------------------------------------------------
@receiver(pre_save, sender=SetModel)
def pre_save_set(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_icon = instance.__class__.objects.get(id=instance.id).icon
    else:
        parent = instance.parent 
        if parent:
            instance.order = parent.order + 1
        else:
            instance.order = 0

@receiver(post_save, sender=SetModel)
def post_save_set(sender, instance=None, created=False, **kwargs):
    # Delete Icon of local storage:
    _icon = None
    _old_icon = None
    if hasattr(instance, "old_icon") and instance.old_icon:
        _old_icon = instance.old_icon
    if hasattr(instance, "icon") and instance.icon:
        _icon = instance.icon
    if _old_icon and (_old_icon != _icon):
        instance.icon.storage.delete(_old_icon.name)


# Shop:---------------------------------------------------

def add_dependent(shop,item,qty=None):
    rep=1
    is_dependent=False
    if item.type == 0:
        is_dependent=True
    elif item.type == 3:
        rep=qty
        is_dependent=True
    elif item.type==1:
        try:
            ShopItemModel.objects.get(service=item.primary,is_dependent=True,shop__owner=shop.owner)
        except ObjectDoesNotExist:
            is_dependent=True
    elif item.type==2:
        try:
            ShopItemModel.objects.get(service__category=item.primary.category,is_dependent=True,shop__owner=shop.owner)
        except ObjectDoesNotExist:
            is_dependent=True
    elif item.type==4:
        try:
            ShopItemModel.objects.get(service=item.dependent,is_dependent=True,shop__owner=shop.owner)
        except ObjectDoesNotExist:
            is_dependent=True
    if is_dependent:   
        qty=item.qty*rep
        return {'shop':shop,'service': item.dependent, 'price': price_calculate_(item.price,item.discount,item.vat), 'qty': item.qty, 'is_dependent': True,'dependent':item.primary}
        
@receiver(pre_save, sender=ShopModel)
def pre_save_set(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_state = instance.__class__.objects.get(id=instance.id).state.title

@receiver(post_save, sender=ShopModel)
def post_save_shop(sender, instance=None, created=False, **kwargs):

    items=[]
    if hasattr(instance, "shopItems") and instance.shopItems!=None:
        items = [dict(i) for i in instance.shopItems]
        services=[i['service'] if type(i['service']) is int else i['service'].pk for i in items ]
        instance.items.filter(is_dependent=True).delete()
        instance.items.exclude(service_id__in=services).delete()
        if items:   
            insert=[]
            update=[]
            for item in items:
                service=item.get('service')
                if service and type(service) is int:
                    service=ServiceModel.objects.get(pk=service)
                    item['service']=service


                try:
                    obj = ShopItemModel.objects.get(shop=instance,service=service)
                    item['price']=price_calculate(service)
                    item['is_installation']=service.is_installation
                    item['is_revival']=service.is_revival
                    item['revival_days']=service.revival_days
                    for attr,value in item.items():
                        setattr(obj,attr,value)
                    update.append(obj)
                except ObjectDoesNotExist:
                    item['shop']=instance
                    item['price']=price_calculate(service)
                    item['is_installation']=service.is_installation
                    item['is_revival']=service.is_revival
                    item['revival_days']=service.revival_days
                    insert.append(ShopItemModel(** item))
                
                            
                dependents=ServiceDependentModel.objects.filter(primary=service)
                dependent_list=[]
                for dep in dependents:
                    dependent_item=add_dependent(instance,dep,item['qty'])
                    dependent_list.append(dependent_item)    
                if dependent_list:
                    for dependent in dependent_list:
                        dep=dependent.copy()
                        try:
                            ShopItemModel.objects.get(shop=dep['shop'],service=dep['service'],dependent=dep['dependent'],is_dependent=True,)
                        except ShopItemModel.DoesNotExist:
                            model=ShopItemModel(** dep)
                            insert.append(model)    
            
            if update:
                ShopItemModel.objects.bulk_update(update,['service_id','qty','price','description'])
            if insert:
                ShopItemModel.objects.bulk_create(insert)
   
        
    old_state=None
    if hasattr(instance, 'old_state') and instance.old_state:
        old_state=instance.old_state    


    if instance.state.title=='pendding' and (old_state=='cart' or ( hasattr(instance,'is_payment')  and instance.is_payment)):
        _items=ShopItemModel.objects.filter(shop_id=instance.pk)
        if _items:
            _total=0
            for item in _items:
                _total+=item.qty*item.price

            _is_wallet=instance.is_wallet
            _wallet=0
            if _is_wallet:
                _wallet=WalletModel.objects.filter(owner=instance.created_by).aggregate(Sum("amount"))["amount__sum"]
                if not _wallet:
                    _wallet=0
            if _wallet>=_total:
                instance.state_id='paid'
                instance.save()

               
              
                data=calculate_commission(instance.owner,instance,instance.amount,None)
                WalletModel.objects.bulk_create(data)

            elif _total>0:
                _total-=_wallet
                _data={'amount':_total,'bank':instance.bank,'platform':instance.platform,'payer':instance.owner,'callbak_url':instance.callback_url,'shop':instance}
                #_data={'amount':1000,'bank':instance.bank,'platform':instance.platform,'payer':instance.owner,'callbak_url':instance.callback_url,'shop':instance}
                try:
                    obj=DepositModel.objects.get(shop=instance)
                    if not obj.is_deposited:
                        obj.receipt_number=('shop : {0}, cancelld').format(instance.pk)
                        obj.shop=None
                        obj.save()
                except ObjectDoesNotExist:
                    pass

                _object=DepositModel(** _data)
                _object.request=instance.request
                _object.save()
                if hasattr(_object,'token'):
                    instance.token=_object.token
                    instance.url=_object.url
                    if instance.bank.title=='saman':
                        instance.callback_url=settings.SAMAN_CALLBACK_URL
                    elif instance.bank.title=='zarinpal':
                        instance.callback_url=settings.ZARINPAL_CALLBACK_URL
        else:
            raise ProjectException(810,"runtime error","shop items empty",status.HTTP_400_BAD_REQUEST,)


    if instance.state.title !=old_state:
        _owner=instance.owner
        _reagent=instance.owner.owner
        _agent=None
        if _reagent:
            _roles=[i.role for i in _reagent.roles.all()]
            if 'agent' in _roles:
                _agent=_reagent               
            if 'seller' in _roles:
                _agent=UserSubordinateModel.objects.get(user=_reagent).parent

        try:
            if _owner and _owner.cellphone and  instance.state.is_client_message:
                sendSMS(_owner.cellphone,instance.state.client_message)
            if _agent and _agent.cellphone and instance.state.is_agent_message:
                sendSMS(_agent.cellphone,instance.state.agent_message)
            if _agent !=_reagent and _reagent.cellphone and instance.state.is_seller_message:
                sendSMS(_reagent.cellphone,instance.state.seller_message)

            if instance.state.is_admin_message:
                for cell in [i.cellphone for i in UserModel.objects.filter(is_staff=True)]:
                    sendSMS(cell,instance.state.seller_message)
        except Exception as err:
            print(err)


# User:---------------------------------------------------
@receiver(pre_delete, sender=UserModel)
def pre_delete_user(sender, instance=None, **kargs):
    if instance:
        try:
            user_profile = ProfileModel.objects.get(owner=instance)
            user_profile.delete()
        except:
            pass

@receiver(pre_save, sender=UserModel)
def pre_save_user(sender, instance, *args, **kwargs):
    if instance.pk:
        instance.old_cellphone = instance.__class__.objects.get(id=instance.id).cellphone
        instance.old_verification_code = instance.__class__.objects.get(id=instance.id).verification_code
        instance.old_avatar = instance.__class__.objects.get(id=instance.id).avatar

@receiver(post_save, sender=UserModel)
def post_save_user(sender, instance=None, created=False, **kwargs):
    if created:
        # Add Wallet zero amount:
        _wallet = WalletModel.objects.create(
            owner=instance,
            amount=0,
            comment="The initial amount of the wallet",
        )
        _wallet.save()
    # Add Role
    if hasattr(instance, "role") and instance.role:
        _role = instance.role
        try:
            user_role = UserRoleModel.objects.get(user_id=instance.pk)
            user_role.role = _role
            user_role.save()
        except UserRoleModel.DoesNotExist:
            _data = {"user": instance.pk, "role": _role.pk}
            _serializer = UserRoleSerializer(data=_data)
            if _serializer.is_valid():
                _serializer.save()
            else:
                raise ProjectException(852,_("runtime error"),_("role error"),status.HTTP_400_BAD_REQUEST,)
        if _role.title == 'seller':
            if hasattr(instance, "agent") and instance.agent:
                try:
                    UserSubordinateModel.objects.get(parent=instance.agent,user=instance)
                except:
                    UserSubordinateModel.objects.create(parent=instance.agent,user=instance,order=1)
    
    # Delete avatar of local storage:
    _avatar = None
    _old_avatar = None
    if hasattr(instance, "old_avatar") and instance.old_avatar:
        _old_avatar = instance.old_avatar
    if hasattr(instance, "avatar") and instance.avatar:
        _avatar = instance.avatar
    if _old_avatar and (_old_avatar != _avatar):
        instance.avatar.storage.delete(_old_avatar.name)

    # Add Profile:
    if hasattr(instance, "profile_data") and instance.profile_data:
        profile_data = instance.profile_data
        try:
            profile = ProfileModel.objects.get(owner=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save() 
        except:
            profile_data['owner'] = instance
            profile = ProfileModel(**profile_data)
            profile.save()
    else:
        try:
            ProfileModel.objects.get(owner=instance)
        except ObjectDoesNotExist:
            # _national_code = generate_national_code()
            profile = ProfileModel.objects.create(owner=instance)

    # Add Address:
    if hasattr(instance, "address_fields") and instance.address_fields:
        address_data = instance.address_fields
        try:
            address_data['owner'] = instance
            address = AddressModel(**address_data)
            address.save()
        except:
            pass
    else:
        pass

    #Send verification code:
    _cellphone = None
    _old_cellphone = None
    _old_verification_code = None
    if hasattr(instance, "cellphone") and instance.cellphone:
        _cellphone = instance.cellphone
    if hasattr(instance, "old_cellphone") and instance.old_cellphone:
        _old_cellphone = instance.old_cellphone
    if hasattr(instance, "old_verification_code") and instance.old_verification_code:
        _old_verification_code = instance.old_verification_code
    _verification_code = instance.verification_code

    if (_cellphone != _old_cellphone) or (_verification_code != _old_verification_code):
        if _verification_code:
            if hasattr(instance,'reset_password') and instance.reset_password:
                _result =sendResetPasswordSMS(_cellphone, _verification_code)
            else:
                _result = sendVerificationSMS(_cellphone, _verification_code)
            print(_result)


#User Role:---------------------------------------------------
@receiver(pre_save, sender=UserRoleModel)
def pre_save_user_role(sender, instance, *args, **kwargs):
    if instance.pk:
        instance.old_role_id = instance.__class__.objects.get(id=instance.id).role_id   
@receiver(post_save, sender=UserRoleModel)
def post_save_user_role(sender, instance=None, created=False, **kwargs):
    # Change Role:
    _role_id = None
    _old_role_id = None
    if hasattr(instance, "old_role_id") and instance.old_role_id:
        _old_role_id = instance.old_role_id
    if hasattr(instance, "role_id") and instance.role_id:
        _role_id = instance.role_id
    if _old_role_id:
        if (_old_role_id=='seller') and (_role_id=='agent'):
            try:
                user_subordinate = UserSubordinateModel.objects.get(user=instance.user)
                childs = UserModel.objects.filter(owner=instance.user)
                for _user in childs:
                    _user.owner = user_subordinate.parent
                    _user.save()
                user_subordinate.delete()
            except:
                pass


@receiver(pre_save, sender=WalletModel)
def pre_save_wallet(sender, instance, *args, **kwargs):
     if instance.type=='withdraw':
        instance.amount= - instance.amount

@receiver(post_save, sender=WalletModel)
def post_save_wallet(sender, instance=None, created=False, **kwargs):
   pass
       




# Notification:---------------------------------------------------
@receiver(post_save, sender=NotificationModel)
def post_save_notification(sender, instance=None, created=False, **kwargs):
    if created:
        _owner_id = instance.owner.id
        _title    = instance.title
        _body     = instance.body
        _icon     = instance.icon
        _data     = instance.data
        _sound    = instance.sound
        _badge    = instance.badge

        sendPush(_owner_id,_title,_body,_icon,_data,_sound,_badge,notification=instance)
def post_notification(owner,title,body,icon=None,data=None,sound=None,badge=None):
    _data = {'owner':owner,'title':title,'body':body}
    if icon:
        _data['icon'] = icon
    if data:
        _data['data'] = data
    if sound:
        _data['sound'] = sound
    if badge:
        _data['badge'] = badge
    
    _model = NotificationModel(** _data)
    _model.save()
def sendPush(owner,title,body,icon=None,data=None,sound=None,badge=None,notification=None):
    from fcm_django.models import FCMDevice
    _data={'title':title,'body':body}
    if icon:
        _data['icon']=icon
    if data:
        _data['data']=data
    if sound:
        _data['sound']=sound
    if badge:
        _data['badge']=badge

    _devices=FCMDevice.objects.filter(user=owner)
    try:
        res=_devices.send_message(** _data)
        _success=res['success']
        if _success:
            notification.sent = True
            notification.save()   
        return (_success,res)
    except Exception as err:
        return (False,err)






def payment(request,amount,bank_portal,cellphone,deposit_id):
    #amount = amount*10  #Convert Toman to Rial
    _token=0
    _return_url=''
    if bank_portal == 'mellat':
        _token=mellat_payment(request,amount,cellphone,deposit_id)
        _return_url='https://bpm.shaparak.ir/pgwchannel/startpay.mellat'
    elif bank_portal == 'saman':
        _token=saman_payment(request,amount,cellphone,deposit_id)
        _return_url='https://sep.shaparak.ir/OnlinePG/OnlinePG'
    elif bank_portal == 'zarinpal':
        _token=zarinpal_payment(request,amount,cellphone,deposit_id)
        _return_url=''.join(['https://next.zarinpal.com/pg/StartPay/',str(_token),'/ZarinGate'])
    elif bank_portal == 'irankish':
        _token=iran_kish_payment(request,amount,cellphone,deposit_id)
        _return_url=''.join(['https://ikc.shaparak.ir/iuiv3/IPG/Index/'])
    return {'url':_return_url,'token':_token}

def mellat_payment(request,amount,cellphone,deposit_id):
    import zeep

    wsdl = 'https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl'
    client = zeep.Client(wsdl=wsdl)
    namespace = 'http://interfaces.core.sw.bps.com/'
    terminal_id = 3526439
    userName = 'k171'
    userPassword = '57923592'
    localDate = datetime.now().strftime('%Y%m%d')
    localTime = datetime.now().strftime('%H%M%S')
    additionalData =str(cellphone)
    callBackUrl = settings.MELLAT_CALLBACK_URL
    deposit_id = 10000000 + deposit_id
    ret = client.service.bpPayRequest(terminal_id,userName,userPassword,deposit_id,amount,localDate,localTime,additionalData,callBackUrl,654321)

    res = ret.split(',')
    ref_id = res[0]
    if res[0] == '0':
        ref_id = res[1]                        
    if (ref_id is not None) and (len(ref_id) > 0):
        return ref_id

def saman_payment(request,amount,cellphone,deposit_id):
    import requests
    import urllib3
    import json

    url = 'https://sep.shaparak.ir/MobilePG/MobilePayment'
    _Action = 'token'
    _TerminalId = settings.SAMAN_TERMINAL
    _RedirectUrl = settings.SAMAN_CALLBACK_URL
    _CellNumber = str(cellphone)
    _ResNum =  deposit_id
    

    headers = {'content-type': 'application/json'}
    body = {"Action":"token","TerminalId":_TerminalId,"RedirectURL":_RedirectUrl,"ResNum":_ResNum,"Amount":amount,"CellNumber":_CellNumber}
    
    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    try:
        requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    except AttributeError:
        # no pyopenssl support used / needed / available
        pass
    
    res = requests.post(url, json=body, headers=headers, verify=False)
    text=res.text
    try:
        text= json.loads(res.text)
        
    except:
        pass
    print(text)
    res = text
    if res['status'] == 1:
        return res['token']

def zarinpal_payment(request,amount,cellphone,deposit_id):
    
    from zeep import Client
    from django.conf import settings
    
    _pin = settings.ZARINPAL
    _wsdl_url = settings.ZARINPAL_URL
    _client = Client(_wsdl_url)
    _amount=amount
    _request_data={
        "MerchantID":_pin,
        "Amount":_amount,
        "Description":str(cellphone),
        "CallbackURL":settings.ZARINPAL_CALLBACK_URL          
        }
        
    try:    
        _response=_client.service.PaymentRequest(** _request_data)
        if _response.Status == 100:
            return str(_response.Authority)
            return (True,''.join(['https://next.zarinpal.com/pg/StartPay/',str(_response.Authority),'/ZarinGate']),)
        elif _response.Status  != 0:
            return None
    except Exception as err:
        return None

def iran_kish_payment(request,amount,cellphone,deposit_id):
    """
    this func will receive amount of the transaction and an arbitrary request id and
    returns a token generated by the ipg if success otherwise raise a NoneToken exception.

    :param amount: amount of the transaction in rials
    :param request_id: an arbitrary request id which will be returned by the ipg at the end. (read ipg docs for more information.)
    :return: token string
    """
    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    try:
        requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    except AttributeError:
        # no pyopenssl support used / needed / available
        pass
    
    # load the rsa public key
    
    rsa_public_key = rsa.PublicKey.load_pkcs1_openssl_pem(settings.IRAN_KISH_RSA_PUBLIC_KEY)
    
    aes_key, aes_iv = os.urandom(16), os.urandom(16)
    aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    byte_array_data = bytearray(48)
    byte_array_data[0:16], byte_array_data[16:48] = aes_key, \
                                                    bytearray(
                                                        SHA256.new(
                                                            aes.encrypt(
                                                                pad(
                                                                    bytes(
                                                                        bytearray.fromhex(
                                                                            settings.IRAN_KISH_TERMINAL +
                                                                            settings.IRAN_KISH_PASS_PHRASE +
                                                                            str(amount).zfill(12) +
                                                                            '00'
                                                                        )
                                                                    ),
                                                                    16
                                                                )
                                                            )
                                                        ).digest()
                                                    )
    authentication_envelope = {
        'iv': aes_iv.hex(),
        'data': rsa.encrypt(byte_array_data, rsa_public_key).hex()
    }
    request = {
        'transactionType': 'Purchase',
        'terminalId': settings.IRAN_KISH_TERMINAL,
        'acceptorId': settings.IRAN_KISH_ACCEPTOR,
        'amount': amount,
        'revertUri': settings.IRAN_KISH_CALLBACK_URL,
        'requestId': str(deposit_id),
        'requestTimestamp': int(time.time())
    }
    payload = {
        'authenticationEnvelope': authentication_envelope,
        'request': request
    }
    r = requests.post(settings.IRAN_KISH_URL, json=payload, verify=False)
  
    if r.ok:
        result = r.json()
        if result['responseCode'] == '00':
            return result['result']['token']
    raise Exception(r.text) 

def calculate_commission(owner,shop,amount,deposite):
    _services=[ i.service for i in shop.items.all()]

    _reagent=owner.owner
    if _reagent:
        _roles=[i.role.pk for i in _reagent.roles.all()]
        
    
        _agent_commission=0
        _seller_commission=0
        for _service in _services:
            if 'agent' in _roles:
                _agent=_reagent
                _agent_commission=calculate_agent_commission(_agent,_service)
            if 'seller' in _roles:
                _agent=UserSubordinateModel.objects.get(user=_reagent).parent
                _agent_commission=calculate_agent_commission(_agent,_service)
                _seller_commission=calculate_seller_commission(_reagent,_service,_agent_commission)
            
        
            _amount=_agent_commission-_seller_commission
            _data=[]
            _data.append(WalletModel(** {'owner':owner,'amount':amount,'deposit_id':deposite,'kind':'increse_credit','type':'order','shop':shop,'service':_service}))
            _data.append(WalletModel(** {'owner':owner,'amount':-amount,'kind':'withdraw','type':'order','service':_service,'shop':shop}))
            _data.append(WalletModel(** {'owner':_agent,'amount':_amount,'kind':'increse_credit','type':'porsant','service':_service,'shop':shop}))
            if _agent!=_reagent:            
                _data.append(WalletModel(** {'owner':_reagent,'amount':_seller_commission,'kind':'increse_credit','type':'porsant','service':_service,'shop':shop}))
           
            
            return _data
           
           

  

def calculate_agent_commission(agent,service):
    try:
        _discount=int((service.price*(service.discount/100)))
        _amount=(service.price - _discount) - service.rebate
        if _amount<0:
            _amount=0

        _commission=CommissionModel.objects.get(owner=agent,service=service)
        if _commission.type == 'cash':
            return _commission.amount
        elif _commission.type == 'cent':
            return _amount*(_commission.amount/100)
    except ObjectDoesNotExist:
        try:
            _setting=SettingModel.objects.get(key=settings.AGENT_COMMISSION_TAG)
            _val=float(_setting.value)
        except ObjectDoesNotExist:
            _val=settings.AGENT_COMMISSION

        return _amount*(_val/100)
    return 0
def calculate_seller_commission(seller,service,amount):
    try:
        _commission=CommissionModel.objects.get(owner=seller,service=service)
        if _commission.type == 'cash':
            return _commission.amount
        elif _commission.type == 'cent':
            return amount*(_commission.amount/100)
    except ObjectDoesNotExist:
        try:
            _setting=SettingModel.objects.get(key=settings.SELLER_COMMISSION_TAG)
            _val=float(_setting.value)
        except ObjectDoesNotExist:
            _val=settings.SELLER_COMMISSION

        return amount*(_val/100)
    return 0

def sendVerificationSMS(cellphone, code):
    
    if type(cellphone) != type([]):
        cellphone = [cellphone]
    _msg ="سامانه myne-tehran.ir\n به شما خوش آمد می گوید \n شناسه کاربری شما : {0} \n کلمه عبور شما : {1} \n لطفا از این اطلاعات برای ورود به سامانه استفاده نمایید".format(cellphone[0],code)
    return sendSMS(cellphone,_msg)    

def sendResetPasswordSMS(cellphone,code):
    if type(cellphone) != type([]):
        cellphone = [cellphone]
    _msg ="سامانه myne-tehran.ir\n توکن ریست پسورد \n {0}".format(code)
    return sendSMS(cellphone,_msg) 


def sendSMS(cellphone,msg):
    import requests
    import json
    import re
    
    url = "https://ippanel.com//api/select"
    username = "mysms-tehran"
    password = "OO73988oo@@"
    sender_one = "5000125475"
    sender_two = "3000505"
    if type(cellphone) != type([]):
        cellphone = [cellphone]
    
   
    _data = {   "op":"send",
                "uname":username,
                "pass":	password,
                "message":msg,
                "from":sender_one,
                "to":cellphone
            }
    _headers = {"Content-type": "application/json"}
    _response = requests.post(url, json=_data, headers=_headers)
    if re.match(r'^\[0,',_response.text):
        return {"result": _response.text, "status": _response.status_code}
    else:
        _data.pop('from',None)
        _data['from'] = sender_two
        _response = requests.post(url, json=_data, headers=_headers)
        if re.match(r'^\[0,',_response.text):
            return {"result": _response.text, "status": _response.status_code}
        else:
            return {"result": _response.text, "status": _response.status_code}