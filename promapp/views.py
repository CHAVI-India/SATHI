from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Questionnaire, Item, QuestionnaireItemResponse, LikertScale, RangeScale
from .forms import QuestionnaireForm, ItemForm, QuestionnaireItemResponseForm, LikertScaleForm, RangeScaleForm, LikertScaleResponseOptionFormSet

# Create your views here.

class QuestionnaireListView(ListView):
    model = Questionnaire
    template_name = 'questionnaire/setup.html'
    context_object_name = 'questionnaires'
    ordering = ['-created_date']

class QuestionnaireCreateView(CreateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = 'questionnaire/create.html'
    success_url = reverse_lazy('questionnaire_setup')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item_form'] = ItemForm()
        context['available_items'] = Item.objects.all()
        context['likert_scales'] = LikertScale.objects.all()
        context['range_scales'] = RangeScale.objects.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        # Handle item responses here
        return response

def get_response_fields(request):
    response_type = request.GET.get('response_type')
    html = render_to_string('questionnaire/response_fields.html', {
        'response_type': response_type,
        'likert_scales': LikertScale.objects.all(),
        'range_scales': RangeScale.objects.all()
    })
    return HttpResponse(html)

def add_item_form(request):
    item_form = ItemForm()
    html = render_to_string('questionnaire/item_form.html', {
        'item_form': item_form,
        'forloop': {'counter': request.GET.get('counter', 1)}
    })
    return HttpResponse(html)

def create_likert_scale(request):
    if request.method == 'POST':
        form = LikertScaleForm(request.POST)
        formset = LikertScaleResponseOptionFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            likert_scale = form.save()
            formset.instance = likert_scale
            formset.save()
            response = HttpResponse("")
            response['HX-Trigger'] = 'likertScaleCreated'
            return response
    else:
        form = LikertScaleForm()
        formset = LikertScaleResponseOptionFormSet()
    html = render_to_string('questionnaire/likert_scale_form.html', {'form': form, 'formset': formset}, request=request)
    return HttpResponse(html)

def create_range_scale(request):
    if request.method == 'POST':
        form = RangeScaleForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse('<script>window.dispatchEvent(new Event("rangeScaleCreated"));closeModal();</script>')
    else:
        form = RangeScaleForm()
    html = render_to_string('questionnaire/range_scale_form.html', {'form': form}, request=request)
    return HttpResponse(html)
