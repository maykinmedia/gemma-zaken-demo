import datetime
from itertools import groupby

from zac.demo.models import SiteConfiguration, client
from zac.demo.utils import api_response_list_to_dict


# Object Types API
def get_objecttype_choices() -> list:
    config = SiteConfiguration.get_solo()
    objecttypes_client = config.objecttypes_api.build_client()

    objecttypes_by_url = api_response_list_to_dict(
        objecttypes_client.list('objecttype')
    )
    objecttype_choices = [(url, obj['name']) for url, obj in objecttypes_by_url.items()]
    return objecttype_choices


def get_objecttype_melding() -> dict:
    config = SiteConfiguration.get_solo()
    objecttypes_client = config.objecttypes_api.build_client()
    return objecttypes_client.retrieve("objecttype", uuid=config.objecttypes_mor_objecttype_uuid)


# Objects API
def get_objects_grouped() -> dict:
    config = SiteConfiguration.get_solo()
    objects_client = config.objects_api.build_client()

    objects_list = objects_client.list("object")
    sorted(objects_list, key=lambda x: x["type"])

    groups = {}
    for object_type, objects in groupby(objects_list, key=lambda x: x['type']):
        groups[object_type] = list(objects)

    return groups


def create_object(data) -> dict:
    config = SiteConfiguration.get_solo()
    objects_client = config.objects_api.build_client()

    return objects_client.create("object", data=data)


def retrieve_object(url=None, uuid=None) -> dict:
    config = SiteConfiguration.get_solo()
    objects_client = config.objects_api.build_client()

    return objects_client.retrieve("object", url=url, uuid=uuid)
