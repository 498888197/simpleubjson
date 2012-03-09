# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
from decimal import Decimal
from types import GeneratorType, MethodType
from simpleubjson import NOOP
from simpleubjson.compat import b, unicode, bytes, basestring, long, \
                                XRangeType, dict_keysiterator, \
                                dict_valuesiterator, dict_itemsiterator

__all__ = ['UBJSONEncoder']

is_byte = lambda value: (-2 ** 7) <= value <= (2 ** 7 - 1)
is_int16 = lambda value: (-2 ** 15) <= value <= (2 ** 15 - 1)
is_int32 = lambda value: (-2 ** 31) <= value <= (2 ** 31 - 1)
is_int64 = lambda value: (-2 ** 63) <= value <= (2 ** 63 - 1)
is_float = lambda value: 1.18e-38 <= abs(value) <= 3.4e38
is_double = lambda value: 2.23e-308 <= abs(value) < 1.8e308 # 1.8e308 is inf
is_infinity = lambda value: value == float('inf') or value == float('-inf')

MARKER_Z = b('Z')
MARKER_N = b('N')
MARKER_F = b('F')
MARKER_T = b('T')
MARKER_B = b('B')
MARKER_i = b('i')
MARKER_I = b('I')
MARKER_L = b('L')
MARKER_d = b('d')
MARKER_D = b('D')
MARKER_s = b('s')
MARKER_S = b('S')
MARKER_h = b('h')
MARKER_H = b('H')
MARKER_a = b('a')
MARKER_A = b('A')
MARKER_o = b('o')
MARKER_O = b('O')
MARKER_E = b('E')
MARKER_FF = b('\xff')


