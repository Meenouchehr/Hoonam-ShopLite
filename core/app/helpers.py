import random
import jdatetime
from datetime import datetime, time





def generate_username(name=''):
    from app.models import UserModel
    username = "".join(name.split(' ')).lower()
    if username and not UserModel.objects.filter(username=username).exists():
        return username
    random_username = username + str(random.randint(0, 1000))
    return generate_username(random_username)


def convert_jalali_string_to_gregorian_date(string_date, spliter='/'):
    string_date = string_date.strip()
    _date = string_date.split(' ')
    _time = None

    if isinstance(_date, list):
        if len(_date) > 1:
            _time = _date[1]
        _date = _date[0]
    _hour, _minute, _second = (None, None, None)
    if _time:
        _times = _time.split(':')
        if len(_times) == 2:
            _times.append('00')
        elif len(_times) == 1:
            _times.append('00')
            _times.append('00')
        _hour, _minute, _second = _times

    _year, _month, _day = _date.split(spliter)
    if _year:
        _year = int(_year)
    if _month:
        _month = int(_month)
    if _day:
        _day = int(_day)

    _date = jdatetime.date(_year, _month, _day).togregorian()
    if _hour and _minute and _second:

        _hour = int(_hour)
        _minute = int(_minute)
        _second = int(_second)
        _time = time(_hour, _minute, _second)
        _date = datetime.combine(_date, _time)

    return _date
def convert_gregorian_to_jalali_string_date(date):
    if date:
        return jdatetime.date.fromgregorian(date=date).strftime("%Y/%m/%d")
    return ""
def convert_gregorian_to_jalali_string_datetime(datetime):
    if datetime:
        return jdatetime.datetime.fromgregorian(datetime=datetime).strftime(
            "%Y/%m/%d %H:%M:%S"
        )
    return ""
def convert_jalali_string_without_seprator_to_gregorian_date(string_date):
    if len(string_date) != 8:
        return ''

    _year = string_date[:4]
    _month = string_date[4:6]
    _day = string_date[6:8]
    if _year:
        _year = int(_year)
    if _month:
        _month = int(_month)
    if _day:
        _day = int(_day)

    return jdatetime.date(_year, _month, _day).togregorian()
def convert_shamsi_string_to_miladi_date(string_date):
    try:
        if len(string_date) < 8:
            return None
        if "/" in string_date:
            return convert_jalali_string_to_gregorian_date(string_date, spliter="/")
        elif "-" in string_date:
            return convert_jalali_string_to_gregorian_date(string_date, spliter="-")
        else:
            if len(string_date) != 8:
                return None
            else:
                return convert_jalali_string_without_seprator_to_gregorian_date(string_date)
    except:
        return None


def random_with_N_digits(n=8):
    range_start = 10**(n - 1)
    range_end = (10**n) - 1
    return random.randint(range_start, range_end)
def get_verfication_code(digit_num=5):
    return random_with_N_digits(digit_num)


def get_dict_data(data):
    from django.http import QueryDict

    if type(data) is QueryDict:
        return {
            k: data.getlist(k) if len(data.getlist(k)) > 1 else v
            for k, v in data.items()
        }
    elif type(data) is dict:
        return data
    return {}

# Pagination: page_size,page_num
def get_data(data: list, pagination: tuple = None):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    total_page_num = 1
    result = data
    if pagination:
        page_size, page_num = pagination
        paginator = Paginator(data, page_size)
        try:
            res = paginator.page(page_num)
        except PageNotAnInteger:
            res = paginator.page(2)
        except EmptyPage:
            res = paginator.page(paginator.num_pages)
        result = res.object_list
        total_page_num = res.paginator.num_pages

    return (result, total_page_num)
def get_response_data(request, queryset):
    if 'page_size' in request.query_params and request.query_params['page_size'] and \
                'page_num' in request.query_params and request.query_params['page_num']:
        _page_size = request.query_params['page_size']
        _page_num = request.query_params['page_num']
        _objects, _total_page_num = get_data(queryset,
                                             pagination=(_page_size,
                                                         _page_num))
    else:
        _objects, _total_page_num = get_data(queryset)

    return _objects, _total_page_num


def get_user(context):
    if context:
        try:
            if 'request' in context:
                _request = context['request']
                if _request:
                    if _request.auth:
                        return _request.auth.user
                    elif _request.user:
                        return _request.user
        except:
            _request = context
            if _request.auth:
                return _request.auth.user
            elif _request.user:
                return _request.user
    return None

def get_user_roles(user):
    from app.models import UserRoleModel
    roles = []
    if hasattr(user,'id') and user.id:
        user_role = UserRoleModel.objects.filter(user_id=user.id)
        roles = [obj.role.title for obj in user_role]
    return roles


def is_leap(year):
    remain = [1,5,9,13,17,22,26,30]
    if (year % 33) in remain:
        return True
    return False
