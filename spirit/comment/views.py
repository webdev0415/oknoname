# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import Http404
from djconfig import config

from ..core.utils.views import is_post, post_data
from ..core.utils.ratelimit.decorators import ratelimit
from ..core.utils.decorators import moderator_required
from ..core.utils import markdown, paginator, render_form_errors, json_response
from ..topic.models import Topic
from .models import Comment
from spirit.topic.models import Profile
from .forms import CommentForm, CommentMoveForm, CommentImageForm, CommentFileForm
from .utils import comment_posted, post_comment_update, pre_comment_update, post_comment_move


@login_required
@ratelimit(rate='1/10s')
def publish(request, topic_id, pk=None):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    initial = None
    if pk:  # todo: move to form
        comment = get_object_or_404(
            Comment.objects.for_access(user=request.user), pk=pk)
        quote = markdown.quotify(comment.comment, comment.user.st.nickname)
        initial = {'comment': quote}

    user = request.user
    topic = get_object_or_404(
        Topic.objects.opened().for_access(user),
        pk=topic_id)
    form = CommentForm(
        user=user,
        topic=topic,
        data=post_data(request),
        initial=initial)

    if is_post(request) and not request.is_limited() and form.is_valid():
        if not user.st.update_post_hash(form.get_comment_hash()):
            # Hashed comment may have not been saved yet
            return redirect(
                request.POST.get('next', None) or
                Comment
                .get_last_for_topic(topic_id)
                .get_absolute_url())

        comment = form.save()

        comment_posted(comment=comment, mentions=form.mentions, request=request)
        return redirect(request.POST.get('next', comment.get_absolute_url()))

    return render(
        request=request,
        template_name='spirit/comment/publish.html',
        context={
            'form': form,
            'topic': topic,
            'profile': profile})


@login_required
def update(request, pk):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    comment = Comment.objects.for_update_or_404(pk, request.user)
    form = CommentForm(data=post_data(request), instance=comment)
    if is_post(request) and form.is_valid():
        pre_comment_update(comment=Comment.objects.get(pk=comment.pk))
        comment = form.save()
        post_comment_update(comment=comment)
        return redirect(request.POST.get('next', comment.get_absolute_url()))
    return render(
        request=request,
        template_name='spirit/comment/update.html',
        context={'form': form, 'profile': profile})


@moderator_required
def delete(request, pk, remove=True):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    comment = get_object_or_404(Comment, pk=pk)
    if is_post(request):
        (Comment.objects
         .filter(pk=pk)
         .update(is_removed=remove))
        return redirect(request.GET.get('next', comment.get_absolute_url()))
    return render(
        request=request,
        template_name='spirit/comment/moderate.html',
        context={'comment': comment, 'profile': profile})


@require_POST
@moderator_required
def move(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    form = CommentMoveForm(topic=topic, data=request.POST)

    if form.is_valid():
        comments = form.save()

        for comment in comments:
            comment_posted(comment=comment, mentions=None, request=request)
            topic.decrease_comment_count()
            post_comment_move(comment=comment, topic=topic)
    else:
        messages.error(request, render_form_errors(form))

    return redirect(request.POST.get('next', topic.get_absolute_url()))


def find(request, pk):
    comment = get_object_or_404(Comment.objects.select_related('topic'), pk=pk)
    comment_number = Comment.objects.filter(topic=comment.topic, date__lte=comment.date).count()
    url = paginator.get_url(
        comment.topic.get_absolute_url(),
        comment_number,
        config.comments_per_page,
        'page')
    return redirect(url)


@require_POST
@login_required
def image_upload_ajax(request):
    if not request.is_ajax():
        return Http404()

    form = CommentImageForm(user=request.user, data=request.POST, files=request.FILES)

    if form.is_valid():
        image = form.save()
        return json_response({'url': image.url})

    return json_response({'error': dict(form.errors.items()), })


@require_POST
@login_required
def file_upload_ajax(request):
    if not request.is_ajax():
        return Http404()

    form = CommentFileForm(user=request.user, data=request.POST, files=request.FILES)

    if form.is_valid():
        file = form.save()
        return json_response({'url': file.url})

    return json_response({'error': dict(form.errors.items())})
