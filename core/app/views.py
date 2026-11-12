from app.models import DepositModel
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.http import HttpRequest
from app.helpers import get_dict_data
from datetime import datetime,timezone
import json
import jdatetime
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# Create your views here.
@csrf_exempt
def mellat_callbak(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    pay = ''
    order=None
    status,pay,order = mellat_payment_callback(request)
    if status:
        status = 'success'
    else:
        status = 'failed'
    return render(request,
                  'callback.html',
                  {
                      'title': _('Callback Page'),
                      'year': datetime.now().year,
                      'status':status, #('success','failed')
                      'pay':pay, # pay :('withdraw','charge')
                      'order':order
                  })

@csrf_exempt
def saman_callbak(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    status = saman_payment_callback(request)
    if status:
        status = 'success'
    else:
        status = 'failed'
    return render(request,
                  'callback.html',
                  {
                      'title': _('Callback Page'),
                      'year': datetime.now().year,
                      'status':status
                  })

@csrf_exempt
def zarinpal_callbak(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    status,shop_id,callback_url = zarinpal_payment_callback(request)
    if status>0:
        status = 'success'
    else:
        status = 'fail'
    return render(request,
                  'callback.html',
                  {
                      'title': _('Callback Page'),
                      'year': datetime.now().year,
                      'status':status,
                      'shop_id':shop_id,
                      'callback_url':callback_url
                  })


def mellat_payment_callback(request):
    import zeep
    _data = get_dict_data(request.POST)
       
    _ref_id = _data['RefId']
    _res_code = _data['ResCode']
    _sale_order_id = _data.get('SaleOrderId','')
    _sale_reference_id = _data.get('SaleReferenceId','') 
    _card_holder_pan = _data.get('CardHolderPan','') 
    if _res_code == '0':            
        _wsdl = 'https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl'
        _client = zeep.Client(wsdl=_wsdl)
        _namespace = 'http://interfaces.core.sw.bps.com/'
        _terminal_id = 3526439
        _userName = 'k171'
        _userPassword = '57923592'
        _retVR = '1'
        _retIR = '1'

        _retVR = _client.service.bpVerifyRequest(_terminal_id,_userName,_userPassword,_sale_order_id,_sale_order_id,_sale_reference_id)
        if (_retVR is None) or (len(_retVR) == 0): 
            _retIR = _client.service.bpinquiryRequest(_terminal_id,_userName,_userPassword,_sale_order_id,_sale_order_id,_sale_reference_id)
            
        if (_retVR == '0') or (_retIR == '0'):
            _client.service.bpSettleRequest(_terminal_id,_userName,_userPassword,_sale_order_id,_sale_order_id,_sale_reference_id)  
            return payment(token=_ref_id) 
    return (False,'bank_error',None) #(status,pay,order)
def saman_payment_callback(request):  
    import zeep
    _data = get_dict_data(request.POST)                    
    _terminalId = settings.SAMAN_TERMINAL
    _res_num = _data.get('ResNum',None)
    _status = _data.get('Status',None)
    _ref_num = _data.get('RefNum',None) 
    _trace_no = _data.get('TraceNo',None) 
    _secure_pan = _data.get('SecurePan',None) 
    _amount=_data.get('Amount',None)
        
                
    if _status == '2':
        client = zeep.Client('https://verify.sep.ir/Payments/ReferencePayment.asmx?wsdl')                   
        _ret=client.service.verifyTransaction(_ref_num, _terminalId)              
        if _ret == _amount:   
            return payment(token=_ref_num)  
    return -1
def zarinpal_payment_callback(request):  
    from django.conf import settings 
    import requests
    _params = get_dict_data(request.GET)        
    print(_params)
    _pin=settings.ZARINPAL
    _authority=_params.get('Authority',None)
    _amount=None
    _shop_id=None
    _callbak_url=None
    try:
        _object=DepositModel.objects.get(refrence=_authority)
        _amount=_object.amount*10
        _shop_id =_object.shop_id
        _callback_url=_object.callbak_url
    except:
        pass

    if _authority and _amount:       
        _url='https://api.zarinpal.com/pg/v4/payment/verify.json'
        _request_data={
            "merchant_id":_pin,
            "authority":_authority,
            "amount":_amount}
        _headers = {'Content-type': 'application/json'}
        _res = requests.post(_url, json=_request_data, headers=_headers)
        _text=_res.text
        try:
            _text= json.loads(_res.text)
            print(_text)            
            _data=_text.get('data',None)
            if _data:
                _status=_data.get('code',None)
                if _status == 100 or _status==101 :
                    res=payment(_authority)
                    return res,_shop_id,_callback_url
        except Exception as err:
            pass
    return -1,_shop_id,_callback_url


def payment(token=None):
    try:
        
        _deposit = DepositModel.objects.get(refrence=token) 
        _deposit.is_deposited = True
        _deposit.deposit_date = datetime.now().astimezone()
        _deposit.save()

       

        return 1
    except Exception as err:
        print(err)
        return 0


def payment_test(request,token=None):
    return render(request, 'bank_saman_test.html', {'token': token})
    # return render(request, 'bank test.html', {})