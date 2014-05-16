from django.shortcuts import render
from django.http import Http404
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework.decorators import (api_view, authentication_classes,
        permission_classes)
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException, ParseError
from rest_framework import status
from docstore.models import Document

class NotAnObject(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'specified path includes non-object'

class InvalidCollection(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'alleged collection is invalid'

def get_oid(query_params):
    if 'id' not in query_params:
        return None
    try:
        return int(query_params['id'])
    except ValueError:
        raise ParseError("id must be integer")

def get_document(user):
    try:
        document = user.document
    except ObjectDoesNotExist:
        document = Document(json={})
        document.owner = user
    return document

def traverse(obj, parts, create=False):
    for part in parts:
        try:
            obj = obj[part]
        except TypeError:
            raise Http404
        except KeyError:
            if create:
                obj[part] = {}
                obj = obj[part]
            else:
                raise Http404
    return obj

def extract_oids(collection):
    if not isinstance(collection, list):
        raise InvalidCollection("not a list")
    invalid_items = [item for item in collection if 'id' not in item]
    try:
        return [int(item['id']) for item in collection]
    except (ValueError, KeyError):
        raise InvalidCollection("items with missing/invalid IDs")

def match_index(collection, oid, error=True):
    if not isinstance(collection, list):
        raise InvalidCollection("not a list")
    invalid_items = [item for item in collection if 'id' not in item]
    if invalid_items:
        raise InvalidCollection("{} invalid items".format(len(invalid_items)))
    matches = [
        index
        for index, item in enumerate(collection)
        if 'id' in item and item['id'] == oid
    ]
    if len(matches) == 0:
        if error:
            raise Http404
        return None
    if len(matches) > 1:
        raise InvalidCollection("duplicate id {}".format(oid))
    return matches[0]

def match(collection, oid, error=True):
    index = match_index(collection, oid, error=error)
    return collection[index]

@api_view(['HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@authentication_classes((SessionAuthentication,))
@permission_classes((IsAuthenticated,))
def document(request, path):
    parts = [part for part in path.split('/') if part]
    document = get_document(request.user)
    oid = get_oid(request.QUERY_PARAMS)

    if request.method == 'HEAD':
        obj = traverse(document.json, parts)
        return Response()

    elif request.method == 'GET':
        obj = traverse(document.json, parts)
        if oid is not None:
            return Response(match(obj, oid))
        else:
            return Response(obj)

    elif request.method == 'POST':
        obj = traverse(document.json, parts)
        if 'oid' in request.DATA:
            return Response({"detail": "cannot specify id for POST"},
                    status=status.HTTP_400_BAD_REQUEST)
        new_obj = request.DATA
        oid = 0
        existing_oids = set(extract_oids(obj))
        while oid in existing_oids:
            oid += 1
        new_obj['id'] = oid
        obj.append(new_obj)
        try:
            document.save()
        except ValidationError:
            return Response({"detail": "invalid JSON"},
                    status=status.HTTP_400_BAD_REQUEST)
        return Response(new_obj, status=status.HTTP_201_CREATED)

    elif request.method == 'PUT':
        if oid is not None:
            if parts:
                obj = traverse(document.json, parts[:-1], create=True)
                last = parts[-1]
                if last not in obj:
                    obj[last] = []
                obj = obj[last]
            else:
                obj = document.json
            index = match_index(obj, oid, error=False)
            if index is not None:
                obj[index] = request.DATA
                newly_created = False
            else:
                new_obj = request.DATA
                new_obj.setdefault('id', oid)
                if new_obj['id'] != oid:
                    return Response({"detail": "item has mismatched id"},
                            status=status.HTTP_400_BAD_REQUEST)
                obj.append(new_obj)
                newly_created = True
        else:
            if parts:
                obj = traverse(document.json, parts[:-1], create=True)
                if not isinstance(obj, dict):
                    raise NotAnObject
                last = parts[-1]
                newly_created = (last not in obj)
                obj[last] = request.DATA
            else:
                document.json = request.DATA
                newly_created = False
        try:
            document.save()
        except ValidationError:
            return Response({"detail": "invalid JSON"},
                    status=status.HTTP_400_BAD_REQUEST)
        if newly_created:
            return Response(request.DATA, status=status.HTTP_201_CREATED)
        else:
            return Response(request.DATA, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        obj = traverse(document.json, parts)
        if oid is not None:
            obj = match(obj, oid)
            if request.DATA.get('id', oid) != oid:
                return Response({"detail": "item has mismatched id"},
                        status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(obj, dict):
            raise NotAnObject
        for key, data in request.DATA.items():
            obj[key] = data
        try:
            document.save()
        except ValidationError:
            return Response({"detail": "invalid JSON"},
                    status=status.HTTP_400_BAD_REQUEST)
        return Response(request.DATA, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        if oid is not None:
            obj = traverse(document.json, parts) if parts else document.json
            index = match_index(obj, oid)
            obj.pop(index)
        else:
            if parts:
                obj = traverse(document.json, parts[:-1])
                last = parts[-1]
                if last not in obj:
                    raise Http404
                del obj[last]
            else:
                document.json = {}
        try:
            document.save()
        except ValidationError:
            return Response({"detail": "invalid JSON"},
                    status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
