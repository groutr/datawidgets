import ipywidgets as ipyw
import collections
import inspect

from .widget_types import WIDGET_MAP

MISSING = set()
try:
    import dataclasses
    MISSING.add(dataclasses.MISSING)
except ImportError:
    pass

try:
    import attr
    MISSING.add(attr.NOTHING)
except ImportError:
    pass

ATTRS_FIELDS = '__attrs_attrs__'
DATACLASS_FIELDS = '__dataclass_fields__'

WIDGET = '__widget__'

def _fields(instance):
    """Generator that will yield
    attribute name, attribute field, attribute type

    Arguments:
        field_list {[type]} -- [description]

    Keyword Arguments:
        types {[type]} -- [description] (default: {None})
    """
    fields = getattr(instance, ATTRS_FIELDS, None)
    if fields is None:
        fields = getattr(instance, DATACLASS_FIELDS, None)
        if fields is None:
            raise TypeError
        return dataclasses.fields(instance)
    else:
        try:
            return attr.fields(instance)
        except TypeError:
            return attr.fields(instance.__class__)
    raise TypeError("Not an instance of dataclass or attrs")


def _observe_handlers(instance):
    """Return a map of attributes and handlers

    Arguments:
        instance {[type]} -- [description]
    """
    handlers = collections.defaultdict(list)
    for name, obj in inspect.getmembers(instance):
        if name.startswith('__') and name.endswith('__'):
            # skip magic methods
            continue

        if inspect.ismethod(obj):
            observees = getattr(obj, '__observe', [])
            for observee in observees:
                handlers[observee].append(obj)
    return handlers

def layout(instance, public_attributes_only=True):
    fields = _fields(instance)

    handlers = _observe_handlers(instance)
    widgets = []
    for field in fields:
        if public_attributes_only and field.name.startswith('_'):
            continue
        kwargs = {'description': field.name}
        kwargs.update(field.metadata.get('__widget__', {}))

        try:
            widget_class = WIDGET_MAP[field.type]
        except KeyError:
            if field.default not in MISSING:
                widget_class = WIDGET_MAP[type(field.default)]
            elif field.default_factory not in MISSING:
                widget_class = WIDGET_MAP[type(field.default_factory())]
            else:
                raise TypeError("Unable to find widget type for {}".format(field.name))

        if field.default not in  MISSING:
            kwargs['value'] = field.default

        widget = widget_class(**kwargs)
        for observer in handlers[field.name]:
            widget.observe(observer)
            widget.observe(setter(instance, field.name), names='value')
        widgets.append(widget)

    return widgets


def setter(instance, attribute):
    def _set(event):
        setattr(instance, attribute, event['new'])
    return _set

def observe(*attributes):
    def _observe(method):
        method.__observe = attributes
        return method
    return _observe
