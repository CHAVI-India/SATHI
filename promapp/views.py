from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from .models import Questionnaire, Item, QuestionnaireItemResponse, LikertScale, RangeScale, ConstructScale
from .forms import (
    QuestionnaireForm, ItemForm, QuestionnaireItemResponseForm, 
    LikertScaleForm, RangeScaleForm, LikertScaleResponseOptionFormSet,
    ItemSelectionForm, ConstructScaleForm
)

# Create your views here.

class QuestionnaireListView(LoginRequiredMixin, ListView):
    model = Questionnaire
    template_name = 'promapp/questionnaire_list.html'
    context_object_name = 'questionnaires'
    ordering = ['-created_date']


class QuestionnaireDetailView(LoginRequiredMixin, DetailView):
    model = Questionnaire
    template_name = 'promapp/questionnaire_detail.html'
    context_object_name = 'questionnaire'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all items associated with this questionnaire
        questionnaire = self.get_object()
        items = Item.objects.filter(
            id__in=QuestionnaireItemResponse.objects.filter(
                questionnaire=questionnaire
            ).values_list('item', flat=True).distinct()
        )
        context['items'] = items
        return context


class QuestionnaireCreateView(LoginRequiredMixin, CreateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = 'promapp/questionnaire_create.html'
    success_url = reverse_lazy('questionnaire_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item_selection_form'] = ItemSelectionForm()
        context['available_items'] = Item.objects.all().order_by('construct_scale__name', 'name')
        context['construct_scales'] = ConstructScale.objects.all()
        return context

    @transaction.atomic
    def form_valid(self, form):
        # Save the questionnaire
        questionnaire = form.save()
        
        # Process selected items
        item_selection_form = ItemSelectionForm(self.request.POST)
        if item_selection_form.is_valid():
            selected_items = item_selection_form.cleaned_data.get('items', [])
            
            # Create QuestionnaireItemResponse objects for each selected item
            for item in selected_items:
                QuestionnaireItemResponse.objects.create(
                    questionnaire=questionnaire,
                    item=item,
                    # Patient will be assigned when the questionnaire is filled out
                    patient=None
                )
            
            messages.success(self.request, f"Questionnaire '{questionnaire.name}' created successfully with {len(selected_items)} items.")
        else:
            messages.warning(self.request, "Questionnaire created, but there was an issue with item selection.")
            
        return redirect(self.success_url)


class QuestionnaireUpdateView(LoginRequiredMixin, UpdateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = 'promapp/questionnaire_update.html'
    success_url = reverse_lazy('questionnaire_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questionnaire = self.get_object()
        
        # Get currently selected items
        current_items = Item.objects.filter(
            id__in=QuestionnaireItemResponse.objects.filter(
                questionnaire=questionnaire, 
                patient__isnull=True  # Only include items that haven't been assigned to patients
            ).values_list('item', flat=True)
        )
        
        # Initialize the form with current items
        context['item_selection_form'] = ItemSelectionForm(initial={'items': current_items})
        context['available_items'] = Item.objects.all().order_by('construct_scale__name', 'name')
        context['construct_scales'] = ConstructScale.objects.all()
        return context

    @transaction.atomic
    def form_valid(self, form):
        questionnaire = form.save()
        
        # Process selected items
        item_selection_form = ItemSelectionForm(self.request.POST)
        if item_selection_form.is_valid():
            selected_items = item_selection_form.cleaned_data.get('items', [])
            
            # Remove existing item associations that haven't been assigned to patients
            QuestionnaireItemResponse.objects.filter(
                questionnaire=questionnaire,
                patient__isnull=True
            ).delete()
            
            # Create new associations for selected items
            for item in selected_items:
                QuestionnaireItemResponse.objects.create(
                    questionnaire=questionnaire,
                    item=item,
                    patient=None
                )
            
            messages.success(self.request, f"Questionnaire '{questionnaire.name}' updated successfully with {len(selected_items)} items.")
        else:
            messages.warning(self.request, "Questionnaire updated, but there was an issue with item selection.")
            
        return redirect(self.success_url)


class ItemListView(LoginRequiredMixin, ListView):
    model = Item
    template_name = 'promapp/item_list.html'
    context_object_name = 'items'
    ordering = ['construct_scale__name', 'name']


class ItemCreateView(LoginRequiredMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'promapp/item_create.html'
    success_url = reverse_lazy('item_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['likert_scales'] = LikertScale.objects.all()
        context['range_scales'] = RangeScale.objects.all()
        return context


def get_response_fields(request):
    response_type = request.GET.get('response_type')
    html = render_to_string('promapp/response_fields.html', {
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
