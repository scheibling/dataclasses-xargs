
import dataclasses as _dc

class _DataclassParams(_dc._DataclassParams):
    def __init__(self, init, repr, eq, order, unsafe_hash, frozen, xargField):
        self.__slots__ = self.__slots__ + ('xargField',)
        self.xargField = xargField
        
        super().__init__(init, repr, eq, order, unsafe_hash, frozen)

def _init_fn(fields, frozen, has_post_init, self_name, globals, xargField = None):
    # fields contains both real fields and InitVar pseudo-fields.

    # Make sure we don't have fields without defaults following fields
    # with defaults.  This actually would be caught when exec-ing the
    # function source code, but catching it here gives a better error
    # message, and future-proofs us in case we build up the function
    # using ast.
    seen_default = False
    for f in fields:
        # Only consider fields in the __init__ call.
        if f.init:
            if not (f.default is _dc.MISSING and f.default_factory is _dc.MISSING):
                seen_default = True
            elif seen_default:
                raise TypeError(f'non-default argument {f.name!r} '
                                'follows default argument')

    locals = {f'_type_{f.name}': f.type for f in fields}
    locals.update({
        'MISSING': _dc.MISSING,
        '_HAS_DEFAULT_FACTORY': _dc._HAS_DEFAULT_FACTORY,
    })

    body_lines = []
    for f in fields:
        line = _dc._field_init(f, frozen, locals, self_name)
        # line is None means that this field doesn't require
        # initialization (it's a pseudo-field).  Just skip it.
        if line:
            body_lines.append(line)

    # Does this class have a post-init function?
    if has_post_init:
        params_str = ','.join(f.name for f in fields
                            if f._field_type is _dc._FIELD_INITVAR)
        body_lines.append(f'{self_name}.{_dc._POST_INIT_NAME}({params_str})')

    basefld = [self_name] 

    if xargField is not None and xargField != "":
        basefld = [self_name, "*xargs"]
        body_lines.append(f"if len(xargs) > 0 and (self.{xargField} is None or len(self.{xargField} == 0)):")
        body_lines.append(f"  self.{xargField} = xargs")

    # If no body lines, use 'pass'.
    if not body_lines:
        body_lines = ['pass']

    return _dc._create_fn('__init__',
                    basefld + [_dc._init_param(f) for f in fields if f.init],
                    body_lines,
                    locals=locals,
                    globals=globals,
                    return_type=None)

