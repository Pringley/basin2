from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework import status
from docstore.models import Document
import json

def join(url, part):
    return url.rstrip('/') + '/' + part

class DocumentViewTest(TestCase):

    def setUp(self):
        self.item2 = {'id': 2, 'val': 'foo'}
        self.item3 = {'id': 3, 'val': 'bar'}
        self.item5 = {'id': 5, 'val': 'baz'}
        self.json = {
            'list': ['a', 'b', 'c'],
            'dict': {'q': 2, 'z': 3, 'a': 4},
            'nested': {
                '1': {'a': 'b', 'c': 'd'},
                '2': {'foo': 'bar'},
            },
            'items': [
                self.item2,
                self.item3,
                self.item5,
            ],
            'dupitems': [
                self.item2,
                self.item3,
                self.item2,
            ],
            'has spaces': [4, 5, 6],
        }
        self.user = User.objects.create_user(username='bob', email='bob@mail.com',
                password='123')
        self.document = Document.objects.create(owner=self.user, json=self.json)
        self.client.login(username='bob', password='123')

    def assertGet(self, url, expected=None, code=status.HTTP_200_OK):
        response = self.client.get(url)
        content = json.loads(response.content.decode())
        if code is not None:
            self.assertEqual(response.status_code, code,
                    msg=response.content)
        if expected is not None:
            self.assertEqual(expected, content)

    def assertPost(self, url, data, code=status.HTTP_201_CREATED):
        encoded_data = json.dumps(data)
        response = self.client.post(url, data=encoded_data,
                content_type='application/json')
        if code is not None:
            self.assertEqual(response.status_code, code,
                    msg=response.content)

    def assertPut(self, url, data, code=None, checkGet=True):
        encoded_data = json.dumps(data)
        response = self.client.put(url, data=encoded_data,
                content_type='application/json')
        if code is not None:
            self.assertEqual(response.status_code, code,
                    msg=response.content)
        if checkGet:
            self.assertGet(url, expected=data)

    def assertDelete(self, url, code=status.HTTP_204_NO_CONTENT, checkGet=True):
        response = self.client.delete(url)
        if code is not None:
            self.assertEqual(response.status_code, code,
                    msg=response.content)
        if checkGet:
            self.assertGet(url, code=status.HTTP_404_NOT_FOUND)

    def assertPatch(self, url, data, code=status.HTTP_200_OK):
        encoded_data = json.dumps(data)
        response = self.client.patch(url, data=encoded_data,
                CONTENT_TYPE='application/json')
        if code is not None:
            self.assertEqual(response.status_code, code,
                    msg=response.content)

    def testGet(self):
        self.assertGet('/doc', self.json)
        self.assertGet('/doc/list', self.json['list'])
        self.assertGet('/doc/dict', self.json['dict'])
        self.assertGet('/doc/has%20spaces', self.json['has spaces'])
        self.assertGet('/doc/nested', self.json['nested'])
        self.assertGet('/doc/nested/1', self.json['nested']['1'])
        self.assertGet('/doc/nested/2/foo', self.json['nested']['2']['foo'])
        self.assertGet('/doc/ldsfasdin', code=status.HTTP_404_NOT_FOUND)
        self.assertGet('/doc/nested/asdflin', code=status.HTTP_404_NOT_FOUND)

    def testGetQuery(self):
        self.assertGet('/doc/items', self.json['items'])
        self.assertGet('/doc/items?id=2', self.item2)
        self.assertGet('/doc/items?id=3', self.item3)
        self.assertGet('/doc/items?id=5', self.item5)
        self.assertGet('/doc/items?id=1', code=status.HTTP_404_NOT_FOUND)
        self.assertGet('/doc/list?id=1', code=status.HTTP_400_BAD_REQUEST)
        self.assertGet('/doc/dict?id=1', code=status.HTTP_400_BAD_REQUEST)
        self.assertGet('/doc/dupitems?id=2', code=status.HTTP_400_BAD_REQUEST)

    def testPost(self):
        self.assertPut('/doc/newitems', [])
        self.assertPost('/doc/newitems', {'val': 1})
        self.assertPost('/doc/newitems', {'val': 2})
        self.assertPost('/doc/newitems', {'val': 13})
        collection = json.loads(self.client.get('/doc/newitems').content.decode())
        values = {item['val'] for item in collection}
        self.assertEqual({1, 2, 13}, values)

    def testPut(self):
        self.assertPut('/doc/foo_new', {'new': 'data'}, code=status.HTTP_201_CREATED)
        self.assertPut('/doc/list', [4, 5, 6], code=status.HTTP_200_OK)
        self.assertPut('/doc/nested/3', {'more': 'new data'},
                code=status.HTTP_201_CREATED)
        self.assertPut('/doc/nested/3', {'different': 'data'},
                code=status.HTTP_200_OK)
        self.assertPut('/doc/newly/created/deep/tree', {'yet': 'more'},
                code=status.HTTP_201_CREATED)

    def testPutQuery(self):
        self.assertPut('/doc/items?id=1', {'id': 1, 'val': 'spam'},
                code=status.HTTP_201_CREATED)
        self.assertPut('/doc/items?id=1', {'id': 1, 'val': 'spammier'},
                code=status.HTTP_200_OK)
        self.assertPut('/doc/items?id=2', {'id': 2, 'val': 'eggs'},
                code=status.HTTP_200_OK)
        self.assertPut('/doc/items?id=7', {'val': 'bacon'},
                checkGet=False, code=status.HTTP_201_CREATED)
        self.assertGet('/doc/items?id=7', {'id': 7, 'val': 'bacon'})
        self.assertPut('/doc/crazy/new/nested/items?id=0',
                {'id': 0, 'val': 'eggs'},
                code=status.HTTP_201_CREATED)
        self.assertPut('/doc/dict?id=1', {'id': 1, 'val': 'meh'},
                checkGet=False,
                code=status.HTTP_400_BAD_REQUEST)
        self.assertPut('/doc/dupitems?id=2', {'id': 2, 'val': 'eh'},
                checkGet=False,
                code=status.HTTP_400_BAD_REQUEST)

    def testDelete(self):
        self.assertDelete('/doc/list')
        self.assertDelete('/doc/dict/a')
        self.assertDelete('/doc/nested/1')
        self.assertDelete('/doc/nested/1', checkGet=False,
                code=status.HTTP_404_NOT_FOUND)
        self.assertDelete('/doc/foo_new', checkGet=False,
                code=status.HTTP_404_NOT_FOUND)
        self.assertDelete('/doc/nested/3asldin', checkGet=False,
                code=status.HTTP_404_NOT_FOUND)
        self.assertDelete('/doc/not/created/deep/tree', checkGet=False,
                code=status.HTTP_404_NOT_FOUND)

    def testDeleteQuery(self):
        self.assertDelete('/doc/items?id=2')
        self.assertDelete('/doc/items?id=2', checkGet=False,
                code=status.HTTP_404_NOT_FOUND)
        self.assertDelete('/doc/items?id=1', checkGet=False,
                code=status.HTTP_404_NOT_FOUND)

    def testPatch(self):
        self.assertPatch('/doc', {'list': [4, 5, 6]})
        self.assertGet('/doc/list', [4, 5, 6])
        self.assertGet('/doc/dict', self.json['dict'])
        self.assertPatch('/doc/nested', {'1': 'foo', '3': 'bar'})
        self.assertGet('/doc/nested/2', self.json['nested']['2'])
        self.assertGet('/doc/nested/1', 'foo')
        self.assertGet('/doc/nested/3', 'bar')
        self.assertPatch('/doc/fiasdfn', {'some': 'data'},
                code=status.HTTP_404_NOT_FOUND)

    def testPatchQuery(self):
        self.assertPatch('/doc/items?id=1', {'id': 1, 'val': 'spam'},
                code=status.HTTP_404_NOT_FOUND)
        self.assertPatch('/doc/items?id=2', {'extra': 'fun'})
        self.assertGet('/doc/items?id=2',
                {'id': 2, 'val': 'foo', 'extra': 'fun'})
        self.assertPatch('/doc/not/exist/items?id=2', {'id': 2, 'foo': 'bar'},
                code=status.HTTP_404_NOT_FOUND)
