
import contextlib
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.parsers import (MultiPartParser, JSONParser)
from rest_framework.renderers import JSONRenderer
from django.db.models import Q, F, CharField, Value as V, Count
from django.db.models import Prefetch
from django.db.models.functions import Concat, Cast
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from django.utils.translation import gettext as _


from app.exceptions import ProjectException
from app.serializers import *
from app.decorators import *
from app.accesses import *
from app.helpers import *
from app.filters import *

from app.views import *
from app.swagger_schema import *
from fcm_django.models import FCMDevice

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


def add_filter(filters , items):
    if filters:
        temp_filters=[]
        for item in items:
            for filter in filters:
                temp=Q(** item)
                filter&=temp
                temp_filters.append(filter)
        
        filters.clear()  
        for filter in temp_filters:
            filters.append(filter)
    
    else:
        for item in items:
            filters.append(Q(** item))
    

def add_owner_filter(filters,request):
    
    if 'owner' in request.query_params and request.query_params['owner']:
        owner = get_owner(request)
    else:
        owner=request.user
    add_filter(filters,[{'owner':owner}])

def get_status_filter(request):
    filters=[]
    user=request.user if hasattr(request, 'user') else None
    if 'status' in request.query_params and request.query_params['status']:
        try:
            status=int(request.query_params['status'])
        except Exception:
            status=1
        if status==-1:
            filters.append({'is_delete':1})
        elif status==1:
            filters.append({'status': 1,'is_delete':0})
        elif status==0:
            if user and  user.is_staff:
                filters.append({'status': 0,'is_delete':0})
            elif user:
                filters.append({'status': 0,'created_by':user,'is_delete':0})
            else:
                filters.append({'status': 1,'is_delete':0})
    else:
        filters.append({'status': 1,'is_delete':0})
        if user and  user.is_staff:
                filters.append({'status': 0,'is_delete':0})
        elif user and user.pk:
            filters.append({'status': 0,'is_delete':0})


    return filters

def get_owner(request):
    user = request.user
    owner = request.query_params['owner']
    if not(user.is_superuser or user.is_staff or owner == user.pk):
        try:
            UserModel.objects.get(Q(owner=user.pk) | Q(owner__owner=user.pk))
        except ObjectDoesNotExist as e:
            raise ProjectException(4031, _('forbidden error'), _('forbidden error'), status.HTTP_403_FORBIDDEN) from e
    return owner
    
def get_filter(filters):  # sourcery skip: avoid-builtin-shadow
    filter=Q()
    for fil in filters:
        filter|=fil
    return filter
    
def get_operation_description(obj,action):
        if action == 'create':
            return "POST create A {0} object api".format(obj)
        elif action == 'delete':
            return "DELETE remove {0}(s) api".format(obj)
        elif action == 'list':
            return "GET list of {0}(s) api".format(obj)
        elif action == 'partial_update':
            return "PATCH update A {0} object api".format(obj)
        elif action == 'retrieve':
            return "GET get A {0} object api".format(obj)
        elif action == 'access':
            return "PATCH update {0}(s)'s access api".format(obj)
        elif action == 'recycle':
            return "PATCH update {0}(s)'s recycle api".format(obj)

class BasicView(viewsets.GenericViewSet):
    queryset=None
   
    

    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):
        return queryset

    def get_object(self,pk=None):
        if pk:
            with contextlib.suppress(ObjectDoesNotExist):
                return self.get_queryset().get(pk=pk,is_delete=0)
    
    def create(self, request):
        data= get_dict_data(request.data)
        serializer = self.get_serializer(data=data)
        serializer.request = request
        if serializer.is_valid():
            obj = serializer.save()
            serializer = self.get_responses()(instance=obj,many=False)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(4001,_("خطای راستی آزمایی"),serializer.errors,status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        data= get_dict_data(request.data)
        serializer = self.get_serializer(data=data)
        serializer.request = request
        if serializer.is_valid():
            obj = serializer.delete()
            return Response({},status=status.HTTP_204_NO_CONTENT)
        else:
            raise ProjectException(4001,_("خطای راستی آزمایی"),serializer.errors,status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset=queryset).order_by('-pk')
        count = queryset.count()
        if count == 0:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        queryset, total_page_num = get_response_data(request, queryset)
        serializer = self.get_serializer(queryset, many=True)
        serializer.request = request
        return Response({
            'list': serializer.data,
            'total_page_num': total_page_num,
            'total_row': count
        })

    def partial_update(self, request, pk=None):
        if pk:
            obj=self.get_object(pk)
            if obj:
                data= get_dict_data(request.data)
                serializer = self.get_serializer(instance=obj, data=data, partial=True)
                serializer.request = request
                if serializer.is_valid():
                        obj = serializer.save()
                        serializer = self.get_responses()(instance=obj)
                        return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    raise ProjectException(4001,_("خطای راستی آزمایی"),serializer.errors,status.HTTP_400_BAD_REQUEST)

        raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)
    
    def retrieve(self, request, pk=None):
        if pk:
            obj=self.get_object(pk)
            if obj:
                serializer = self.get_serializer(obj)
                serializer.request = request
                return Response(serializer.data, status=status.HTTP_200_OK)
             
        raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)


    @action(detail=False, methods=['patch'])
    def access(self, request):   
        data= get_dict_data(request.data)
        serializer = self.get_serializer(data=data)
        serializer.request = request
        if serializer.is_valid():
            obj = serializer.access_execute()
            return Response({},status=status.HTTP_200_OK)
        else:
            raise ProjectException(4001,_("خطای راستی آزمایی"),serializer.errors,status.HTTP_400_BAD_REQUEST)

       
    @action(detail=False, methods=['patch'])
    def recycle(self, request):   
        data= get_dict_data(request.data)
        serializer = self.get_serializer(data=data)
        serializer.request = request
        if serializer.is_valid():
            obj = serializer.recycle()
            return Response({},status=status.HTTP_200_OK)
        else:
            raise ProjectException(4001,_("خطای راستی آزمایی"),serializer.errors,status.HTTP_400_BAD_REQUEST)


# Address
class AddressView(BasicView):

    queryset = AddressModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=AddressSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Address'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": AddressInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':AddressDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':AddressInformationSerializer}
        elif action == 'partial_update':
            return {"200": AddressInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return AddressInformationSerializer
        elif self.action == 'delete':
            return AddressDeleteSerializer
        elif self.action == "partial_update":
            return AddressInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AddressSerializer
        elif self.action == 'delete':
            return AddressDeleteSerializer
        elif self.action in ['list','retrieve']:
            return AddressInformationSerializer
        elif self.action == "partial_update":
            return AddressUpdateSerializer
        elif self.action == "access":
            return AddressAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.select_related('owner').prefetch_related('evidences')
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        add_owner_filter(filters,self.request)
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=AddressDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=AddressFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class AttributeViewSet(viewsets.GenericViewSet):
    queryset = AttributeModel.objects.all()
    serializer_class = AttributeSerializer
    permission_classes = ([IsAuthenticated])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        # (hasattr(self,'name') and self.name in ["Upload",])
        action_map = list(self.action_map.values())
        _action = ["some", "status", "trash", "recycle"]
        if any(item in action_map for item in _action):
            # if ["some","status"] in action_map
            parser_classes = [JSONParser]
        elif ("upload" in action_map):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            AttributeInfoSerializer,
            "200_OK":
            openapi.Response({}),
            "201":
            AttributeSchemaSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_some":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_status":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "827": {
                            "status": "failed",
                            "code": 827,
                            "message": "validation error",
                            "detail": "Status field is Invalid.",
                        },
                    }
                },
            ),
            "404_multi":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "811": {
                            "status": "failed",
                            "code": 845,
                            "message": "not found",
                            "detail": "Some users are not in the system.",
                        },
                        "819": {
                            "status": "failed",
                            "code": 819,
                            "message": "not found",
                            "detail": "Primary keys list is empty.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer,
            "200_some":
            SampleSomeVirResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"], "400": rsd["807"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"],
                         "400": rsd["400"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAuthenticated, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return AttributeInfoSerializer
        elif self.action in ['partial_update']:
            return AttributeUpdateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = self.queryset
        _user = self.request.user
        role_list = get_user_roles(_user)
        if not _user.pk:
            queryset = queryset.filter(pk=-1)
        elif _user.is_superuser:  # superuser
            queryset = queryset.filter(owner__is_superuser=False)
        elif _user.is_staff:  # admin
            queryset = queryset.filter(owner__is_staff=False)
        elif 'agent' in role_list:  # agent
            queryset = queryset.filter(Q(owner__owner=_user) | Q(owner__parent__parent=_user) | Q(
                owner__owner__parent__parent=_user)).exclude(owner__is_staff=True, owner__roles__role__title='agent')
        elif 'seller' in role_list:
            queryset = queryset.filter(Q(owner__owner=_user)).exclude(
                owner__is_staff=True, owner__roles__role__title__in=['agent', 'seller'])
        elif 'client' in role_list:
            queryset = queryset.filter(pk=-1)

        sh_me = queryset.filter(owner=_user)
        queryset = (queryset | sh_me).distinct()
        return queryset

    def filter_queryset(self, queryset):
        _filter = {}
        if 'owner' in self.request.query_params and self.request.query_params['owner']:
            _owner = self.request.query_params['owner']
            _filter.update({'owner_id': _owner})
        if 'feature' in self.request.query_params and self.request.query_params['feature']:
            _feature = self.request.query_params['feature']
            _filter.update({'feature_id': _feature})
        if 'service' in self.request.query_params and self.request.query_params['service']:
            _service = self.request.query_params['service']
            _filter.update({'feature__service_id': _service})

        queryset = queryset.filter(**_filter).distinct()
        return queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=AttributeFilterQuerySerializer)
    def list(self, request):
        """
        get list of Attribute API.

        ---

        """
        _queryset = self.get_queryset()
        _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        serializer.request = request
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('create'))
    # @execute_with_permission('Attribute', 'create')
    @transaction.atomic
    def create(self, request):
        """
        inset a Attribute API.

        ---

        """
        _data = get_dict_data(request.data)

        serializer = self.get_serializer(context={'request': request}, data=_data)
        serializer.request = request
        if serializer.is_valid():
            _object = serializer.save()
            serializer = AttributeInfoSerializer(instance=_object)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    def retrieve(self, request, pk=None):
        """
        get a Attribute API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('update'))
    # @execute_with_permission('Attribute', 'update')
    @transaction.atomic
    def partial_update(self, request, pk=None):
        """
        update a Attribute partial API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                    serializer = AttributeInfoSerializer(instance=_object)
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('delete'))
    # @execute_with_permission('Attribute', 'delete')
    @transaction.atomic
    def destroy(self, request, pk=None):
        """
        delete a Attribute  API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)


class BankView(BasicView):
    queryset = BankModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=BankSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Bank'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": BankInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':BankDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':BankInformationSerializer}
        elif action == 'partial_update':
            return {"200": BankInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return BankInformationSerializer
        elif self.action == 'delete':
            return BankDeleteSerializer
        elif self.action == "partial_update":
            return BankInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BankSerializer
        elif self.action == 'delete':
            return BankDeleteSerializer
        elif self.action in ['list','retrieve']:
            return BankInformationSerializer
        elif self.action == "partial_update":
            return BankUpdateSerializer
        elif self.action == "access":
            return BankAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=BankDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=BankFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class BannerView(BasicView): 
    queryset = BannerModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=BannerSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Banner'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": BannerInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':BannerDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':BannerInformationSerializer}
        elif action == 'partial_update':
            return {"200": BannerInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return BannerInformationSerializer
        elif self.action == 'delete':
            return BannerDeleteSerializer
        elif self.action == "partial_update":
            return BannerInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BannerSerializer
        elif self.action == 'delete':
            return BannerDeleteSerializer
        elif self.action in ['list','retrieve']:
            return BannerInformationSerializer
        elif self.action == "partial_update":
            return BannerUpdateSerializer
        elif self.action == "access":
            return BannerAccessSerializer
        elif self.action == "recycle":
            return BannerRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]        
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])
        if 'position' in self.request.query_params and self.request.query_params['position']:
            position = self.request.query_params['position']
            add_filter(filters,[{'position__icontains':position}])
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=BannerDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=BannerFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)

   
class BlogView(BasicView):
    queryset = BlogModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=BlogSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Blog'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": BlogInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':BlogDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':BlogInformationSerializer}
        elif action == 'partial_update':
            return {"200": BlogInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return BlogInformationSerializer
        elif self.action == 'delete':
            return BlogDeleteSerializer
        elif self.action == "partial_update":
            return BlogInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BlogSerializer
        elif self.action == 'delete':
            return BlogDeleteSerializer
        elif self.action in ['list','retrieve']:
            return BlogInformationSerializer
        elif self.action == "partial_update":
            return BlogUpdateSerializer
        elif self.action == "access":
            return BlogAccessSerializer
        elif self.action == "recycle":
            return BlogRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.select_related('owner','set').prefetch_related('tags')
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]    
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])
        if 'alias' in self.request.query_params and self.request.query_params['alias']:
            alias = self.request.query_params['alias']
            add_filter(filters,[{'alias__icontains': alias}])
        if 'set' in self.request.query_params and self.request.query_params['set']:
            set = self.request.query_params['set']
            add_filter(filters,[{'set__slug': set}])
        if 'tag' in self.request.query_params and self.request.query_params['tag']:
            tag = self.request.query_params['tag']
            add_filter(filters,[{'tags__title': tag}])

        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset

            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=BlogDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=BlogFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


    @swagger_auto_schema(operation_description=get_operation_description_schema('get'),responses={})
    @action(detail=False, methods=['get'], url_path='get/(?P<alias>[^/.]+)')
    def get(self, request, alias=None):
        """
        get a Blog API.

        ---

        """
        if alias:
            _object = self.get_queryset().filter(alias=alias)  # alias__icontains
            if _object:
                _object = _object.first()
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

   
    @swagger_auto_schema(operation_description=get_operation_description_schema('upload'),responses={})
    # @execute_with_permission('Blog', 'update')
    @action(detail=True, methods=['patch'],)
    @transaction.atomic
    def upload(self, request, pk=None):
        """
        upload icon for Blog API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                    serializer = BlogInformationSerializer(instance=_object)
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)


