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


try:
    FailTest(1, 2, 3, 4, 5, a=1, b="b")
except TypeError as e:
    assert e.args[0] == "FailTest.__init__() got multiple values for argument 'a'"

dcl = SuccessTest(1, 2, 3, 4, 5, a=1, b="b")
print(dcl)
assert dcl.a == 1
assert dcl.b == "b"
assert dcl.c == (1, 2, 3, 4, 5)

dcl = SuccessTest(1, 2, 3, 4, 5, a=1, b="b", c=[0, 0, 0])
print(dcl)
assert dcl.a == 1
assert dcl.b == "b"
assert dcl.c == [0, 0, 0]

exit(0)