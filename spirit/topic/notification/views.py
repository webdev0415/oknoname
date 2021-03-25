# -*- coding: utf-8 -*-

import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.utils.html import escape
from django.db import transaction

from djconfig import config
from infinite_scroll_pagination.serializers import to_page_key

from ...core.conf import settings
from ...core import utils
from ...core.utils.paginator import yt_paginate
from ...core.utils.paginator.infinite_paginator import paginate
from ...topic.models import Topic
from .models import TopicNotification
from spirit.topic.models import Profile
from .forms import NotificationForm, NotificationCreationForm


@require_POST
@login_required
def create(request, topic_id):
    topic = get_object_or_404(
        Topic.objects.for_access(request.user),
        pk=topic_id)
    form = NotificationCreationForm(
        user=request.user,
        topic=topic,
        data=request.POST)

    if form.is_valid():
        form.save()
    else:
        messages.error(request, utils.render_form_errors(form))

    return redirect(request.POST.get('next', topic.get_absolute_url()))


@require_POST
@login_required
def update(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    form = NotificationForm(data=request.POST, instance=topic)

    if form.is_valid():
        try:
            with transaction.atomic():
                print(type(request.POST.getlist('is_active')[0]))
                if request.POST.getlist('is_active')[0] == 'True':
                    print('hello')
                    topic.follow.add(request.user)
                else:
                    topic.follow.remove(request.user)
                print(topic.follow.all())
                form.save()
        except Exception as e:
            print(e)
    else:
        messages.error(request, utils.render_form_errors(form))

    return redirect(request.POST.get('next', topic.get_absolute_url()))


@login_required
def index_ajax(request):
    if not request.is_ajax():
        return Http404()

    notifications = (
        TopicNotification.objects
            .for_access(request.user)
            .order_by("is_read", "-date")
            .with_related_data())
    notifications = notifications[:settings.ST_NOTIFICATIONS_PER_PAGE]
    notifications = [
        {'user': escape('Anonymous') if n.comment.anonymous == True else escape(n.comment.user.st.nickname),
         'action': n.action,
         'title': escape(n.topic.title),
         'url': n.get_absolute_url(),
         'is_read': n.is_read}
        for n in notifications]
    


    return HttpResponse(json.dumps({'n': notifications}), content_type="application/json")


@login_required
def index_unread(request):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    notifications = (
        TopicNotification.objects
            .for_access(request.user)
            .filter(is_read=False)
            .with_related_data())

    page = paginate(
        request,
        query_set=notifications,
        lookup_field='date',
        page_var='p',
        per_page=settings.ST_NOTIFICATIONS_PER_PAGE)


    context = {
        'page': page,
        'next_page': to_page_key(**page.next_page()),
        'profile': profile,}


    return render(request, 'spirit/topic/notification/index_unread.html', context)


@login_required
def index(request):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    if profile.is_allowed == True:
        notifications = yt_paginate(
            TopicNotification.objects
                .for_access(request.user)
                .with_related_data(),
            per_page=config.topics_per_page,
            page_number=request.GET.get('page', 1))
        

        return render(
            request=request,
            template_name='spirit/topic/notification/index.html',
            context={'notifications': notifications, 'profile': profile})
    else:
        return HttpResponse()