def shamsi_month_to_gregorian_date(year,month,type='start'):
    if type == 'start':
        date = f"{year}/{month}/01"
        return convert_jalali_string_to_gregorian_date(date)
    elif type == 'end':
        if month == 12:
            # Edit : Needs more work
            if is_leap(year):
                date = f"{year}/{month}/30"
            else:
                date = f"{year}/{month}/29"
        elif month <= 6:
            date = f"{year}/{month}/31"
        else:
            date = f"{year}/{month}/30"
        return convert_jalali_string_to_gregorian_date(date)
    return None

def get_current_year():
    date = datetime.now().date()
    date_sh = convert_gregorian_to_jalali_string_date(date)
    year = int(date_sh.split('/')[0])
    return year


def format_card(card_num):
    """
    Formats card numbers to remove any spaces, unnecessary characters, etc
    Input: Card number, integer or string
    Output: Correctly formatted card number, string
    """
    import re
    card_num = str(card_num)
    # Regex to remove any nondigit characters
    return re.sub(r"\D", "", card_num)
def validate_card(card_num):
    """
    Input: Card number, integer or string
    Output: Valid?, boolean
    card = [0,[1,2,3,4,5],[6,7,8,9,10,12,13,14],15]
    dard[0] in [3,4,5,6]
    if dard[0] == 3 then card[1][0]=7
    """
    double = 0
    total = 0

    digits = str(format_card(card_num))

    for i in range(len(digits) - 1, -1, -1):
        #---------------
        # dig = (double+1)*int(digits[i])
        # if dig > 9:
        #     dig -= 9
        # total += dig
        # Or 
        for c in str((double + 1) * int(digits[i])):
            total += int(c)
        #---------------
        double = (double + 1) % 2

    return (total % 10) == 0


def distance_calculate(queryset, origin:tuple()=(None,None), radius=None):
    """
    ---
    d = "6371000 * acos(cos(radians(%s)) * cos(radians(d_latitude)) * cos(radians(d_longitude) - radians(%s)) + sin(radians(%s)) * sin(radians(d_latitude)))"
        .format(s_latitude, s_longitude, s_latitude)
    ---
    d = 2*6371000*atan2(sqrt(power(sin((radians(latitude)-radians(%s))/2),2)+(cos(radians(latitude))*cos(radians(%s))*power(sin((radians(longitude)-radians(%s))/2),2))),
               sqrt(1-(power(sin((radians(latitude)-radians(%s))/2),2)+(cos(radians(latitude))*cos(radians(%s))*power(sin((radians(longitude)-radians(%s))/2),2)))))
        .format(s_latitude,s_latitude, s_longitude, s_latitude,s_latitude,s_longitude)
    ---
    """
    import math
    from django.db.models import F
    from django.db.models.functions.math import (Radians,Sin,Cos,ATan2,Sqrt)
    # radius of the Earth:
    R    = 6373.0*1000.0
    # coordinates:
    latitude = math.radians(origin[0])
    longitude = math.radians(origin[1]) 

    _queryset = queryset.annotate(
                  a=(
                    Sin(Radians(F('latitude') - latitude)/2)**2 +
                    (
                        Cos(F('latitude'))*Cos(latitude)*
                        Sin(Radians(F('longitude') - longitude)/2)**2
                    )
                )
            )
    _queryset = _queryset.annotate(
                  c=(2*ATan2(Sqrt(F('a')),Sqrt(1-F('a'))))
                )
    _queryset = _queryset.annotate(
                  distance=R*F('c')
                ).order_by('distance')
    _queryset = _queryset.filter(distance__lte=float(radius))
    
    return _queryset


def is_national_code_verify(national_code):
    _national_code = str(national_code)
    if len(_national_code) == 10:
        _sum = 0
        for i in range(0, len(_national_code) - 1):
            _state = 10 - i
            try:
                _num = int(_national_code[i])
                _sum += (_num * _state)
            except:
                return False
        if _sum > 0:
            _modulo = _sum % 11
            _parety = _modulo
            if _modulo >= 2:
                _parety = 11 - _modulo
            try:
                _num = int(_national_code[9])
                if _num == _parety:
                    return True
            except:
                return False
    return False


def validate_phone_number(cellphone,country_code=None):
    #Regular expression: /^(\+98|0098|0)?(9[0-9]{9})$/
    import phonenumbers
    try:
        if not country_code:
            country_code = "IR"
        cellphone_check = phonenumbers.parse(cellphone, country_code)
        return phonenumbers.is_valid_number(cellphone_check)
    except:
        return False

def is_deleted_parent(obj):
    if obj.parent:
        if obj.parent.status == -1:
            return True
        else:
            return is_deleted_parent(obj=obj.parent)
    return False


