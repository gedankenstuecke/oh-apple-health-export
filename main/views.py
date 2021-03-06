import io
import urllib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from openhumans.models import OpenHumansMember
from .tasks import process_batch
from .models import AppleHealthUser
from datetime import datetime


def index(request):
    """
    Starting page for app.
    """
    try:
        auth_url = OpenHumansMember.get_auth_url()
    except ImproperlyConfigured:
        auth_url = None
    if not auth_url:
        messages.info(request,
                      mark_safe(
                          '<b>You need to set up your ".env"'
                          ' file!</b>'))

    context = {'auth_url': auth_url}
    if request.user.is_authenticated:
        receiver_url = urllib.parse.urljoin(
            settings.OPENHUMANS_APP_BASE_URL,
            "receiver/{}/".format(
                request.user.openhumansmember.applehealthuser.endpoint_token))
        context['exporter_url'] = receiver_url
        context['exporter_endpoint'] = "com.HealthExport://apiexport?url={}".format(receiver_url)
    return render(request, 'main/index.html', context=context)


def get_overland_file(oh_member):
    files = oh_member.list_files()
    for f in files:
        if f['basename'] == 'overland-data.json':
            return f['download_url']
    return None


def about(request):
    """
    give FAQ and further details on the app
    """
    return render(request, 'main/about.html')


def logout_user(request):
    """
    Logout user
    """
    if request.method == 'POST':
        logout(request)
    redirect_url = settings.LOGOUT_REDIRECT_URL
    return redirect(redirect_url)


@csrf_exempt
def receiver(request, token):
    """
    Endpoint for receiving Overland data
    """
    if request.method == 'POST':
        ahuser = AppleHealthUser.objects.get(endpoint_token=token)
        body = json.loads(request.body)
        print(body.keys())
        print(body['data'].keys())
        print(len(body['data']['metrics']))
        # for i in body['data']['metrics']:
        #   print(i)
        # print(body['data']['workouts'])
        body = json.loads(request.body)
        metrics = body['data']['metrics']
        now = (datetime.now().timestamp())
        fname = 'health-metric-batch-{}.json'.format(now)
        stream = io.BytesIO(bytes(json.dumps(metrics), 'utf-8'))
        metadata = {
            'tags': ['apple health', 'metrics', 'unprocessed'],
            'description': 'unprocessed apple health match'}
        ahuser.oh_member.upload(
            stream=stream, filename=fname,
            metadata=metadata)
        print('UPLOADED BATCH FOR {0}'.format(ahuser.oh_member.oh_id))
        process_batch.delay(fname, ahuser.oh_member.oh_id)
        return JsonResponse({"result": "ok"})
        #return HttpResponse('In receiver: no user')
#    try:
#        oluser = OverlandUser.objects.get(endpoint_token=token)
#        print('IN RECEIVER FOR {0}'.format(oluser.oh_member.oh_id))
#        if request.method == 'POST':
#            # this is just to temporarily stop adding more batch files!!!
#            # return HttpResponse('temp offline')
#            #
#            now = (datetime.now().timestamp())
#            fname = 'overland-batch-{}.json'.format(now)
#            stream = io.BytesIO(request.body)
#            metadata = {
#                'tags': ['GPS', 'location', 'json', 'unprocessed'],
#                'description': 'Overland GPS data batch'}
#            oluser.oh_member.upload(
#                stream=stream, filename=fname,
#                metadata=metadata)
#            print('UPLOADED BATCH FOR {0}'.format(oluser.oh_member.oh_id))
#            process_batch.delay(fname, oluser.oh_member.oh_id)
#            return JsonResponse({"result": "ok"})
#        else:
#            context = {'overland_endpoint': urllib.parse.urljoin(
#                settings.OPENHUMANS_APP_BASE_URL,
#                token+"/")}
#            return render(request, 'main/receiver.html', context=context)
#    except OverlandUser.DoesNotExist:
#        return HttpResponse('In receiver: no user')
