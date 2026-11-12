from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.schemas.coreapi import ManualSchema
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Q, F
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _

from json import loads

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from ticket.serializers import *
from ticket.permissions import *


class TicketViewSet(viewsets.GenericViewSet):
    queryset = TicketModel.objects.all()

    def get_response_schema(action):
        # response_schema_dict
        responses = {}
        rsd = {
            "200": TicketInfoSerializer,
            "201": TicketSerializer,
            "204": openapi.Response({}),
            "400": openapi.Response(
                description="Bad request",
                schema=TicketSampleResponseSerializer,
                examples={
                    "application/json": {
                        "803": {
                            "status": "failed",
                            "code": 803,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                    }
                },
            ),
            "403": openapi.Response(
                description="Forbidden",
                schema=TicketSampleResponseSerializer,
                examples={
                    "application/json": {
                        "821": {
                            "status": "failed",
                            "code": 821,
                            "message": _("validation error"),
                            "detail": _(
                                "You do not have permission to perform this action."
                            ),
                            "data": {},
                        },
                    }
                },
            ),
            "404": openapi.Response(
                description="Not found",
                schema=TicketSampleResponseSerializer,
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
            "800": openapi.Response(
                description="Bad request",
                schema=TicketSampleResponseSerializer,
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
            "400res": openapi.Response(
                description="Bad request",
                schema=TicketSampleResponseSerializer,
                examples={
                    "application/json": {
                        "800": {
                            "status": "failed",
                            "code": 800,
                            "message": "unknown error",
                            "detail": "Unknown error.",
                        },
                        "803": {
                            "status": "failed",
                            "code": 803,
                            "message": "validation error",
                            "detail": "System default error.",
                        },
                        "853": {
                            "status": "failed",
                            "code": 853,
                            "message": "validation error",
                            "detail": "response exist.",
                        },
                    }
                },
            ),
            "refrence": TicketRefrenceSerializer,
            "response": TicketResponseSerializer,
        }
        if action == "create":
            responses = {"201": rsd["201"], "400": rsd["400"]}
        elif action == "replay":
            responses = {"201": rsd["201"], "404": rsd["404"], "400": rsd["800"]}
        elif action == "upload":
            responses = {"201": rsd["200"], "404": rsd["404"], "400": rsd["400"]}
        elif action == "resend":
            responses = {"201": rsd["resend"], "404": rsd["404"], "400": rsd["800"]}
        elif action == "refrence":
            responses = {"200": rsd["refrence"], "404": rsd["404"], "400": rsd["400"]}
        elif action == "response":
            responses = {
                "200": rsd["response"],
                "400": rsd["400res"],
                "403": rsd["403"],
                "404": rsd["404"],
            }

        return responses

    def get_serializer_class(self):
        if self.action in ["create", "replay"]:
            return TicketSerializer
        elif self.action == "upload":
            return MultiImageSerializer
        elif self.action == "list":
            return TicketInfoSerializer
        elif self.action == "inbox":
            return TicketInformationSerializer
        elif self.action == "refrence":
            return TicketRefrenceSerializer
        elif self.action == "response":
            return TicketResponseSerializer

    def get_permissions(self):
        if self.action in ["create", "list", "response", "replay", "upload"]:
            permission_classes = [IsAuthenticated]
        elif self.action in ["inbox", "refrence"]:
            permission_classes = [IsSuperUserOrAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        _queryset = self.queryset
        _user = self.request.user
        _filter = {"parent__isnull": True, "sender_id": _user.pk, "kind": "actor"}
        _queryset = _queryset.annotate(
            sender_first_name=F("sender__first_name"),
            sender_last_name=F("sender__last_name"),
        ).filter(**_filter)
        return _queryset

    def get_inbox_queryset(self):
        _queryset = self.queryset
        _filter = {"kind": "actor", "status": "wait"}
        _queryset = _queryset.annotate(
            sender_first_name=F("sender__first_name"),
            sender_last_name=F("sender__last_name"),
        ).filter(**_filter)
        return _queryset

    def get_object(self, pk=None):
        if pk:
            try:
                _object = self.queryset.get(pk=pk)
                return _object
            except ObjectDoesNotExist:
                pass

    def list(self, request):
        """
        list of my tickets.

        ---

        """
        _query = self.get_queryset()
        _count = _query.count()
        if _count == 0:
            return Response(status=status.HTTP_204_NO_CONTENT)

        _queryset = _query.order_by("id")
        _queryset, _total_page_num = get_response_data(request, _queryset)

        _serializer = self.get_serializer(_queryset, many=True)
        return Response(
            {
                "items": _serializer.data,
                "total_page_num": _total_page_num,
                "total_row": _count,
            }
        )

    @action(detail=False, methods=["get"])
    def inbox(self, request):
        """
        list of new tickets.

        ---

        """
        _query = self.get_inbox_queryset()
        _count = _query.count()
        if _count == 0:
            return Response(status=status.HTTP_204_NO_CONTENT)

        _queryset = _query.order_by("id")
        _queryset, _total_page_num = get_response_data(request, _queryset)

        _serializer = self.get_serializer(_queryset, many=True)
        return Response(
            {
                "items": _serializer.data,
                "total_page_num": _total_page_num,
                "total_row": _count,
            }
        )

    @transaction.atomic
    @swagger_auto_schema(responses=get_response_schema("create"))
    def create(self, request):
        """
        add a ticket.

        ---

        """
        _data = get_request_data(request.data)
        _serializer = self.get_serializer(context={"request": request}, data=_data)
        if _serializer.is_valid():
            _serializer.save()
            return Response(_serializer.data, status=status.HTTP_201_CREATED)
        else:
            raise TicketException(
                803,
                _("validation error"),
                _serializer.errors,
                status.HTTP_400_BAD_REQUEST,
            )
        raise TicketException(
            800, _("unkown error"), _("unkown error"), status.HTTP_400_BAD_REQUEST
        )

    @transaction.atomic
    @swagger_auto_schema(responses=get_response_schema("refrence"))
    @action(detail=True, methods=["post"])
    def refrence(self, request, pk=None):
        """
        refrence a ticket api.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_request_data(request.data)
                _serializer = self.get_serializer(
                    context={"request": request},
                    instance=_object,
                    data=_data,
                    partial=True,
                )
                if _serializer.is_valid():
                    _serializer.save()
                    return Response(_serializer.data)
                else:
                    raise TicketException(
                        803,
                        _("validation error"),
                        _serializer.errors,
                        status.HTTP_400_BAD_REQUEST,
                    )
            else:
                raise TicketException(
                    820,
                    _("not found"),
                    _("This primary key not found"),
                    status.HTTP_404_NOT_FOUND,
                )
        raise TicketException(
            800, _("unkown error"), _("unkown error"), status.HTTP_400_BAD_REQUEST
        )

    @transaction.atomic
    @swagger_auto_schema(responses=get_response_schema("response"))
    @action(detail=True, methods=["post"])
    def response(self, request, pk=None):
        """
        respanse a ticket api.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_request_data(request.data)
                _user = request.user
                if _user.is_staff or _object.refrence_id == _user.id:
                    _serializer = self.get_serializer(
                        context={"request": request}, data=_data
                    )
                    if _serializer.is_valid():
                        _serializer.validated_data["parent_id"] = _object.id
                        _serializer.save()
                        return Response(
                            _serializer.data, status=status.HTTP_201_CREATED
                        )
                    else:
                        raise TicketException(
                            803,
                            _("validation error"),
                            _serializer.errors,
                            status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    raise TicketException(
                        821,
                        _("validation error"),
                        _("You do not have permission to perform this action"),
                        status.HTTP_403_FORBIDDEN,
                    )
            else:
                raise TicketException(
                    820,
                    _("not found"),
                    _("This primary key not found"),
                    status.HTTP_404_NOT_FOUND,
                )
        raise TicketException(
            800, _("unkown error"), _("unkown error"), status.HTTP_400_BAD_REQUEST
        )

    @transaction.atomic
    @swagger_auto_schema(responses=get_response_schema("replay"))
    @action(detail=True, methods=["post"])
    def replay(self, request, pk=None):
        """
        reply a ticket api.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_request_data(request.data)
                _data.update({"parent_id": _object.id})
                _serializer = self.get_serializer(
                    context={"request": request}, data=_data
                )
                if _serializer.is_valid():
                    _serializer.validated_data["parent_id"] = _object.id
                    _serializer.save()
                    return Response(_serializer.data, status=status.HTTP_201_CREATED)
                else:
                    raise TicketException(
                        803,
                        _("validation error"),
                        _serializer.errors,
                        status.HTTP_400_BAD_REQUEST,
                    )
            else:
                raise TicketException(
                    820,
                    _("not found"),
                    _("This primary key not found"),
                    status.HTTP_404_NOT_FOUND,
                )
        raise TicketException(
            800, _("unkown error"), _("unkown error"), status.HTTP_400_BAD_REQUEST
        )

    @transaction.atomic
    @swagger_auto_schema(responses=get_response_schema("upload"))
    @action(
        detail=True,
        url_path="upload",
        url_name="upload",
        methods=["patch"],
        parser_classes=(MultiPartParser,),
    )
    def upload(self, request, pk=None):
        """
        upload a image for ticket.

        ---

        """
        if pk:
            _object = self.get_object(pk)
            if _object:
                _data = get_request_data(request.data)
                _user = request.user
                if _user.is_staff or _object.sender == _user:
                    _serializer = self.get_serializer(
                        context={"request": request},
                        instance=_object,
                        data=_data,
                        partial=True,
                    )
                    if _serializer.is_valid():
                        _serializer.save()
                        _serializer = TicketInfoSerializer(_object)
                        return Response(
                            _serializer.data, status=status.HTTP_201_CREATED
                        )
                    else:
                        raise TicketException(
                            803,
                            _("validation error"),
                            _serializer.errors,
                            status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    raise TicketException(
                        820,
                        _("not found"),
                        _("This primary key not found"),
                        status.HTTP_404_NOT_FOUND,
                    )
            raise TicketException(
                800, _("unkown error"), _("unkown error"), status.HTTP_400_BAD_REQUEST
            )


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


def get_request_data(data):
    from django.http import QueryDict

    if type(data) is QueryDict:
        return {
            k: data.getlist(k) if len(data.getlist(k)) > 1 else v
            for k, v in data.items()
        }
    elif type(data) is dict:
        return data
    return {}


def get_response_data(request, queryset):
    if (
        "page_size" in request.query_params
        and request.query_params["page_size"]
        and "page_num" in request.query_params
        and request.query_params["page_num"]
    ):
        _page_size = request.query_params["page_size"]
        _page_num = request.query_params["page_num"]
        _objects, _total_page_num = get_data(
            queryset, pagination=(_page_size, _page_num)
        )
    else:
        _objects, _total_page_num = get_data(queryset)

    return _objects, _total_page_num