class UBJSONEncoder(object):
    """Base encoder of Python objects to UBJSON data that follows next rules:

    +----------------------------+----------------------------+-------+
    | Python type                | UBJSON type                | Notes |
    +============================+============================+=======+
    | :const:`NOOP`              | noop                       |       |
    +----------------------------+----------------------------+-------+
    | None                       | null                       |       |
    +----------------------------+----------------------------+-------+
    | False                      | false                      |       |
    +----------------------------+----------------------------+-------+
    | True                       | true                       |       |
    +----------------------------+----------------------------+-------+
    | int                        | byte                       | \(1)  |
    +----------------------------+----------------------------+-------+
    | int                        | int16                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | int or long                | int32                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | int or long                | int64                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | float                      | float                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | float                      | double                     | \(1)  |
    +----------------------------+----------------------------+-------+
    | long                       | huge                       | \(2)  |
    +----------------------------+----------------------------+-------+
    | str                        | string                     | \(2)  |
    +----------------------------+----------------------------+-------+
    | unicode                    | string                     | \(2)  |
    +----------------------------+----------------------------+-------+
    | tuple                      | sized array                | \(2)  |
    +----------------------------+----------------------------+-------+
    | list                       | sized array                | \(2)  |
    +----------------------------+----------------------------+-------+
    | set                        | sized array                | \(2)  |
    +----------------------------+----------------------------+-------+
    | frozenset                  | sized array                | \(2)  |
    +----------------------------+----------------------------+-------+
    | generator                  | unsized array              |       |
    +----------------------------+----------------------------+-------+
    | dict                       | sized object               | \(2)  |
    +----------------------------+----------------------------+-------+
    | dict.iterkeys()            | unsized array              |       |
    +----------------------------+----------------------------+-------+
    | dict.itervalues()          | unsized array              |       |
    +----------------------------+----------------------------+-------+
    | dict.iteritems()           | unsized object             |       |
    +----------------------------+----------------------------+-------+
    | xrange                     | unsized array              |       |
    +----------------------------+----------------------------+-------+
    | decimal.Decimal            | huge                       | \(2)  |
    +----------------------------+----------------------------+-------+

    Notes:

    (1)
        Depending on value it will be encoded to specified UBJSON type:

        * byte: if -128 <= value <= 127
        * int16: if -32768 <= value <= 32767
        * int32: if -2147483648 <= value <= 2147483647
        * int64: if -9223372036854775808 <= value 9223372036854775807
        * float: if 1.18e-38 <= abs(value) <= 3.4e38
        * double: if 2.23e-308 <= abs(value) < 1.80e308

        Any other values would be encoded as huge number.

    (2)
        Depending on value length it would be encoded to short data version
        to long one.
    """
    def __init__(self, default=None, handlers=None):
        self._handlers = {
            type(None): self.encode_none,
            bool: self.encode_bool,
            int: self.encode_number,
            long: self.encode_number,
            float: self.encode_float,
            basestring: self.encode_str,
            tuple: self.encode_array,
            list: self.encode_array,
            set: self.encode_array,
            frozenset: self.encode_array,
            dict_keysiterator: self.encode_generator,
            dict_valuesiterator: self.encode_generator,
            dict_itemsiterator: self.encode_iterated_dict,
            XRangeType: self.encode_generator,
            GeneratorType: self.encode_generator,
            dict: self.encode_dict,
            Decimal: self.encode_huge_number
        }
        if default is not None:
            self.encode_default = MethodType(default, self)
        if handlers is not None:
            for key, handler in handlers.items():
                if handler is not None:
                    handlers[key] = MethodType(handler, self)
            self._handlers.update(handlers)

    def pack_data(self, pattern, data):
        return struct.pack(pattern, data)

    def encode(self, value, output=None):
        """Encodes Python object into UBJSON data.

        :param value: Python object.
                      See :class:`~simpleubjson.encoder.UBJSONEncoder` mapping
                      table for supported object types.
        :param output: `.write([data])`-able object. If omitted result would be
                       returned as string.
        """
        if output is None:
            return bytes().join(self.iterencode(value))
        for chunk in self.iterencode(value):
            output.write(chunk)

    def iterencode(self, value):
        handler = self.get_handler(value)
        for chunk in handler(value):
            yield chunk

    def get_handler(self, value):
        if value is NOOP:
            return self.encode_noop
        tval = type(value)
        maybe_handler = None
        handler = self._handlers.get(tval)
        if handler is not None:
            return handler
        for pytype, handler in self._handlers.items():
            if isinstance(value, pytype):
                maybe_handler = handler
        if maybe_handler is not None:
            return maybe_handler
        return self.encode_default

    def encode_default(self, value):
        raise TypeError('Unable to encode %r to ubjson' % value)

    def encode_noop(self, value):
        yield MARKER_N

    def encode_none(self, value):
        yield MARKER_Z

    def encode_bool(self, value):
        yield [MARKER_F, MARKER_T][value]

    def encode_number(self, value):
        if is_byte(value):
            return [MARKER_B, struct.pack('>b', value)]
        elif is_int16(value):
            return [MARKER_i, struct.pack('>h', value)]
        elif is_int32(value):
            return [MARKER_I, struct.pack('>i', value)]
        elif is_int64(value):
            return [MARKER_L, struct.pack('>q', value)]
        else:
            return self.encode_huge_number(value)

    def encode_float(self, value):
        if is_float(value):
            return [MARKER_d, struct.pack('>f', value)]
        elif is_double(value):
            return [MARKER_D, struct.pack('>d', value)]
        elif is_infinity(value):
            return [MARKER_Z]
        else:
            return self.encode_huge_number(value)

    def encode_str(self, value):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        length = len(value)
        if length < 255:
            return [MARKER_s, struct.pack('>B', length),
                              struct.pack('>%ds' % length, value)]
        else:
            return [MARKER_S, struct.pack('>I', length),
                         struct.pack('>%ds' % length, value)]

    def encode_array(self, value):
        size = len(value)
        if size < 255:
            yield MARKER_a
            yield struct.pack('>B', size)
        else:
            yield MARKER_A
            yield struct.pack('>I', size)
        for item in value:
            for chunk in self.iterencode(item):
                yield chunk

    def encode_generator(self, value):
        yield MARKER_a
        yield MARKER_FF
        for item in value:
            for chunk in self.iterencode(item):
                yield chunk
        yield MARKER_E

    def encode_dict(self, value):
        size = len(value)
        if size < 255:
            yield MARKER_o
            yield struct.pack('>B', size)
        else:
            yield MARKER_O
            yield struct.pack('>I', size)
        for key, val in value.items():
            assert isinstance(key, basestring), 'object key should be a string'
            for chunk in self.iterencode(key):
                yield chunk
            for chunk in self.iterencode(val):
                yield chunk

    def encode_iterated_dict(self, value):
        yield MARKER_o
        yield MARKER_FF
        for key, value in value:
            assert isinstance(key, basestring), 'object key should be a string'
            for chunk in self.iterencode((key, value)):
                yield chunk
        yield MARKER_E

    def encode_huge_number(self, value):
        value = unicode(value).encode('utf-8')
        size = len(value)
        if size < 255:
            return [MARKER_h, struct.pack('>B', size),
                              struct.pack('>%ds' % size, value)]
        else:
            return [MARKER_H, struct.pack('>I', size),
                              struct.pack('>%ds' % size, value)]
