from rest_framework import serializers, status
from django.utils.translation import gettext as _
from django.conf import settings
from django.db.models import Q, F
from ticket.models import *
from ticket.exceptions import TicketException
import jdatetime
from django.contrib.auth import get_user_model


class MultiImageSerializer(serializers.Serializer):

    image = serializers.ImageField(max_length=None, use_url=True)

    def validate(self, attrs):

        return super(MultiImageSerializer, self).validate(attrs)

    def update(self, instance, validated_data):
        _image = validated_data.get("image", None)
        _img = MultiImageModel.objects.create(ticket=instance, image=_image)
        _img.save()

        return instance


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketModel
        fields = (
            "id",
            "subject",
            "content",
        )

    subject = serializers.CharField(required=False, max_length=130, allow_blank=True)
    content = serializers.CharField(required=False, max_length=None, allow_blank=True)

    def validate(self, attrs):
        return super(TicketSerializer, self).validate(attrs)

    def update(self, instance, validated_data):
        validated_data["sender"] = self.context["request"].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

    def create(self, validated_data):
        # validated_data['created_by'] =self.context['request'].user
        validated_data["sender"] = self.context["request"].user
        validated_data["status"] = "wait"
        _new_instance = self.Meta.model(**validated_data)
        _new_instance.save()
        return _new_instance


class TicketResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketModel
        fields = (
            "id",
            "subject",
            "content",
        )

    subject = serializers.CharField(required=False, max_length=130, allow_blank=True)
    content = serializers.CharField(required=False, max_length=None, allow_blank=True)

    def validate(self, attrs):
        _user = self.context["request"].user
        _parent = attrs.get("parent", None)

        if _parent:
            try:
                self.Meta.model.objects.get(parent_id=_parent)
                raise TicketException(
                    853,
                    _("validation error"),
                    _("response exist"),
                    status.HTTP_400_BAD_REQUEST,
                )
            except self.Meta.model.MultipleObjectsReturned:
                raise TicketException(
                    853,
                    _("validation error"),
                    _("response exist"),
                    status.HTTP_400_BAD_REQUEST,
                )
            except self.Meta.model.DoesNotExist:
                pass
        # _is_raise_error=True
        # if _user.is_staff:
        #     _is_raise_error=False
        # if  _parent and _parent.refrence and _parent.refrence_id == _user.id:
        #      _is_raise_error=False

        # if _is_raise_error:
        #     raise TicketException(0,_('validation error'),_('permission denied'),status.HTTP_403_FORBIDDEN)

        return super(TicketResponseSerializer, self).validate(attrs)

    def update(self, instance, validated_data):
        _parent = validated_data.get("parent_id", None)

        validated_data["sender"] = self.context["request"].user
        validated_data["kind"] = "responder"
        validated_data["status"] = "done"
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

    def create(self, validated_data):
        _parent = validated_data.get("parent_id", None)

        validated_data["sender"] = self.context["request"].user
        validated_data["kind"] = "responder"
        validated_data["status"] = "done"
        _new_instance = self.Meta.model(**validated_data)
        _new_instance.save()
        return _new_instance


class TicketRefrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketModel
        fields = (
            "id",
            "sender_id",
            "sender_name",
            "date",
            "subject",
            "content",
            "refrence",
        )

    refrence = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=get_user_model().objects.all(),
        error_messages={
            "does_not_exist": "user does not exist",
            "invalid": "invalid value",
        },
    )
    sender_id = serializers.IntegerField(read_only=True)
    sender_name = serializers.SerializerMethodField(
        read_only=True, method_name="get_name"
    )
    date = serializers.SerializerMethodField(read_only=True, method_name="get_date")
    subject = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)

    def validate(self, attrs):
        return super(TicketRefrenceSerializer, self).validate(attrs)

    def update(self, instance, validated_data):
        validated_data["refrence_by"] = self.context["request"].user
        validated_data["status"] = "review"

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.is_refrence = True
        instance.save()

        return instance

    def create(self, validated_data):
        validated_data["refrence_by"] = self.context["request"].user
        validated_data["status"] = "review"

        _new_instance = self.Meta.model(**validated_data)
        _new_instance.save()
        return _new_instance

    def get_name(self, obj):
        _name = "".join([obj.sender.first_name, " ", obj.sender.last_name])
        return _name

    def get_date(self, obj):
        return self.gregorian_to_jalali(obj.date)

    def gregorian_to_jalali(self, date):

        if date:
            return jdatetime.date.fromgregorian(date=date).strftime("%Y/%m/%d")
        return ""


class TicketInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    sender_id = serializers.IntegerField(read_only=True)
    sender_name = serializers.SerializerMethodField(
        read_only=True, method_name="get_name"
    )
    date = serializers.SerializerMethodField(read_only=True, method_name="get_date")
    subject = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    subtickets = serializers.SerializerMethodField(
        read_only=True, method_name="get_children"
    )
    ticket_image = MultiImageSerializer(read_only=True, many=True)

    def get_children(self, obj):
        serializer = TicketInfoSerializer(
            instance=obj.subtickets.annotate(
                sender_first_name=F("sender__first_name"),
                sender_last_name=F("sender__last_name"),
            ).all(),
            many=True,
        )
        return serializer.data

    def get_name(self, obj):
        _name = "".join([obj.sender.first_name, " ", obj.sender.last_name])
        return _name

    def get_date(self, obj):
        return self.gregorian_to_jalali(obj.date)

    def gregorian_to_jalali(self, date):
        if date:
            return jdatetime.date.fromgregorian(date=date).strftime("%Y/%m/%d")
        return ""


class TicketInformationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    sender_id = serializers.IntegerField(read_only=True)
    sender_name = serializers.SerializerMethodField(
        read_only=True, method_name="get_name"
    )
    date = serializers.SerializerMethodField(read_only=True, method_name="get_date")
    subject = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    def get_name(self, obj):
        _name = "".join([obj.sender.first_name, " ", obj.sender.last_name])
        return _name

    def get_date(self, obj):
        return self.gregorian_to_jalali(obj.date)

    def gregorian_to_jalali(self, date):
        if date:
            return jdatetime.date.fromgregorian(date=date).strftime("%Y/%m/%d")
        return ""


class TicketSampleResponseSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=None)
    code = serializers.IntegerField()
    message = serializers.CharField(max_length=None)
    detail = serializers.CharField(max_length=None)
    # data    = serializers.DictField(child=serializers.CharField(), allow_empty=True)
