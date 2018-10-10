import ipywidgets as ipyw


WIDGET_MAP = {
    int: ipyw.IntSlider,
    float: ipyw.FloatSlider
    str: ipyw.Text,
    bool: ipyw.Checkbox,
    list: ipyw.Dropdown,
    tuple: ipyw.Dropdown,
    set: ipyw.Dropdown
}

def register(_type, widget):
    if _type not in WIDGET_TYPES:
        WIDGET_TYPES[_type] = widget
