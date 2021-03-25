# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.contrib.auth import get_user_model

import spirit
from ..category.models import Category
from ..comment.flag.models import CommentFlag
from ..comment.like.models import CommentLike
from ..comment.models import Comment
from ..topic.models import Topic
from ..core.utils.views import is_post, post_data
from ..core.utils.decorators import administrator_required
from .forms import BasicConfigForm
from spirit.topic.models import Password, Profile

User = get_user_model()


@administrator_required
def config_basic(request):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    form = BasicConfigForm(data=post_data(request))
    if is_post(request) and form.is_valid():
        form.save()
        Password.objects.last().delete()
        Password(password=request.POST.get('forum_password')).save()
        messages.info(request, _("Settings updated!"))
        return redirect(request.GET.get("next", request.get_full_path()))        

    return render(
        request=request,
        template_name='spirit/admin/config_basic.html',
        context={'form': form, 'profile': profile})


@administrator_required
def dashboard(request):
    loggedinuser = request.user
    profile = Profile.objects.get(user=loggedinuser)
    # Strongly inaccurate counters below...
    context = {
        'version': spirit.__version__,
        'category_count': Category.objects.all().count() - 1,  # - private
        'topics_count': Topic.objects.all().count(),
        'comments_count': Comment.objects.all().count(),
        'users_count': User.objects.all().count(),
        'flags_count': CommentFlag.objects.filter(is_closed=False).count(),
        'likes_count': CommentLike.objects.all().count(),
        'profile': profile
    }

    return render(request, 'spirit/admin/dashboard.html', context)
