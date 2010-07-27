from django.db.models import Q

from avocado.settings import settings as avs
from avocado.concepts.library import BaseLibrary
from avocado.fields.operators import *
from avocado.fields.fieldtypes import MODEL_FIELD_MAP

class OperatorNotPermitted(Exception):
    pass


class AbstractTranslator(object):
    "The base translator class that all translators must subclass."
    operators = None
    formfield = None

    def __call__(self, operator, value, mfield, **kwargs):
        fieldtype = MODEL_FIELD_MAP[mfield.field.__class__.__name__]
        if not self.operators:
            self.operators = fieldtype.operators
        if not self.formfield:
            self.formfield = fieldtype.formfield
        return self.translate(operator, value, mfield=mfield, **kwargs)

    def _get_operators(self):
        if not hasattr(self, '__operators'):
            self.__operators = dict([(x.operator, x) for x in self.operators])
        return self.__operators
    _operators = property(_get_operators)

    def _clean_operator(self, operator, **kwargs):
        if not self._operators.has_key(operator):
            raise OperatorNotPermitted, 'operator "%s" cannot be used for this translator' % operator
        return self._operators[operator]

    def _clean_value(self, value, **kwargs):
        field = self.formfield()
        return field.clean(value)

    def validate(self, operator, value, **kwargs):
        clean_op = self._clean_operator(operator, **kwargs)
        clean_val = self._clean_value(value, **kwargs)
        return clean_op, clean_val

    def translate(self, operator, value, mfield, **kwargs):
        clean_operator, clean_value = self.validate(operator, value, **kwargs)
        query_string = mfield.query_string(operator)
        kwarg = {query_string: clean_value}
        return Q(**kwarg)


class SimpleTranslator(AbstractTranslator):
    pass


class TranslatorLibrary(BaseLibrary):
    "The base class for defining the translator library."
    STORE_KEY = 'translators'

    def _get_store(self, key=None):
        return self._cache

    def _fmt_name(self, name):
        return super(TranslatorLibrary, self)._fmt_name(name, 'Translator')

    def _register(self, klass_name, obj):
        self._add_item(None, klass_name, obj)

    def register(self, klass):
        return super(TranslatorLibrary, self).register(klass, AbstractTranslator)

    def choices(self):
        "Returns a list of tuples that can be used as choices in a form."
        return [(n, n) for n in self._cache.keys()]


library = TranslatorLibrary()

# find all other translators
library.autodiscover(avs.TRANSLATOR_MODULE_NAME)