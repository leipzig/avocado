from django.test import TestCase

from avocado.exceptions import RegisterError, AlreadyRegisteredError
from avocado.columns.format import (FormatterLibrary, AbstractFormatter,
    RemoveFormatter, PassFormatter, FormatError)

__all__ = ('FormatterLibraryTestCase',)


class ConcatStrFormatter(AbstractFormatter):
    def csv(self, *args):
        return ' '.join(map(lambda x: str(x), args))


class Add(AbstractFormatter):
    name = 'Add Numbers'
    def csv(self, *args):
        return sum(args)


class Add2(AbstractFormatter):
    name = 'Add Numbers'
    def csv(self, *args):
        return sum(args)


class FormatterLibraryTestCase(TestCase):
    def test_no_formatters(self):
        library = FormatterLibrary()
        self.assertEqual(library._cache, {
            'json': {'formatters': {}, 'error': '[data format error]'},
            'html': {'null': '<span class="lg ht">(no data)</span>', 'formatters': {},
                'error': '<span class="data-format-error">[data format error]</span>'},
            'csv': {'null': '', 'formatters': {}, 'error': '[data format error]'}
        })

    def test_bad_register(self):
        library = FormatterLibrary()

        class BadConcatFormatter(object):
            def csv(self, arg1, arg2):
                return ' '.join([str(arg1), str(arg2)])

        self.assertRaises(RegisterError, library.register, BadConcatFormatter)

    def _setup_library(self):
        library = FormatterLibrary()
        library.register(ConcatStrFormatter)
        library.register(Add)
        # should not raise AlreadyRegisteredError, it will merely replace it
        library.register(Add)

        self.assertRaises(AlreadyRegisteredError, library.register, Add2)

        self.assertEqual(library.choices('csv'), [('Add Numbers', 'Add Numbers'),
            ('Concat Str', 'Concat Str')])

        return library

    def test_simple(self):
        library = self._setup_library()

        rows = [
            (1, 2, 3, 4, 5),
            (6, 7, 8, 9, 10),
            (3, 3, 3, 3, 3),
        ]

        out = library.format(rows, [('Add Numbers', 5)], 'csv')

        self.assertEqual(list(out), [(15,), (40,), (15,)])

    def test_bultins(self):
        library = self._setup_library()

        # builtin formatters
        library.register(RemoveFormatter)
        library.register(PassFormatter)

        rows = [
            (1, 2, 3, 4, 5),
            (6, 7, 8, 9, 10),
            (3, 3, 3, 3, 3),
        ]

        out = library.format(rows, [
            ('Add Numbers', 2),
            ('Pass', 1),
            ('Remove', 2)
        ], 'csv')

        self.assertEqual(list(out), [(3, 3), (13, 8), (6, 3)])

    def test_format_error(self):
        library = self._setup_library()

        rows = [
            (1, 2, 3, 4, 5),
            (6, 7, 8, 9, 10),
            (3, 3, 3, 3, 3),
        ]

        out = library.format(rows, [('Add Numbers', 3)], 'csv')

        self.assertRaises(FormatError, list, out)

    def test_error_fallback(self):
        library = self._setup_library()
        # builtin formatters
        library.register(RemoveFormatter)
        library.register(PassFormatter)

        @library.register
        class AddOneFormatter(AbstractFormatter):
            def csv(self, arg):
                return arg + 1

        rows = [
            (4, None, 'foo', set([3,4,5]), 10.5, 11.0, 2.0, {}),
            (10, 29, 'foo', [3,4,5], False, 372.19, None, []),
            (None, 'bar', 'foo', None, True, 199.0, 1.0, 192),
        ]

        out = library.format(rows, [
            ('Concat Str', 2),
            ('Concat Str', 1),
            ('Pass', 1),
            ('Add Numbers', 3),
            ('Add One', 1),
        ], 'csv')

        self.assertEqual(list(out), [
            ('4 None', 'foo', set([3, 4, 5]), 23.5, '[data format error]'),
            ('10 29', 'foo', [3, 4, 5], '[data format error]', '[data format error]'),
            ('None bar', 'foo', '', 201.0, 193)
        ])