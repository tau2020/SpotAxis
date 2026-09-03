import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from upload_logos.forms import UploadedFileForm


@login_required
@require_POST
def upload(request):
    """Stage an image upload (logo/photo) and return its URL."""
    upload_file = request.FILES.get('file')
    if upload_file is not None and upload_file.size > settings.MAX_UPLOAD_SIZE:
        return HttpResponseBadRequest(json.dumps({'errors': {'file': ['File is too large.']}}), content_type='application/json')
    form = UploadedFileForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        uploaded_file = form.save()
        return HttpResponse(json.dumps({'path': uploaded_file.file.url}), content_type='application/json')
    return HttpResponseBadRequest(json.dumps({'errors': form.errors}), content_type='application/json')