class CategoryView(BasicView):
    queryset = CategoryModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=CategorySerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Category'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": CategoryInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':CategoryDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':CategoryInformationSerializer}
        elif action == 'partial_update':
            return {"200": CategoryInformationSerializer, "400": {}} 
    
    def get_responses(self):
        if self.action == 'create':
            return CategoryInformationSerializer
        elif self.action == 'delete':
            return CategoryDeleteSerializer
        elif self.action == "partial_update":
            return CategoryInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve','category']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CategorySerializer
        elif self.action == 'delete':
            return CategoryDeleteSerializer
        elif self.action in ['list','retrieve','category']:
            return CategoryInformationSerializer
        elif self.action == "partial_update":
            return CategoryUpdateSerializer
        elif self.action == "access":
            return CategoryAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.select_related('parent').prefetch_related('groups')
        #Prefetch('groups',queryset=GroupMemberModel.objects.all()))
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]    
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])

        if 'group' in self.request.query_params and self.request.query_params['group']:
            group = self.request.query_params['group']
            add_filter(filters,[{'groups__group':group,'groups__group__status':1,'groups__group__is_delete':0}])
        
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    def get_object_with_slug(self, slug=None):
        if slug:
            try:
                return self.get_queryset().get(slug=slug,is_delete=0)
            except ObjectDoesNotExist:
                return None

    def group_post(self, groups, category_id):
        if groups:
            _models = []

            _objects = [str(i.group_id) for i in GroupMemberModel.objects.filter(
                category_id=category_id, group_id__in=groups)]
            if len(_objects) > 0:
                msg = 'categories [{0}] is exist ...'.format(
                    ','.join(_objects))
                raise ProjectException(840, 'validation error',
                                       msg,
                                       status.HTTP_400_BAD_REQUEST)

            for grp in groups:
                _data = {'category_id': group_id, 'group_id': grp}
                _models.append(GroupMemberModel(** _data))

            if _models:
                GroupMemberModel.objects.bulk_create(_models)
                return

        raise ProjectException(0, _('unkown error'),
                               _('unkown error'),
                               status.HTTP_400_BAD_REQUEST)

    def group_delete(self, groups, category_id):
        GroupMemberModel.objects.filter(
            group_id__in=groups, category_id=category_id).delete()
        return



    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=CategoryDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=CategoryFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


    @swagger_auto_schema(operation_description=get_operation_description_schema('upload'),responses={})
    # @execute_with_permission('Category', 'update')
    @action(detail=True, methods=['patch'],)
    @transaction.atomic
    def upload(self, request, pk=None):
        """
        upload icon for Category API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                    serializer = CategoryInfoSerializer(instance=_object)
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(operation_description='GET A server object with slug')
    @action(detail=False, url_path='slug/(?P<slug>[-\w]+)', methods=['get'])
    def category(self, request, slug=None):
        if type(slug) is int:
            return  super().retrieve(request, pk=slug)
        elif type(slug) is str:
            if obj := self.get_object_with_slug(slug):
                serializer = self.get_serializer(obj)
                serializer.request = request
                return Response(serializer.data, status=status.HTTP_200_OK)

            raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)


    @swagger_auto_schema(method='post', operation_description=get_operation_description_schema('privacy'),responses={})
    @swagger_auto_schema(method='delete', operation_description=get_operation_description_schema('privacy'),request_body=CategoryGroupSerializer, responses={})
    @action(detail=True, methods=['post', 'delete'])
    @transaction.atomic
    def group(self, request, pk=None):
        """
        add/delete groups a Group API.

        ---

        """
        _user = request.user
        if pk:
            _object = self.get_object(pk)
            _data = get_dict_data(request.data)

            if _object:
                _groups = []
                serializer = self.get_serializer(
                    context={'request': request}, data=_data)
                serializer.request=request
                if serializer.is_valid():
                    _groups = _data.get('groups', None)
                else:
                    raise ProjectException(831, 'validate error',
                                           serializer.errors,
                                           status.HTTP_404_NOT_FOUND)

                if request.method == 'POST':

                    self.group_post(_groups, _object.pk)
                    serializer = CategoryInfoSerializer(instance=_object)
                    return Response(serializer.data, status=status.HTTP_200_OK)

                elif request.method == 'DELETE':
                    self.group_delete(_groups, _object.pk)
                    return Response(status=status.HTTP_204_NO_CONTENT)

            else:
                raise ProjectException(0, _('not found error'),
                                       _('not found error'),
                                       status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(0, _('not found error'),
                                   _('not found error'),
                                   status.HTTP_404_NOT_FOUND)


class CommissionView(BasicView):
    queryset = CommissionModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=CommissionSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Commission'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": CommissionInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':CommissionDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':CommissionInformationSerializer}
        elif action == 'partial_update':
            return {"200": CommissionInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return CommissionInformationSerializer
        elif self.action == 'delete':
            return CommissionDeleteSerializer
        elif self.action == "partial_update":
            return CommissionInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CommissionSerializer
        elif self.action == 'delete':
            return CommissionDeleteSerializer
        elif self.action in ['list','retrieve']:
            return CommissionInformationSerializer
        elif self.action == "partial_update":
            return CommissionUpdateSerializer
        elif self.action == "access":
            return CommissionAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filter={} 
        if 'owner' in self.request.query_params and self.request.query_params['owner']:
            owner = self.request.query_params['owner']
            filter.update({'owner': owner})
        if 'service' in self.request.query_params and self.request.query_params['service']:
            service = self.request.query_params['service']
            filter.update({'service': service})
        if 'company' in self.request.query_params and self.request.query_params['company']:
            company = self.request.query_params['company']
            filter.update({'service__company_id': company})
        if 'category' in self.request.query_params and self.request.query_params['category']:
            category = self.request.query_params['category']
            filter.update({'service__category_id': category})

        if 'status' in self.request.query_params and self.request.query_params['status']:
            status = get_dict_data(self.request.GET).get('status', None)
            if type(status) != type([]):
                status = [status, ]
            status_filter= get_status(status)
            filter.update(status_filter)
        else:
            filter.update({'status__in': [0, 1],'is_delete':0})

        queryset = queryset.filter(** filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=CommissionDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=CommissionFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


    @action(detail=False, methods=['post'])
    @transaction.atomic
    def agent(self, request):
        """
        Agent Commission API.

        ---

        """
        _data = get_dict_data(request.data)
        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            serializer = SettingInfoSerializer(serializer.save())
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def seller(self, request):
        """
        Seller Commission API.

        ---

        """
        _data = get_dict_data(request.data)
        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            serializer = SettingInfoSerializer(serializer.save())
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    @transaction.atomic
    def setting(self, request):
        """
        Setting Commission API.

        ---

        """
        from django.conf import settings
        _query = SettingModel.objects.filter(
            key__in=[settings.AGENT_COMMISSION_TAG, settings.SELLER_COMMISSION_TAG])
        serializer = SettingInfoSerializer(_query, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompanyView(BasicView):

    queryset = CompanyModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=CompanySerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Company'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": CompanyInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':CompanyDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':CompanyInformationSerializer}
        elif action == 'partial_update':
            return {"200": CompanyInformationSerializer, "400": {}} 
    
    def get_responses(self):
        if self.action == 'create':
            return CompanyInformationSerializer
        elif self.action == 'delete':
            return CompanyDeleteSerializer
        elif self.action == "partial_update":
            return CompanyInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve','company']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CompanySerializer
        elif self.action == 'delete':
            return CompanyDeleteSerializer
        elif self.action in ['list','retrieve','company']:
            return CompanyInformationSerializer
        elif self.action == "partial_update":
            return CompanyUpdateSerializer
        elif self.action == "access":
            return CompanyAccessSerializer
        elif self.action == "recycle":
            return CompanyRecycleSerializer

        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]    
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])

               
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    def get_object_with_slug(self, slug=None):
        if slug:
            try:
                return self.get_queryset().get(slug=slug,is_delete=0)
            except ObjectDoesNotExist:
                return None

    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=CompanyDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=CompanyFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        if type(pk) is int:
            return  super().retrieve(request, pk=pk)
        elif type(pk) is str:
            slug=pk
            if obj := self.get_object_with_slug(slug):
                serializer = self.get_serializer(obj)
                serializer.request = request
                return Response(serializer.data, status=status.HTTP_200_OK)

            raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)


    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)

    @swagger_auto_schema(method='get')
    @action(detail=False, methods=['get'])
    def company(self, request, slug=None):
        if type(slug) is int:
            return  super().retrieve(request, pk=slug)
        elif type(slug) is str:
            if obj := self.get_object_with_slug(slug):
                serializer = self.get_serializer(obj)
                serializer.request = request
                return Response(serializer.data, status=status.HTTP_200_OK)

            raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)

       
class DefaultViewSet(viewsets.GenericViewSet):
    queryset = UserModel.objects.all()

    def get_response_schema(action):
        # response_schema_dict
        rsd = {
            "200":
            LoginSerializer,
            "200_user":
            UserSchemaSerializer,
            "201":
            UserSchemaSerializer,
            "201_refresh":
            RefreshTokenSerializer,
            "400_login":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "802": {
                            "status": "failed",
                            "code": 802,
                            "message": "vauthentication error",
                            "detail": "You are not active on the system.",
                        },
                    }
                },
            ),
            "400_reg":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "808": {
                            "status": "failed",
                            "code": 808,
                            "message": "validation error",
                            "detail": "Cellphone exist.",
                        },
                        "809": {
                            "status": "failed",
                            "code": 809,
                            "message": "validation error",
                            "detail": "Email exist.",
                        },
                        "810": {
                            "status": "failed",
                            "code": 810,
                            "message": "validation error",
                            "detail": "Username exist.",
                        },
                        "811": {
                            "status": "failed",
                            "code": 811,
                            "message": "validation error",
                            "detail": "Username cannot les than 4 digit.",
                        },
                        "812": {
                            "status": "failed",
                            "code": 812,
                            "message": "validation error",
                            "detail": "password cannot les than 8 digit.",
                        },
                        "846": {
                            "status": "failed",
                            "code": 846,
                            "message": "validation error",
                            "detail": "Set the role.",
                        },
                        "852": {
                            "status": "failed",
                            "code": 852,
                            "message": "runtime error",
                            "detail": "role error.",
                        },
                    }
                },
            ),
            "400_change_pass":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "805": {
                            "status": "failed",
                            "code": 805,
                            "message": "change password",
                            "detail": "Wrong password.",
                        },
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "812": {
                            "status": "failed",
                            "code": 812,
                            "message": "validation error",
                            "detail": "password cannot less than 8 digit.",
                        },
                    }
                },
            ),
            "401":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                        "803": {
                            "status": "failed",
                            "code": 803,
                            "message": "authentication error",
                            "detail": "You will not be able to access the system until t time.",
                        },
                        "804": {
                            "status": "failed",
                            "code": 804,
                            "message": "authentication error",
                            "detail": "You have been disabled by the system for security reasons.",
                        },
                    }
                },
            ),
            "401":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                        "803": {
                            "status": "failed",
                            "code": 803,
                            "message": "authentication error",
                            "detail": "You will not be able to access the system until t time.",
                        },
                        "804": {
                            "status": "failed",
                            "code": 804,
                            "message": "authentication error",
                            "detail": "You have been disabled by the system for security reasons.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "401_refresh":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                    }
                },
            ),

            "200_logout":
            openapi.Response(
                description="OK",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "200": {
                            "status": "success",
                            "code": 200,
                            "message": _("token burned"),
                            "detail": _("Logout user."),
                        },
                    }
                },
            ),
            "200_change_pass":
            openapi.Response(
                description="OK",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "200": {
                            "status": "success",
                            "code": 200,
                            "message": "_('password updated successfully')",
                            "detail": "Change password.",
                        },
                    }
                },
            ),
            "204_logout":
            openapi.Response(
                description="NO_CONTENT",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "204": {
                            "status": "failed",
                            "code": 204,
                            "message": _("not login before"),
                            "detail": _("User has not logged in before."),
                        },
                    }
                },
            ),
        }
        responses = dict()
        if action == "login":
            responses = {"200": rsd["200"],
                         "401": rsd["401"], "400": rsd["400_login"]}
        elif action in ["logout_get", "logout_post"]:
            responses = {"200": rsd["200_logout"],
                         "204": rsd["204_logout"], "401": rsd["401_token"]}
        elif action == "changepassword":
            responses = {"200": rsd["200_change_pass"],
                         "400": rsd["400_change_pass"], "401": rsd["401_token"]}
        elif action == "create":
            responses = {"201": rsd["200_user"], "400": rsd["400_reg"]}
        elif action == "refresh_token":
            responses = {"201": rsd["201_refresh"],
                         "400": rsd["807"], "401": rsd["401_refresh"]}
        return responses

    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegisterSerializer
        elif self.action == 'login':
            return LoginSerializer
        elif self.action == 'logout':
            return NoneSerializer
        elif self.action == 'changepassword':
            return UserChangePasswordSerializer
        elif self.action == 'refresh_token':
            return RefreshTokenSerializer
        elif self.action == 'deposit':
            return DepositSerializer
        elif self.action == 'sms':
            return SmsSerializer
        elif self.action == "reset_password":
            return UserResetPasswordSerializer
        elif self.action == "reset":
            return UserResetSerializer

    def get_permissions(self):
        if self.action in ['register', 'login', 'refresh_token','sms','reset_password','reset']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    @swagger_auto_schema(responses=get_response_schema('create'))
    @transaction.atomic
    # ,url_path='(?P<role>[\w\-]+)/register')
    @action(detail=False, methods=["post"])
    def register(self, request):
        data = get_dict_data(request.data)
        serializer = self.get_serializer(data=data)
        serializer.request=request
        if serializer.is_valid():
            obj = serializer.save()
            serializer = UserInformationSerializer(instance=obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(807,
                                   _('validation error'), serializer.errors,
                                   status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('login'))
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        login.

        ---
        username = [username,]
        """
        _chk = False
        serializer = self.get_serializer(data=request.data)
        serializer.request=request
        if serializer.is_valid():
            _data = serializer.validated_data
            _chk, _user, _access_token, _refresh_token = signin(
                request, data=_data)
        else:
            raise ProjectException(807, _('validation error'),
                                   serializer.errors,
                                   status.HTTP_400_BAD_REQUEST)

        if _chk:
            _user.login_error = 0
            _user.deactive_expire = None
            _user.save()

            registration_id = request.data.get('firebase', None)
            if registration_id:
                _token = TokenModel.objects.filter(
                    key=_access_token, user=_user)
                if _token:
                    _device_id = _token.first().player_id
                    try:
                        _device = FCMDevice.objects.get(
                            user=_user, device_id=_device_id)
                        _device.registration_id = registration_id
                        _device.save()
                    except ObjectDoesNotExist:
                        FCMDevice.objects.create(
                            user=_user, device_id=_device_id, registration_id=registration_id)

            serializer = LoginSerializer(_user, many=False)
            _data = {'access_token': _access_token,
                     'refresh_token': _refresh_token}
            for attr, value in serializer.data.items():
                _data[attr] = value

            _response = Response(_data, status=status.HTTP_200_OK)
            _response.set_cookie(key='access_token', value=_access_token)
            return _response
        else:
            # return Response(status.HTTP_401_UNAUTHORIZED)
            raise ProjectException(801, _('authentication error'),
                                   _('Authentication error'),
                                   status.HTTP_401_UNAUTHORIZED)

    # @swagger_auto_schema(methods=["get"],responses=get_response_schema('logout_get'))

    @swagger_auto_schema(methods=["post"],
                         responses=get_response_schema('logout_post'))
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        logout.

        ---

        """
        _user = request.user
        if _user:
            signout(request)
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': _('token burned'),
                "detail": _("Logout user."),
            }
        else:
            response = {
                'status': 'failed',
                'code': status.HTTP_204_NO_CONTENT,
                'message': _('not login before'),
                "detail": _("User has not logged in before."),
            }
        return Response(response)

    @swagger_auto_schema(responses=get_response_schema('changepassword'))
    @action(detail=False, methods=['post'])
    def changepassword(self, request):
        """
        change password for current user.
        ---
        """

        serializer = self.get_serializer(context={'request': request}, data=request.data)
        serializer.request=request
        if serializer.is_valid():
            serializer.save()
            response = {
                "status": _("success"),
                "code": status.HTTP_200_OK,
                "message": _('password updated successfully'),
                "detail": _("Change password."),
            }
            return Response(response, status=status.HTTP_200_OK)
        else:
            raise ProjectException(807, _('validation error'),
                                   serializer.errors,
                                   status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('refresh_token'))
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def refresh_token(self, request):
        """
        create Access Token API.

        ---

        """
        data = get_dict_data(request.data)
        serializer = self.get_serializer(context={'request': request}, data=data)
        if not serializer.is_valid():
            raise ProjectException(807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def deposit(self, request):
        """
        deposit API.

        ---

        """
        data = get_dict_data(request.data)
        serializer = self.get_serializer(context={'request': request}, data=data)
        serializer.request=request
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            raise ProjectException(807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['post'])
    def sms(self, request):
      
        import requests
        import json
        import re
        data = get_dict_data(request.data)
        url = "https://ippanel.com//api/select"
        username = "mysms-tehran"
        password = "OO73988oo@@"
        sender_one = "5000125475"
        sender_two = "3000505"
        if type(data['cellphone']) != type([]):
            cellphone = [data['cellphone']]
        
    
        _data = {   "op":"send",
                    "uname":username,
                    "pass":	password,
                    "message":data['msg'],
                    "from":sender_one,
                    "to":cellphone
                }
        _headers = {"Content-type": "application/json"}
        _response = requests.post(url, json=_data, headers=_headers)
        if re.match(r'^\[0,',_response.text):
            return Response({"result": _response.text, "status": _response.status_code})
        else:
            _data.pop('from',None)
            _data['from'] = sender_two
            _response = requests.post(url, json=_data, headers=_headers)
            if re.match(r'^\[0,',_response.text):
                return Response({"result": _response.text, "status": _response.status_code})
            else:
                return Response({"result": _response.text, "status": _response.status_code})

    @action(detail=False, methods=['post'])
    def reset_password(self,request):
        serializer = self.get_serializer(
            context={'request': request}, data=request.data)
        if not serializer.is_valid():
            raise ProjectException(807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({},status=status.HTTP_200_OK)


    @action(detail=False, methods=['post'])
    def reset(self,request):
        serializer = self.get_serializer(context={'request': request}, data=request.data)
        if not serializer.is_valid():
            raise ProjectException(807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({},status=status.HTTP_200_OK)

            
class DocumentViewSet(BasicView):
    queryset = DocumentModel.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = ([IsAuthenticated])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        # (hasattr(self,'name') and self.name in ["Upload",])
        action_map = list(self.action_map.values())
        _action = ["some", "status", "trash", "recycle"]
        if any(item in action_map for item in _action):
            # if ["some","status"] in action_map
            parser_classes = [JSONParser]
        elif ("upload" in action_map):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [MultiPartParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            DocumentSchemaSerializer,
            "200_OK":
            openapi.Response({}),
            "201":
            DocumentSchemaSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_some":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_status":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "827": {
                            "status": "failed",
                            "code": 827,
                            "message": "validation error",
                            "detail": "Status field is Invalid.",
                        },
                    }
                },
            ),
            "404_multi":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "811": {
                            "status": "failed",
                            "code": 845,
                            "message": "not found",
                            "detail": "Some users are not in the system.",
                        },
                        "819": {
                            "status": "failed",
                            "code": 819,
                            "message": "not found",
                            "detail": "Primary keys list is empty.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer,
            "200_some":
            SampleSomeVirResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"], "400": rsd["807"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"],
                         "400": rsd["400"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAuthenticated, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return DocumentInfoSerializer
        elif self.action in ['partial_update']:
            return DocumentUpdateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = self.queryset
        _user = self.request.user
        role_list = get_user_roles(_user)
        if not _user.pk:
            queryset = queryset.filter(pk=-1)
        elif _user.is_superuser:  # superuser
            queryset = queryset.filter(owner__is_superuser=False)
        elif _user.is_staff:  # admin
            queryset = queryset.filter(owner__is_staff=False)
        elif 'agent' in role_list:  # agent
            queryset = queryset.filter(Q(owner__owner=_user) | Q(owner__parent__parent=_user) | Q(
                owner__owner__parent__parent=_user)).exclude(owner__is_staff=True, owner__roles__role__title='agent')
        elif 'seller' in role_list:
            queryset = queryset.filter(Q(owner__owner=_user)).exclude(
                owner__is_staff=True, owner__roles__role__title__in=['agent', 'seller'])
        elif 'client' in role_list:
            queryset = queryset.filter(pk=-1)

        sh_me = queryset.filter(owner=_user)
        queryset = (queryset | sh_me).distinct()
        return queryset

    def filter_queryset(self, queryset):
        _filter = {}
        if 'owner' in self.request.query_params and self.request.query_params['owner']:
            _owner = self.request.query_params['owner']
            _filter.update({'owner_id': _owner})
        if 'record' in self.request.query_params and self.request.query_params['record']:
            _record = self.request.query_params['record']
            _filter.update({'record_id': _record})
        if 'service' in self.request.query_params and self.request.query_params['service']:
            _service = self.request.query_params['service']
            _filter.update({'record__service_id': _service})
        
        queryset = queryset.filter(**_filter).distinct()
        return queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=DocumentFilterQuerySerializer)
    def list(self, request):
        """
        get list of Document API.

        ---

        """
        _queryset = self.get_queryset()
        _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('create'))
    # @execute_with_permission('Document', 'create')
    @transaction.atomic
    def create(self, request):
        """
        inset a Document API.

        ---

        """
        _data = get_dict_data(request.data)

        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            _object = serializer.save()
            serializer = DocumentInfoSerializer(instance=_object)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    def retrieve(self, request, pk=None):
        """
        get a Document API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('update'))
    # @execute_with_permission('Document', 'update')
    @transaction.atomic
    def partial_update(self, request, pk=None):
        """
        update a Document partial API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                    serializer = DocumentInfoSerializer(instance=_object)
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('delete'))
    # @execute_with_permission('Document', 'delete')
    @transaction.atomic
    def destroy(self, request, pk=None):
        """
        delete a Document  API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)


