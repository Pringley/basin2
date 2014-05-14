from django.db import models
from django.utils.six import with_metaclass
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import json

class JSONField(with_metaclass(models.SubfieldBase, models.TextField)):
    """Field containing JSON-encoded data."""
    description = 'Field containing JSON-encoded data.'

    def to_python(self, value):
        """Convert JSON value from DB to Python object."""
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except ValueError:
            raise ValidationError("Invalid JSON")

    def get_prep_value(self, value):
        """Convert Python object to JSON for DB storage."""
        try:
            return json.dumps(value)
        except TypeError:
            raise ValidationError("Could not serialize object to JSON")

    def value_to_string(self, obj):
        """Return a string representation of value."""
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

class Document(models.Model):
    """A User document."""
    json = JSONField()
    owner = models.OneToOneField(User, related_name='document')
