# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect

from djconfig import config

from ..core.utils.views import is_post, post_data
from ..core.utils.paginator import yt_paginate
from .utils.email import send_email_change_email
from .utils.tokens import UserEmailChangeTokenGenerator
from ..topic.models import Topic
from ..comment.models import Comment
from .forms import UserProfileForm, EmailChangeForm, UserForm, EmailCheckForm
from spirit.topic.models import Profile

User = get_user_model()


@login_required
def update(request):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    if profile.is_allowed == True:
        uform = UserForm(
            data=post_data(request),
            instance=request.user)
        form = UserProfileForm(
            data=post_data(request),
            instance=request.user.st)
        if is_post(request) and all([uform.is_valid(), form.is_valid()]):  # TODO: test!
            uform.save()
            form.save()
            messages.info(request, _("Your profile has been updated!"))
            return redirect(reverse('spirit:user:update'))
        return render(
            request=request,
            template_name='spirit/user/profile_update.html',
            context={'form': form, 'uform': uform, 'profile': profile})
    else:
        return HttpResponseRedirect('/')


@login_required
def password_change(request):
    form = PasswordChangeForm(
        user=request.user,
        data=post_data(request))
    if is_post(request) and form.is_valid():
        form.save()
        update_session_auth_hash(request, form.user)
        messages.info(request, _("Your password has been changed!"))
        return redirect(reverse('spirit:user:update'))
    return render(
        request=request,
        template_name='spirit/user/profile_password_change.html',
        context={'form': form})


@login_required
def email_change(request):
    form = EmailChangeForm(
        user=request.user,
        data=post_data(request))
    if is_post(request) and form.is_valid():
        send_email_change_email(request, request.user, form.get_email())
        messages.info(
            request,
            _("We have sent you an email "
              "so you can confirm the change!"))
        return redirect(reverse('spirit:user:update'))
    return render(
        request=request,
        template_name='spirit/user/profile_email_change.html',
        context={'form': form})


@login_required
def email_change_confirm(request, token):
    user = request.user
    user_email_change = UserEmailChangeTokenGenerator()

    if user_email_change.is_valid(user, token):
        email = user_email_change.get_email()
        form = EmailCheckForm(data={'email': email, })

        if form.is_valid():
            user.email = form.get_email()
            user.save()
            messages.info(request, _("Your email has been changed!"))
            return redirect(reverse('spirit:user:update'))

    messages.error(request, _("Sorry, we were not able to change your email."))
    return redirect(reverse('spirit:user:update'))


@login_required
def _activity(request, pk, slug, queryset, template, reverse_to, context_name, per_page):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    p_user = get_object_or_404(User, pk=pk)
    if p_user.st.slug != slug:
        return HttpResponsePermanentRedirect(
            reverse(reverse_to, kwargs={'pk': p_user.pk, 'slug': p_user.st.slug}))
    items = yt_paginate(
        queryset,
        per_page=per_page,
        page_number=request.GET.get('page', 1))
    return render(
        request=request,
        template_name=template,
        context={'p_user': p_user, context_name: items, 'profile': profile})



def topics(request, pk, slug):
    user_topics = (
        Topic.objects
        .visible()
        .with_bookmarks(user=request.user)
        .filter(user_id=pk, anonymous=False)
        .select_related('category', 'user__st')
        .order_by('-date', '-pk'))

    return _activity(
        request, pk, slug,
        queryset=user_topics,
        template='spirit/user/profile_topics.html',
        reverse_to='spirit:user:topics',
        context_name='topics',
        per_page=config.topics_per_page)


def comments(request, pk, slug):
    # todo: test with_polls!
    user_comments = (
        Comment.objects
        .filter(user_id=pk, anonymous=False)
        .visible()
        .with_polls(user=request.user)
        .select_related('topic'))

    return _activity(
        request, pk, slug,
        queryset=user_comments,
        template='spirit/user/profile_comments.html',
        reverse_to='spirit:user:detail',
        context_name='comments',
        per_page=config.comments_per_page)


def likes(request, pk, slug):
    # todo: test with_polls!
    user_comments = (
        Comment.objects
        .filter(comment_likes__user_id=pk)
        .visible()
        .with_polls(user=request.user)
        .select_related('topic')
        .order_by('-comment_likes__date', '-pk'))

    return _activity(
        request, pk, slug,
        queryset=user_comments,
        template='spirit/user/profile_likes.html',
        reverse_to='spirit:user:likes',
        context_name='comments',
        per_page=config.comments_per_page)


@login_required
def menu(request):
    return render(
        request=request,
        template_name='spirit/user/menu.html')
