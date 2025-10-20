from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.conf import settings
from patientapp.views import get_patient_count
from promapp.views import get_questionnaire_count, get_item_count, get_questionnaire_submission_count
import os


def service_worker_view(request):
    """
    Custom service worker view that adds the Service-Worker-Allowed header.
    This header is required to allow the service worker to control the root scope.
    """
    sw_path = settings.PWA_SERVICE_WORKER_PATH
    
    try:
        with open(sw_path, 'r') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='application/javascript')
        # Allow service worker to control the entire site (root scope)
        response['Service-Worker-Allowed'] = '/'
        # Cache control for service worker updates
        response['Cache-Control'] = 'max-age=0, no-cache, no-store, must-revalidate'
        return response
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)


class IndexView(TemplateView):
    """
    Main index/home page view that displays system statistics.
    """
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics from each app
        context['patient_count'] = get_patient_count()
        context['questionnaire_count'] = get_questionnaire_count()
        context['item_count'] = get_item_count()
        context['submission_count'] = get_questionnaire_submission_count()
        
        return context
