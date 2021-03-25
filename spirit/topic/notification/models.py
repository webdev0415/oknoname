# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from .managers import TopicNotificationQuerySet
from ...core.conf import settings
from spirit.topic.models import Topic, Profile
from spirit.user.models import UserProfile
from django.contrib.auth.models import User
from anymail.message import AnymailMessage
from djconfig import config


UNDEFINED, MENTION, COMMENT, TOPIC = range(4)

ACTION_CHOICES = (
    (UNDEFINED, _("Undefined")),
    (MENTION, _("Mention")),
    (COMMENT, _("Comment")),
    (TOPIC, _("Topic")))


class TopicNotification(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='st_topic_notifications',
        on_delete=models.CASCADE)
    topic = models.ForeignKey(
        'spirit_topic.Topic',
        on_delete=models.CASCADE)
    comment = models.ForeignKey(
        'spirit_comment.Comment',
        on_delete=models.CASCADE, default=None, null=True)

    date = models.DateTimeField(default=timezone.now)
    action = models.IntegerField(choices=ACTION_CHOICES, default=UNDEFINED)
    is_read = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    objects = TopicNotificationQuerySet.as_manager()

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = _("topic notification")
        verbose_name_plural = _("topics notification")

    def get_absolute_url(self):
        if self.topic_id != self.comment.topic_id:
            # Out of sync
            return self.topic.get_absolute_url()
        return self.comment.get_absolute_url()

    @property
    def text_action(self):
        return ACTION_CHOICES[self.action][1]

    @property
    def is_mention(self):
        return self.action == MENTION

    @property
    def is_comment(self):
        return self.action == COMMENT

    @property
    def is_topic(self):
        return self.action == TOPIC

    @classmethod
    def mark_as_read(cls, user, topic):
        if not user.is_authenticated:
            return

        (cls.objects
         .filter(user=user, topic=topic)
         .update(is_read=True))

    @classmethod
    def create_maybe(cls, user, comment, is_read=True, action=COMMENT):
        # Create a dummy notification
        print(comment.topic.id, user.id)
        try:
            users = comment.topic.follow.all()
            li=[]
            for i in users:
                user_id = User.objects.get(username=i).id
                profile = UserProfile.objects.get(user__id=user_id)
                if i != comment.user:
                    li.append(i)
            print(users, li)
            if user not in comment.topic.follow.all():
                comment.topic.follow.add(user)

            if li:
                for i in li:
                    nottification = cls.objects.create(
                                    user=i,
                                    topic=comment.topic,
                                    comment=comment,
                                    action=action,
                                    is_read=is_read,
                                    is_active=True)
                return nottification
            
        except Exception as e:
            print('comment error',e)

    @classmethod
    def create_maybe_topic(cls, user, topic, is_read=False):
        # Create a dummy notification
        for i in user:
            cls.objects.get_or_create(
            user=i,
            topic=topic,
            defaults={
                'is_read': is_read,
                'is_active': True,
                'action': TOPIC
            })
        if topic.user not in topic.follow.all():
            topic.follow.add(topic.user)



    @classmethod
    def notify_new_comment(cls, comment, request):
        topic_followers = Topic.objects.get(id=comment.topic.id)
        followers = topic_followers.follow.all()

        if comment.user in followers:
            (cls.objects
            .filter(topic=comment.topic, is_active=True, is_read=True)
            .exclude(user=comment.user)
            .update(comment=comment, is_read=False, action=COMMENT, date=timezone.now()))

            
            print(followers)
            email_li = []
            for i in followers:
                user_id = User.objects.get(username=i).id
                profile = UserProfile.objects.get(user__id=user_id)
                print(comment.user, comment.topic.user, request.user, profile.user, comment.topic.follow.all())
                if User.objects.get(id=user_id).email != '' and profile.user in comment.topic.follow.all():
                    if profile.user != comment.user and comment.user == request.user:
                        email_li.append(User.objects.get(id=user_id).email)
                    else:
                        pass

            print('here it is?!',email_li)
            
            for i in email_li:
                current_site = Site.objects.get_current()
                domain = current_site.domain
                subject, from_email, to = f'New Comment on: {comment.topic.title}', 'Spaghetti@example.com', ['arnoutdev@gmail.com'] # i
                msg_plain = render_to_string('spirit/topic/emailcomment.html', {'comment': comment, 'domain': domain, 'slug': comment.topic.slug, 'id': comment.topic.id, 'site_name': config.site_name, 'user': User.objects.get(email=i)})
                text_content = 'Someone Commented on Topic.'
                html_content = msg_plain
                msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

    @classmethod
    def notify_new_mentions(cls, comment, mentions, request):
        if not mentions:
            return

        # TODO: refactor
        email_li = []
        for username, user in mentions.items():
            email_li.append(user.email)
            try:
                with transaction.atomic():
                    cls.objects.create(
                        user=user,
                        topic=comment.topic,
                        comment=comment,
                        is_read=True,
                        action=MENTION,
                        is_active=True)
            except IntegrityError as e:
                print(e)

        (cls.objects
         .filter(
            user__in=mentions.values(),
            topic=comment.topic,
            is_read=True)
         .update(
            comment=comment,
            is_read=False,
            action=MENTION,
            date=timezone.now()))

        print(email_li, 'here')

        current_site = Site.objects.get_current()
        domain = current_site.domain
        for i in email_li:
            subject, from_email, to = f'Mentioned on: {comment.topic.title}', 'Spaghetti@example.com', ['arnoutdev@gmail.com'] # i
            msg_plain = render_to_string('spirit/topic/emailmention.html', {'comment': comment, 'domain': domain, 'slug': comment.topic.slug, 'id': comment.topic.id, 'site_name': config.site_name, 'user': User.objects.get(email=i)})
            text_content = 'Someone Mentioned you on a comment.'
            html_content = msg_plain
            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

    @classmethod
    def bulk_create(cls, users, comment):
        return cls.objects.bulk_create([
            cls(user=user,
                topic=comment.topic,
                comment=comment,
                action=COMMENT,
                is_active=True)
            for user in users])

    # XXX add tests
    # XXX fix with migration (see issue #237)
    @classmethod
    def sync(cls, comment, topic):
        # Notifications can go out of sync
        # when the comment is no longer
        # within the topic (i.e moved).
        # User is subscribed to the topic,
        # not the comment, so we either update
        # it to a newer comment or set it as undefined
        if comment.topic_id == topic.pk:
            return
        next_comment = (
            topic.comment_set
                .filter(date__gt=comment.date)
                .order_by('date')
                .first())
        if next_comment is None:
            (cls.objects
             .filter(comment=comment, topic=topic)
             .update(is_read=True, action=UNDEFINED))
            return
        (cls.objects
         .filter(comment=comment, topic=topic)
         .update(comment=next_comment, action=COMMENT))

    @classmethod
    def notify_new_topic(cls, topic, comment=False):
        (cls.objects
         .filter(topic=topic, is_active=True, is_read=True)
         .exclude(user=topic.user)
         .update(is_read=False, date=timezone.now()))

        if topic.send_email == True:
            li = []
            if topic.user.st.is_moderator == True:
                users = list(UserProfile.objects.filter(Q(email_send='1') | Q(email_send='2')).exclude(user__id=topic.user.id).values('user__email'))
                for user in users:
                    if user['user__email'] != '':
                        li.append(user['user__email'])
            elif not topic.user.st.is_moderator == True:
                users = list(UserProfile.objects.filter(email_send='2').exclude(user__id=topic.user.id).values('user__email'))
                for user in users:
                    if user['user__email'] != '':
                        li.append(user['user__email'])
            print(li)
            current_site = Site.objects.get_current()
            domain = current_site.domain
            subject, from_email, to = f'New topic on {config.site_name} : {topic.title}', 'Spaghetti@example.com', ['arnoutdev@gmail.com'] # li
            text_content = 'Someone Created a new Topic.'

            for i in li:
                msg_plain = render_to_string('spirit/topic/topicemailnew.html', {'slug': topic.slug, 'id': topic.id, 'user': User.objects.get(email=i), 'domain': domain, 'title': topic.title, 'site_name': config.site_name})
                html_content = msg_plain
                msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                msg.attach_alternative(html_content, "text/html")
                msg.send()