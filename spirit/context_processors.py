from django.http import request

from spirit.topic.notification.models import TopicNotification


def notification_count(request):
    '''
    count notifications and show
    '''
    if request.user.is_authenticated:
        commentNotification = TopicNotification.objects.filter(is_read=False, user=request.user).count()
        return {'notification_count': commentNotification}
    else:
        return {'notification_count': 0 }
