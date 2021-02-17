# Subproxy

General Subprocess Proxy Object.

## Usage

Simplest example:

```python
from subproxy import subproxy

class MyClass:
    pass

MyClassProxy = subproxy(MyClass)

# now MyClassProxy may be treated like `MyClass`,
# except when it doesn't work.

```

Also see the [test file](tests/test_subproxy.py) for a quick reference.

## Limitations

While the proxy generally works, we do have to draw the line somewhere
in transitioning between native objects and proxy objects.

Therefore, the below code would work:

```python
MyClassProxy = subproxy(MyClass)
p = MyClassProxy()
p.a = 'b'
print(p.a) # 'b'
```

But the below code would not work:

```python
MyClassProxy = subproxy(MyClass)
p = MyClassProxy()
p.a = {'a':0, 'b':1}
p.a['a'] = 1
print(p.a['a']) # still 0
```

This is because `p.a` would return a `dict` rather than a `subproxy(dict)`.
