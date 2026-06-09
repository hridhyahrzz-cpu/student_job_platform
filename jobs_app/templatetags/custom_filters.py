from django import template

register = template.Library()

@register.filter(name='rjust')
def rjust(value, arg):
    """
    Custom rjust filter that repeats the string `value` `arg` times.
    This allows us to render ratings stars dynamically: e.g. {{ "★"|rjust:5 }} -> ★★★★★
    """
    try:
        times = int(arg)
        return str(value) * times
    except (ValueError, TypeError):
        return value
