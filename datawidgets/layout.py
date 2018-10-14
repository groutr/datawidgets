import inspect
import collections
import ipywidgets as ipyw
from collections.abc import Sequence
from collections import OrderedDict
from operator import attrgetter
from functools import wraps

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

WIDGET_MAP = {
    int: (ipyw.IntSlider, 'value'),
    float: (ipyw.FloatSlider, 'value'),
    str: (ipyw.Text, 'value'),
    bool: (ipyw.Checkbox, 'value'),
    list: (ipyw.Dropdown, 'options'),
    tuple: (ipyw.Dropdown, 'options'),
    set: (ipyw.Dropdown, 'options')
}

ATTRS_FIELDS = '__attrs_attrs__'
DATACLASS_FIELDS = '__dataclass_fields__'

WIDGET = '__widget__'

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

        if inspect.isfunction(obj):
            print(name, obj)
            observees = getattr(obj, '_observes', {})
            for observee, kwargs in observees.items():
                handlers[observee].append((-1, obj, kwargs))

    return handlers

def create_widgets(instance, public_attributes_only=True):
    fields = _fields(instance)

    handlers = _observe_handlers(instance)
    print(handlers)
    widgets = []
    __widgets = OrderedDict()
    for field in fields:
        if public_attributes_only and field.name.startswith('_'):
            continue
        kwargs = {'description': field.name}
        kwargs.update(field.metadata.get('__widget', {}))

        try:
            _type = field.type
            widget_class, dattr = WIDGET_MAP[_type]
        except KeyError:
            if field.default not in MISSING:
                _type = type(field.default)
                widget_class, dattr = WIDGET_MAP[_type]
            elif field.default_factory not in MISSING:
                _type = type(field.default_factory())
                widget_class, dattr = WIDGET_MAP[_type]
            else:
                raise TypeError("Unable to find widget type for {}".format(field.name))

        if field.default not in  MISSING:
            kwargs['value'] = field.default

        widget = widget_class(**kwargs)
        for _t, observer, kwargs in handlers[field.name]:
            widget.observe(observer, names='value')

        widgets.append(widget)
        __widgets[field.name] = widget

    instance.__widgets = __widgets
    return widgets


def _observer(instance, attribute, name):
    def _observe(event):
        setattr(instance, attribute, event[name])
    return _observe


class Sync(object):
    def __init__(self, method, observes, updates):
        self.method = method
        self.observes = observes
        self.updates = updates

    def _sync_to_widgets(self, instance):
        _widgets = getattr(instance, '__widgets', {})
        if not _widgets:
            return
        for attribute, trait in self.updates.items():
            setattr(_widgets[attribute], trait, getattr(instance, attribute))

    def __get__(self, instance, owner):
        @wraps(self.method)
        def method(*args, **kwargs):
            rv = self.method(instance, *args, **kwargs)
            if self.updates:
                self._sync_to_widgets(instance)
            return rv
        method._observes = self.observes
        method._updates = self.updates
        return method

def sync(observes=None, updates=None):
    def _sync(method):
        return Sync(method, observes or {}, updates or {})
    return _sync
