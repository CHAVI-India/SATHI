from django.shortcuts import render
from django.views.generic import TemplateView
from patientapp.views import get_patient_count
from promapp.views import get_questionnaire_count, get_item_count, get_questionnaire_submission_count


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
