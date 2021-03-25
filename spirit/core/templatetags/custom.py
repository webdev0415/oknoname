from django import template

from spirit.topic.notification.models import UserProfile

register = template.Library()

@register.filter(name='is_allowed')
def is_allowed(value, arg):
    """
    check user is allowed or not
    """
    p = value
    if p.anonymous == False:
        return p.user.username
    else:
        return 'Anonymous'


@register.simple_tag
def check_notification(value, user):
    '''
    check notification
    '''
    print(user, value)
    if user in value.follow.all():
        return True
    else:
        return False
    
