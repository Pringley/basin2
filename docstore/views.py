from django.shortcuts import render
from django.http import Http404
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework.decorators import (api_view, authentication_classes,
        permission_classes)
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from rest_framework import status
from docstore.models import Document

class NotAnObject(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'specified path includes non-object'

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
            raise NotAnObject
        except KeyError:
            if create:
                obj[part] = {}
                obj = obj[part]
            else:
                raise Http404
    return obj

@api_view(['HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
def document(request, path):
    parts = [part for part in path.split('/') if part]
    document = get_document(request.user)

    if request.method == 'HEAD':
        obj = traverse(document.json, parts)
        return Response()

    elif request.method == 'GET':
        obj = traverse(document.json, parts)
        return Response(obj)

    elif request.method == 'POST':
        obj = traverse(document.json, parts)
        if not isinstance(obj, list):
            return Response({"detail": "cannot POST to non-list"},
                    status=status.HTTP_405_METHOD_NOT_ALLOWED)
        obj.append(request.DATA)
        try:
            document.save()
        except ValidationError:
            return Response({"detail": "invalid JSON"},
                    status=status.HTTP_400_BAD_REQUEST)
        return Response(request.DATA, status=status.HTTP_201_CREATED)

    elif request.method == 'PUT':
        if len(parts) == 0:
            document.json = request.DATA
            newly_created = False
        else:
            obj = traverse(document.json, parts[:-1], create=True)
            if not isinstance(obj, dict):
                raise NotAnObject
            last = parts[-1]
            newly_created = (last not in obj)
            obj[last] = request.DATA
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
        obj = traverse(document.json, parts[:-1])
        last = parts[-1]
        if last not in obj:
            raise Http404
        del obj[last]
        return Response(status=status.HTTP_204_NO_CONTENT)