class EvidenceView(BasicView):
    queryset = EvidenceModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=EvidenceSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Evidence'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": EvidenceInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':EvidenceDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':EvidenceInformationSerializer}
        elif action == 'partial_update':
            return {"200": EvidenceInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return EvidenceInformationSerializer
        elif self.action == 'delete':
            return EvidenceDeleteSerializer
        elif self.action == "partial_update":
            return EvidenceInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EvidenceSerializer
        elif self.action == 'delete':
            return EvidenceDeleteSerializer
        elif self.action in ['list','retrieve']:
            return EvidenceInformationSerializer
        elif self.action == "partial_update":
            return EvidenceUpdateSerializer
        elif self.action == "access":
            return EvidenceAccessSerializer
        elif self.action == "recycle":
            return EvidenceRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filter={} 
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            filter.update({'title__icontains': search})
        if 'media' in self.request.query_params and self.request.query_params['media']:
            media = self.request.query_params['media']
            filter.update({'media': media})



        if 'status' in self.request.query_params and self.request.query_params['status']:
            status = get_dict_data(self.request.GET).get('status', None)
            if type(status) != type([]):
                status = [status, ]
            status_filter= get_status(status)
            filter.update(status_filter)
        else:
            filter.update({'status__in': [0, 1],'is_delete':0})

       
        
            

        queryset = queryset.filter(** filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=EvidenceDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=EvidenceFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class FaqCategoryView(BasicView):
    queryset = FaqCategoryModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=FaqCategorySerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='FaqCategory'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": FaqCategoryInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':FaqCategoryDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':FaqCategoryInformationSerializer}
        elif action == 'partial_update':
            return {"200": FaqCategoryInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return FaqCategoryInformationSerializer
        elif self.action == 'delete':
            return FaqCategoryDeleteSerializer
        elif self.action == "partial_update":
            return FaqCategoryInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve','faq_category']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FaqCategorySerializer
        elif self.action == 'delete':
            return FaqCategoryDeleteSerializer
        elif self.action in ['list','retrieve','faq_category']:
            return FaqCategoryInformationSerializer
        elif self.action == "partial_update":
            return FaqCategoryUpdateSerializer
        elif self.action == "access":
            return FaqCategoryAccessSerializer
        elif self.action == "recycle":
            return FaqCategoryRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filter={} 
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            filter.update({'title__icontains': search})
        
        if 'status' in self.request.query_params and self.request.query_params['status']:
            status = get_dict_data(self.request.GET).get('status', None)
            if type(status) != type([]):
                status = [status, ]
            status_filter= get_status(status)
            filter.update(status_filter)
        else:
            filter.update({'status__in': [0, 1],'is_delete':0})

       
        
            

        queryset = queryset.filter(** filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    def get_object_with_slug(self, slug=None):
        if slug:
            try:
                return self.get_queryset().get(slug=slug,is_delete=0)
            except ObjectDoesNotExist:
                return None

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=FaqCategoryDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=FaqCategoryFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)

    @swagger_auto_schema(operation_description='GET get A service object with slug')
    @action(detail=False, url_path='slug/(?P<slug>[-\w]+)', methods=['get'])
    def faq_category(self, request, slug=None):
        if type(slug) is int:
            return  super().retrieve(request, pk=slug)
        elif type(slug) is str:
            if obj := self.get_object_with_slug(slug):
                serializer = self.get_serializer(obj)
                serializer.request = request
                return Response(serializer.data, status=status.HTTP_200_OK)

            raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)


class FaqView(BasicView):
    queryset = FaqModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=FaqSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Faq'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": FaqInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':FaqDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':FaqInformationSerializer}
        elif action == 'partial_update':
            return {"200": FaqInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return FaqInformationSerializer
        elif self.action == 'delete':
            return FaqDeleteSerializer
        elif self.action == "partial_update":
            return FaqInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FaqSerializer
        elif self.action == 'delete':
            return FaqDeleteSerializer
        elif self.action in ['list','retrieve']:
            return FaqInformationSerializer
        elif self.action == "partial_update":
            return FaqUpdateSerializer
        elif self.action == "access":
            return FaqAccessSerializer
        elif self.action == "recycle":
            return FaqRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.select_related('category')
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[] 
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])
        if 'category' in self.request.query_params and self.request.query_params['category']:
            category = self.request.query_params['category']
            add_filter(filters,[{'category': category}])

        if 'category_slug' in self.request.query_params and self.request.query_params['category_slug']:
            category_slug = self.request.query_params['category_slug']
            add_filter(filters,[{'category__slug': category_slug}])
        
        add_filter(filters,get_status_filter(self.request))
        add_filter(filters,[{'category__status':1,'category__is_delete':0}])
    
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=FaqDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=FaqFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class FeatureViewSet(viewsets.GenericViewSet):
    queryset = FeatureModel.objects.all()
    serializer_class = FeatureInfoSerializer
    permission_classes = ([IsAuthenticated])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        # (hasattr(self,'name') and self.name in ["Upload",])
        action_map = list(self.action_map.values())
        _action = ["some", "status", "trash", "recycle"]
        if any(item in action_map for item in _action):
            # if ["some","status"] in action_map
            parser_classes = [JSONParser]
        elif ("upload" in action_map):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            FeatureSchemaSerializer,
            "200_OK":
            openapi.Response({}),
            "201":
            FeatureSchemaSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_some":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_status":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "827": {
                            "status": "failed",
                            "code": 827,
                            "message": "validation error",
                            "detail": "Status field is Invalid.",
                        },
                    }
                },
            ),
            "404_multi":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "811": {
                            "status": "failed",
                            "code": 845,
                            "message": "not found",
                            "detail": "Some users are not in the system.",
                        },
                        "819": {
                            "status": "failed",
                            "code": 819,
                            "message": "not found",
                            "detail": "Primary keys list is empty.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer,
            "200_some":
            SampleSomeVirResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"], "400": rsd["807"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"],
                         "400": rsd["400"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAdminUser, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return FeatureInfoSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = self.queryset
        _user = self.request.user
        list_role = get_user_roles(_user)

        return queryset

    def filter_queryset(self, queryset):
        _filter = {}
        if 'service' in self.request.query_params and self.request.query_params['service']:
            _service = self.request.query_params['service']
            _filter.update({'service_id': _service})
        if 'property' in self.request.query_params and self.request.query_params['property']:
            _property = self.request.query_params['property']
            _filter.update({'property_id': _property})
        queryset = queryset.filter(**_filter).distinct()
        return queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=FeatureFilterQuerySerializer)
    def list(self, request):
        """
        get list of Feature API.

        ---

        """
        _queryset = self.get_queryset()
        _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    def retrieve(self, request, pk=None):
        """
        get a Feature API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

# Grade
class GradeView(BasicView):
    queryset = GradeModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=GradeSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Grade'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": GradeInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':GradeDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':GradeInformationSerializer}
        elif action == 'partial_update':
            return {"200": GradeInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return GradeInformationSerializer
        elif self.action == 'delete':
            return GradeDeleteSerializer
        elif self.action == "partial_update":
            return GradeInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return GradeSerializer
        elif self.action == 'delete':
            return GradeDeleteSerializer
        elif self.action in ['list','retrieve']:
            return GradeInformationSerializer
        elif self.action == "partial_update":
            return GradeUpdateSerializer
        elif self.action == "access":
            return GradeAccessSerializer
        elif self.action == "recycle":
            return GradeRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filter={} 
        
        if 'status' in self.request.query_params and self.request.query_params['status']:
            status = get_dict_data(self.request.GET).get('status', None)
            if type(status) != type([]):
                status = [status, ]
            status_filter= get_status(status)
            filter.update(status_filter)
        else:
            filter.update({'status__in': [0, 1],'is_delete':0})

       
        
            

        queryset = queryset.filter(** filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=GradeDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=GradeFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class GroupView(BasicView):
    queryset = GroupModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=GroupSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Group'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": GroupInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':GroupDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':GroupInformationSerializer}
        elif action == 'partial_update':
            return {"200": GroupInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return GroupInformationSerializer
        elif self.action == 'delete':
            return GroupDeleteSerializer
        elif self.action == "partial_update":
            return GroupInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return GroupSerializer
        elif self.action == 'delete':
            return GroupDeleteSerializer
        elif self.action in ['list','retrieve']:
            return GroupInformationSerializer
        elif self.action == "partial_update":
            return GroupUpdateSerializer
        elif self.action == "access":
            return GroupAccessSerializer
        elif self.action == "recycle":
            return GroupRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])
        if 'category' in self.request.query_params and self.request.query_params['category']:
            category = self.request.query_params['category']
            add_filter(filters,[{'categories__category':category,'categories__category__status':1,'categories__category__is_delete':0}])
        
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset           
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

   
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=GroupDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=GroupFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)

    @swagger_auto_schema(method='post', operation_description=get_operation_description_schema('privacy'),responses={})
    @transaction.atomic
    @action(detail=True, methods=['post'])
    def category_post(self, categories, group_id):
        if categories:
            _models = []

            _objects = [str(i.category_id) for i in GroupMemberModel.objects.filter(
                group_id=group_id, category_id__in=categories)]
            if len(_objects) > 0:
                msg = 'categories [{0}] is exist ...'.format(
                    ','.join(_objects))
                raise ProjectException(840, 'validation error',
                                       msg,
                                       status.HTTP_400_BAD_REQUEST)

            for cat in categories:
                _data = {'group_id': group_id, 'category_id': cat}
                _models.append(GroupMemberModel(** _data))

            if _models:
                GroupMemberModel.objects.bulk_create(_models)
                return

        raise ProjectException(0, _('unkown error'),
                               _('unkown error'),
                               status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(method='delete', operation_description=get_operation_description_schema('privacy'),responses={})
    @action(detail=True, methods=['delete'])
    def category_delete(self, categories, group_id):
        GroupMemberModel.objects.filter(
            category_id__in=categories, group_id=group_id).delete()
        return


class OperateViewSet(viewsets.GenericViewSet):
    queryset = OperateModel.objects.all()
    serializer_class = OperateSerializer
    permission_classes = ([IsAdminUser])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        if (hasattr(self, 'action') and self.action in ["upload", ]) or (hasattr(self, 'name') and self.name in ["Upload", ]):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            OperateSerializer,
            "200_Ok":
            openapi.Response({}),
            "201":
            OperateSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"], "400": rsd["400"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAdminUser, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        return super().get_serializer_class()

    def get_queryset(self):
        return super().get_queryset()

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'))
    # @execute_with_permission('operate', 'list')
    def list(self, request):
        """
        get list of Operate API.

        ---

        """
        _queryset = self.get_queryset().order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('create'))
    # @execute_with_permission('operate', 'create')
    @transaction.atomic
    def create(self, request):
        """
        inset a Operate API.

        ---

        """
        _data = get_dict_data(request.data)
        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    # @execute_with_permission('operate', 'read')
    def retrieve(self, request, pk=None):
        """
        get a Operate API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('update'))
    # @execute_with_permission('operate', 'update')
    @transaction.atomic
    def partial_update(self, request, pk=None):
        """
        update a Operate partial API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('delete'))
    # @execute_with_permission('operate', 'delete')
    @transaction.atomic
    def destroy(self, request, pk=None):
        """
        delete a Operate  API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

#porsant
class PorsantView(BasicView):

    queryset = PorsantModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=PorsantSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Porsant'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": PorsantInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':PorsantDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':PorsantInformationSerializer}
        elif action == 'partial_update':
            return {"200": PorsantInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return PorsantInformationSerializer
        elif self.action == 'delete':
            return PorsantDeleteSerializer
        elif self.action == "partial_update":
            return PorsantInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PorsantSerializer
        elif self.action == 'delete':
            return PorsantDeleteSerializer
        elif self.action in ['list','retrieve']:
            return PorsantInformationSerializer
        elif self.action == "partial_update":
            return PorsantUpdateSerializer
        elif self.action == "access":
            return PorsantAccessSerializer
        elif self.action == "recycle":
            return PorsantRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.select_related('company','service','category','grade','role','owner')
        return queryset
    
    def get_object(self,pk=None):
        if pk:
            with contextlib.suppress(ObjectDoesNotExist):
                return self.get_queryset().get(pk=pk)
    
    def filter_queryset(self, queryset):  
        filter={} 
        
        

       
        
            

        queryset = queryset.filter(** filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=PorsantDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=PorsantFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class PropertyViewSet(viewsets.GenericViewSet):
    queryset = PropertyModel.objects.all()
    serializer_class = PropertySerializer
    permission_classes = ([IsAuthenticated])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        # (hasattr(self,'name') and self.name in ["Upload",])
        action_map = list(self.action_map.values())
        _action = ["some", "status", "trash", "recycle"]
        if any(item in action_map for item in _action):
            # if ["some","status"] in action_map
            parser_classes = [JSONParser]
        elif ("upload" in action_map):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            PropertySchemaSerializer,
            "200_OK":
            openapi.Response({}),
            "201":
            PropertySchemaSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_some":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_status":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "827": {
                            "status": "failed",
                            "code": 827,
                            "message": "validation error",
                            "detail": "Status field is Invalid.",
                        },
                    }
                },
            ),
            "404_multi":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "811": {
                            "status": "failed",
                            "code": 845,
                            "message": "not found",
                            "detail": "Some users are not in the system.",
                        },
                        "819": {
                            "status": "failed",
                            "code": 819,
                            "message": "not found",
                            "detail": "Primary keys list is empty.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer,
            "200_some":
            SampleSomeVirResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"], "400": rsd["807"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"],
                         "400": rsd["400"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAdminUser, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return PropertyInfoSerializer
        elif self.action in ['partial_update']:
            return PropertyUpdateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = self.queryset
        _user = self.request.user
        list_role = get_user_roles(_user)

        return queryset

    def filter_queryset(self, queryset):
        _filter = {}
        if 'search' in self.request.query_params and self.request.query_params['search']:
            _search = self.request.query_params['search']
            _filter.update({'title__icontains': _search})
        if 'type' in self.request.query_params and self.request.query_params['type']:
            _type = self.request.query_params['type']
            _filter.update({'type': _type})
        queryset = queryset.filter(**_filter).distinct()
        return queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=PropertyFilterQuerySerializer)
    def list(self, request):
        """
        get list of Property API.

        ---

        """
        _queryset = self.get_queryset()
        _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('create'))
    # @execute_with_permission('Property', 'create')
    @transaction.atomic
    def create(self, request):
        """
        inset a Property API.

        ---

        """
        _data = get_dict_data(request.data)

        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            _object = serializer.save()
            serializer = PropertyInfoSerializer(instance=_object)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    def retrieve(self, request, pk=None):
        """
        get a Property API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('update'))
    # @execute_with_permission('Property', 'update')
    @transaction.atomic
    def partial_update(self, request, pk=None):
        """
        update a Property partial API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                    serializer = PropertyInfoSerializer(instance=_object)
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('delete'))
    # @execute_with_permission('Property', 'delete')
    @transaction.atomic
    def destroy(self, request, pk=None):
        """
        delete a Property  API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)


class RecordViewSet(viewsets.GenericViewSet):
    queryset = RecordModel.objects.all()
    serializer_class = RecordInfoSerializer
    permission_classes = ([IsAuthenticated])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        # (hasattr(self,'name') and self.name in ["Upload",])
        action_map = list(self.action_map.values())
        _action = ["some", "status", "trash", "recycle"]
        if any(item in action_map for item in _action):
            # if ["some","status"] in action_map
            parser_classes = [JSONParser]
        elif ("upload" in action_map):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            RecordSchemaSerializer,
            "200_OK":
            openapi.Response({}),
            "201":
            RecordSchemaSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_some":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_status":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "827": {
                            "status": "failed",
                            "code": 827,
                            "message": "validation error",
                            "detail": "Status field is Invalid.",
                        },
                    }
                },
            ),
            "404_multi":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "811": {
                            "status": "failed",
                            "code": 845,
                            "message": "not found",
                            "detail": "Some users are not in the system.",
                        },
                        "819": {
                            "status": "failed",
                            "code": 819,
                            "message": "not found",
                            "detail": "Primary keys list is empty.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer,
            "200_some":
            SampleSomeVirResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"], "400": rsd["807"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"],
                         "400": rsd["400"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAdminUser, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecordInfoSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = self.queryset
        _user = self.request.user
        list_role = get_user_roles(_user)

        return queryset

    def filter_queryset(self, queryset):
        _filter = {}
        if 'service' in self.request.query_params and self.request.query_params['service']:
            _service = self.request.query_params['service']
            _filter.update({'service_id': _service})
        if 'evidence' in self.request.query_params and self.request.query_params['evidence']:
            _evidence = self.request.query_params['evidence']
            _filter.update({'evidence_id': _evidence})
        queryset = queryset.filter(**_filter).distinct()
        return queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=RecordFilterQuerySerializer)
    def list(self, request):
        """
        get list of Record API.

        ---

        """
        _queryset = self.get_queryset()
        _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    def retrieve(self, request, pk=None):
        """
        get a Record API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)


