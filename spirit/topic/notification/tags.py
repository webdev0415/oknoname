# -*- coding: utf-8 -*-

from ...core.tags.registry import register
from .models import TopicNotification
from spirit.comment.models import Comment
from .forms import NotificationForm


@register.simple_tag()
def has_topic_notifications(user):
    return TopicNotification.objects.for_access(user=user).unread().exists()


@register.inclusion_tag('spirit/topic/notification/_form.html')
def render_notification_form(user, topic, next=None):
    # TODO: remove form and use notification_activate and notification_deactivate ?
    # try:
    #     print(topic)
    #     # notification = TopicNotification.objects.filter(user=user, topic=topic, action=2).first()
    # except TopicNotification.DoesNotExist:
    #     notification = None

    initial = {}

    if topic:
        if user in topic.follow.all():
            initial['is_active'] = not True
        else:
            initial['is_active'] = not False

    form = NotificationForm(initial=initial)
    return {'form': form, 'topic_id': topic.pk, 'notification': topic, 'next': next, 'user': user}
