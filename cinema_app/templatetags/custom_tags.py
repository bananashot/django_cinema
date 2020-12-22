import datetime

from django import template

register = template.Library()


@register.filter()
def add_days(days):
    new_date = datetime.date.today() + datetime.timedelta(days=days)
    return new_date
