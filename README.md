# dataclasses-xargs
An extension to the dataclasses library allowing you to push your unnamed parameters to a specific field.

## Installation
```bash
pip3 install dataclasses-xargs
```

# Usage
```python
from dataclasses_xargs import dataclass

@dataclass
class ExampleClass(object):
    argA: str
    argB: str = None
    unnamedArgs: list[int] = None

test = ExampleClass(1, 2, 3, 4, 5, argA="argA", argB="argB")
print(test)



```