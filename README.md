# dataclasses-xargs
An extension to the dataclasses library allowing you to push your unnamed parameters to a specific field.

## Installation
```bash
pip3 install dataclasses-xargs
```

# Usage Example
```python
from dataclasses_xargs import dataclass

@dataclass
class FailTest(object):
    a: int = None
    b: str = None
    c: list = None

@dataclass(xarg_field="c")
class SuccessTest(object):
    a: int = None
    b: str = None
    c: list = None

# When xarg_field is not defined, dataclasses work as normal and will throw an error if you pass in double parameters
try:
    FailTest(1, 2, 3, 4, 5, a=1, b="b")
except TypeError as e:
    assert e.args[0] == "FailTest.__init__() got multiple values for argument 'a'"

# When defined, and the xarg_field is not passed as a named parameter, all unnamed parameters will be pushed to the xarg_field.
# Note that the xarg_field still needs to be defined in the class, see above.
dcl = SuccessTest(1, 2, 3, 4, 5, a=1, b="b")
print(dcl)
"""
SuccessTest(a=1, b='b', c=(1, 2, 3, 4, 5))
"""
assert dcl.a == 1
assert dcl.b == "b"
assert dcl.c == (1, 2, 3, 4, 5)

dcl = SuccessTest(1, 2, 3, 4, 5, a=1, b="b", c=[0, 0, 0])
print(dcl)
"""
SuccessTest(a=1, b='b', c=[0, 0, 0])
"""
assert dcl.a == 1
assert dcl.b == "b"
assert dcl.c == [0, 0, 0]

exit(0)
```