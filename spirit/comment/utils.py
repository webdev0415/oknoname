# -*- coding: utf-8 -*-
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.sites.models import Site

from djconfig import config

from ..topic.notification.models import TopicNotification, UNDEFINED
from spirit.user.models import UserProfile
from ..topic.unread.models import TopicUnread
from .history.models import CommentHistory
from .poll.utils.render_static import post_render_static_polls
from spirit.topic.models import Topic


def published_topic(topic, user):
    TopicNotification.create_maybe_topic(user=user, topic=topic)
    TopicNotification.notify_new_topic(topic=topic)


def comment_posted(comment, mentions, request):
    if not mentions:
        TopicNotification.create_maybe(user=comment.user, comment=comment)
        print(mentions)
        TopicNotification.notify_new_comment(comment=comment, request=request)
    elif mentions:
        TopicNotification.notify_new_mentions(comment=comment, mentions=mentions)
    TopicUnread.unread_new_comment(comment=comment)
    comment.topic.increase_comment_count()


def pre_comment_update(comment):
    comment.comment_html = post_render_static_polls(comment)
    CommentHistory.create_maybe(comment)


def post_comment_update(comment):
    comment.increase_modified_count()

    comment.comment_html = post_render_static_polls(comment)
    CommentHistory.create(comment)


# XXX add tests
def post_comment_move(comment, topic):
    TopicNotification.sync(comment=comment, topic=topic)