def _process_class(cls, init, repr, eq, order, unsafe_hash, frozen, xargField):
    # Now that dicts retain insertion order, there's no reason to use
    # an ordered dict.  I am leveraging that ordering here, because
    # derived class fields overwrite base class fields, but the order
    # is defined by the base class, which is found first.
    fields = {}

    if cls.__module__ in _dc.sys.modules:
        globals = _dc.sys.modules[cls.__module__].__dict__
    else:
        # Theoretically this can happen if someone writes
        # a custom string to cls.__module__.  In which case
        # such dataclass won't be fully introspectable
        # (w.r.t. typing.get_type_hints) but will still function
        # correctly.
        globals = {}

    setattr(cls, _dc._PARAMS, _DataclassParams(init, repr, eq, order,
                                        unsafe_hash, frozen, xargField))

    # Find our base classes in reverse MRO order, and exclude
    # ourselves.  In reversed order so that more derived classes
    # override earlier field definitions in base classes.  As long as
    # we're iterating over them, see if any are frozen.
    any_frozen_base = False
    has_dataclass_bases = False
    for b in cls.__mro__[-1:0:-1]:
        # Only process classes that have been processed by our
        # decorator.  That is, they have a _FIELDS attribute.
        base_fields = getattr(b, _dc._FIELDS, None)
        if base_fields:
            has_dataclass_bases = True
            for f in base_fields.values():
                fields[f.name] = f
            if getattr(b, _dc._PARAMS).frozen:
                any_frozen_base = True

    # Annotations that are defined in this class (not in base
    # classes).  If __annotations__ isn't present, then this class
    # adds no new annotations.  We use this to compute fields that are
    # added by this class.
    #
    # Fields are found from cls_annotations, which is guaranteed to be
    # ordered.  Default values are from class attributes, if a field
    # has a default.  If the default value is a Field(), then it
    # contains additional info beyond (and possibly including) the
    # actual default value.  Pseudo-fields ClassVars and InitVars are
    # included, despite the fact that they're not real fields.  That's
    # dealt with later.
    cls_annotations = cls.__dict__.get('__annotations__', {})

    # Now find fields in our class.  While doing so, validate some
    # things, and set the default values (as class attributes) where
    # we can.
    cls_fields = [_dc._get_field(cls, name, type)
                for name, type in cls_annotations.items()]
    for f in cls_fields:
        fields[f.name] = f

        # If the class attribute (which is the default value for this
        # field) exists and is of type 'Field', replace it with the
        # real default.  This is so that normal class introspection
        # sees a real default value, not a Field.
        if isinstance(getattr(cls, f.name, None), _dc.Field):
            if f.default is _dc.MISSING:
                # If there's no default, delete the class attribute.
                # This happens if we specify field(repr=False), for
                # example (that is, we specified a field object, but
                # no default value).  Also if we're using a default
                # factory.  The class attribute should not be set at
                # all in the post-processed class.
                delattr(cls, f.name)
            else:
                setattr(cls, f.name, f.default)

    # Do we have any Field members that don't also have annotations?
    for name, value in cls.__dict__.items():
        if isinstance(value, _dc.Field) and not name in cls_annotations:
            raise TypeError(f'{name!r} is a field but has no type annotation')

    # Check rules that apply if we are derived from any dataclasses.
    if has_dataclass_bases:
        # Raise an exception if any of our bases are frozen, but we're not.
        if any_frozen_base and not frozen:
            raise TypeError('cannot inherit non-frozen dataclass from a '
                            'frozen one')

        # Raise an exception if we're frozen, but none of our bases are.
        if not any_frozen_base and frozen:
            raise TypeError('cannot inherit frozen dataclass from a '
                            'non-frozen one')

    # Remember all of the fields on our class (including bases).  This
    # also marks this class as being a dataclass.
    setattr(cls, _dc._FIELDS, fields)

    # Was this class defined with an explicit __hash__?  Note that if
    # __eq__ is defined in this class, then python will automatically
    # set __hash__ to None.  This is a heuristic, as it's possible
    # that such a __hash__ == None was not auto-generated, but it
    # close enough.
    class_hash = cls.__dict__.get('__hash__', _dc.MISSING)
    has_explicit_hash = not (class_hash is _dc.MISSING or
                            (class_hash is None and '__eq__' in cls.__dict__))

    # If we're generating ordering methods, we must be generating the
    # eq methods.
    if order and not eq:
        raise ValueError('eq must be true if order is true')

    if init:
        # Does this class have a post-init function?
        has_post_init = hasattr(cls, _dc._POST_INIT_NAME)

        # Include InitVars and regular fields (so, not ClassVars).
        flds = [f for f in fields.values()
                if f._field_type in (_dc._FIELD, _dc._FIELD_INITVAR)]
        _dc._set_new_attribute(cls, '__init__',
                        _init_fn(flds,
                                frozen,
                                has_post_init,
                                # The name to use for the "self"
                                # param in __init__.  Use "self"
                                # if possible.
                                '__dataclass_self__' if 'self' in fields
                                        else 'self',
                                globals,
                                xargField
                        ))

    # Get the fields as a list, and include only real fields.  This is
    # used in all of the following methods.
    field_list = [f for f in fields.values() if f._field_type is _dc._FIELD]

    if repr:
        flds = [f for f in field_list if f.repr]
        _dc._set_new_attribute(cls, '__repr__', _dc._repr_fn(flds, globals))

    if eq:
        # Create _eq__ method.  There's no need for a __ne__ method,
        # since python will call __eq__ and negate it.
        flds = [f for f in field_list if f.compare]
        self_tuple = _dc._tuple_str('self', flds)
        other_tuple = _dc._tuple_str('other', flds)
        _dc._set_new_attribute(cls, '__eq__',
                        _dc._cmp_fn('__eq__', '==',
                                self_tuple, other_tuple,
                                globals=globals))

    if order:
        # Create and set the ordering methods.
        flds = [f for f in field_list if f.compare]
        self_tuple = _dc._tuple_str('self', flds)
        other_tuple = _dc._tuple_str('other', flds)
        for name, op in [('__lt__', '<'),
                        ('__le__', '<='),
                        ('__gt__', '>'),
                        ('__ge__', '>='),
                        ]:
            if _dc._set_new_attribute(cls, name,
                                _dc._cmp_fn(name, op, self_tuple, other_tuple,
                                        globals=globals)):
                raise TypeError(f'Cannot overwrite attribute {name} '
                                f'in class {cls.__name__}. Consider using '
                                'functools.total_ordering')

    if frozen:
        for fn in _dc._frozen_get_del_attr(cls, field_list, globals):
            if _dc._set_new_attribute(cls, fn.__name__, fn):
                raise TypeError(f'Cannot overwrite attribute {fn.__name__} '
                                f'in class {cls.__name__}')

    # Decide if/how we're going to create a hash function.
    hash_action = _dc._hash_action[bool(unsafe_hash),
                            bool(eq),
                            bool(frozen),
                            has_explicit_hash]
    if hash_action:
        # No need to call _set_new_attribute here, since by the time
        # we're here the overwriting is unconditional.
        cls.__hash__ = hash_action(cls, field_list, globals)

    if not getattr(cls, '__doc__'):
        # Create a class doc-string.
        cls.__doc__ = (cls.__name__ +
                    str(_dc.inspect.signature(cls)).replace(' -> None', ''))

    return cls