def delete_child(obj=None,state=None,status=None):
    from app.models import CategoryModel,SetModel
    if obj and state=='category':
        sub_categories = CategoryModel.objects.filter(parent=obj)
        if status == -2:
            for ch_obj in sub_categories:
                delete_child(obj=ch_obj,state='category',status=-2)
                ch_obj.delete()
        elif status == -1:
            sub_categories = sub_categories.filter(status__in=[0,1])
            for ch_obj in sub_categories:
                delete_child(obj=ch_obj,state='category',status=-1)
                ch_obj.status_old = ch_obj.status
                ch_obj.status = -1
                ch_obj.save()
    elif obj and state=='set':
        sub_sets = SetModel.objects.filter(parent=obj)
        if status == -2:
            for ch_obj in sub_sets:
                delete_child(obj=ch_obj,state='set',status=-2)
                ch_obj.delete()
        elif status == -1:
            sub_sets = sub_sets.filter(status__in=[0,1])
            for ch_obj in sub_sets:
                delete_child(obj=ch_obj,state='set',status=-1)
                ch_obj.status_old = ch_obj.status
                ch_obj.status = -1
                ch_obj.save()

def recover_child(obj=None,state=None):
    if obj and state=='category':
        sub_categories = CategoryModel.objects.filter(parent=obj,status=-1)
        for ch_obj in sub_categories:
            ch_obj.status = ch_obj.status_old
            ch_obj.status_old = -1
            ch_obj.save()
            recover_child(obj=ch_obj,state='category')
    elif obj and state=='set':
        sub_sets = SetModel.objects.filter(parent=obj,status=-1)
        for ch_obj in sub_sets:
            ch_obj.status = ch_obj.status_old
            ch_obj.status_old = -1
            ch_obj.save()
            recover_child(obj=ch_obj,state='set')

def price_calculate(service=None):
    orginal_price = service.price
    discount      = service.discount
    vat           = service.vat
    discounted_price = orginal_price*(1 - discount/100)
    vat_price        = discounted_price*(1 + vat/100)
    price            = int(vat_price)
    return price

def price_calculate_(price,discount,vat):
    orginal_price = price
    discount      = discount
    vat           = vat
    discounted_price = orginal_price*(1 - discount/100)
    vat_price        = discounted_price*(1 + vat/100)
    price            = int(vat_price)
    return price

def has_items(basket=None):
    items = BasketItemModel.objects.filter(basket=basket)
    from rest_framework import status
    from app.exceptions    import ProjectException
    from django.utils.translation import gettext as _ 
    for item in items:
        _no = item.qty
        _service = item.service
        if _service.qty < _no:
            raise ProjectException(807, _('validation error'),f'{_no} service with ID {_service.pk} are not in stock.',status.HTTP_400_BAD_REQUEST)
    return True


def has_access(user,instance):
    user_role     = get_user_roles(user)
    instance_role = get_user_roles(instance)
    if user.is_superuser: #superuser
        return True
    elif instance.is_superuser:
        return False
    elif user.is_staff: # admin
        if instance.is_staff:
            return False
        else:
            return True
    elif 'agent' in user_role:
        if 'agent' in instance_role:
            return False
        elif 'seller' in instance_role:
            chart = UserSubordinateModel.objects.get(user=instance)
            if chart.parent == user:
                return True
            else:
                return False
        elif 'client' in instance_role:
            if instance.owner == user:
                return True
            else:
                chart = UserSubordinateModel.objects.get(user=instance.owner)
                if chart.parent == user:
                    return True
                else:
                    return False
    elif 'seller' in user_role:
        if 'agent' in instance_role:
            return False
        elif 'seller' in instance_role:
            return False
        else:
            if instance.owner == user:
                return True
            else:
                return False
    elif 'client' in user_role:
        return False   

 
def allow_delete(user,instance):
    user_role     = get_user_roles(user)
    instance_role = get_user_roles(instance)
    if user.is_superuser: #superuser
        return True
    elif instance.is_superuser:
        return False
    elif user.is_staff: # admin
        if instance.is_staff:
            return False
        else:
            return True
    elif 'agent' in user_role:
        if 'agent' in instance_role:
            return False
        elif 'seller' in instance_role:
            chart = UserSubordinateModel.objects.get(user=instance)
            if chart.parent == user:
                return True
            else:
                return False
        elif 'client' in instance_role:
            if instance.owner == user:
                return True
            else:
                chart = UserSubordinateModel.objects.get(user=instance.owner)
                if chart.parent == user:
                    return True
                else:
                    return False
    elif 'seller' in user_role:
        if 'agent' in instance_role:
            return False
        elif 'seller' in instance_role:
            return False
        else:
            if instance.owner == user:
                return True
            else:
                return False
    elif 'client' in user_role:
        return False  

def basket_requirement(basket):
    _items = BasketItemModel.objects.filter(basket=basket)
    is_require = False
    for item in _items:
        _records = RecordModel.objects.filter(service=item.service)
        for record in _records:
            try:
                DocumentModel.objects.get(owner=basket.owner,record=record)
            except:
                is_require = True
        _features = FeatureModel.objects.filter(service=item.service)
        for feature in _features:
            try:
                AttributeModel.objects.get(owner=basket.owner,feature=feature)
            except:
                is_require = True           
    return is_require

def slugify(title):
    import re
    _slug=re.sub(r"[^\w\s]", '_', title.strip())
    _slug=_slug.replace(' ','-').replace('-_','-')
    return _slug