# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponsePermanentRedirect, JsonResponse, HttpResponseRedirect
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models import Q
from django.db import transaction
from djconfig import config

from ..core.utils.views import is_post, post_data
from ..core.utils.paginator import paginate, yt_paginate
from spirit.topic.notification.models import TopicNotification
from ..core.utils.ratelimit.decorators import ratelimit
from ..category.models import Category
from ..comment.models import MOVED
from ..comment.forms import CommentForm
from ..comment.utils import comment_posted, published_topic
from ..comment.models import Comment
from .models import Topic, Password, Profile
from .forms import TopicForm
from spirit.user.models import UserProfile
from . import utils


@login_required
@ratelimit(rate='1/10s')
def publish(request, category_id=None):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    if profile.is_allowed == True:
        if category_id:
            get_object_or_404(
                Category.objects.visible(),
                pk=category_id)

        user = request.user
        form = TopicForm(
            user=user,
            data=post_data(request),
            initial={'category': category_id})
        cform = CommentForm(
            user=user,
            data=post_data(request))
        if (is_post(request) and
                all([form.is_valid(), cform.is_valid()]) and
                not request.is_limited()):
            # if not user.st.update_post_hash(form.get_topic_hash()):
            #     return redirect(
            #         request.POST.get('next', None) or
            #         form.get_category().get_absolute_url())

            topic = form.save()
            if topic.send_email == True:
                li = []
                if loggedinuser.st.is_moderator == True:
                    users = list(UserProfile.objects.filter(Q(email_send='1') | Q(email_send='2')).exclude(user__id=loggedinuser.id).values('user__email'))
                    for user in users:
                        if user['user__email'] != '':
                            li.append(user['user__email'])
                elif not loggedinuser.st.is_moderator == True:
                    users = list(UserProfile.objects.filter(email_send='2').exclude(user__id=loggedinuser.id).values('user__email'))
                    for user in users:
                        if user['user__email'] != '':
                            li.append(user['user__email'])
                print(li)
                # current_site = Site.objects.get_current()
                # domain = current_site.domain
                # msg_plain = render_to_string('spirit/topic/topicemailnew.html', {'slug': topic.slug, 'id': topic.id, 'loggedinuser': loggedinuser, 'domain': domain, 'title': topic.title, 'site_name': config.site_name})
                # if li:
                #     subject, from_email, to = f'New topic on {config.site_name} : {topic.title}', 'Spaghetti@example.com', ['hammadarshad834@gmail.com'] # li
                #     text_content = 'Someone Created a new Topic.'
                #     html_content = msg_plain
                #     msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                #     msg.attach_alternative(html_content, "text/html")
                #     msg.send()
            cform.topic = topic 
            if cform.cleaned_data['anonymous']:
                topic.anonymous = True
                topic.save()
            comment = cform.save()
            published_topic(topic=topic, user=User.objects.all().exclude(id=request.user.id))
            comment_posted(comment=comment, mentions=cform.mentions, request=request)
            return redirect(topic.get_absolute_url())
                
        return render(
            request=request,
            template_name='spirit/topic/publish.html',
            context={'form': form, 'cform': cform, 'profile': profile})
            

    return HttpResponseRedirect('/')


@login_required
def update(request, pk):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    topic = Topic.objects.for_update_or_404(pk, request.user)
    category_id = topic.category_id
    form = TopicForm(
        user=request.user,
        data=post_data(request),
        instance=topic)
    if is_post(request) and form.is_valid():
        topic = form.save()
        if topic.category_id != category_id:
            Comment.create_moderation_action(
                user=request.user, topic=topic, action=MOVED)
        return redirect(request.POST.get('next', topic.get_absolute_url()))
    return render(
        request=request,
        template_name='spirit/topic/update.html',
        context={'form': form, 'profile': profile})

@login_required
def detail(request, pk, slug):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    topic = Topic.objects.get_public_or_404(pk, request.user)

    if topic.slug != slug:
        return HttpResponsePermanentRedirect(topic.get_absolute_url())

    utils.topic_viewed(request=request, topic=topic)

    comments = (
        Comment.objects
        .for_topic(topic=topic)
        .with_likes(user=request.user)
        .with_polls(user=request.user)
        .order_by('date'))

    comments = paginate(
        comments,
        per_page=config.comments_per_page,
        page_number=request.GET.get('page', 1))

    return render(
        request=request,
        template_name='spirit/topic/detail.html',
        context={
            'topic': topic,
            'comments': comments,
            'profile': profile})

@login_required
def index_active(request):
    loggedinuser = request.user
    if not Profile.objects.filter(user=loggedinuser):
        try:
            with transaction.atomic():
                if loggedinuser.is_superuser:
                    Profile(user=loggedinuser, is_allowed=True).save()
                else:
                    Profile(user=loggedinuser).save()
        except Exception as e:
            print(e)
    
    if not Password.objects.last():
        Password(password='default123').save()

    profile = Profile.objects.get(user=loggedinuser)
    if profile.is_allowed == True:
        categories = (
            Category.objects
            .visible()
            .parents())

        topics = (
            Topic.objects
            .visible()
            .global_()
            .with_bookmarks(user=request.user)
            .order_by('-is_globally_pinned', '-last_active')
            .select_related('category'))

        topics = yt_paginate(
            topics,
            per_page=config.topics_per_page,
            page_number=request.GET.get('page', 1))

        return render(
            request=request,
            template_name='spirit/topic/active.html',
            context={
                'categories': categories,
                'topics': topics,
                'profile': profile})

    if request.method == 'POST':
        samp = request.POST.get('samp')
        if samp == 'forum_password':
            password = Password.objects.last()
            password_get = request.POST.get('password')
            if password.password == password_get:
                pr = Profile.objects.get(user=loggedinuser)
                pr.is_allowed = True
                pr.save()
                return JsonResponse({'success': 'success'})
            else:
                return JsonResponse({'error': 'Password is Invalid'})
                

    return render(request, 'spirit/topic/active.html', {'profile': profile})


def find_topic(request, pk):
    topic=Topic.objects.get(id=pk)
    # n = TopicNotification.objects.filter(topic__id=pk, user=request.user)
    # n.is_read = True
    # n.save()
    # print('here', n)
    # topic = get_object_or_404(Topic.objects.select_related('topic'), pk=pk)
    url = paginator.get_url(
        topic.get_absolute_url(),
        'page')
    return redirect(url)