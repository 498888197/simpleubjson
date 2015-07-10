Library for decoding data in [Universal Binary JSON](http://ubjson.org) format to Python objects and encode them vice versa.

simpleubjson supports Draft-8 and Draft-9 specification versions and uses next decoding/encoding rule set:

| **UBJSON type** | **Python type** | **UBJSON type (encoded)** | **Notes** |
|:----------------|:----------------|:--------------------------|:----------|
| noop            | NOOP            | noop                      |           |
| null            | None            | null                      |           |
| false           | bool            | false                     |           |
| true            | bool            | true                      |           |
| byte            | int             | byte                      | (1)       |
| int16           | int             | int16                     | (1)       |
| int32           | int             | int32                     | (1)       |
| int64           | int             | int64                     | (1)       |
| float           | float           | float                     | (1)       |
| double          | float           | double                    | (1)       |
| string          | unicode         | string                    | (2)       |
| huge            | decimal.Decimal | huge                      | (2)       |
| array           | list            | array                     | (2)       |
| object          | dict            | object                    | (2)       |
| unsized array   | generator       | unsized array             | (3)       |
| unsized object  | generator       | unsized array             | (4)       |
|                 | str             | string                    | (2)       |
|                 | long            | int or huge               | (2)       |
|                 | tuple           | array                     | (2)       |
|                 | set             | array                     | (2)       |
|                 | frozenset       | array                     | (2)       |
|                 | xrange          | unsized array             |           |
|                 | dict\_keyiterator | unsized array             | (3)       |
|                 | dict\_valueiterator | unsized array             | (3)       |
|                 | dict\_itemiterator | unsized object            |           |
|                 | float('inf')    | null                      |           |
|                 | float('-inf')   | null                      |           |

1. Depending on value it will be encoded to specified UBJSON type:

  * byte: if -128 <= value <= 127
  * int16: if -32768 <= value <= 32767
  * int32: if -2147483648 <= value <= 2147483647
  * int64: if -9223372036854775808 <= value 9223372036854775807
  * float: if 1.18e-38 <= abs(value) <= 3.4e38
  * double: if 2.23e-308 <= abs(value) < 1.80e308

> Any other values would be encoded as huge number.

2. Depending on value length it would be encoded to short type version or to long one.

3. Nested unsized arrays will be automatically transformed into lists.

4. Unsized object decodes into generator of key-value pairs similar to dict.iteritems().


Since **0.3** version there is `simpleubjson.pprint` function that allows to represent UBJSON data in readable `[]`-notation form:
```
[a] [6]
    [Z]
    [T]
    [F]
    [I] [4782345193]
    [D] [153.132417549]
    [s] [3] [ham]
```