class RoleViewSet(viewsets.GenericViewSet):
    queryset = RoleModel.objects.all()
    serializer_class = RoleSerializer
    permission_classes = ([IsAdminUser])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        if (hasattr(self, 'action') and self.action in ["upload", ]) or (hasattr(self, 'name') and self.name in ["Upload", ]):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            RoleInfoSerializer,
            "200_Ok":
            openapi.Response({}),
            "201":
            RoleSerializer,
            "201_permission":
            RolesPermissionsSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "get":
            RoleInfoGetSerializer,
            "sample":
            SampleResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"], "400": rsd["400"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        elif action == "update":
            responses = {
                "200": rsd["200"], "401": rsd["401_token"], "404": rsd["404"], "400": rsd["400"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        elif action in ["get"]:
            responses = {"200": rsd["get"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action in ["permission"]:
            responses = {"201": rsd["200_Ok"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "operate":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        elif action == "state":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAdminUser, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve', ]:
            return RoleInfoSerializer
        elif self.action == 'get':
            return RoleInfoGetSerializer
        elif self.action == 'permission':
            return RolesPermissionsSerializer
        elif self.action == 'single_permission':
            return NoneSerializer
        elif self.action in ['operate', 'state']:
            return NoneSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        _queryset = self.queryset.exclude(title="superuser")
        _user = self.request.user
        user_role = get_user_roles(_user)
        if not _user.pk:
            _queryset = _queryset.filter(pk=-1)
        elif _user.is_superuser:
            pass
        elif "admin" in user_role:
            _queryset = _queryset.exclude(title="admin")
        elif "personnel" in user_role:
            _queryset = _queryset.exclude(title__in=["admin", "personnel"])
        elif "agent" in user_role:
            _queryset = _queryset.filter(title__in=["seller", "client"])
        elif "seller" in user_role:
            _queryset = _queryset.filter(title__in=["client"])
        else:
            _queryset = _queryset.filter(pk=-1)
        return _queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    def get_object_access(self, pk=None):
        if pk:
            try:
                _object = RoleAccessModel.objects.get(pk=pk)
                return _object
            except RoleAccessModel.DoesNotExist:
                return None

    def get_object_permission(self, pk=None):
        if pk:
            try:
                _object = RolePermissionModel.objects.get(pk=pk)
                return _object
            except RolePermissionModel.DoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'))
    # @execute_with_permission('role', 'list')
    def list(self, request):
        """
        get list of Role API.

        ---

        """
        _queryset = self.get_queryset().order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('create'))
    # @execute_with_permission('role', 'create')
    @transaction.atomic
    def create1(self, request):
        """
        inset a Role API.

        ---

        """
        _data = get_dict_data(request.data)
        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    # @execute_with_permission('role', 'read')
    def retrieve(self, request, pk=None):
        """
        get a Role API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('update'))
    # @execute_with_permission('role', 'update')
    @transaction.atomic
    def partial_update1(self, request, pk=None):
        """
        update a Role partial API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('delete'))
    # @execute_with_permission('role', 'delete')
    @transaction.atomic
    def destroy1(self, request, pk=None):
        """
        delete a Role  API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('get'))
    # @execute_with_permission('role', 'list')
    # @action(detail=False, methods=['get'])
    def get(self, request):
        """
        get list of Role API.

        ---

        """
        _objects = self.get_queryset()
        _count = self.queryset.count()
        if 'page_size' in request.query_params and request.query_params['page_size'] and \
                'page_num' in request.query_params and request.query_params['page_num']:

            _page_size = request.query_params['page_size']
            _page_num = request.query_params['page_num']
            _objects, _total_page_num = get_data(
                _objects, pagination=(_page_size, _page_num))
        else:
            _objects, _total_page_num = get_data(_objects)

        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(_objects, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('permission'))
    # @execute_with_permission('permission', 'create')
    # @action(detail=False, methods=['post'])
    @transaction.atomic
    def permission(self, request):
        _user = request.user
        _data = get_dict_data(request.data)
        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            _role_list = []
            _validated_data = serializer.validated_data
            _permissions = _validated_data.get('permissions', None)
            for _obj in _permissions:
                _role = _obj['role']
                _role_list.append(_role)
                _states = _obj['states']
                for _state_obj in _states:
                    _state = _state_obj['state']
                    _access = RoleAccessModel.objects.create(
                        role=_role, state=_state)
                    _access.save()
                    _operates = _state_obj['operates']
                    for _operate in _operates:
                        _permission = RolePermissionModel.objects.create(
                            access=_access, operate=_operate)
                        _permission.save()

            return Response(status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(807, _('validation error'),
                                   serializer.errors,
                                   status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('operate'))
    # @execute_with_permission('permission', 'delete')
    # @action(detail=False, methods=['delete'], url_path="operate/(?P<pk>[^/.]+)")
    @transaction.atomic
    def operate(self, request, pk=None):
        """
        delete an Operate from a Role  API.

        ---

        """
        if pk:
            _object = self.get_object_permission(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('state'))
    # @execute_with_permission('permission', 'delete')
    # @action(detail=False, methods=['delete'], url_path="state/(?P<pk>[^/.]+)")
    @transaction.atomic
    def state(self, request, pk=None):
        """
        delete a State from a Role  API.

        ---

        """
        if pk:
            _object = self.get_object_access(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)


class ServiceView(BasicView):
    queryset = ServiceModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=ServiceSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Service'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": ServiceInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':ServiceDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':ServiceInformationSerializer}
        elif action == 'partial_update':
            return {"200": ServiceInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return ServiceInformationSerializer
        elif self.action == 'delete':
            return ServiceDeleteSerializer
        elif self.action == "partial_update":
            return ServiceInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve','service','related']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceSerializer
        elif self.action == 'delete':
            return ServiceDeleteSerializer
        elif self.action in ['list','retrieve','service','related']:
            return ServiceInformationSerializer
        elif self.action == "partial_update":
            return ServiceUpdateSerializer
        elif self.action == "access":
            return ServiceAccessSerializer
        elif self.action == "recycle":
            return ServiceRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.select_related('category','company').prefetch_related('gallery',
        Prefetch('properties',
        queryset=ServiceClassificationModel.objects.select_related('property','static').prefetch_related('property__group')),
        Prefetch('category__groups',
        queryset=GroupMemberModel.objects.select_related('group').order_by('group__order')
        .prefetch_related(Prefetch('group__items',
            queryset=GroupItemModel.objects.order_by('order')
        
        ))))
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]

        if 'filter' in self.request.query_params and self.request.query_params['filter']:
            fil = self.request.query_params['filter'].split(',')
            #add_filter(filters,[{'properties__property__in': fil}])
            for i in fil:
               queryset=queryset.filter(properties__property_id=i)

        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])
        if 'category' in self.request.query_params and self.request.query_params['category']:
            category = self.request.query_params['category']
            add_filter(filters,[{'category__slug': category}])
        if 'company' in self.request.query_params and self.request.query_params['company']:
            company = self.request.query_params['company']
            add_filter(filters,[{'company__slug': company}])
        

        if 'qty' in self.request.query_params and self.request.query_params['qty']:
            qty = self.request.query_params['qty']
            add_filter(filters,[{'qty__gte': qty}])
        if 'price_low' in self.request.query_params and self.request.query_params['price_low']:
            price_low = self.request.query_params['price_low']
            add_filter(filters,[{'price__gte': price_low}])
        if 'price_up' in self.request.query_params and self.request.query_params['price_up']:
            price_up = self.request.query_params['price_up']
            add_filter(filters,[{'price__lte': price_up}])
        
        if 'is_revival' in self.request.query_params and self.request.query_params['is_revival']:
            try:
                is_revival = eval(self.request.query_params['is_revival'])
                add_filter(filters,[{'is_revival': is_revival}])
            except:
                pass

        if 'is_special' in self.request.query_params and self.request.query_params['is_special']:
            try:
                is_special = eval(self.request.query_params['is_special'])
                add_filter(filters,[{'is_special': is_special}])
            except:
                pass     
            
            
        add_filter(filters,get_status_filter(self.request))
        if hasattr(self.request,'user') and self.request.user.is_staff:
            pass
        else:
            add_filter(filters,[{'is_saleable': True}])

        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset   
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    def get_object_with_slug(self, slug=None):
        if slug:
            try:
                return self.get_queryset().get(slug=slug,is_delete=0)
            except ObjectDoesNotExist:
                return None

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=ServiceDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=ServiceFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


    @swagger_auto_schema(operation_description=get_operation_description_schema('upload'),responses={})
    # @execute_with_permission('Service', 'update')
    @action(detail=True, methods=['patch'],)
    @transaction.atomic
    def upload(self, request, pk=None):
        """
        upload icon for Service API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                    serializer = ServiceInfoSerializer(instance=_object)
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)   


    @swagger_auto_schema(operation_description='GET get A service object with slug')
    @action(detail=False, url_path='slug/(?P<slug>[-\w]+)', methods=['get'])
    def service(self, request, slug=None):
        if type(slug) is int:
            return  super().retrieve(request, pk=slug)
        elif type(slug) is str:
            if obj := self.get_object_with_slug(slug):
                serializer = self.get_serializer(obj)
                serializer.request = request
                return Response(serializer.data, status=status.HTTP_200_OK)

            raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)


    @swagger_auto_schema(operation_description='GET get related service objects with slug',query_serializer=ServiceRelatedFilterSerializer)
    @action(detail=False, methods=['get'])
    def related(self, request, slug=None):
        if obj := self.get_object_with_slug(slug):

            queryset = self.get_queryset()
            queryset = queryset.filter(category=obj.category,is_delete=0).exclude(id=obj.id).order_by('-pk')
            count = queryset.count()
            if count == 0:
                return Response({}, status=status.HTTP_204_NO_CONTENT)

            queryset, total_page_num = get_response_data(request, queryset)
            serializer = self.get_serializer(queryset, many=True)
            serializer.request = request
            return Response({
                'list': serializer.data,
                'total_page_num': total_page_num,
                'total_row': count
            })
        raise ProjectException(4001,_("ایتم پیدا نشد"),_("ایتم پیدا نشد"),status.HTTP_404_NOT_FOUND)

class ServiceGalleryView(BasicView):
    queryset = ServiceGalleryModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=ServiceGallerySerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Gallery'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": ServiceGalleryInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':ServiceGalleryDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':ServiceGalleryInformationSerializer}
        elif action == 'partial_update':
            return {"200": ServiceGalleryInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return ServiceGalleryInformationSerializer
        elif self.action == 'delete':
            return ServiceGalleryDeleteSerializer
        elif self.action == "partial_update":
            return ServiceGalleryInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceGallerySerializer
        elif self.action == 'delete':
            return ServiceGalleryDeleteSerializer
        elif self.action in ['list','retrieve']:
            return ServiceGalleryInformationSerializer
        
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        if 'service' in self.request.query_params and self.request.query_params['service']:
            service = self.request.query_params['service']
            add_filter(filters,[{'service':service}])
        #add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=ServiceGalleryDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=ServiceGalleryFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

class ServiceDependentView(BasicView):
    queryset = ServiceDependentModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=ServiceDependentSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='ServiceDependent'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": ServiceDependentInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':ServiceDependentDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':ServiceDependentInformationSerializer}
        elif action == 'partial_update':
            return {"200": ServiceDependentInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return ServiceDependentInformationSerializer
        elif self.action == 'delete':
            return ServiceDependentDeleteSerializer
        elif self.action == "partial_update":
            return ServiceDependentInformationSerializer
        return None
    
    def get_permissions(self):
        if self.action in ['list','retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes=self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceDependentSerializer
        elif self.action == 'delete':
            return ServiceDependentDeleteSerializer
        elif self.action in ['list','retrieve']:
            return ServiceDependentInformationSerializer
        elif self.action == "partial_update":
            return ServiceDependentUpdateSerializer
        elif self.action == "access":
            return ServiceDependentAccessSerializer
        elif self.action == "recycle":
            return ServiceDependentRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.select_related('primary','dependent')
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[] 
        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'title__icontains':search}])
        if 'service' in self.request.query_params and self.request.query_params['service']:
            service = self.request.query_params['service']
            add_filter(filters,[{'primary':service}])
        
        
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=ServiceDependentDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=ServiceDependentFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class ShopView(viewsets.GenericViewSet):
    queryset = ShopModel.objects.all()
    serializer_class = ShopSerializer
    permission_classes = ([IsAuthenticated])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        # (hasattr(self,'name') and self.name in ["Upload",])
        action_map = list(self.action_map.values())
        _action = ["some", "status", "trash", "recycle"]
        if any(item in action_map for item in _action):
            # if ["some","status"] in action_map
            parser_classes = [JSONParser]
        elif ("upload" in action_map):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            ShopSchemaSerializer,
            "200_OK":
            openapi.Response({}),
            "201":
            ShopSchemaSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_some":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "400_status":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "827": {
                            "status": "failed",
                            "code": 827,
                            "message": "validation error",
                            "detail": "Status field is Invalid.",
                        },
                    }
                },
            ),
            "404_multi":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "811": {
                            "status": "failed",
                            "code": 845,
                            "message": "not found",
                            "detail": "Some users are not in the system.",
                        },
                        "819": {
                            "status": "failed",
                            "code": 819,
                            "message": "not found",
                            "detail": "Primary keys list is empty.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer,
            "200_some":
            SampleSomeVirResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"], "400": rsd["807"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"],
                         "400": rsd["400"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve','cart','create','payment']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAdminUser, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ShopInformationSerializer
        elif self.action in ['cart']:
            return ShopCartSerializer
        elif self.action in ['next']:
            return ShopNextSerializer
        elif self.action in ['payment']:
            return ShopPaymentSerializer
        elif self.action in ['partial_update']:
            return ShopUpdateSerializer
            
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = self.queryset
        _user = self.request.user
        role_list = get_user_roles(_user)
        if not _user.pk:
            queryset = queryset.filter(pk=-1)
        elif _user.is_superuser:  # superuser
            queryset = queryset.filter(owner__is_superuser=False)
        elif _user.is_staff:  # admin
            queryset = queryset.filter(owner__is_staff=False)
        elif 'agent' in role_list:  # agent
            queryset = queryset.filter(Q(owner__owner=_user) | Q(owner__parent__parent=_user) | Q(
                owner__owner__parent__parent=_user)).exclude(owner__is_staff=True, owner__roles__role__title='agent')
        elif 'seller' in role_list:
            queryset = queryset.filter(Q(owner__owner=_user)).exclude(
                owner__is_staff=True, owner__roles__role__title__in=['agent', 'seller'])
        elif 'client' in role_list:
            queryset = queryset.filter(pk=-1)

        sh_me = self.queryset.filter(owner=_user)
        queryset = (queryset | sh_me).distinct()
        return queryset

    def filter_queryset(self, queryset):
        _filter = {}
        if 'owner' in self.request.query_params and self.request.query_params['owner']:
            _owner = self.request.query_params['owner']
            _filter.update({'owner_id': _owner})
        if 'service' in self.request.query_params and self.request.query_params['service']:
            _service = self.request.query_params['service']
            _filter.update({'items__service_id': _service})
        if 'state' in self.request.query_params and self.request.query_params['state']:
            _state = self.request.query_params['state']
            _filter.update({'state': _state})
        if 'date_start' in self.request.query_params and self.request.query_params['date_start']:
            _date_low = self.request.query_params['date_start']
            m_date_low = convert_shamsi_string_to_miladi_date(_date_low)
            _filter.update({'date__date__gte': m_date_low})
        if 'date_end' in self.request.query_params and self.request.query_params['date_end']:
            _date_high = self.request.query_params['date_end']
            m_date_high = convert_shamsi_string_to_miladi_date(_date_high)
            _filter.update({'date__date__lte': m_date_high})

        queryset = queryset.filter(**_filter).distinct()
        if 'agent' in self.request.query_params and self.request.query_params['agent']:
            _agent = self.request.query_params['agent']
            queryset = queryset.filter(Q(owner_id=_agent) | Q(owner__owner_id=_agent) | Q(
                owner__parent__parent_id=_agent) | Q(owner__owner__parent__parent_id=_agent))
        if 'seller' in self.request.query_params and self.request.query_params['seller']:
            _seller = self.request.query_params['seller']
            queryset = queryset.filter(
                Q(owner_id=_seller) | Q(owner__owner_id=_seller))

        return queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=ShopFilterQuerySerializer)
    def list(self, request):
        """
        get list of Shop API.

        ---

        """
        _queryset = self.get_queryset()
        _queryset = self.filter_queryset(queryset=_queryset).exclude(state__title__in=['cart','next']).order_by('-pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(method='post', responses=get_response_schema('create'))
    @swagger_auto_schema(method='get', responses=get_response_schema('retrieve'))
    @transaction.atomic
    @action(detail=False, methods=['post', 'get'])
    def cart(self, request):
        """
        Cart API.

        ---

        """

        if request.method == 'POST':
            _data = get_dict_data(request.data)

            serializer = self.get_serializer(data=_data)
            serializer.request=request
            if serializer.is_valid():
                _object = serializer.save()
                serializer = ShopInformationSerializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            _user = request.user
            try:
                _object = self.queryset.get(state='cart', owner=_user)

                serializer = ShopInformationSerializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    @transaction.atomic
    @action(detail=False, methods=['get'], url_path='cart/(?P<owner>[^/.]+)')
    def cart_get(self, request, owner=None):
        try:
            _user = request.user
            if _user.is_staff:
                _user = UserModel.objects.get(pk=owner)
                try:
                    _object = self.queryset.get(state='cart', owner=_user)

                    serializer = ShopInformationSerializer(instance=_object)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except ObjectDoesNotExist:
                    return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(
                    802, 'forbidden', 'forbidden', status.HTTP_403_FORBIDDEN)
        except ObjectDoesNotExist:
            raise ProjectException(
                801, 'not found error', 'not found error', status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(method='post', responses=get_response_schema('create'))
    @swagger_auto_schema(method='get', responses=get_response_schema('retrieve'))
    @transaction.atomic
    @action(detail=False, methods=['post', 'get'])
    def next(self, request):
        """
        Next API.

        ---

        """
        if request.method == 'POST':
            _data = get_dict_data(request.data)

            serializer = self.get_serializer(
                context={'request': request}, data=_data)
            serializer.request=request
            if serializer.is_valid():
                _object = serializer.save()
                serializer = ShopInformationSerializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(
                    807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            _user = request.user
            try:
                _object = self.queryset.get(state='next', owner=_user)

                serializer = ShopInformationSerializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    @transaction.atomic
    @action(detail=False, methods=['get'], url_path='next/(?P<owner>[^/.]+)')
    def next_get(self, request, owner=None):
        try:
            _user = request.user
            if _user.is_staff:
                _user = UserModel.objects.get(pk=owner)
                try:
                    _object = self.queryset.get(state='next', owner=_user)

                    serializer = ShopInformationSerializer(instance=_object)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except ObjectDoesNotExist:
                    return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(
                    802, 'forbidden', 'forbidden', status.HTTP_403_FORBIDDEN)
        except ObjectDoesNotExist:
            raise ProjectException(
                801, 'not found error', 'not found error', status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(responses=get_response_schema('create'))
    @transaction.atomic
    def create(self, request):
        """
        inset a Shop API.

        ---

        """
        _data = get_dict_data(request.data)

        serializer = self.get_serializer(data=_data)
        serializer.request=request
        if serializer.is_valid():
            _object = serializer.save()
            serializer = ShopInformationSerializer(instance=_object)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(responses=get_response_schema('create'))
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def payment(self, request, pk=None):
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
    
                serializer = self.get_serializer(context={'request': request,'owner':_object.owner}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                serializer = ShopInformationSerializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
                    
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    def retrieve(self, request, pk=None):
        """
        get a shop API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def partial_update(self, request, pk=None):
        """
        update a Order partial API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer( instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)


class StateViewSet(viewsets.GenericViewSet):
    queryset = StateModel.objects.all()
    serializer_class = StateSerializer
    permission_classes = ([IsAdminUser])
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_parsers(self):
        if (hasattr(self, 'action') and self.action in ["upload", ]) or (hasattr(self, 'name') and self.name in ["Upload", ]):
            parser_classes = [MultiPartParser]
        else:
            parser_classes = [JSONParser]

        return [parser() for parser in parser_classes]

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200":
            StateSerializer,
            "200_Ok":
            openapi.Response({}),
            "201":
            StateSerializer,
            "204":
            openapi.Response({}),
            "400":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "401_token":
            openapi.Response(
                description="UNAUTHORIZE",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "401": {
                            "status": "failed",
                            "code": 401,
                            "message": "Unauthorized",
                            "detail": "Authentication error.",
                        },
                        "440": {
                            "status": "failed",
                            "code": 440,
                            "message": "Unauthorized",
                            "detail": "Your account has expired.",
                        },
                        "441": {
                            "status": "failed",
                            "code": 441,
                            "message": "Unauthorized",
                            "detail": "The token is invalid for this system.",
                        },
                        "442": {
                            "status": "failed",
                            "code": 442,
                            "message": "Unauthorized",
                            "detail": "The access token has expired.",
                        },
                        "443": {
                            "status": "failed",
                            "code": 443,
                            "message": "Unauthorized",
                            "detail": "The refresh token has expired.",
                        },
                        "445": {
                            "status": "failed",
                            "code": 445,
                            "message": "Unauthorized",
                            "detail": "The refresh token is invalid.",
                        },
                        "801": {
                            "status": "failed",
                            "code": 801,
                            "message": "authentication error",
                            "detail": "Authentication error.",
                        },
                    }
                },
            ),
            "403":
            openapi.Response(
                description="Forbidden",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status":
                            "failed",
                            "code":
                            821,
                            "message":
                            _("validation error"),
                            "detail":
                            _("You do not have permission to perform this action."
                              ),
                            "data": {},
                        },
                    }
                },
            ),
            "404":
            openapi.Response(
                description="Not found",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "820": {
                            "status": "failed",
                            "code": 820,
                            "message": "not found",
                            "detail": "This primary key not found",
                        },
                    }
                },
            ),
            "807":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "807": {
                            "status": "failed",
                            "code": 807,
                            "message": "validation error",
                            "detail": "System default error.",
                        },

                    }
                },
            ),
            "800":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "813":
            openapi.Response(
                description="Bad request",
                schema=SampleResponseSerializer,
                examples={
                    "application/json": {
                        "813": {
                            "status": "failed",
                            "code": 813,
                            "message": "validation error",
                            "detail": "Set the primary key.",
                        },
                    }
                },
            ),
            "sample":
            SampleResponseSerializer
        }
        if action in ["list"]:
            responses = {"200": rsd["200"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action in ["create"]:
            responses = {"201": rsd["201"],
                         "400": rsd["807"], "401": rsd["401_token"]}
        elif action == "retrieve":
            responses = {"200": rsd["200"], "400": rsd["400"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        elif action == "update":
            responses = {"200": rsd["200"], "404": rsd["404"],
                         "400": rsd["400"], "401": rsd["401_token"]}
        elif action == "delete":
            responses = {"204": rsd["204"], "400": rsd["813"],
                         "401": rsd["401_token"], "404": rsd["404"]}
        return responses

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, ]
        else:
            permission_classes = [IsAdminUser, ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        return super().get_serializer_class()

    def get_queryset(self):
        return super().get_queryset()

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.get_queryset().get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                return None

    @swagger_auto_schema(responses=get_response_schema('list'))
    # @execute_with_permission('state', 'list')
    def list(self, request):
        """
        get list of State API.

        ---

        """
        _queryset = self.get_queryset().order_by('pk')
        _count = _queryset.count()
        if _count == 0:
            return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

        _queryset, _total_page_num = get_response_data(request, _queryset)
        serializer = self.get_serializer(_queryset, many=True)
        return Response({
            'list': serializer.data,
            'total_page_num': _total_page_num,
            'total_row': _count
        })

    @swagger_auto_schema(responses=get_response_schema('create'))
    # @execute_with_permission('state', 'create')
    @transaction.atomic
    def create(self, request):
        """
        inset a State API.

        ---

        """
        _data = get_dict_data(request.data)
        serializer = self.get_serializer(
            context={'request': request}, data=_data)
        serializer.request=request
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise ProjectException(
                807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('retrieve'))
    # @execute_with_permission('state', 'read')
    def retrieve(self, request, pk=None):
        """
        get a State API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                serializer = self.get_serializer(instance=_object)
                return Response(serializer.data)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('update'))
    # @execute_with_permission('state', 'update')
    @transaction.atomic
    def partial_update(self, request, pk=None):
        """
        update a State partial API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(
                    context={'request': request}, instance=_object, data=_data, partial=True)
                serializer.request=request
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    raise ProjectException(
                        807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses=get_response_schema('delete'))
    # @execute_with_permission('state', 'delete')
    @transaction.atomic
    def destroy(self, request, pk=None):
        """
        delete a State  API.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ProjectException(820, _('not found'), _(
                    'This primary key not found.'), status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'), _(
                'Set the primary key.'), status.HTTP_400_BAD_REQUEST)



class SetView(BasicView):
    queryset = SetModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=SetSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Set'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": SetInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':SetDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':SetInformationSerializer}
        elif action == 'partial_update':
            return {"200": SetInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return SetInformationSerializer
        elif self.action == 'delete':
            return SetDeleteSerializer
        elif self.action == "partial_update":
            return SetInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SetSerializer
        elif self.action == 'delete':
            return SetDeleteSerializer
        elif self.action in ['list','retrieve']:
            return SetInformationSerializer
        elif self.action == "partial_update":
            return SetUpdateSerializer
        elif self.action == "access":
            return SetAccessSerializer
        elif self.action == "recycle":
            return SetRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        
        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=SetDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=SetFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class StatusView(BasicView):
    queryset = StatusModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=StatusSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Status'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": StatusInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':StatusDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':StatusInformationSerializer}
        elif action == 'partial_update':
            return {"200": StatusInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return StatusInformationSerializer
        elif self.action == 'delete':
            return StatusDeleteSerializer
        elif self.action == "partial_update":
            return StatusInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StatusSerializer
        elif self.action == 'delete':
            return StatusDeleteSerializer
        elif self.action in ['list','retrieve']:
            return StatusInformationSerializer
        elif self.action == "partial_update":
            return StatusUpdateSerializer
        elif self.action == "access":
            return StatusAccessSerializer
        elif self.action == "access":
            return StatusRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        if 'owner' in self.request.query_params and self.request.query_params['owner']:
            owner = get_owner(self.request)
            add_filter(filters,[{'owner':owner}])
        if 'is_system' in self.request.query_params and self.request.query_params['is_system']:
            try:
                is_system = eval(self.request.query_params['is_system'])
                add_filter(filters,[{'is_system': is_system}])
            except:
                pass
       

        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset 
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=StatusDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=StatusFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class SupportView(BasicView):
    queryset = Support.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=SupportSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Support'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": SupportInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':SupportDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':SupportInformationSerializer}
        elif action == 'partial_update':
            return {"200": SupportInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return SupportInformationSerializer
        elif self.action == 'delete':
            return SupportDeleteSerializer
        elif self.action == "partial_update":
            return SupportInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SupportSerializer
        elif self.action == 'delete':
            return SupportDeleteSerializer
        elif self.action in ['list','retrieve']:
            return SupportInformationSerializer
        elif self.action == "partial_update":
            return SupportUpdateSerializer
        elif self.action == "access":
            return SupportAccessSerializer
        elif self.action == "access":
            return SupportRecycleSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filter={} 
        
        if 'status' in self.request.query_params and self.request.query_params['status']:
            status = get_dict_data(self.request.GET).get('status', None)
            if type(status) != type([]):
                status = [status, ]
            status_filter= get_status(status)
            filter.update(status_filter)
        else:
            filter.update({'status__in': [0, 1],'is_delete':0})


        queryset = queryset.filter(** filter).distinct()
        return queryset
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=SupportDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=SupportFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class TagView(BasicView):
    queryset = TagModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=TagSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Tag'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"200": TagSerializer,"201": TagSerializer, "400": {}}
        

    def get_responses(self):
        if self.action == 'create':
            return TagSerializer
    
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TagSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filter={} 
        
        if 'status' in self.request.query_params and self.request.query_params['status']:
            status = get_dict_data(self.request.GET).get('status', None)
            if type(status) != type([]):
                status = [status, ]
            status_filter= get_status(status)
            filter.update(status_filter)
        else:
            filter.update({'status__in': [0, 1],'is_delete':0})

       
        
            

        queryset = queryset.filter(** filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    

class UserView(BasicView):
    queryset = UserModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=UserSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='User'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": UserInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':UserDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':UserInformationSerializer}
        elif action == 'partial_update':
            return {"200": UserInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return UserInformationSerializer
        elif self.action == 'delete':
            return UserDeleteSerializer
        elif self.action == "partial_update":
            return UserInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        elif self.action == 'delete':
            return UserDeleteSerializer
        elif self.action in ['list','retrieve']:
            return UserInformationSerializer
        elif self.action == "partial_update":
            return UserUpdateSerializer
        elif self.action == "access":
            return UserAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset.annotate(name=Concat('first_name',V(' '),'last_name')).select_related('profile').prefetch_related('address')
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        
        if 'role' in self.request.query_params and self.request.query_params['role']:
            role = self.request.query_params['role']
            add_filter(filters,[{'roles__role__title': role}])

        if 'search' in self.request.query_params and self.request.query_params['search']:
            search = self.request.query_params['search']
            add_filter(filters,[{'name__icontains':search},{'cellphone__icontains':search},{'email__icontains':search}])


        if not(self.request.user.is_superuser or self.request.user.is_staff):
            add_owner_filter(filters,self.request)

        add_filter(filters,get_status_filter(self.request))
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset


            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=UserDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=UserFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


    @swagger_auto_schema(operation_description=get_operation_description_schema('me'))
    @action(detail=False, methods=['get'])
    def me(self, request):
        _user = request.user
        if _user:
            serializer = self.get_serializer(instance=_user)
            return Response(serializer.data)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(operation_description=get_operation_description_schema('upload'),responses=get_responses_schema('upload'))
    @action(detail=True, methods=["patch"], parser_classes=(MultiPartParser, ),)
    @transaction.atomic
    def upload(self, request, pk=None):
        if pk:
            _object = self.get_object(pk)
            if _object and (_object.status in [0, 1]):
                _data = get_dict_data(request.data)
                serializer = self.get_serializer(context={"request": request},
                                                  instance=_object, data=_data, partial=True,
                                                  )
                serializer.request=request
                if serializer.is_valid():
                    _object = serializer.save()
                    serializer = UserInfoSerializer(instance=_object)
                    return Response(serializer.data,
                                    status=status.HTTP_200_OK)
                else:
                    raise ProjectException(807, _('validation error'),
                                           serializer.errors,
                                           status.HTTP_400_BAD_REQUEST)
            else:
                raise ProjectException(820, _('not found'),
                                       _('This primary key not found.'),
                                       status.HTTP_404_NOT_FOUND)
        else:
            raise ProjectException(813, _('validation error'),
                                   _('Set the primary key.'),
                                   status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('resend'),responses={})
    @action(detail=False, methods=["post"], url_path='resend_verification_code')
    def resend(self, request):
        """
        resend verification code to user.

        ---

        """
        serializer = self.get_serializer(
            context={"request": request}, data=request.data)
        serializer.request=request
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_200_OK)
        else:
            raise ProjectException(807, _("validation error"), serializer.errors,
                                   status.HTTP_400_BAD_REQUEST,
                                   )

        
    
    @swagger_auto_schema(operation_description=get_operation_description_schema('add_role'),responses={})
    @action(detail=True,methods=["post"],url_path='role')
    @transaction.atomic
    def add_role(self, request, pk=None):
        """
        add role API
        role : [client,visitor,admin]
        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_dict_data(request.data)
                _data['user'] = _object.pk
                serializer = UserRoleSerializer(
                    context={"request": request}, data=_data, partial=True,)
                serializer.request=request
                if serializer.is_valid():
                    serializer.save()
                    new_object = self.get_object(pk)
                    serializer = UserInfoSerializer(instance=new_object)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    raise ProjectException(
                        807,
                        _("validation error"),
                        serializer.errors,
                        status.HTTP_400_BAD_REQUEST,
                    )
            else:
                raise ProjectException(
                    820,
                    _("not found"),
                    _("This primary key not found."),
                    status.HTTP_404_NOT_FOUND,
                )
        else:
            raise ProjectException(
                813,
                _("validation error"),
                _("Set the primary key."),
                status.HTTP_400_BAD_REQUEST,
            )

    
    @swagger_auto_schema(operation_description=get_operation_description_schema('add_role'),responses={})
    @action(detail=True,methods=["delete"],url_path='role/(?P<role>[\w\-]+)')
    @transaction.atomic
    def delete_role(self, request, pk=None, role=None):
        """
        delete a role API.

        """
        _user = request.user
        if pk:
            _object = self.get_object(pk)
            if _object:
                if _object != _user:
                    if role:
                        try:
                            user_role = UserRoleModel.objects.get(
                                user=_object, role__pk=role)
                            user_role.delete()
                            return Response(status=status.HTTP_204_NO_CONTENT)
                        except:
                            raise ProjectException(
                                847, _("not found"), _("This role not found."),
                                status.HTTP_404_NOT_FOUND,
                            )
                    else:
                        raise ProjectException(
                            846,
                            _("validation error"),
                            _("Set the role."),
                            status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    raise ProjectException(
                        848,
                        _("Forbidden"),
                        _("You do not have access to delete your role"),
                        status.HTTP_403_FORBIDDEN,
                    )
            else:
                raise ProjectException(
                    820,
                    _("not found"),
                    _("This primary key not found"),
                    status.HTTP_404_NOT_FOUND,
                )
        else:
            raise ProjectException(
                813,
                _("validation error"),
                _("Set the primary key."),
                status.HTTP_400_BAD_REQUEST,
            )


class UserEvidenceView(BasicView):
    queryset = UserEvidenceModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=UserEvidenceSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='UserEvidence'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": UserEvidenceInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':UserEvidenceDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':UserEvidenceInformationSerializer}
        elif action == 'partial_update':
            return {"200": UserEvidenceInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return UserEvidenceInformationSerializer
        elif self.action == 'delete':
            return UserEvidenceDeleteSerializer
        elif self.action == "partial_update":
            return UserEvidenceInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserEvidenceSerializer
        elif self.action == 'delete':
            return UserEvidenceDeleteSerializer
        elif self.action in ['list','retrieve']:
            return UserEvidenceInformationSerializer
        elif self.action == "partial_update":
            return UserEvidenceUpdateSerializer
        elif self.action == "access":
            return UserEvidenceAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filter={}
        if 'media' in self.request.query_params and self.request.query_params['media']:
            media = self.request.query_params['media']
            filter['media'] = media
               
                
                    

        queryset = queryset.filter(** filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=UserEvidenceDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=UserEvidenceFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class UserFileView(BasicView):

    queryset = UserFileModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=UserFileSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='UserFile'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": UserFileInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':UserFileDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':UserFileInformationSerializer}
        elif action == 'partial_update':
            return {"200": UserFileInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return UserFileInformationSerializer
        elif self.action == 'delete':
            return UserFileDeleteSerializer
        elif self.action == "partial_update":
            return UserFileInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserFileSerializer
        elif self.action == 'delete':
            return UserFileDeleteSerializer
        elif self.action in ['list','retrieve']:
            return UserFileInformationSerializer
        elif self.action == "partial_update":
            return UserFileUpdateSerializer
        elif self.action == "access":
            return UserFileAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        if 'media' in self.request.query_params and self.request.query_params['media']:
            media = self.request.query_params['media']
            add_filter(filters,[{'media':media}])
        add_owner_filter(filters,self.request)
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    
    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('delete'),request_body=UserEvidenceDeleteSerializer)
    def delete(self, request):
        return  super().delete(request)

    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=UserEvidenceFilterSerializer)    
    def list(self, request):
        return super().list(request)

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('partial_update'),responses=get_responses_schema('update'))
    def partial_update(self, request, pk=None):
      return   super().partial_update(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('retrieve'))
    def retrieve(self, request, pk=None):
        return  super().retrieve(request, pk=pk)

    @swagger_auto_schema(operation_description=get_operation_description_schema('privacy'),responses={})
    def access(self, request):   
        return  super().access(request)


class WalletView(BasicView):

    queryset = WalletModel.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class=WalletSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_operation_description_schema(action):
        obj='Wallet'
        return get_operation_description(obj,action)

    def get_responses_schema(action):
        if action == 'create':
            return {"201": WalletInformationSerializer, "400": {}}
        elif action == 'delete':
            return {'204':WalletDeleteSerializer}
        elif action in ['list','retrieve']:
            return {'200':WalletInformationSerializer}
        elif action == 'partial_update':
            return {"200": WalletInformationSerializer, "400": {}} 
    

    def get_responses(self):
        if self.action == 'create':
            return WalletInformationSerializer
        elif self.action == 'delete':
            return WalletDeleteSerializer
        elif self.action == "partial_update":
            return WalletInformationSerializer
        return None
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return WalletSerializer
        elif self.action == 'delete':
            return WalletDeleteSerializer
        elif self.action in ['list','retrieve']:
            return WalletInformationSerializer
        elif self.action == "partial_update":
            return WalletUpdateSerializer
        elif self.action == "access":
            return WalletAccessSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset=self.queryset
        return queryset
    
    def filter_queryset(self, queryset):  
        filters=[]
        

        if 'owner' in self.request.query_params and self.request.query_params['owner']:
            owner = get_owner(self.request)
            add_filter(filters,[{'owner':owner}])
            

       
        filter=get_filter(filters)
        queryset = queryset.filter(filter).distinct()
        return queryset
        
            
    def get_parsers(self):  
        parser_classes = [JSONParser]
        return [parser() for parser in parser_classes]

    @transaction.atomic
    @swagger_auto_schema(operation_description=get_operation_description_schema('create'),responses=get_responses_schema('create'))
    def create(self, request):
       return  super().create(request)
        
    @swagger_auto_schema(operation_description=get_operation_description_schema('list') , query_serializer=WalletFilterQuerySerializer)    
    def list(self, request):
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset=queryset).order_by('-pk')
        count = queryset.count()
        if count == 0:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        queryset, total_page_num = get_response_data(request, queryset)
        serializer = self.get_serializer(queryset, many=True)
        serializer.request = request
        wallet=queryset.aggregate(Sum("amount"))["amount__sum"]
        return Response({
            'list': serializer.data,
            'wallet':wallet,
            'total_page_num': total_page_num,
            'total_row': count
        })
       

   
    # queryset = WalletModel.objects.all()
    # serializer_class = WalletSerializer
    # permission_classes = ([AllowAny])
    # renderer_classes = (JSONRenderer,)
    # parser_classes = (JSONParser,)

    # def get_parsers(self):
    #     if (hasattr(self, 'action') and self.action in ["upload", ]) or (hasattr(self, 'name') and self.name in ["Upload", ]):
    #         parser_classes = [MultiPartParser]
    #     else:
    #         parser_classes = [JSONParser]

    #     return [parser() for parser in parser_classes]

    # def get_response_schema(action):
    #     # response_schema_dict
    #     responses = {}
    #     rsd = {
    #         "200":
    #         WalletInfoSerializer,
    #         "200List":
    #         WalletInfoSerializer,
    #         "201":
    #         UserSchemaSerializer,
    #         "204":
    #         openapi.Response({}),
    #         "400":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "401_token":
    #         openapi.Response(
    #             description="UNAUTHORIZE",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "401": {
    #                         "status": "failed",
    #                         "code": 401,
    #                         "message": "Unauthorized",
    #                         "detail": "Authentication error.",
    #                     },
    #                     "440": {
    #                         "status": "failed",
    #                         "code": 440,
    #                         "message": "Unauthorized",
    #                         "detail": "Your account has expired.",
    #                     },
    #                     "441": {
    #                         "status": "failed",
    #                         "code": 441,
    #                         "message": "Unauthorized",
    #                         "detail": "The token is invalid for this system.",
    #                     },
    #                     "442": {
    #                         "status": "failed",
    #                         "code": 442,
    #                         "message": "Unauthorized",
    #                         "detail": "The access token has expired.",
    #                     },
    #                     "443": {
    #                         "status": "failed",
    #                         "code": 443,
    #                         "message": "Unauthorized",
    #                         "detail": "The refresh token has expired.",
    #                     },
    #                     "445": {
    #                         "status": "failed",
    #                         "code": 445,
    #                         "message": "Unauthorized",
    #                         "detail": "The refresh token is invalid.",
    #                     },
    #                     "801": {
    #                         "status": "failed",
    #                         "code": 801,
    #                         "message": "authentication error",
    #                         "detail": "Authentication error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "403":
    #         openapi.Response(
    #             description="Forbidden",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "821": {
    #                         "status":
    #                         "failed",
    #                         "code":
    #                         821,
    #                         "message":
    #                         _("validation error"),
    #                         "detail":
    #                         _("You do not have permission to perform this action."
    #                           ),
    #                         "data": {},
    #                     },
    #                 }
    #             },
    #         ),
    #         "848":
    #         openapi.Response(
    #             description="Forbidden",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "848": {
    #                         "status": "failed",
    #                         "code": 848,
    #                         "message": _("validation error"),
    #                         "detail": _("You do not have access to delete your role."),
    #                         "data": {},
    #                     },
    #                 }
    #             },
    #         ),
    #         "404":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "820": {
    #                         "status": "failed",
    #                         "code": 820,
    #                         "message": "not found",
    #                         "detail": "This primary key not found",
    #                     },
    #                 }
    #             },
    #         ),
    #         "819":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "819": {
    #                         "status": "failed",
    #                         "code": 819,
    #                         "message": "not found",
    #                         "detail": "Primary keys list is empty.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "800":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "800": {
    #                         "status": "failed",
    #                         "code": 800,
    #                         "message": "unknown error",
    #                         "detail": "Unknown error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "807":
    #             openapi.Response(
    #                 description="Bad request",
    #                 schema=SampleResponseSerializer,
    #                 examples={
    #                     "application/json": {
    #                         "807": {
    #                             "status": "failed",
    #                             "code": 807,
    #                             "message": "validation error",
    #                             "detail": "System default error.",
    #                         },
    #                     }
    #                 },
    #         ),
    #         "813":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "852":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "852": {
    #                         "status": "failed",
    #                         "code": 852,
    #                         "message": "runtime error",
    #                         "detail": "role error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_reg":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "809": {
    #                         "status": "failed",
    #                         "code": 809,
    #                         "message": "validation error",
    #                         "detail": "Email exist.",
    #                     },
    #                     "810": {
    #                         "status": "failed",
    #                         "code": 810,
    #                         "message": "validation error",
    #                         "detail": "Username exist.",
    #                     },
    #                     "811": {
    #                         "status": "failed",
    #                         "code": 811,
    #                         "message": "validation error",
    #                         "detail": "Username cannot les than 4 digit.",
    #                     },
    #                     "812": {
    #                         "status": "failed",
    #                         "code": 812,
    #                         "message": "validation error",
    #                         "detail": "password cannot les than 8 digit.",
    #                     },
    #                     "846": {
    #                         "status": "failed",
    #                         "code": 846,
    #                         "message": "validation error",
    #                         "detail": "Set the role.",
    #                     },
    #                     "852": {
    #                         "status": "failed",
    #                         "code": 852,
    #                         "message": "runtime error",
    #                         "detail": "role error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400pk":
    #             openapi.Response(
    #                 description="Bad request",
    #                 schema=SampleResponseSerializer,
    #                 examples={
    #                     "application/json": {
    #                         "807": {
    #                             "status": "failed",
    #                             "code": 807,
    #                             "message": "validation error",
    #                             "detail": "System default error.",
    #                         },
    #                         "809": {
    #                             "status": "failed",
    #                             "code": 809,
    #                             "message": "validation error",
    #                             "detail": "Email exist.",
    #                         },
    #                         "810": {
    #                             "status": "failed",
    #                             "code": 810,
    #                             "message": "validation error",
    #                             "detail": "Username exist.",
    #                         },
    #                         "811": {
    #                             "status": "failed",
    #                             "code": 811,
    #                             "message": "validation error",
    #                             "detail": "Username cannot les than 4 digit.",
    #                         },
    #                         "812": {
    #                             "status": "failed",
    #                             "code": 812,
    #                             "message": "validation error",
    #                             "detail": "password cannot les than 8 digit.",
    #                         },
    #                         "813": {
    #                             "status": "failed",
    #                             "code": 813,
    #                             "message": "validation error",
    #                             "detail": "Set the primary key.",
    #                         },
    #                         "852": {
    #                             "status": "failed",
    #                             "code": 852,
    #                             "message": "runtime error",
    #                             "detail": "role error.",
    #                         },
    #                     }
    #                 },
    #         ),
    #         "400_forget":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "830": {
    #                         "status": "failed",
    #                         "code": 830,
    #                         "message": "validation error",
    #                         "detail": "Error at encoding of Security Question.",
    #                     },
    #                     "831": {
    #                         "status": "failed",
    #                         "code": 831,
    #                         "message": "validation error",
    #                         "detail": "Error at encoding of username and Security Question.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_reset":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "850": {
    #                         "status": "failed",
    #                         "code": 850,
    #                         "message": "validation error",
    #                         "detail": "Token is invalid.",
    #                     },
    #                 }
    #             },
    #         ),

    #         "400_status":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "827": {
    #                         "status": "failed",
    #                         "code": 827,
    #                         "message": "validation error",
    #                         "detail": "Status field is Invalid.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_role":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                     "846": {
    #                         "status": "failed",
    #                         "code": 846,
    #                         "message": "validation error",
    #                         "detail": "Set the role.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "404_multi":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "811": {
    #                         "status": "failed",
    #                         "code": 845,
    #                         "message": "not found",
    #                         "detail": "Some users are not in the system.",
    #                     },
    #                     "819": {
    #                         "status": "failed",
    #                         "code": 819,
    #                         "message": "not found",
    #                         "detail": "Primary keys list is empty.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "404_role":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "820": {
    #                         "status": "failed",
    #                         "code": 820,
    #                         "message": "not found",
    #                         "detail": "This primary key not found",
    #                     },
    #                     "847": {
    #                         "status": "failed",
    #                         "code": 847,
    #                         "message": "not found",
    #                         "detail": "This role not found",
    #                     },
    #                 }
    #             },
    #         ),

    #         "200_forget":
    #         SampleForgetPasswordResponseSerializer,
    #         "sample":
    #         SampleResponseSerializer,
    #         "200_some":
    #         SampleSomeVirResponseSerializer,
    #         "200_OK":
    #         openapi.Response({}),
    #     }
    #     responses = dict()
    #     if action == ["list", "trash"]:
    #         responses = {"200": rsd["200List"],
    #                      "204": rsd["204"], "401": rsd["401_token"]}
    #     elif action == "create":
    #         responses = {"201": rsd["201"], "400": rsd["400_reg"]}
    #     elif action == "retrieve":
    #         responses = {"200": rsd["200"], "400": rsd["813"],
    #                      "401": rsd["401_token"], "404": rsd["404"]}
    #     elif action == "update":
    #         responses = {"200": rsd["200"], "400": rsd["400pk"],
    #                      "401": rsd["401_token"], "404": rsd["404"]}
    #     elif action == "delete":
    #         responses = {"204": rsd["204"], "400": rsd["813"],
    #                      "401": rsd["401_token"], "403": rsd["403"], "404": rsd["404"]}
    #     elif action in ["upload", "add_role"]:
    #         responses = {"200": rsd["200"], "400": rsd["400"],
    #                      "401": rsd["401_token"], "404": rsd["404"]}

    #     elif action == "activated":
    #         responses = {"200": rsd["200"], "400": rsd["816"]}
    #     elif action == "reactive":
    #         responses = {"200": rsd["sample"], "400": rsd["816"]}

    #     elif action == "forgotpassword":
    #         responses = {"200": rsd["200_forget"], "400": rsd["400_forget"]}
    #     elif action == "resetpassword":
    #         responses = {"200": rsd["sample"], "400": rsd["400_reset"]}

    #     elif action == "some":
    #         responses = {"200": rsd["200_some"], "204": rsd["204"],
    #                      "400": rsd["807"], "401": rsd["401_token"], "404": rsd["404_multi"]}
    #     elif action == "status":
    #         responses = {"200": rsd["200_OK"], "400": rsd["400_status"],
    #                      "401": rsd["401_token"], "404": rsd["404_multi"]}
    #     elif action == "recycle":
    #         responses = {"200": rsd["200_OK"], "400": rsd["813"],
    #                      "401": rsd["401_token"], "403": rsd["403"], "404": rsd["404"]}
    #     elif action == "delete_role":
    #         responses = {"204": rsd["204"], "400": rsd["400_role"],
    #                      "401": rsd["401_token"], "403": rsd["848"], "404": rsd["404_role"]}
    #     elif action == "charge":
    #         responses = {"200": rsd["200"]}

    #     return responses

    # def get_serializer_class(self):
    #     if self.action in ['list']:
    #         return WalletInfoSerializer
    #     elif self.action == "charge":
    #         return WalletChargeSerializer
    #     else:
    #         return UserSerializer

    # def get_permissions(self):
    #     if self.action in ["charge"]:
    #         permission_classes = [IsAdminUser, ]
    #     else:
    #         permission_classes = [IsAuthenticated, ]
    #     return [permission() for permission in permission_classes]

    # def get_queryset(self):
    #     queryset = self.queryset
    #     _user = self.request.user
    #     # if not _user.pk:
    #     #     return queryset.filter(pk=-1)
    #     # elif _user.is_superuser: # superuser
    #     #     queryset = queryset.filter(is_superuser=False)
    #     # elif _user.is_staff: # admin
    #     #     queryset = queryset.filter(is_staff=False)
    #     # elif 'agent' in role_list: # agent
    #     #     queryset = queryset.filter(Q(owner=_user)|Q(parent__parent=_user)|Q(owner__parent__parent=_user)).exclude(is_staff=True,roles__role__title='agent')
    #     # elif 'seller' in role_list: # seller
    #     #     queryset = queryset.filter(Q(owner=_user)).exclude(is_staff=True,roles__role__title__in=['agent','seller'])
    #     # elif 'client' in role_list: # client
    #     #     queryset = queryset.filter(pk=-1)
    #     # me = self.queryset.filter(pk=_user.pk)
    #     # queryset = (queryset | me).distinct()
    #     return queryset

    # def filter_queryset(self, queryset, status=None):
    #     _filter = {}

    #     if 'owner' in self.request.query_params and self.request.query_params['owner']:
    #         _user = self.request.user
    #         _owner = self.request.query_params['owner']
    #         if not (_user.is_superuser or _user.is_staff) and _owner != _user.pk:
    #             raise ProjectException(
    #                 801, 'forbidden error', 'forbidden error', status.HTTP_403_FORBIDDEN)

    #         _filter.update({'owner': _owner})
    #     else:
    #         _user = self.request.user
    #         _filter.update({'owner': _user})
    #     queryset = queryset.filter(** _filter).distinct()

    #     return queryset

    # def get_object(self, pk=None):
    #     if pk:
    #         try:
    #             _object = self.get_queryset().get(pk=pk)
    #             return _object
    #         except ObjectDoesNotExist:
    #             pass

    # def get_object_trash(self, pk=None):
    #     if pk:
    #         try:
    #             _object = self.get_queryset().get(pk=pk, status=-1)
    #             return _object
    #         except ObjectDoesNotExist:
    #             pass

    # @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=WalletFilterQuerySerializer)
    # def list(self, request):
    #     """
    #     get Wallet API.

    #     ---

    #     """
    #     _queryset = self.get_queryset()
    #     # _queryset = _queryset.exclude(pk=request.user.pk)
    #     _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
    #     _count = _queryset.count()
    #     if _count == 0:
    #         return Response(status=status.HTTP_204_NO_CONTENT)

    #     _queryset, _total_page_num = get_response_data(request, _queryset)
    #     serializer = self.get_serializer(_queryset, many=True)
    #     _wallet=_queryset.aggregate(Sum("amount"))["amount__sum"]
    #     return Response({
    #         'list': serializer.data,
    #         'wallet':_wallet,
    #         'total_page_num': _total_page_num,
    #         'total_row': _count
    #     })

    # @action(detail=False, methods=['post'])
    # @swagger_auto_schema(responses=get_response_schema('charge'))
    # def charge(self, request):
    #     """
    #     charge API.

    #     ---

    #     """
    #     _data = get_dict_data(request.data)

    #     serializer = self.get_serializer(
    #         context={'request': request}, data=_data)
    #     if serializer.is_valid():
    #         _object = serializer.save()
    #         serializer = WalletSerializer(instance=_object)
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     else:
    #         raise ProjectException(
    #             807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)


# class AddressViewSet(viewsets.GenericViewSet):
#     queryset = AddressModel.objects.all()
#     serializer_class = AddressSerializer
#     permission_classes = ([IsAuthenticated])
#     renderer_classes = (JSONRenderer,)
#     parser_classes = (JSONParser,)

#     def get_parsers(self):
#         # (hasattr(self,'name') and self.name in ["Upload",])
#         action_map = list(self.action_map.values())
#         _action = ["some", "status", "trash", "recycle"]
#         if any(item in action_map for item in _action):
#             # if ["some","status"] in action_map
#             parser_classes = [JSONParser]
#         elif ("upload" in action_map):
#             parser_classes = [MultiPartParser]
#         else:
#             parser_classes = [JSONParser]

#         return [parser() for parser in parser_classes]

#     def get_response_schema(action):
#         # response_schema_dict
#         responses = {}
#         rsd = {
#             "200":
#             AddressSchemaSerializer,
#             "200List": AddressListSchemaSerializer,
#             "200_OK":
#             openapi.Response({}),
#             "201":
#             AddressSchemaSerializer,
#             "204":
#             openapi.Response({}),
#             "400":
#             openapi.Response(
#                 description="Bad request",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "807": {
#                             "status": "failed",
#                             "code": 807,
#                             "message": "validation error",
#                             "detail": "System default error.",
#                         },
#                         "813": {
#                             "status": "failed",
#                             "code": 813,
#                             "message": "validation error",
#                             "detail": "Set the primary key.",
#                         },
#                     }
#                 },
#             ),
#             "400_some":
#             openapi.Response(
#                 description="Bad request",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "807": {
#                             "status": "failed",
#                             "code": 807,
#                             "message": "validation error",
#                             "detail": "System default error.",
#                         },
#                     }
#                 },
#             ),
#             "401_token":
#             openapi.Response(
#                 description="UNAUTHORIZE",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "401": {
#                             "status": "failed",
#                             "code": 401,
#                             "message": "Unauthorized",
#                             "detail": "Authentication error.",
#                         },
#                         "440": {
#                             "status": "failed",
#                             "code": 440,
#                             "message": "Unauthorized",
#                             "detail": "Your account has expired.",
#                         },
#                         "441": {
#                             "status": "failed",
#                             "code": 441,
#                             "message": "Unauthorized",
#                             "detail": "The token is invalid for this system.",
#                         },
#                         "442": {
#                             "status": "failed",
#                             "code": 442,
#                             "message": "Unauthorized",
#                             "detail": "The access token has expired.",
#                         },
#                         "443": {
#                             "status": "failed",
#                             "code": 443,
#                             "message": "Unauthorized",
#                             "detail": "The refresh token has expired.",
#                         },
#                         "445": {
#                             "status": "failed",
#                             "code": 445,
#                             "message": "Unauthorized",
#                             "detail": "The refresh token is invalid.",
#                         },
#                         "801": {
#                             "status": "failed",
#                             "code": 801,
#                             "message": "authentication error",
#                             "detail": "Authentication error.",
#                         },
#                     }
#                 },
#             ),
#             "403":
#             openapi.Response(
#                 description="Forbidden",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "821": {
#                             "status":
#                             "failed",
#                             "code":
#                             821,
#                             "message":
#                             _("validation error"),
#                             "detail":
#                             _("You do not have permission to perform this action."
#                               ),
#                             "data": {},
#                         },
#                     }
#                 },
#             ),
#             "404":
#             openapi.Response(
#                 description="Not found",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "820": {
#                             "status": "failed",
#                             "code": 820,
#                             "message": "not found",
#                             "detail": "This primary key not found",
#                         },
#                     }
#                 },
#             ),
#             "807":
#             openapi.Response(
#                 description="Bad request",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "807": {
#                             "status": "failed",
#                             "code": 807,
#                             "message": "validation error",
#                             "detail": "System default error.",
#                         },

#                     }
#                 },
#             ),
#             "800":
#             openapi.Response(
#                 description="Bad request",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "800": {
#                             "status": "failed",
#                             "code": 800,
#                             "message": "unknown error",
#                             "detail": "Unknown error.",
#                         },
#                     }
#                 },
#             ),
#             "813":
#             openapi.Response(
#                 description="Bad request",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "813": {
#                             "status": "failed",
#                             "code": 813,
#                             "message": "validation error",
#                             "detail": "Set the primary key.",
#                         },
#                     }
#                 },
#             ),
#             "400_status":
#             openapi.Response(
#                 description="Bad request",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "807": {
#                             "status": "failed",
#                             "code": 807,
#                             "message": "validation error",
#                             "detail": "System default error.",
#                         },
#                         "827": {
#                             "status": "failed",
#                             "code": 827,
#                             "message": "validation error",
#                             "detail": "Status field is Invalid.",
#                         },
#                     }
#                 },
#             ),
#             "404_multi":
#             openapi.Response(
#                 description="Not found",
#                 schema=SampleResponseSerializer,
#                 examples={
#                     "application/json": {
#                         "811": {
#                             "status": "failed",
#                             "code": 845,
#                             "message": "not found",
#                             "detail": "Some users are not in the system.",
#                         },
#                         "819": {
#                             "status": "failed",
#                             "code": 819,
#                             "message": "not found",
#                             "detail": "Primary keys list is empty.",
#                         },
#                     }
#                 },
#             ),
#             "sample":
#             SampleResponseSerializer,
#             "200_some":
#             SampleSomeVirResponseSerializer
#         }
#         if action in ["list"]:
#             responses = {"200": rsd["200List"], "400": rsd["807"]}
#         elif action in ["create"]:
#             responses = {"201": rsd["201"],
#                          "400": rsd["807"], "401": rsd["401_token"]}
#         elif action == "retrieve":
#             responses = {"200": rsd["200"],
#                          "400": rsd["400"], "404": rsd["404"]}
#         elif action == "update":
#             responses = {"200": rsd["200"], "404": rsd["404"],
#                          "400": rsd["400"], "401": rsd["401_token"]}
#         elif action == "delete":
#             responses = {"204": rsd["204"], "400": rsd["813"],
#                          "401": rsd["401_token"], "404": rsd["404"]}
#         return responses

#     def get_permissions(self):
#         if self.action in ['list', 'retrieve']:
#             permission_classes = [IsAuthenticated, ]
#         else:
#             permission_classes = [IsAuthenticated, ]

#         return [permission() for permission in permission_classes]

#     def get_serializer_class(self):
#         if self.action in ['list', 'retrieve']:
#             return AddressInfoSerializer
#         elif self.action in ['partial_update']:
#             return AddressUpdateSerializer
#         return super().get_serializer_class()

#     def get_queryset(self):
#         queryset = self.queryset
#         _user = self.request.user
#         list_role = get_user_roles(_user)

#         return queryset

#     def filter_queryset(self, queryset):
#         _filter = {}
#         if 'search' in self.request.query_params and self.request.query_params['search']:
#             _search = self.request.query_params['search']
#             _filter.update({'address__icontains': _search})
#         if 'owner' in self.request.query_params and self.request.query_params['owner']:
#             _user = self.request.user
#             _owner = self.request.query_params['owner']
#             if not (_user.is_superuser or _user.is_staff) and _owner != _user.pk:

#                 try:
#                     UserModel.objects.get(owner=_user.pk)
#                 except ObjectDoesNotExist:

#                     raise ProjectException(
#                         801, 'forbidden error', 'forbidden error', status.HTTP_403_FORBIDDEN)
#                 except UserModel.MultipleObjectsReturned:
#                     pass

#             _filter.update({'owner': _owner})
#         else:
#             _user = self.request.user
#             _filter.update({'owner': _user})
#         if 'is_default' in self.request.query_params and self.request.query_params['is_default']:
#             is_default = self.request.query_params['is_default']
#             if is_default == 'false':
#                 _filter.update({'is_default': False})
#             else:
#                 _filter.update({'is_default': True})
        
        
#         queryset = queryset.filter(**_filter).distinct()
#         return queryset

#     def get_object(self, pk=None):
#         if pk:
#             try:
#                 _object = self.get_queryset().get(pk=pk)
#                 return _object
#             except ObjectDoesNotExist:
#                 return None

#     @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=AddressFilterQuerySerializer)
#     def list(self, request):
#         """
#         get list of Address API.

#         ---

#         """
#         _queryset = self.get_queryset()
#         _queryset = self.filter_queryset(
#             queryset=_queryset).order_by('-is_default')
#         _count = _queryset.count()
#         if _count == 0:
#             return Response({'list': [], 'total_page_num': 0, 'total_row': 0}, status=status.HTTP_204_NO_CONTENT)

#         _queryset, _total_page_num = get_response_data(request, _queryset)
#         serializer = self.get_serializer(_queryset, many=True)
#         return Response({
#             'list': serializer.data,
#             'total_page_num': _total_page_num,
#             'total_row': _count
#         })

#     @swagger_auto_schema(responses=get_response_schema('create'))
#     # @execute_with_permission('Address', 'create')
#     @transaction.atomic
#     def create(self, request):
#         """
#         inset a Address API.

#         ---

#         """
#         _data = get_dict_data(request.data)

#         serializer = self.get_serializer(
#             context={'request': request}, data=_data)
#         if serializer.is_valid():
#             _object = serializer.save()
#             serializer = AddressInfoSerializer(instance=_object)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         else:
#             raise ProjectException(
#                 807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

#     @swagger_auto_schema(responses=get_response_schema('retrieve'))
#     def retrieve(self, request, pk=None):
#         """
#         get a Address API.

#         ---

#         """
#         if pk:
#             _object = self.get_object(pk)
#             if _object:
#                 serializer = self.get_serializer(instance=_object)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
#             else:
#                 raise ProjectException(820, _('not found'), _(
#                     'This primary key not found.'), status.HTTP_404_NOT_FOUND)
#         else:
#             raise ProjectException(813, _('validation error'), _(
#                 'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

#     @swagger_auto_schema(responses=get_response_schema('update'))
#     # @execute_with_permission('Address', 'update')
#     @transaction.atomic
#     def partial_update(self, request, pk=None):
#         """
#         update a Address partial API.

#         ---

#         """
#         if pk:
#             _object = self.get_object(pk)
#             if _object:
#                 _data = get_dict_data(request.data)
#                 serializer = self.get_serializer(
#                     context={'request': request}, instance=_object, data=_data, partial=True)
#                 if serializer.is_valid():
#                     _object = serializer.save()
#                     serializer = AddressInfoSerializer(instance=_object)
#                     return Response(serializer.data)
#                 else:
#                     raise ProjectException(
#                         807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
#             else:
#                 raise ProjectException(820, _('not found'), _(
#                     'This primary key not found.'), status.HTTP_404_NOT_FOUND)
#         else:
#             raise ProjectException(813, _('validation error'), _(
#                 'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

#     @swagger_auto_schema(responses=get_response_schema('delete'))
#     # @execute_with_permission('Address', 'delete')
#     @transaction.atomic
#     def destroy(self, request, pk=None):
#         """
#         delete a Address  API.

#         ---

#         """
#         if pk:
#             _object = self.get_object(pk)
#             if _object:
#                 _object.delete()
#                 return Response(status=status.HTTP_204_NO_CONTENT)
#             else:
#                 raise ProjectException(820, _('not found'), _(
#                     'This primary key not found.'), status.HTTP_404_NOT_FOUND)
#         else:
#             raise ProjectException(813, _('validation error'), _(
#                 'Set the primary key.'), status.HTTP_400_BAD_REQUEST)







    # queryset = UserFileModel.objects.all()
    # serializer_class = UserFileSerializer
    # permission_classes = ([IsAuthenticated])
    # renderer_classes = (JSONRenderer,)
    # parser_classes = (JSONParser,)

    # def get_parsers(self):
    #     # (hasattr(self,'name') and self.name in ["Upload",])
    #     action_map = list(self.action_map.values())
    #     _action = ["some", "status", "trash", "recycle"]
    #     if any(item in action_map for item in _action):
    #         # if ["some","status"] in action_map
    #         parser_classes = [JSONParser]
    #     elif ("upload" in action_map):
    #         parser_classes = [MultiPartParser]
    #     else:
    #         parser_classes = [MultiPartParser]

    #     return [parser() for parser in parser_classes]

    # def get_response_schema(action):
    #     # response_schema_dict
    #     responses = {}
    #     rsd = {
    #         "200":
    #         UserFileSchemaSerializer,
    #         "200List":
    #         UserFileListSchemaSerializer,
    #         "200_OK":
    #         openapi.Response({}),
    #         "201":
    #         UserFileSchemaSerializer,
    #         "204":
    #         openapi.Response({}),
    #         "400":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_some":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "401_token":
    #         openapi.Response(
    #             description="UNAUTHORIZE",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "401": {
    #                         "status": "failed",
    #                         "code": 401,
    #                         "message": "Unauthorized",
    #                         "detail": "Authentication error.",
    #                     },
    #                     "440": {
    #                         "status": "failed",
    #                         "code": 440,
    #                         "message": "Unauthorized",
    #                         "detail": "Your account has expired.",
    #                     },
    #                     "441": {
    #                         "status": "failed",
    #                         "code": 441,
    #                         "message": "Unauthorized",
    #                         "detail": "The token is invalid for this system.",
    #                     },
    #                     "442": {
    #                         "status": "failed",
    #                         "code": 442,
    #                         "message": "Unauthorized",
    #                         "detail": "The access token has expired.",
    #                     },
    #                     "443": {
    #                         "status": "failed",
    #                         "code": 443,
    #                         "message": "Unauthorized",
    #                         "detail": "The refresh token has expired.",
    #                     },
    #                     "445": {
    #                         "status": "failed",
    #                         "code": 445,
    #                         "message": "Unauthorized",
    #                         "detail": "The refresh token is invalid.",
    #                     },
    #                     "801": {
    #                         "status": "failed",
    #                         "code": 801,
    #                         "message": "authentication error",
    #                         "detail": "Authentication error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "403":
    #         openapi.Response(
    #             description="Forbidden",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "821": {
    #                         "status":
    #                         "failed",
    #                         "code":
    #                         821,
    #                         "message":
    #                         _("validation error"),
    #                         "detail":
    #                         _("You do not have permission to perform this action."
    #                           ),
    #                         "data": {},
    #                     },
    #                 }
    #             },
    #         ),
    #         "404":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "820": {
    #                         "status": "failed",
    #                         "code": 820,
    #                         "message": "not found",
    #                         "detail": "This primary key not found",
    #                     },
    #                 }
    #             },
    #         ),
    #         "807":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },

    #                 }
    #             },
    #         ),
    #         "800":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "800": {
    #                         "status": "failed",
    #                         "code": 800,
    #                         "message": "unknown error",
    #                         "detail": "Unknown error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "813":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_status":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "827": {
    #                         "status": "failed",
    #                         "code": 827,
    #                         "message": "validation error",
    #                         "detail": "Status field is Invalid.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "404_multi":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "811": {
    #                         "status": "failed",
    #                         "code": 845,
    #                         "message": "not found",
    #                         "detail": "Some users are not in the system.",
    #                     },
    #                     "819": {
    #                         "status": "failed",
    #                         "code": 819,
    #                         "message": "not found",
    #                         "detail": "Primary keys list is empty.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "sample":
    #         SampleResponseSerializer,
    #         "200_some":
    #         SampleSomeVirResponseSerializer
    #     }
    #     if action in ["list"]:
    #         responses = {"200": rsd["200List"], "400": rsd["807"]}
    #     elif action in ["create"]:
    #         responses = {"201": rsd["201"],
    #                      "400": rsd["807"], "401": rsd["401_token"]}
    #     elif action == "retrieve":
    #         responses = {"200": rsd["200"],
    #                      "400": rsd["400"], "404": rsd["404"]}
    #     elif action == "update":
    #         responses = {"200": rsd["200"], "404": rsd["404"],
    #                      "400": rsd["400"], "401": rsd["401_token"]}
    #     elif action == "delete":
    #         responses = {"204": rsd["204"], "400": rsd["813"],
    #                      "401": rsd["401_token"], "404": rsd["404"]}
    #     return responses

    # def get_permissions(self):
    #     if self.action in ['list', 'retrieve']:
    #         permission_classes = [IsAuthenticated, ]
    #     else:
    #         permission_classes = [IsAuthenticated, ]

    #     return [permission() for permission in permission_classes]

    # def get_serializer_class(self):
    #     if self.action in ['list', 'retrieve']:
    #         return UserFileInfoSerializer
    #     elif self.action in ['partial_update']:
    #         return UserFileUpdateSerializer
    #     return super().get_serializer_class()

    # def get_queryset(self):
    #     queryset = self.queryset
    #     _user = self.request.user
    #     list_role = get_user_roles(_user)

    #     return queryset

    # def filter_queryset(self, queryset):
    #     _filter = {}
    #     if 'admin' in self.request.query_params and self.request.query_params['admin']:
    #         _admin = self.request.query_params['admin']
    #         _filter.update({'admin_id': _admin})
    #     if 'evidence' in self.request.query_params and self.request.query_params['evidence']:
    #         _evidence = self.request.query_params['evidence']
    #         _filter.update({'evidence_id': _evidence})

    #     queryset = queryset.filter(**_filter).distinct()
    #     return queryset

    # def get_object(self, pk=None):
    #     if pk:
    #         try:
    #             _object = self.get_queryset().get(pk=pk)
    #             return _object
    #         except ObjectDoesNotExist:
    #             return None

    # @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=UserFileFilterQuerySerializer)
    # def list(self, request):
    #     """
    #     get list of UserFile API.

    #     ---

    #     """
    #     _queryset = self.get_queryset()
    #     _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
    #     _count = _queryset.count()
    #     if _count == 0:
    #         return Response({}, status=status.HTTP_204_NO_CONTENT)

    #     _queryset, _total_page_num = get_response_data(request, _queryset)
    #     serializer = self.get_serializer(_queryset, many=True)


    #     _evidences=[{'id':i.id,'title':i.title,'description':i.description,'media':i.media} for i in  UserEvidenceModel.objects.all()]
       
    #     return Response({
    #         'list': serializer.data,
    #         'evidences':_evidences,
    #         'total_page_num': _total_page_num,
    #         'total_row': _count
    #     })

    # @swagger_auto_schema(responses=get_response_schema('create'))
    # # @execute_with_permission('UserFile', 'create')
    # @transaction.atomic
    # def create(self, request):
    #     """
    #     inset a UserFile API.

    #     ---

    #     """
    #     _data = get_dict_data(request.data)

    #     serializer = self.get_serializer(
    #         context={'request': request}, data=_data)
    #     if serializer.is_valid():
    #         _object = serializer.save()
    #         serializer = UserFileInfoSerializer(instance=_object)
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     else:
    #         raise ProjectException(
    #             807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)

    # @swagger_auto_schema(responses=get_response_schema('retrieve'))
    # def retrieve(self, request, pk=None):
    #     """
    #     get a UserFile API.

    #     ---

    #     """
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object:
    #             serializer = self.get_serializer(instance=_object)
    #             return Response(serializer.data, status=status.HTTP_200_OK)
    #         else:
    #             raise ProjectException(820, _('not found'), _(
    #                 'This primary key not found.'), status.HTTP_404_NOT_FOUND)
    #     else:
    #         raise ProjectException(813, _('validation error'), _(
    #             'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    # @swagger_auto_schema(responses=get_response_schema('update'))
    # # @execute_with_permission('UserFile', 'update')
    # @transaction.atomic
    # def partial_update(self, request, pk=None):
    #     """
    #     update a UserFile partial API.

    #     ---

    #     """
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object:
    #             _data = get_dict_data(request.data)
    #             serializer = self.get_serializer(
    #                 context={'request': request}, instance=_object, data=_data, partial=True)
    #             if serializer.is_valid():
    #                 _object = serializer.save()
    #                 serializer = UserFileInfoSerializer(instance=_object)
    #                 return Response(serializer.data)
    #             else:
    #                 raise ProjectException(
    #                     807, _('validation error'), serializer.errors, status.HTTP_400_BAD_REQUEST)
    #         else:
    #             raise ProjectException(820, _('not found'), _(
    #                 'This primary key not found.'), status.HTTP_404_NOT_FOUND)
    #     else:
    #         raise ProjectException(813, _('validation error'), _(
    #             'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    # @swagger_auto_schema(responses=get_response_schema('delete'))
    # # @execute_with_permission('UserFile', 'delete')
    # @transaction.atomic
    # def destroy(self, request, pk=None):
    #     """
    #     delete a UserFile  API.

    #     ---

    #     """
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object:
    #             _object.delete()
    #             return Response(status=status.HTTP_204_NO_CONTENT)
    #         else:
    #             raise ProjectException(820, _('not found'), _(
    #                 'This primary key not found.'), status.HTTP_404_NOT_FOUND)
    #     else:
    #         raise ProjectException(813, _('validation error'), _(
    #             'Set the primary key.'), status.HTTP_400_BAD_REQUEST)




    # queryset = UserModel.objects.all()
    # serializer_class = UserSerializer
    # permission_classes = ([AllowAny])
    # renderer_classes = (JSONRenderer,)
    # parser_classes = (JSONParser,)

    # def get_parsers(self):
    #     if (hasattr(self, 'action') and self.action in ["upload", ]) or (hasattr(self, 'name') and self.name in ["Upload", ]):
    #         parser_classes = [MultiPartParser]
    #     else:
    #         parser_classes = [JSONParser]

    #     return [parser() for parser in parser_classes]

    # def get_response_schema(action):
    #     # response_schema_dict
    #     responses = {}
    #     rsd = {
    #         "200":
    #         UserSchemaSerializer,
    #         "200List":
    #         UserListSchemaSerializer,
    #         "201":
    #         UserSchemaSerializer,
    #         "204":
    #         openapi.Response({}),
    #         "400":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "401_token":
    #         openapi.Response(
    #             description="UNAUTHORIZE",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "401": {
    #                         "status": "failed",
    #                         "code": 401,
    #                         "message": "Unauthorized",
    #                         "detail": "Authentication error.",
    #                     },
    #                     "440": {
    #                         "status": "failed",
    #                         "code": 440,
    #                         "message": "Unauthorized",
    #                         "detail": "Your account has expired.",
    #                     },
    #                     "441": {
    #                         "status": "failed",
    #                         "code": 441,
    #                         "message": "Unauthorized",
    #                         "detail": "The token is invalid for this system.",
    #                     },
    #                     "442": {
    #                         "status": "failed",
    #                         "code": 442,
    #                         "message": "Unauthorized",
    #                         "detail": "The access token has expired.",
    #                     },
    #                     "443": {
    #                         "status": "failed",
    #                         "code": 443,
    #                         "message": "Unauthorized",
    #                         "detail": "The refresh token has expired.",
    #                     },
    #                     "445": {
    #                         "status": "failed",
    #                         "code": 445,
    #                         "message": "Unauthorized",
    #                         "detail": "The refresh token is invalid.",
    #                     },
    #                     "801": {
    #                         "status": "failed",
    #                         "code": 801,
    #                         "message": "authentication error",
    #                         "detail": "Authentication error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "403":
    #         openapi.Response(
    #             description="Forbidden",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "821": {
    #                         "status":
    #                         "failed",
    #                         "code":
    #                         821,
    #                         "message":
    #                         _("validation error"),
    #                         "detail":
    #                         _("You do not have permission to perform this action."
    #                           ),
    #                         "data": {},
    #                     },
    #                 }
    #             },
    #         ),
    #         "848":
    #         openapi.Response(
    #             description="Forbidden",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "848": {
    #                         "status": "failed",
    #                         "code": 848,
    #                         "message": _("validation error"),
    #                         "detail": _("You do not have access to delete your role."),
    #                         "data": {},
    #                     },
    #                 }
    #             },
    #         ),
    #         "404":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "820": {
    #                         "status": "failed",
    #                         "code": 820,
    #                         "message": "not found",
    #                         "detail": "This primary key not found",
    #                     },
    #                 }
    #             },
    #         ),
    #         "819":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "819": {
    #                         "status": "failed",
    #                         "code": 819,
    #                         "message": "not found",
    #                         "detail": "Primary keys list is empty.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "800":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "800": {
    #                         "status": "failed",
    #                         "code": 800,
    #                         "message": "unknown error",
    #                         "detail": "Unknown error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "807":
    #             openapi.Response(
    #                 description="Bad request",
    #                 schema=SampleResponseSerializer,
    #                 examples={
    #                     "application/json": {
    #                         "807": {
    #                             "status": "failed",
    #                             "code": 807,
    #                             "message": "validation error",
    #                             "detail": "System default error.",
    #                         },
    #                     }
    #                 },
    #         ),
    #         "813":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "852":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "852": {
    #                         "status": "failed",
    #                         "code": 852,
    #                         "message": "runtime error",
    #                         "detail": "role error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_reg":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "809": {
    #                         "status": "failed",
    #                         "code": 809,
    #                         "message": "validation error",
    #                         "detail": "Email exist.",
    #                     },
    #                     "810": {
    #                         "status": "failed",
    #                         "code": 810,
    #                         "message": "validation error",
    #                         "detail": "Username exist.",
    #                     },
    #                     "811": {
    #                         "status": "failed",
    #                         "code": 811,
    #                         "message": "validation error",
    #                         "detail": "Username cannot les than 4 digit.",
    #                     },
    #                     "812": {
    #                         "status": "failed",
    #                         "code": 812,
    #                         "message": "validation error",
    #                         "detail": "password cannot les than 8 digit.",
    #                     },
    #                     "846": {
    #                         "status": "failed",
    #                         "code": 846,
    #                         "message": "validation error",
    #                         "detail": "Set the role.",
    #                     },
    #                     "852": {
    #                         "status": "failed",
    #                         "code": 852,
    #                         "message": "runtime error",
    #                         "detail": "role error.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400pk":
    #             openapi.Response(
    #                 description="Bad request",
    #                 schema=SampleResponseSerializer,
    #                 examples={
    #                     "application/json": {
    #                         "807": {
    #                             "status": "failed",
    #                             "code": 807,
    #                             "message": "validation error",
    #                             "detail": "System default error.",
    #                         },
    #                         "809": {
    #                             "status": "failed",
    #                             "code": 809,
    #                             "message": "validation error",
    #                             "detail": "Email exist.",
    #                         },
    #                         "810": {
    #                             "status": "failed",
    #                             "code": 810,
    #                             "message": "validation error",
    #                             "detail": "Username exist.",
    #                         },
    #                         "811": {
    #                             "status": "failed",
    #                             "code": 811,
    #                             "message": "validation error",
    #                             "detail": "Username cannot les than 4 digit.",
    #                         },
    #                         "812": {
    #                             "status": "failed",
    #                             "code": 812,
    #                             "message": "validation error",
    #                             "detail": "password cannot les than 8 digit.",
    #                         },
    #                         "813": {
    #                             "status": "failed",
    #                             "code": 813,
    #                             "message": "validation error",
    #                             "detail": "Set the primary key.",
    #                         },
    #                         "852": {
    #                             "status": "failed",
    #                             "code": 852,
    #                             "message": "runtime error",
    #                             "detail": "role error.",
    #                         },
    #                     }
    #                 },
    #         ),
    #         "400_forget":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "830": {
    #                         "status": "failed",
    #                         "code": 830,
    #                         "message": "validation error",
    #                         "detail": "Error at encoding of Security Question.",
    #                     },
    #                     "831": {
    #                         "status": "failed",
    #                         "code": 831,
    #                         "message": "validation error",
    #                         "detail": "Error at encoding of username and Security Question.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_reset":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "850": {
    #                         "status": "failed",
    #                         "code": 850,
    #                         "message": "validation error",
    #                         "detail": "Token is invalid.",
    #                     },
    #                 }
    #             },
    #         ),

    #         "400_status":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "807": {
    #                         "status": "failed",
    #                         "code": 807,
    #                         "message": "validation error",
    #                         "detail": "System default error.",
    #                     },
    #                     "827": {
    #                         "status": "failed",
    #                         "code": 827,
    #                         "message": "validation error",
    #                         "detail": "Status field is Invalid.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "400_role":
    #         openapi.Response(
    #             description="Bad request",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "813": {
    #                         "status": "failed",
    #                         "code": 813,
    #                         "message": "validation error",
    #                         "detail": "Set the primary key.",
    #                     },
    #                     "846": {
    #                         "status": "failed",
    #                         "code": 846,
    #                         "message": "validation error",
    #                         "detail": "Set the role.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "404_multi":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "811": {
    #                         "status": "failed",
    #                         "code": 845,
    #                         "message": "not found",
    #                         "detail": "Some users are not in the system.",
    #                     },
    #                     "819": {
    #                         "status": "failed",
    #                         "code": 819,
    #                         "message": "not found",
    #                         "detail": "Primary keys list is empty.",
    #                     },
    #                 }
    #             },
    #         ),
    #         "404_role":
    #         openapi.Response(
    #             description="Not found",
    #             schema=SampleResponseSerializer,
    #             examples={
    #                 "application/json": {
    #                     "820": {
    #                         "status": "failed",
    #                         "code": 820,
    #                         "message": "not found",
    #                         "detail": "This primary key not found",
    #                     },
    #                     "847": {
    #                         "status": "failed",
    #                         "code": 847,
    #                         "message": "not found",
    #                         "detail": "This role not found",
    #                     },
    #                 }
    #             },
    #         ),

    #         "200_forget":
    #         SampleForgetPasswordResponseSerializer,
    #         "sample":
    #         SampleResponseSerializer,
    #         "200_some":
    #         SampleSomeVirResponseSerializer,
    #         "200_OK":
    #         openapi.Response({}),
    #     }
    #     responses = dict()
    #     if action == ["list", "trash"]:
    #         responses = {"200": rsd["200List"],
    #                      "204": rsd["204"], "401": rsd["401_token"]}
    #     elif action == "create":
    #         responses = {"201": rsd["201"], "400": rsd["400_reg"]}
    #     elif action == "retrieve":
    #         responses = {"200": rsd["200"], "400": rsd["813"],
    #                      "401": rsd["401_token"], "404": rsd["404"]}
    #     elif action == "update":
    #         responses = {"200": rsd["200"], "400": rsd["400pk"],
    #                      "401": rsd["401_token"], "404": rsd["404"]}
    #     elif action == "delete":
    #         responses = {"204": rsd["204"], "400": rsd["813"],
    #                      "401": rsd["401_token"], "403": rsd["403"], "404": rsd["404"]}
    #     elif action in ["upload", "add_role"]:
    #         responses = {"200": rsd["200"], "400": rsd["400"],
    #                      "401": rsd["401_token"], "404": rsd["404"]}

    #     elif action == "activated":
    #         responses = {"200": rsd["200"], "400": rsd["816"]}
    #     elif action == "reactive":
    #         responses = {"200": rsd["sample"], "400": rsd["816"]}

    #     elif action == "forgotpassword":
    #         responses = {"200": rsd["200_forget"], "400": rsd["400_forget"]}
    #     elif action == "resetpassword":
    #         responses = {"200": rsd["sample"], "400": rsd["400_reset"]}

    #     elif action == "some":
    #         responses = {"200": rsd["200_some"], "204": rsd["204"],
    #                      "400": rsd["807"], "401": rsd["401_token"], "404": rsd["404_multi"]}
    #     elif action == "status":
    #         responses = {"200": rsd["200_OK"], "400": rsd["400_status"],
    #                      "401": rsd["401_token"], "404": rsd["404_multi"]}
    #     elif action == "recycle":
    #         responses = {"200": rsd["200_OK"], "400": rsd["813"],
    #                      "401": rsd["401_token"], "403": rsd["403"], "404": rsd["404"]}
    #     elif action == "delete_role":
    #         responses = {"204": rsd["204"], "400": rsd["400_role"],
    #                      "401": rsd["401_token"], "403": rsd["848"], "404": rsd["404_role"]}

    #     return responses

    # def get_serializer_class(self):
    #     if self.action in ['list', 'retrieve', 'me', 'trash']:
    #         return UserInfoSerializer
    #     elif self.action == "partial_update":
    #         return UserUpdateSerializer
    #     elif self.action == "resend":
    #         return UserResendPasswordSerializer
    #     elif self.action == "upload":
    #         return UserUploadSerializer
    #     elif self.action == 'status':
    #         return UserStatusSerializer
    #     elif self.action in ['some', 'recycle']:
    #         return NoneSerializer
    #     elif self.action in ['add_role', 'delete_role']:
    #         return UserRoleInSerializer
    #     else:
    #         return UserSerializer

    # def get_permissions(self):
    #     if self.action in ['resend', ]:
    #         permission_classes = [AllowAny, ]
    #     else:
    #         permission_classes = [IsAuthenticated, ]

    #     return [permission() for permission in permission_classes]

    # def get_queryset(self):
    #     queryset = self.queryset
    #     _user = self.request.user
    #     role_list = get_user_roles(_user)
    #     queryset = queryset.annotate(name=Concat(F("first_name"), V(
    #         " "), F("last_name"), output_field=CharField(), ))
    #     if not _user.pk:
    #         return queryset.filter(pk=-1)
    #     elif _user.is_superuser:  # superuser
    #         queryset = queryset.filter(is_superuser=False)
    #     elif _user.is_staff:  # admin
    #         queryset = queryset.filter(is_staff=False)
    #     elif 'agent' in role_list:  # agent
    #         queryset = queryset.filter(Q(owner=_user) | Q(parent__parent=_user) | Q(
    #             owner__parent__parent=_user)).exclude(is_staff=True, roles__role__title='agent')
    #     elif 'seller' in role_list:  # seller
    #         queryset = queryset.filter(Q(owner=_user)).exclude(
    #             is_staff=True, roles__role__title__in=['agent', 'seller'])
    #     elif 'client' in role_list:  # client
    #         queryset = queryset.filter(pk=-1)
    #     me = self.queryset.filter(pk=_user.pk)
    #     queryset = (queryset | me).distinct()
    #     return queryset

    # def filter_queryset(self, queryset, status=None):
    #     _filter = {}
       
    #     if 'status' in self.request.query_params and self.request.query_params['status']:
    #         _status = get_dict_data(self.request.GET).get('status', None)
    #         if type(_status) != type([]):
    #             _status = [_status, ]
    #         status_filter= get_status(_status)
    #         _filter.update(status_filter)
    #     else:
    #         _filter.update({'status__in': [0, 1],'is_delete':0})

    #     if 'role' in self.request.query_params and self.request.query_params['role']:
    #         _role = get_dict_data(self.request.GET).get('role', None)
    #         if type(_role) != type([]):
    #             _role = [_role, ]
    #         _filter.update({'roles__role__pk__in': _role})

        
    #     if 'search' in self.request.query_params and self.request.query_params['search']:
    #         _search = self.request.query_params['search']
    #         _filter1,_filter2,_filter3,_filter4={},{},{},{}
    #         _filter1.update(_filter)
    #         _filter2.update(_filter)
    #         _filter3.update(_filter)
    #         _filter4.update(_filter)
            
    #         _filter1.update({'first_name__icontains': _search})
    #         _filter2.update({'last_name__icontains': _search})
    #         _filter3.update({'cellphone__icontains': _search})
    #         _filter4.update({'email__icontains': _search})

    #         queryset = queryset.filter(Q(** _filter1)|Q(** _filter2)|Q(** _filter3)|Q(** _filter4)).distinct()
        
    #     else:
    #         queryset = queryset.filter(**_filter).distinct()

    #     return queryset

    # def get_object(self, pk=None):
    #     if pk:
    #         try:
    #             _object = self.get_queryset().get(pk=pk)
    #             return _object
    #         except ObjectDoesNotExist:
    #             pass

    # def get_object_trash(self, pk=None):
    #     if pk:
    #         try:
    #             _object = self.get_queryset().get(pk=pk, status=-1)
    #             return _object
    #         except ObjectDoesNotExist:
    #             pass

    # @swagger_auto_schema(responses=get_response_schema('list'))
    # @action(detail=False, methods=['get'])
    # def me(self, request):
    #     _user = request.user
    #     if _user:
    #         serializer = self.get_serializer(instance=_user)
    #         return Response(serializer.data)
    #     return Response(status=status.HTTP_400_BAD_REQUEST)

    # @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=UserFilterQuerySerializer)
    # def list(self, request):
    #     """
    #     get list of User API.

    #     ---

    #     """
    #     _queryset = self.get_queryset()
    #     # _queryset = _queryset.exclude(pk=request.user.pk)
    #     _queryset = self.filter_queryset(queryset=_queryset).order_by('pk')
    #     _count = _queryset.count()
    #     if _count == 0:
    #         return Response(status=status.HTTP_204_NO_CONTENT)

    #     _queryset, _total_page_num = get_response_data(request, _queryset)
    #     serializer = self.get_serializer(_queryset, many=True)
    #     return Response({
    #         'list': serializer.data,
    #         'total_page_num': _total_page_num,
    #         'total_row': _count
    #     })

    # @swagger_auto_schema(responses=get_response_schema('create'))
    # @transaction.atomic
    # def create(self, request):
    #     """
    #     create user API.
    #     ---
    #         role = ['admin','agent','seller','client']
    #         if role is 'seller' then agent field cannot be None.
    #     """
    #     _data = get_dict_data(request.data)
    #     serializer = self.get_serializer(
    #         context={'request': request}, data=_data)
    #     if serializer.is_valid():
    #         new_object = serializer.save()
    #         serializer = UserInfoSerializer(instance=new_object)
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     else:
    #         raise ProjectException(807,
    #                                _('validation error'), serializer.errors,
    #                                status.HTTP_400_BAD_REQUEST)

    # # @execute_with_permission('user', 'read')

    # @swagger_auto_schema(responses=get_response_schema('retrieve'))
    # def retrieve(self, request, pk=None):
    #     """
    #     get a User API.

    #     ---

    #     """
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object and (_object.status in [0, 1]):
    #             serializer = self.get_serializer(instance=_object)
    #             return Response(serializer.data)
    #         else:
    #             raise ProjectException(820, _('not found'),
    #                                    _('This primary key not found.'),
    #                                    status.HTTP_404_NOT_FOUND)
    #     else:
    #         raise ProjectException(813, _('validation error'),
    #                                _('Set the primary key.'),
    #                                status.HTTP_400_BAD_REQUEST)

    # # @execute_with_permission('user', 'update')

    # @swagger_auto_schema(responses=get_response_schema('update'))
    # @transaction.atomic
    # def partial_update(self, request, pk=None):
    #     """
    #     update a User partial API.

    #     ---
    #         birth_day : "1369/08/15"
    #         role = ['admin','agent','seller','client']
    #     """
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object and (_object.status in [0, 1]):
    #             _data = get_dict_data(request.data)
    #             serializer = self.get_serializer(context={'request': request},
    #                                               instance=_object, data=_data, partial=True)
    #             if serializer.is_valid():
    #                 _object = serializer.save()
    #                 serializer = UserInfoSerializer(instance=_object)
    #                 return Response(serializer.data)
    #             else:
    #                 raise ProjectException(807, _('validation error'),
    #                                        serializer.errors,
    #                                        status.HTTP_400_BAD_REQUEST)
    #         else:
    #             raise ProjectException(820, _('not found'),
    #                                    _('This primary key not found.'),
    #                                    status.HTTP_404_NOT_FOUND)
    #     else:
    #         raise ProjectException(813, _('validation error'),
    #                                _('Set the primary key.'),
    #                                status.HTTP_400_BAD_REQUEST)

    # # @execute_with_permission('user', 'delete')

    # @swagger_auto_schema(responses=get_response_schema('delete'))
    # @transaction.atomic
    # def destroy(self, request, pk=None):
    #     """
    #     delete a User  API.

    #     ---

    #     """
    #     _user = request.user
    #     if pk:
    #         if pk != _user.pk:
    #             _object = self.get_object(pk)
    #             if _object:
    #                 if allow_delete(user=_user, instance=_object):
    #                     if _object.status == -1:
    #                         _object.delete()
    #                     else:
    #                         _object.status = -1
    #                         _object.is_active = False
    #                         _object.save()
    #                     return Response(status=status.HTTP_204_NO_CONTENT)
    #                 else:
    #                     raise ProjectException(821, _('Forbidden'),
    #                                            _('You do not have permission to perform this action.'),
    #                                            status.HTTP_403_FORBIDDEN)
    #             else:
    #                 raise ProjectException(820, _('not found'),
    #                                        _('This primary key not found.'),
    #                                        status.HTTP_404_NOT_FOUND)
    #         else:
    #             raise ProjectException(821, _('Forbidden'),
    #                                    _('You do not have permission to perform this action.'),
    #                                    status.HTTP_403_FORBIDDEN)
    #     else:
    #         raise ProjectException(813, _('validation error'),
    #                                _('Set the primary key.'),
    #                                status.HTTP_400_BAD_REQUEST)

    # # @execute_with_permission('user', 'update')

    # @swagger_auto_schema(responses=get_response_schema('upload'))
    # @action(detail=True, methods=["patch"], parser_classes=(MultiPartParser, ),)
    # @transaction.atomic
    # def upload(self, request, pk=None):
    #     """
    #     upload avatar field for user API.
    #     ---

    #     """
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object and (_object.status in [0, 1]):
    #             _data = get_dict_data(request.data)
    #             serializer = self.get_serializer(context={"request": request},
    #                                               instance=_object, data=_data, partial=True,
    #                                               )
    #             if serializer.is_valid():
    #                 _object = serializer.save()
    #                 serializer = UserInfoSerializer(instance=_object)
    #                 return Response(serializer.data,
    #                                 status=status.HTTP_200_OK)
    #             else:
    #                 raise ProjectException(807, _('validation error'),
    #                                        serializer.errors,
    #                                        status.HTTP_400_BAD_REQUEST)
    #         else:
    #             raise ProjectException(820, _('not found'),
    #                                    _('This primary key not found.'),
    #                                    status.HTTP_404_NOT_FOUND)
    #     else:
    #         raise ProjectException(813, _('validation error'),
    #                                _('Set the primary key.'),
    #                                status.HTTP_400_BAD_REQUEST)

    # @transaction.atomic
    # @swagger_auto_schema(responses=get_response_schema("resend"))
    # @action(detail=False, methods=["post"], url_path='resend_verification_code')
    # def resend(self, request):
    #     """
    #     resend verification code to user.

    #     ---

    #     """
    #     serializer = self.get_serializer(
    #         context={"request": request}, data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(status=status.HTTP_200_OK)
    #     else:
    #         raise ProjectException(807, _("validation error"), serializer.errors,
    #                                status.HTTP_400_BAD_REQUEST,
    #                                )

    # # @execute_with_permission('user', 'some')

    # @swagger_auto_schema(method='delete',
    #                      request_body=openapi.Schema(
    #                          type=openapi.TYPE_OBJECT,
    #                          properties={
    #                              'id': openapi.Schema(type=openapi.TYPE_ARRAY,
    #                                                   items=openapi.Items(
    #                                                       type=openapi.TYPE_INTEGER),
    #                                                   description='A list of primary keys'),
    #                          }
    #                      ),
    #                      responses=get_response_schema('some')
    #                      )
    # @action(detail=False, methods=['delete'])
    # @transaction.atomic
    # def some(self, request):
    #     """
    #     delete some User API.

    #     ---

    #     """
    #     _user = request.user
    #     user_access = self.get_queryset().exclude(pk=_user.pk)
    #     _data = get_dict_data(request.data)
    #     _ids = _data['id']
    #     if type(_ids) == type([]):
    #         serializer = UserSomeSerializer(
    #             context={"request": request}, data=_data,)
    #         if serializer.is_valid():
    #             valid_data = serializer.validated_data
    #             _queryset = valid_data['id']
    #             if all(item in user_access for item in _queryset):
    #                 _id_in = [obj.pk for obj in _queryset]
    #                 _queryset = self.queryset.filter(pk__in=_id_in)
    #                 if _queryset:
    #                     _deletes = []
    #                     _v_deletes = []
    #                     _count = 0
    #                     _v_count = 0
    #                     for _obj in _queryset:
    #                         if _obj.pk == _user.pk:
    #                             raise ProjectException(821, _('Forbidden'),
    #                                                    _('You do not have permission to perform this action.'),
    #                                                    status.HTTP_403_FORBIDDEN)
    #                         if _obj.status == -1:
    #                             _count += 1
    #                             _deletes.append({str(_obj.id): _('deleted')})
    #                             _v_deletes.append(
    #                                 {str(_obj.id): _('deletion is not possible')})
    #                         else:
    #                             _v_count += 1
    #                             _v_deletes.append(
    #                                 {str(_obj.id): _('virtual deleted')})
    #                             _deletes.append(
    #                                 {str(_obj.id): _('virtual deletion is not possible')})

    #                     if _deletes or _v_deletes:
    #                         if _count > 0:
    #                             for _obj in _queryset:
    #                                 _obj.delete()
    #                             return Response(_deletes,
    #                                             status=status.HTTP_204_NO_CONTENT)
    #                         elif _v_count > 0:
    #                             for _obj in _queryset:
    #                                 _obj.is_delete=1
    #                                 _obj.is_active = False
    #                                 _obj.save()
    #                             return Response(_v_deletes, status=status.HTTP_200_OK)
    #                     else:
    #                             raise ProjectException(845, _('not found'),
    #                                                _("Some users are not in the system."),
    #                                                status.HTTP_404_NOT_FOUND)
                            
    #                 else:
    #                     raise ProjectException(819, _('not found error'),
    #                                            _('Primary keys list is empty.'),
    #                                            status.HTTP_404_NOT_FOUND)
    #             else:
    #                 raise ProjectException(821, _('Forbidden'),
    #                                        _('You do not have permission to perform this action.'),
    #                                        status.HTTP_403_FORBIDDEN)
    #         else:
    #             raise ProjectException(807, _('validation error'),
    #                                    serializer.errors,
    #                                    status.HTTP_400_BAD_REQUEST)
    #     else:
    #         raise ProjectException(807, _('validation error'),
    #                                _("id:[Expected a list of items but got type.]"),
    #                                status.HTTP_400_BAD_REQUEST)

    # # @execute_with_permission('user', 'status')

    # @swagger_auto_schema(responses=get_response_schema('status'))
    # @action(detail=False, methods=['patch'])
    # @transaction.atomic
    # def status(self, request):
    #     """
    #     change status some Users  API.

    #     ---

    #     """
    #     _user = request.user
    #     user_access = self.get_queryset().exclude(pk=_user.pk)
    #     _data = get_dict_data(request.data)
    #     serializer = self.get_serializer(
    #         context={"request": request}, data=_data,)
    #     if serializer.is_valid():
    #         valid_data = serializer.validated_data
    #         _users = valid_data['id']
    #         if all(item in user_access for item in _users):
    #             _status = valid_data['status']
    #             if _users and (_status is not None):
    #                 for obj in _users:
    #                     if obj.pk == _user.pk:
    #                         raise ProjectException(821, _('Forbidden'),
    #                                                _('You do not have permission to perform this action.'),
    #                                                status.HTTP_403_FORBIDDEN)
                        
    #                     if _status == -1:
    #                         obj.is_delete = 1
    #                         obj.is_active = False
    #                     elif _status == 1:
    #                         obj.status = _status
    #                         obj.is_active = True
    #                         obj.is_delete = 0
    #                 self.queryset.bulk_update(_users, ['status', 'is_delete'])
    #                 return Response(status=status.HTTP_200_OK)
    #             else:
    #                 raise ProjectException(819, _('not found error'),
    #                                        _('Primary keys list is empty.'),
    #                                        status.HTTP_404_NOT_FOUND)
    #         else:
    #             raise ProjectException(821, _('Forbidden'),
    #                                    _('You do not have permission to perform this action.'),
    #                                    status.HTTP_403_FORBIDDEN)
    #     else:
    #         raise ProjectException(807, _('validation error'),
    #                                serializer.errors,
    #                                status.HTTP_400_BAD_REQUEST)

    # # @execute_with_permission('user', 'trash')
    # @swagger_auto_schema(responses=get_response_schema('list'), query_serializer=UserTrashFilterQuerySerializer)
    # @action(detail=False, methods=['get'])
    # def trash(self, request):
    #     """
    #     get list of deleted Users API.

    #     ---
    #     status=(-1,'trash'),(0,'unpublish'),(1,'publish')

    #     """
    #     _queryset = self.get_queryset()
    #     _queryset = self.filter_queryset(
    #         queryset=_queryset, status=-1).order_by('id')
    #     _count = _queryset.count()
    #     if _count == 0:
    #         return Response(status=status.HTTP_204_NO_CONTENT)

    #     _queryset, _total_page_num = get_response_data(request, _queryset)
    #     serializer = self.get_serializer(_queryset, many=True)
    #     return Response({
    #         'list': serializer.data,
    #         'total_page_num': _total_page_num,
    #         'total_row': _count
    #     })

    # # @execute_with_permission('user', 'recycle')

    # @swagger_auto_schema(responses=get_response_schema("recycle"))
    # @action(detail=True, methods=['patch'])
    # @transaction.atomic
    # def recycle(self, request, pk=None):
    #     """
    #     recycle a User API.

    #     ---

    #     """
    #     _user = request.user
    #     if pk:
    #         if pk != _user.pk:
    #             _object = self.get_object(pk)
    #             if _object and _object.status == -1:
    #                 _object.status = 1
    #                 _object.is_active = True
    #                 _object.save()
    #                 return Response(status=status.HTTP_200_OK)
    #             else:
    #                 raise ProjectException(820, _('not found'), _('This primary key not found.'),
    #                                        status.HTTP_404_NOT_FOUND)
    #         else:
    #             raise ProjectException(821, _('Forbidden'), _(
    #                 'You do not have permission to perform this action.'), status.HTTP_403_FORBIDDEN)
    #     else:
    #         raise ProjectException(813, _('validation error'), _(
    #             'Set the primary key.'), status.HTTP_400_BAD_REQUEST)

    # # @execute_with_permission('userrole', 'create')

    # @swagger_auto_schema(responses=get_response_schema("add_role"))
    # # @action(detail=True,methods=["post"],url_path='role')
    # @transaction.atomic
    # def add_role(self, request, pk=None):
    #     """
    #     add role API
    #     role : [client,visitor,admin]
    #     """
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object:
    #             _data = get_dict_data(request.data)
    #             _data['user'] = _object.pk
    #             serializer = UserRoleSerializer(
    #                 context={"request": request}, data=_data, partial=True,)
    #             if serializer.is_valid():
    #                 serializer.save()
    #                 new_object = self.get_object(pk)
    #                 serializer = UserInfoSerializer(instance=new_object)
    #                 return Response(serializer.data, status=status.HTTP_200_OK)
    #             else:
    #                 raise ProjectException(
    #                     807,
    #                     _("validation error"),
    #                     serializer.errors,
    #                     status.HTTP_400_BAD_REQUEST,
    #                 )
    #         else:
    #             raise ProjectException(
    #                 820,
    #                 _("not found"),
    #                 _("This primary key not found."),
    #                 status.HTTP_404_NOT_FOUND,
    #             )
    #     else:
    #         raise ProjectException(
    #             813,
    #             _("validation error"),
    #             _("Set the primary key."),
    #             status.HTTP_400_BAD_REQUEST,
    #         )

    # @execute_with_permission('userrole', 'delete')
    # @swagger_auto_schema(responses=get_response_schema("delete_role"))
    # # @action(detail=True,methods=["delete"],url_path='role/(?P<role>[\w\-]+)')
    # @transaction.atomic
    # def delete_role(self, request, pk=None, role=None):
    #     """
    #     delete a role API.

    #     """
    #     _user = request.user
    #     if pk:
    #         _object = self.get_object(pk)
    #         if _object:
    #             if _object != _user:
    #                 if role:
    #                     try:
    #                         user_role = UserRoleModel.objects.get(
    #                             user=_object, role__pk=role)
    #                         user_role.delete()
    #                         return Response(status=status.HTTP_204_NO_CONTENT)
    #                     except:
    #                         raise ProjectException(
    #                             847, _("not found"), _("This role not found."),
    #                             status.HTTP_404_NOT_FOUND,
    #                         )
    #                 else:
    #                     raise ProjectException(
    #                         846,
    #                         _("validation error"),
    #                         _("Set the role."),
    #                         status.HTTP_400_BAD_REQUEST,
    #                     )
    #             else:
    #                 raise ProjectException(
    #                     848,
    #                     _("Forbidden"),
    #                     _("You do not have access to delete your role"),
    #                     status.HTTP_403_FORBIDDEN,
    #                 )
    #         else:
    #             raise ProjectException(
    #                 820,
    #                 _("not found"),
    #                 _("This primary key not found"),
    #                 status.HTTP_404_NOT_FOUND,
    #             )
    #     else:
    #         raise ProjectException(
    #             813,
    #             _("validation error"),
    #             _("Set the primary key."),
    #             status.HTTP_400_BAD_REQUEST,
    #         )

