from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db import transaction
from .models import Questionnaire, Item, QuestionnaireItem, LikertScale, RangeScale, ConstructScale, RangeScaleResponseOption
from .forms import (
    QuestionnaireForm, ItemForm, QuestionnaireItemForm, 
    LikertScaleForm, RangeScaleForm, LikertScaleResponseOptionFormSet,
    ItemSelectionForm, ConstructScaleForm
)

# Create your views here.

class QuestionnaireListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Questionnaire
    template_name = 'promapp/questionnaire_list.html'
    context_object_name = 'questionnaires'
    ordering = ['-created_date']
    permission_required = 'promapp.view_questionnaire'


class QuestionnaireDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Questionnaire
    template_name = 'promapp/questionnaire_detail.html'
    context_object_name = 'questionnaire'
    permission_required = 'promapp.view_questionnaire'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all items associated with this questionnaire
        questionnaire = self.get_object()
        items = Item.objects.filter(
            id__in=QuestionnaireItem.objects.filter(
                questionnaire=questionnaire
            ).values_list('item', flat=True).distinct()
        )
        context['items'] = items
        return context


class QuestionnaireCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = 'promapp/questionnaire_create.html'
    success_url = reverse_lazy('questionnaire_list')
    permission_required = 'promapp.add_questionnaire'

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
            
            # Create QuestionnaireItem objects for each selected item
            for item in selected_items:
                # Get the question number for this item
                question_number = self.request.POST.get(f'question_number_{item.id}')
                
                QuestionnaireItem.objects.create(
                    questionnaire=questionnaire,
                    item=item,
                    question_number=question_number if question_number else None
                )
            
            messages.success(self.request, f"Questionnaire '{questionnaire.name}' created successfully with {len(selected_items)} items.")
        else:
            messages.warning(self.request, "Questionnaire created, but there was an issue with item selection.")
            
        return redirect(self.success_url)


class QuestionnaireUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = 'promapp/questionnaire_update.html'
    success_url = reverse_lazy('questionnaire_list')
    permission_required = 'promapp.change_questionnaire'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questionnaire = self.get_object()
        
        # Get all questionnaire items for this questionnaire
        questionnaire_items = QuestionnaireItem.objects.filter(questionnaire=questionnaire)
        
        # Create a mapping of item IDs to question numbers
        item_to_question_number = {str(qi.item.id): qi.question_number for qi in questionnaire_items}
        
        # Get all available items
        available_items = Item.objects.all().order_by('construct_scale__name', 'name')
        
        # Get currently selected items
        current_items = Item.objects.filter(
            id__in=questionnaire_items.values_list('item', flat=True)
        )
        
        # Add question_number attribute to each item
        for item in available_items:
            item.question_number = item_to_question_number.get(str(item.id))
        
        # Initialize the form with current items
        context['item_selection_form'] = ItemSelectionForm(initial={'items': current_items})
        context['available_items'] = available_items
        context['construct_scales'] = ConstructScale.objects.all()
        return context

    @transaction.atomic
    def form_valid(self, form):
        questionnaire = form.save()
        
        # Process selected items
        item_selection_form = ItemSelectionForm(self.request.POST)
        if item_selection_form.is_valid():
            selected_items = item_selection_form.cleaned_data.get('items', [])
            
            # Remove existing item associations
            QuestionnaireItem.objects.filter(
                questionnaire=questionnaire,
            ).delete()
            
            # Create new associations for selected items
            for item in selected_items:
                # Get the question number for this item
                question_number = self.request.POST.get(f'question_number_{item.id}')
                
                QuestionnaireItem.objects.create(
                    questionnaire=questionnaire,
                    item=item,
                    question_number=question_number if question_number else None
                )
            
            messages.success(self.request, f"Questionnaire '{questionnaire.name}' updated successfully with {len(selected_items)} items.")
        else:
            messages.warning(self.request, "Questionnaire updated, but there was an issue with item selection.")
            
        return redirect(self.success_url)


class ItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Item
    template_name = 'promapp/item_list.html'
    context_object_name = 'items'
    ordering = ['construct_scale__name', 'name']
    permission_required = 'promapp.view_item'


class ItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'promapp/item_create.html'
    success_url = reverse_lazy('item_list')
    permission_required = 'promapp.add_item'

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
            messages.success(request, "Likert scale created successfully.")
            return redirect('item_create')
    else:
        form = LikertScaleForm()
        formset = LikertScaleResponseOptionFormSet()
    
    return render(request, 'promapp/likert_scale_form.html', {
        'form': form, 
        'formset': formset
    })

def create_range_scale(request):
    if request.method == 'POST':
        form = RangeScaleForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create the RangeScale
                range_scale = form.save()
                
                # Create the RangeScaleResponseOption
                RangeScaleResponseOption.objects.create(
                    range_scale=range_scale,
                    min_value=form.cleaned_data['min_value'],
                    min_value_text=form.cleaned_data['min_value_text'],
                    max_value=form.cleaned_data['max_value'],
                    max_value_text=form.cleaned_data['max_value_text'],
                    increment=form.cleaned_data['increment'] or 1  # Default to 1 if not provided
                )
                
            messages.success(request, "Range scale created successfully.")
            return redirect('item_create')
    else:
        form = RangeScaleForm()
    
    return render(request, 'promapp/range_scale_form.html', {
        'form': form
    })

def create_construct_scale(request):
    if request.method == 'POST':
        form = ConstructScaleForm(request.POST)
        if form.is_valid():
            construct_scale = form.save()
            messages.success(request, "Construct scale created successfully.")
            return redirect('item_create')
    else:
        form = ConstructScaleForm()
    
    return render(request, 'promapp/construct_scale_form.html', {
        'form': form
    })