def dataclass(cls=None, /, *, init=True, repr=True, eq=True, order=False,
            unsafe_hash=False, frozen=False, xargField=False):
    """Returns the same class as was passed in, with dunder methods
    added based on the fields defined in the class.

    Examines PEP 526 __annotations__ to determine fields.

    If init is true, an __init__() method is added to the class. If
    repr is true, a __repr__() method is added. If order is true, rich
    comparison dunder methods are added. If unsafe_hash is true, a
    __hash__() method function is added. If frozen is true, fields may
    not be assigned to after instance creation.
    """

    def wrap(cls):
        return _process_class(cls, init, repr, eq, order, unsafe_hash, frozen, xargField)

    # See if we're being called as @dataclass or @dataclass().
    if cls is None:
        # We're called with parens.
        return wrap

    # We're called as @dataclass without parens.
    return wrap(cls)

def make_dataclass(cls_name, fields, *, bases=(), namespace=None, init=True,
                repr=True, eq=True, order=False, unsafe_hash=False,
                frozen=False, xargField=False):
    """Return a new dynamically created dataclass.

    The dataclass name will be 'cls_name'.  'fields' is an iterable
    of either (name), (name, type) or (name, type, Field) objects. If type is
    omitted, use the string 'typing.Any'.  Field objects are created by
    the equivalent of calling 'field(name, type [, Field-info])'.

    C = make_dataclass('C', ['x', ('y', int), ('z', int, field(init=False))], bases=(Base,))

    is equivalent to:

    @dataclass
    class C(Base):
        x: 'typing.Any'
        y: int
        z: int = field(init=False)

    For the bases and namespace parameters, see the builtin type() function.

    The parameters init, repr, eq, order, unsafe_hash, and frozen are passed to
    dataclass().
    """

    if namespace is None:
        namespace = {}
    else:
        # Copy namespace since we're going to mutate it.
        namespace = namespace.copy()

    # While we're looking through the field names, validate that they
    # are identifiers, are not keywords, and not duplicates.
    seen = set()
    anns = {}
    for item in fields:
        if isinstance(item, str):
            name = item
            tp = 'typing.Any'
        elif len(item) == 2:
            name, tp, = item
        elif len(item) == 3:
            name, tp, spec = item
            namespace[name] = spec
        else:
            raise TypeError(f'Invalid field: {item!r}')

        if not isinstance(name, str) or not name.isidentifier():
            raise TypeError(f'Field names must be valid identifiers: {name!r}')
        if _dc.keyword.iskeyword(name):
            raise TypeError(f'Field names must not be keywords: {name!r}')
        if name in seen:
            raise TypeError(f'Field name duplicated: {name!r}')

        seen.add(name)
        anns[name] = tp

    namespace['__annotations__'] = anns
    # We use `types.new_class()` instead of simply `type()` to allow dynamic creation
    # of generic dataclassses.
    cls = _dc.types.new_class(cls_name, bases, {}, lambda ns: ns.update(namespace))
    return dataclass(cls, init=init, repr=repr, eq=eq, order=order,
                    unsafe_hash=unsafe_hash, frozen=frozen, xargField=xargField)

