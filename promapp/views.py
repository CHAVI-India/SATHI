from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from django.utils import translation
from .models import Questionnaire, Item, QuestionnaireItem, LikertScale, RangeScale, ConstructScale, ResponseTypeChoices, LikertScaleResponseOption, PatientQuestionnaire, QuestionnaireItemResponse, Patient, QuestionnaireItemRule, QuestionnaireItemRuleGroup
from .forms import (
    QuestionnaireForm, ItemForm, QuestionnaireItemForm, 
    LikertScaleForm, LikertScaleResponseOptionFormSet,
    ItemSelectionForm, ConstructScaleForm,
    LikertScaleResponseOptionForm, RangeScaleForm,
    QuestionnaireResponseForm, QuestionnaireItemRuleForm, QuestionnaireItemRuleGroupForm,
    ItemTranslationForm, QuestionnaireTranslationForm, LikertScaleResponseOptionTranslationForm, RangeScaleTranslationForm,
    TranslationSearchForm, ConstructEquationForm
)
from django.utils.translation import get_language
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
import json
import logging
from datetime import datetime, timedelta
from django.utils.timesince import timeuntil
from django.conf import settings
from django.utils import translation

# Create your views here.

class QuestionnaireListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Questionnaire
    template_name = 'promapp/questionnaire_list.html'
    context_object_name = 'questionnaires'
    ordering = ['-created_date']
    permission_required = 'promapp.view_questionnaire'

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(translations__name__icontains=search)
            
        return queryset.distinct('id').order_by('id', 'translations__name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        return context

    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/questionnaire_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)


class QuestionnaireDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Questionnaire
    template_name = 'promapp/questionnaire_detail.html'
    context_object_name = 'questionnaire'
    permission_required = 'promapp.view_questionnaire'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all items associated with this questionnaire
        questionnaire = self.get_object()
        current_language = get_language()
        items = Item.objects.language(current_language).filter(
            id__in=QuestionnaireItem.objects.filter(
                questionnaire=questionnaire
            ).values_list('item', flat=True).distinct()
        )
        context['items'] = items
        context['available_languages'] = settings.LANGUAGES
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
        current_language = get_language()
        context['available_items'] = Item.objects.language(current_language).all().order_by('construct_scale__name', 'translations__name')
        context['construct_scales'] = ConstructScale.objects.all().order_by('name')
        context['questionnaire_items'] = []  # Always empty for create view
        
        # Add rules and rule groups context
        if self.object:
            questionnaire_items = QuestionnaireItem.objects.filter(questionnaire=self.object)
            context['rules'] = QuestionnaireItemRule.objects.filter(
                questionnaire_item__in=questionnaire_items
            ).order_by('rule_order')
            context['rule_groups'] = QuestionnaireItemRuleGroup.objects.filter(
                questionnaire_item__in=questionnaire_items
            ).order_by('group_order')
        
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
            
            # Use getattr with default value instead of safe_translation_getter
            questionnaire_name = getattr(questionnaire, 'name', 'New Questionnaire')
            messages.success(self.request, f"Questionnaire '{questionnaire_name}' created successfully with {len(selected_items)} items.")
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
        from django.db.models import Prefetch
        # Prefetch rules and rule groups for all questionnaire items
        raw_items = QuestionnaireItem.objects.filter(
            questionnaire=questionnaire
        ).order_by('question_number').prefetch_related(
            Prefetch('visibility_rules', queryset=QuestionnaireItemRule.objects.order_by('rule_order')),
            Prefetch('rule_groups', queryset=QuestionnaireItemRuleGroup.objects.order_by('group_order').prefetch_related('rules'))
        )
        questionnaire_items_structured = []
        for item in raw_items:
            rules = list(item.visibility_rules.all())
            groups = list(item.rule_groups.all())
            grouped_rule_ids = set()
            for group in groups:
                grouped_rule_ids.update(r.id for r in group.rules.all())
            ungrouped_rules = [r for r in rules if r.id not in grouped_rule_ids]
            questionnaire_items_structured.append({
                'item': item,
                'rules': rules,
                'rule_groups': groups,
                'ungrouped_rules': ungrouped_rules,
            })
        context['questionnaire_items_structured'] = questionnaire_items_structured
        item_to_question_number = {str(qi.item.id): qi.question_number for qi in raw_items}
        current_language = get_language()
        
        # Get all items and order them by their question numbers
        available_items = Item.objects.language(current_language).all()
        current_items = Item.objects.filter(
            id__in=raw_items.values_list('item', flat=True)
        )
        
        # Create a list of items with their question numbers
        items_with_numbers = []
        for item in available_items:
            item.question_number = item_to_question_number.get(str(item.id))
            items_with_numbers.append(item)
        
        # Sort items by question number (None values go to the end)
        items_with_numbers.sort(key=lambda x: (x.question_number is None, x.question_number))
        
        context['item_selection_form'] = ItemSelectionForm(initial={'items': current_items})
        context['available_items'] = items_with_numbers
        context['construct_scales'] = ConstructScale.objects.all
        context['rule_groups'] = QuestionnaireItemRuleGroup.objects.filter(
            questionnaire_item__in=raw_items
        ).order_by('group_order')
        return context

    @transaction.atomic
    def form_valid(self, form):
        try:
            questionnaire = form.save()
            
            # Process selected items
            item_selection_form = ItemSelectionForm(self.request.POST)
            if item_selection_form.is_valid():
                selected_items = item_selection_form.cleaned_data.get('items', [])
                
                # Get existing questionnaire items
                existing_items = QuestionnaireItem.objects.filter(
                    questionnaire=questionnaire
                ).select_related('item')
                
                # Create a mapping of item IDs to their existing questionnaire items
                existing_item_map = {str(qi.item.id): qi for qi in existing_items}
                
                # Track which items we've processed
                processed_item_ids = set()
                
                # Process selected items
                for item in selected_items:
                    question_number = self.request.POST.get(f'question_number_{item.id}')
                    if question_number:
                        try:
                            question_number = int(question_number)
                        except (ValueError, TypeError):
                            question_number = None
                    
                    if str(item.id) not in existing_item_map:
                        # Create new questionnaire item
                        QuestionnaireItem.objects.create(
                            questionnaire=questionnaire,
                            item=item,
                            question_number=question_number
                        )
                    else:
                        # Update existing questionnaire item
                        qi = existing_item_map[str(item.id)]
                        qi.question_number = question_number
                        qi.save()
                    
                    processed_item_ids.add(str(item.id))
                
                # Remove questionnaire items that are no longer selected
                items_to_remove = existing_items.exclude(item__id__in=processed_item_ids)
                if items_to_remove.exists():
                    items_to_remove.delete()
                
                questionnaire_name = getattr(questionnaire, 'name', 'Questionnaire')
                messages.success(self.request, f"Questionnaire '{questionnaire_name}' updated successfully with {len(selected_items)} items.")
            else:
                messages.warning(self.request, "Questionnaire updated, but there was an issue with item selection.")
            
            # Stay on the same update page after saving
            return redirect('questionnaire_update', pk=questionnaire.id)
            
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"An error occurred while updating the questionnaire: {str(e)}")
            return self.form_invalid(form)


class ItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Item
    template_name = 'promapp/item_list.html'
    context_object_name = 'items'
    permission_required = 'promapp.view_item'
    paginate_by = 10  # Show 5 items per page for testing
    
    def get_queryset(self):
        current_language = get_language()
        # Start with base queryset and select related fields
        queryset = Item.objects.language(current_language).select_related(
            'construct_scale',
            'likert_response',
            'range_response'
        )
        
        # Apply filters based on query parameters
        construct_scale = self.request.GET.get('construct_scale')
        response_type = self.request.GET.get('response_type')
        search = self.request.GET.get('search')
        
        if construct_scale and construct_scale != 'all':
            queryset = queryset.filter(construct_scale_id=construct_scale)
        
        if response_type and response_type != 'all':
            queryset = queryset.filter(response_type=response_type)
            
        if search:
            queryset = queryset.filter(translations__name__icontains=search)
            
        # Use distinct() with id to prevent duplicates while keeping all fields
        return queryset.distinct('id').order_by('id', 'construct_scale__name', 'translations__name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all construct scales for the filter dropdown
        context['all_construct_scales'] = ConstructScale.objects.all().order_by('name')
        # Get all response types for the filter dropdown
        context['response_types'] = [
            {'value': choice[0], 'display': choice[1]} 
            for choice in ResponseTypeChoices.choices
        ]
        # Keep the selected filters in the context
        context['selected_construct_scale'] = self.request.GET.get('construct_scale', 'all')
        context['selected_response_type'] = self.request.GET.get('response_type', 'all')
        context['search_query'] = self.request.GET.get('search', '')
        
        # Add available languages to context
        context['available_languages'] = settings.LANGUAGES
        
        # Flag to determine if we're responding to an HTMX request
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        
        return context
    
    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/item_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)


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


class ItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Item
    form_class = ItemForm
    template_name = 'promapp/item_update.html'
    success_url = reverse_lazy('item_list')
    permission_required = 'promapp.change_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['likert_scales'] = LikertScale.objects.all()
        context['range_scales'] = RangeScale.objects.all()
        
        # Add the selected scales to the context
        if self.object:
            context['selected_likert_scale'] = str(self.object.likert_response.id) if self.object.likert_response else None
            context['selected_range_scale'] = str(self.object.range_response.id) if self.object.range_response else None
        
        return context


def get_response_fields(request):
    response_type = request.GET.get('response_type')
    selected_likert_scale = request.GET.get('likert_response')
    selected_range_scale = request.GET.get('range_response')
    
    # Get the item instance if we're editing
    item_id = request.GET.get('item_id')
    if item_id:
        try:
            item = Item.objects.get(id=item_id)
            if not selected_likert_scale and item.likert_response:
                selected_likert_scale = str(item.likert_response.id)
            if not selected_range_scale and item.range_response:
                selected_range_scale = str(item.range_response.id)
        except Item.DoesNotExist:
            pass
    
    html = render_to_string('promapp/response_fields.html', {
        'response_type': response_type,
        'likert_scales': LikertScale.objects.all(),
        'range_scales': RangeScale.objects.all(),
        'selected_likert_scale': selected_likert_scale,
        'selected_range_scale': selected_range_scale
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
    # Check if we're editing an existing Likert scale
    edit_id = request.GET.get('edit')
    instance = None
    
    if edit_id:
        instance = get_object_or_404(LikertScale, pk=edit_id)
        print(f"Editing likert scale: {instance.likert_scale_name} (ID: {instance.id})")
    
    if request.method == 'POST':
        # Collect and debug POST data
        print("POST data:", request.POST)
        
        # Get the standard formset prefix
        prefix = 'likertscaleresponseoption_set'
        print(f"Standard formset prefix: {prefix}")
        print(f"TOTAL_FORMS: {request.POST.get(f'{prefix}-TOTAL_FORMS')}")
        print(f"INITIAL_FORMS: {request.POST.get(f'{prefix}-INITIAL_FORMS')}")
        
        # Process the form for the likert scale itself
        form = LikertScaleForm(request.POST, instance=instance)
        
        # Process the standard formset
        if instance:
            formset = LikertScaleResponseOptionFormSet(request.POST, request.FILES, instance=instance)
        else:
            formset = LikertScaleResponseOptionFormSet(request.POST, request.FILES)
        
        # Debug formset
        print(f"Formset has {len(formset.forms)} forms")
        for i, form_instance in enumerate(formset.forms):
            print(f"Formset form {i} data:", {
                'option_order': form_instance['option_order'].value(),
                'option_value': form_instance['option_value'].value(),
                'option_text': form_instance['option_text'].value(),
            })
        
        # Check form validity first
        valid_form = form.is_valid()
        valid_formset = formset.is_valid()
        
        # Also collect any dynamically added forms (with 'form-' prefix)
        dynamic_forms = []
        
        # We need to process the raw request data to get all form instances
        # This is because request.POST.getlist() doesn't handle nested lists properly
        
        # First, identify all the unique form indices in the dynamic forms
        form_indices = set()
        for key in request.POST:
            if key.startswith('form-') and '-option_order' in key:
                parts = key.split('-')
                if len(parts) == 3 and parts[1].isdigit():  # form-X-field format
                    form_indices.add(parts[1])
        
        print(f"Found {len(form_indices)} unique form indices: {', '.join(form_indices)}")
        
        # For each form index, extract all fields
        for form_index in form_indices:
            option_order = request.POST.get(f'form-{form_index}-option_order', '')
            option_value = request.POST.get(f'form-{form_index}-option_value', '')
            option_text = request.POST.get(f'form-{form_index}-option_text', '')
            likert_scale_id = request.POST.get(f'form-{form_index}-likert_scale', '')
            
            # Only add non-empty forms
            if option_order.strip() or option_text.strip():
                dynamic_forms.append({
                    'index': form_index,
                    'option_order': option_order.strip(),
                    'option_value': option_value.strip(),
                    'option_text': option_text.strip(),
                    'likert_scale_id': likert_scale_id.strip()
                })
        
        print(f"Found {len(dynamic_forms)} dynamically added form entries")
        for i, dform in enumerate(dynamic_forms):
            print(f"Dynamic form {i+1} data:", dform)
        
        if valid_form and valid_formset:
            with transaction.atomic():
                # First save the likert scale
                likert_scale = form.save()
                print(f"Saved likert scale: {likert_scale.likert_scale_name} (ID: {likert_scale.id})")
                
                # Save the standard formset (skip empty forms)
                formset.instance = likert_scale
                saved_options = []
                for form_instance in formset.forms:
                    # Check if this form has data and isn't marked for deletion
                    if form_instance.is_valid():
                        # Only process forms with actual data
                        option_order = form_instance.cleaned_data.get('option_order')
                        option_text = form_instance.cleaned_data.get('option_text', '')
                        option_value = form_instance.cleaned_data.get('option_value')
                        delete_flag = form_instance.cleaned_data.get('DELETE', False)
                        
                        # Debug
                        print(f"Processing form with data: order={option_order}, value={option_value}, text={option_text}, delete={delete_flag}")
                        
                        if not delete_flag and (option_order is not None or option_text):
                            try:
                                # Handle existing or new instances
                                if form_instance.instance.pk:
                                    option = form_instance.instance
                                    if option_order is not None:
                                        option.option_order = option_order
                                    if option_value is not None:
                                        option.option_value = option_value
                                    if option_text:
                                        option.option_text = option_text
                                    option.likert_scale = likert_scale
                                else:
                                    # Create new option
                                    option = LikertScaleResponseOption()
                                    option.likert_scale = likert_scale
                                    option.option_order = option_order if option_order is not None else 0
                                    option.option_value = option_value if option_value is not None else 0
                                    option.option_text = option_text
                                
                                try:
                                    # Save and track
                                    option.save()
                                    saved_options.append(option)
                                    print(f"Saved option: {option.option_text} (order: {option.option_order}, value: {option.option_value})")
                                except Exception as e:
                                    if 'unique constraint' in str(e).lower():
                                        error_msg = f"Cannot save option: A response option with order {option.option_order} and value {option.option_value} already exists in this scale."
                                        print(error_msg)
                                        messages.error(request, error_msg)
                                    else:
                                        print(f"Error saving option: {e}")
                                        messages.error(request, f"Error saving option: {e}")
                            except Exception as e:
                                print(f"Error processing option: {e}")
                                messages.error(request, f"Error processing option: {e}")
                        elif delete_flag and form_instance.instance.pk:
                            # Delete if marked and exists
                            form_instance.instance.delete()
                            print(f"Deleted option with ID: {form_instance.instance.pk}")
                    else:
                        print(f"Form validation failed: {form_instance.errors}")
                
                print(f"Saved {len(saved_options)} options from formset")
                
                # Process and save dynamically added forms manually
                for dform in dynamic_forms:
                    try:
                        # Create a new option
                        option = LikertScaleResponseOption()
                        option.likert_scale = likert_scale
                        
                        # Handle empty values
                        try:
                            option.option_order = int(dform['option_order']) if dform['option_order'].strip() else 0
                        except (ValueError, TypeError):
                            option.option_order = 0
                        
                        try:
                            # Explicitly handle '0' or '0.00' values
                            option_value = dform['option_value'].strip()
                            if option_value == '' or option_value is None:
                                option.option_value = 0
                            else:
                                option.option_value = float(option_value)
                        except (ValueError, TypeError):
                            option.option_value = 0
                        
                        option.option_text = dform['option_text']
                        
                        # Check for duplicates before saving
                        try:
                            option.save()
                            print(f"Saved dynamic option: {option.option_text} (order: {option.option_order}, value: {option.option_value})")
                        except Exception as e:
                            if 'unique constraint' in str(e).lower():
                                error_msg = f"Cannot save dynamic option: A response option with order {option.option_order} and value {option.option_value} already exists in this scale."
                                print(error_msg)
                                messages.error(request, error_msg)
                            else:
                                print(f"Error saving dynamic option: {e}")
                                messages.error(request, f"Error saving dynamic option: {e}")
                    except Exception as e:
                        print(f"Error processing dynamic option: {e}")
                        messages.error(request, f"Error processing dynamic option: {e}")
                
                if instance:
                    messages.success(request, "Likert scale updated successfully.")
                else:
                    messages.success(request, "Likert scale created successfully.")
                
                # Redirect to the likert scale list if available, otherwise to item create
                if request.user.has_perm('promapp.view_likertscale'):
                    return redirect('likert_scale_list')
                else:
                    return redirect('item_create')
        else:
            if not valid_form:
                print("Form errors:", form.errors)
                messages.error(request, "Please check the scale details for errors.")
            if not valid_formset:
                print("Formset errors:", formset.errors)
                print("Formset non-form errors:", formset.non_form_errors())
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        print(f"Form {i} errors:", form_errors)
                messages.error(request, "Please check the response options for errors.")
    else:
        # Initialize form and formset with instance data if editing
        form = LikertScaleForm(instance=instance)
        
        if instance:
            formset = LikertScaleResponseOptionFormSet(instance=instance)
        else:
            formset = LikertScaleResponseOptionFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'is_edit': bool(instance),
        'scale': instance,
        'dynamic_row_count': request.POST.get('dynamic_row_count', 0) if request.method == 'POST' else 0
    }
    
    return render(request, 'promapp/likert_scale_form.html', context)



def create_construct_scale(request):
    if request.method == 'POST':
        form = ConstructScaleForm(request.POST)
        if form.is_valid():
            construct_scale = form.save()
            messages.success(request, "Construct scale created successfully.")
            # Get the referrer URL, defaulting to item_create if not available
            referrer = request.META.get('HTTP_REFERER')
            if referrer and 'item_create' in referrer:
                return redirect('item_create')
            elif referrer and 'item_update' in referrer:
                return redirect('item_update', pk=request.GET.get('item_id'))
            else:
                return redirect('construct_scale_list')
    else:
        form = ConstructScaleForm()
    
    return render(request, 'promapp/construct_scale_form.html', {
        'form': form,
        'referrer': request.META.get('HTTP_REFERER', '')
    })

def add_likert_option(request):
    """Add a new empty row to the Likert scale formset."""
    # Extract all parameters from the request for debugging
    params = {key: request.GET.get(key) for key in request.GET}
    print(f"Add option request parameters: {params}")
    
    # Get the form index (default to a safe value if missing)
    form_index = int(request.GET.get('form_index', 0))
    
    # Get the likert scale ID if it's being edited
    scale_id = request.GET.get('scale_id', None)
    scale = None
    
    # Get suggested order and value directly from request
    # Explicitly handle the conversion to avoid type errors
    try:
        suggested_order = int(request.GET.get('next_order', 2))
    except (ValueError, TypeError):
        suggested_order = 2
        
    try:
        suggested_value = float(request.GET.get('next_value', 1))
    except (ValueError, TypeError):
        suggested_value = 1.0
    
    # Handle edge case of first row
    if suggested_order == 1:
        suggested_value = 0.0
    
    if scale_id:
        try:
            scale = LikertScale.objects.get(pk=scale_id)
            print(f"Found likert scale: {scale.likert_scale_name} (ID: {scale.id})")
            
            # If we have a scale but no suggested values in request, determine them
            if 'next_order' not in request.GET:
                max_order = LikertScaleResponseOption.objects.filter(
                    likert_scale=scale
                ).aggregate(models.Max('option_order'))['option_order__max'] or 0
                suggested_order = max_order + 1
                
            if 'next_value' not in request.GET:
                max_value = LikertScaleResponseOption.objects.filter(
                    likert_scale=scale
                ).aggregate(models.Max('option_value'))['option_value__max'] or 0
                suggested_value = float(max_value) + 1
        except LikertScale.DoesNotExist:
            print(f"LikertScale with ID {scale_id} not found")
    
    # Render a new empty form row
    context = {
        'form_index': form_index,
        'scale': scale,
        'suggested_order': suggested_order,
        'suggested_value': suggested_value,
    }
    
    # Log debug info
    print(f"Adding option row with index {form_index}, scale_id: {scale_id}, suggested_order: {suggested_order}, suggested_value: {suggested_value}")
    
    return render(request, 'promapp/likert_option_row.html', context)

def remove_likert_option(request):
    """Remove a row from the Likert scale formset."""
    # Return an empty response to remove the row
    return HttpResponse('')

class LikertScaleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = LikertScale
    template_name = 'promapp/likert_scale_list.html'
    context_object_name = 'likert_scales'
    permission_required = 'promapp.view_likertscale'
    paginate_by = 10  # Show 10 likert scales per page
    
    def get_queryset(self):
        queryset = LikertScale.objects.all()
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(likert_scale_name__icontains=search)
            
        return queryset.order_by('-created_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add response options for each likert scale
        likert_scales_with_options = []
        current_language = get_language()
        
        for scale in context['likert_scales']:
            options = LikertScaleResponseOption.objects.language(current_language).filter(
                likert_scale=scale
            ).order_by('option_order')
            
            likert_scales_with_options.append({
                'scale': scale,
                'options': options,
                'option_count': options.count()
            })
        
        context['likert_scales_with_options'] = likert_scales_with_options
        context['search_query'] = self.request.GET.get('search', '')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        
        return context
    
    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/likert_scale_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)

def create_range_scale(request):
    # Check if we're editing an existing Range scale
    edit_id = request.GET.get('edit')
    instance = None
    
    if edit_id:
        instance = get_object_or_404(RangeScale, pk=edit_id)
        print(f"Editing range scale: {instance.range_scale_name} (ID: {instance.id})")
    
    if request.method == 'POST':
        form = RangeScaleForm(request.POST, instance=instance)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    range_scale = form.save()
                    
                    # Validate the range values
                    if range_scale.min_value >= range_scale.max_value:
                        raise ValidationError("Minimum value must be less than maximum value")
                    if range_scale.increment <= 0:
                        raise ValidationError("Increment must be greater than 0")
                    if (range_scale.max_value - range_scale.min_value) % range_scale.increment != 0:
                        raise ValidationError("Maximum value minus minimum value must be divisible by increment")
                    
                    if instance:
                        messages.success(request, "Range scale updated successfully.")
                    else:
                        messages.success(request, "Range scale created successfully.")
                    
                    # Redirect to the range scale list if available, otherwise to item create
                    if request.user.has_perm('promapp.view_rangescale'):
                        return redirect('range_scale_list')
                    else:
                        return redirect('item_create')
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error saving range scale: {str(e)}")
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = RangeScaleForm(instance=instance)
    
    context = {
        'form': form,
        'is_edit': bool(instance),
        'scale': instance
    }
    
    return render(request, 'promapp/range_scale_form.html', context)

class RangeScaleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = RangeScale
    template_name = 'promapp/range_scale_list.html'
    context_object_name = 'range_scales'
    permission_required = 'promapp.view_rangescale'
    paginate_by = 10  # Show 10 range scales per page
    
    def get_queryset(self):
        queryset = RangeScale.objects.all()
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(range_scale_name__icontains=search)
            
        return queryset.order_by('-created_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        return context
    
    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/range_scale_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)

class ConstructScaleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ConstructScale
    template_name = 'promapp/construct_scale_list.html'
    context_object_name = 'construct_scales'
    permission_required = 'promapp.view_constructscale'
    paginate_by = 25  # Show 25 items per page
    
    def get_queryset(self):
        queryset = ConstructScale.objects.all()
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
            
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        return context
    
    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/construct_scale_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)

class QuestionnaireResponseView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View for handling questionnaire responses.
    This view allows patients to respond to questionnaires assigned to them.
    """
    model = PatientQuestionnaire
    template_name = 'promapp/questionnaire_response.html'
    context_object_name = 'patient_questionnaire'
    permission_required = ['promapp.view_patientquestionnaire', 'promapp.add_questionnaireitemresponse']
    
    def get_queryset(self):
        # Only allow access to questionnaires assigned to the current patient
        return PatientQuestionnaire.objects.filter(
            patient__user=self.request.user,
            display_questionnaire=True
        )
    
    def check_interval(self, patient_questionnaire):
        """Helper method to check if questionnaire can be answered"""
        last_response = QuestionnaireItemResponse.objects.filter(
            patient_questionnaire=patient_questionnaire
        ).order_by('-response_date').first()
        
        if last_response:
            interval_seconds = patient_questionnaire.questionnaire.questionnaire_answer_interval
            next_available = last_response.response_date + timedelta(seconds=interval_seconds)
            can_answer = timezone.now() >= next_available
        else:
            can_answer = True
            next_available = None
            
        return can_answer, next_available
    
    def dispatch(self, request, *args, **kwargs):
        # Check if the questionnaire can be answered before proceeding with any view logic
        patient_questionnaire = self.get_object()
        can_answer, next_available = self.check_interval(patient_questionnaire)
        
        if not can_answer:
            messages.error(request, _('You cannot answer this questionnaire yet. You can answer it again in %(time)s.') % {
                'time': timeuntil(next_available)
            })
            return redirect('my_questionnaire_list')
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_questionnaire = self.get_object()
        
        # Get all questionnaire items ordered by question number
        questionnaire_items = QuestionnaireItem.objects.filter(
            questionnaire=patient_questionnaire.questionnaire
        ).order_by('question_number')
        
        # Initialize the form with the questionnaire items
        form = QuestionnaireResponseForm(
            questionnaire_items=questionnaire_items
        )
        
        # Add can_answer flag to context
        can_answer, next_available = self.check_interval(patient_questionnaire)
        context['can_answer'] = can_answer
        context['next_available'] = next_available
        context['form'] = form
        context['questionnaire_items'] = questionnaire_items
        
        return context
    
    def post(self, request, *args, **kwargs):
        # Check if user has permission to add responses
        if not request.user.has_perm('promapp.add_questionnaireitemresponse'):
            messages.error(request, _('You do not have permission to submit responses.'))
            return redirect('my_questionnaire_list')
            
        patient_questionnaire = self.get_object()
        
        # Check if the questionnaire can be answered
        can_answer, next_available = self.check_interval(patient_questionnaire)
        
        if not can_answer:
            messages.error(request, _('You cannot answer this questionnaire yet. You can answer it again in %(time)s.') % {
                'time': timeuntil(next_available)
            })
            return redirect('my_questionnaire_list')
        
        questionnaire_items = QuestionnaireItem.objects.filter(
            questionnaire=patient_questionnaire.questionnaire
        ).order_by('question_number')
        
        form = QuestionnaireResponseForm(
            request.POST,
            questionnaire_items=questionnaire_items
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create response objects for all questions, using empty string for unanswered ones
                    for qi in questionnaire_items:
                        response_value = form.cleaned_data.get(f'response_{qi.id}', '')
                        QuestionnaireItemResponse.objects.create(
                            patient_questionnaire=patient_questionnaire,
                            questionnaire_item=qi,
                            response_value=str(response_value) if response_value else ''
                        )
                
                messages.success(request, _('Your responses have been saved successfully.'))
                
                # Check if there's a redirect questionnaire
                redirect_questionnaire = patient_questionnaire.questionnaire.questionnaire_redirect
                if redirect_questionnaire:
                    # Check if the patient has this questionnaire assigned
                    try:
                        next_patient_questionnaire = PatientQuestionnaire.objects.get(
                            patient=patient_questionnaire.patient,
                            questionnaire=redirect_questionnaire,
                            display_questionnaire=True
                        )
                        # Redirect to the next questionnaire
                        return redirect('questionnaire_response', pk=next_patient_questionnaire.id)
                    except PatientQuestionnaire.DoesNotExist:
                        # If the patient doesn't have the redirect questionnaire assigned,
                        # just redirect to the questionnaire list
                        messages.info(request, _('The next questionnaire is not available for you at this time.'))
                        return redirect('my_questionnaire_list')
                
                # If no redirect questionnaire, go to the questionnaire list
                return redirect('my_questionnaire_list')
                
            except Exception as e:
                messages.error(request, _('An error occurred while saving your responses. Please try again.'))
                return self.render_to_response(self.get_context_data(form=form))
        else:
            messages.error(request, _('Please correct the errors below.'))
            return self.render_to_response(self.get_context_data(form=form))

class PatientQuestionnaireManagementView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View for managing questionnaires assigned to a patient.
    This view allows staff to assign/unassign questionnaires to patients.
    """
    model = Patient
    template_name = 'promapp/patient_questionnaire_management.html'
    context_object_name = 'patient'
    permission_required = 'promapp.add_patientquestionnaire'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Get all questionnaires with proper translation handling
        current_language = get_language()
        
        # Get all questionnaires with their translations in the current language
        all_questionnaires = Questionnaire.objects.filter(
            translations__language_code=current_language
        ).distinct('id').order_by('id', 'translations__name')
        
        # Get currently assigned questionnaires
        assigned_questionnaires = PatientQuestionnaire.objects.filter(
            patient=patient
        ).select_related('questionnaire')
        
        # Create a list of questionnaires with their assignment status
        questionnaires_with_status = []
        for questionnaire in all_questionnaires:
            assigned = assigned_questionnaires.filter(questionnaire=questionnaire).first()
            questionnaires_with_status.append({
                'questionnaire': questionnaire,
                'is_assigned': bool(assigned),
                'is_displayed': assigned.display_questionnaire if assigned else False,
                'assigned_date': assigned.created_date if assigned else None,
                'patient_questionnaire_id': assigned.id if assigned else None
            })
        
        context['questionnaires_with_status'] = questionnaires_with_status
        return context
    
    def post(self, request, *args, **kwargs):
        patient = self.get_object()
        action = request.POST.get('action')
        questionnaire_id = request.POST.get('questionnaire_id')
        
        try:
            questionnaire = Questionnaire.objects.get(id=questionnaire_id)
            
            if action == 'assign':
                # Create new assignment
                PatientQuestionnaire.objects.create(
                    patient=patient,
                    questionnaire=questionnaire,
                    display_questionnaire=True
                )
                messages.success(request, _('Questionnaire assigned successfully.'))
                
            elif action == 'unassign':
                # Remove assignment
                PatientQuestionnaire.objects.filter(
                    patient=patient,
                    questionnaire=questionnaire
                ).delete()
                messages.success(request, _('Questionnaire unassigned successfully.'))
                
            elif action == 'toggle_display':
                # Toggle display status
                patient_questionnaire = PatientQuestionnaire.objects.get(
                    patient=patient,
                    questionnaire=questionnaire
                )
                patient_questionnaire.display_questionnaire = not patient_questionnaire.display_questionnaire
                patient_questionnaire.save()
                status = 'displayed' if patient_questionnaire.display_questionnaire else 'hidden'
                messages.success(request, _(f'Questionnaire is now {status}.'))
                
        except Questionnaire.DoesNotExist:
            messages.error(request, _('Questionnaire not found.'))
        except PatientQuestionnaire.DoesNotExist:
            messages.error(request, _('Questionnaire assignment not found.'))
        except Exception as e:
            messages.error(request, _('An error occurred. Please try again.'))
        
        return redirect('patient_questionnaire_management', pk=patient.id)

class PatientQuestionnaireListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View for listing patients who have questionnaires assigned to them.
    """
    model = Patient
    template_name = 'promapp/patient_questionnaire_list.html'
    context_object_name = 'patients'
    permission_required = 'promapp.view_patientquestionnaire'
    paginate_by = 25

    def get_queryset(self):
        queryset = Patient.objects.select_related('user').all()
        
        # Apply search filter
        search_query = self.request.GET.get('search')
        if search_query:
            # Use exact match for secured fields
            queryset = queryset.filter(
                models.Q(name__exact=search_query) |
                models.Q(patient_id__exact=search_query)
            )
        
        # Apply questionnaire count filter
        questionnaire_count = self.request.GET.get('questionnaire_count')
        if questionnaire_count:
            if questionnaire_count == '0':
                queryset = queryset.annotate(
                    q_count=models.Count('patientquestionnaire', distinct=True)
                ).filter(q_count=0)
            elif questionnaire_count == '1-5':
                queryset = queryset.annotate(
                    q_count=models.Count('patientquestionnaire', distinct=True)
                ).filter(q_count__gte=1, q_count__lte=5)
            elif questionnaire_count == '6-10':
                queryset = queryset.annotate(
                    q_count=models.Count('patientquestionnaire', distinct=True)
                ).filter(q_count__gte=6, q_count__lte=10)
            elif questionnaire_count == '10+':
                queryset = queryset.annotate(
                    q_count=models.Count('patientquestionnaire', distinct=True)
                ).filter(q_count__gt=10)
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'name':
            queryset = queryset.order_by('name')
        elif sort_by == '-name':
            queryset = queryset.order_by('-name')
        elif sort_by == 'questionnaire_count':
            queryset = queryset.annotate(
                q_count=models.Count('patientquestionnaire', distinct=True)
            ).order_by('q_count')
        elif sort_by == '-questionnaire_count':
            queryset = queryset.annotate(
                q_count=models.Count('patientquestionnaire', distinct=True)
            ).order_by('-q_count')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_language = get_language()
        for patient in context['patients']:
            # Count only unique questionnaire assignments
            patient.questionnaire_count = PatientQuestionnaire.objects.filter(
                patient=patient
            ).values('questionnaire').distinct().count()
            
            # Get unique questionnaire names in current language using a subquery
            questionnaire_ids = PatientQuestionnaire.objects.filter(
                patient=patient
            ).values_list('questionnaire_id', flat=True).distinct()
            
            patient.questionnaire_names = list(
                Questionnaire.objects.filter(
                    id__in=questionnaire_ids,
                    translations__language_code=current_language
                ).values_list('translations__name', flat=True)
            )
            
        # Add current filter values to context
        context['current_search'] = self.request.GET.get('search', '')
        context['current_questionnaire_count'] = self.request.GET.get('questionnaire_count', '')
        context['current_sort'] = self.request.GET.get('sort', 'name')
        return context

class MyQuestionnaireListView(LoginRequiredMixin, ListView):
    model = PatientQuestionnaire
    template_name = 'promapp/my_questionnaire_list.html'
    context_object_name = 'patient_questionnaires'

    def get_queryset(self):
        # Only show questionnaires for the logged-in patient, ordered by questionnaire_order
        return PatientQuestionnaire.objects.filter(
            patient__user=self.request.user,
            display_questionnaire=True
        ).select_related('questionnaire').order_by('questionnaire__questionnaire_order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = getattr(self.request.user, 'patient', None)
        
        # Add information about when each questionnaire can be answered next
        for pq in context['patient_questionnaires']:
            # Get the last response for this questionnaire
            last_response = QuestionnaireItemResponse.objects.filter(
                patient_questionnaire=pq
            ).order_by('-response_date').first()
            
            # Store the last response for display
            pq.last_response = last_response
            
            if last_response:
                # Calculate when the questionnaire can be answered next
                interval_seconds = pq.questionnaire.questionnaire_answer_interval
                next_available = last_response.response_date + timedelta(seconds=interval_seconds)
                pq.next_available = next_available
                pq.can_answer = timezone.now() >= next_available
            else:
                # If no previous response, can answer immediately
                pq.next_available = None
                pq.can_answer = True
        
        return context

class QuestionnaireItemRuleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View for listing rules associated with a questionnaire item.
    """
    model = QuestionnaireItemRule
    template_name = 'promapp/questionnaire_item_rules_list.html'
    context_object_name = 'rules'
    permission_required = 'promapp.view_questionnaireitemrule'

    def get_queryset(self):
        questionnaire_item = get_object_or_404(QuestionnaireItem, pk=self.kwargs['questionnaire_item_id'])
        return QuestionnaireItemRule.objects.filter(
            questionnaire_item=questionnaire_item
        ).order_by('rule_order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaire_item'] = get_object_or_404(
            QuestionnaireItem, 
            pk=self.kwargs['questionnaire_item_id']
        )
        return context

class QuestionnaireItemRuleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    View for creating a new rule for a questionnaire item.
    """
    model = QuestionnaireItemRule
    form_class = QuestionnaireItemRuleForm
    template_name = 'promapp/questionnaire_item_rule_form.html'
    permission_required = 'promapp.add_questionnaireitemrule'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        questionnaire_item = get_object_or_404(QuestionnaireItem, pk=self.kwargs['questionnaire_item_id'])
        kwargs['initial'] = kwargs.get('initial', {})
        kwargs['initial']['questionnaire_item'] = questionnaire_item
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.questionnaire_item = get_object_or_404(
            QuestionnaireItem, 
            pk=self.kwargs['questionnaire_item_id']
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaire_item'] = get_object_or_404(
            QuestionnaireItem, 
            pk=self.kwargs['questionnaire_item_id']
        )
        return context

    def get_success_url(self):
        return reverse('questionnaire_item_rules_list', 
                      kwargs={'questionnaire_item_id': self.kwargs['questionnaire_item_id']})

class QuestionnaireItemRuleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for updating an existing rule.
    """
    model = QuestionnaireItemRule
    form_class = QuestionnaireItemRuleForm
    template_name = 'promapp/questionnaire_item_rule_form.html'
    permission_required = 'promapp.change_questionnaireitemrule'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaire_item'] = self.object.questionnaire_item
        return context

    def get_success_url(self):
        return reverse('questionnaire_item_rules_list', 
                      kwargs={'questionnaire_item_id': self.object.questionnaire_item.id})

class QuestionnaireItemRuleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    View for deleting a rule.
    """
    model = QuestionnaireItemRule
    permission_required = 'promapp.delete_questionnaireitemrule'

    def get_success_url(self):
        return reverse('questionnaire_item_rules_list', 
                      kwargs={'questionnaire_item_id': self.object.questionnaire_item.id})

class QuestionnaireItemRuleGroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View for listing rule groups associated with a questionnaire item.
    """
    model = QuestionnaireItemRuleGroup
    template_name = 'promapp/questionnaire_item_rule_groups_list.html'
    context_object_name = 'rule_groups'
    permission_required = 'promapp.view_questionnaireitemrulegroup'

    def get_queryset(self):
        questionnaire_item = get_object_or_404(QuestionnaireItem, pk=self.kwargs['questionnaire_item_id'])
        return QuestionnaireItemRuleGroup.objects.filter(
            questionnaire_item=questionnaire_item
        ).order_by('group_order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaire_item'] = get_object_or_404(
            QuestionnaireItem, 
            pk=self.kwargs['questionnaire_item_id']
        )
        return context

class QuestionnaireItemRuleGroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    View for creating a new rule group.
    """
    model = QuestionnaireItemRuleGroup
    form_class = QuestionnaireItemRuleGroupForm
    template_name = 'promapp/questionnaire_item_rule_group_form.html'
    permission_required = 'promapp.add_questionnaireitemrulegroup'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        questionnaire_item = get_object_or_404(QuestionnaireItem, pk=self.kwargs['questionnaire_item_id'])
        kwargs['initial'] = kwargs.get('initial', {})
        kwargs['initial']['questionnaire_item'] = questionnaire_item
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.questionnaire_item = get_object_or_404(
            QuestionnaireItem, 
            pk=self.kwargs['questionnaire_item_id']
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questionnaire_item = get_object_or_404(
            QuestionnaireItem, 
            pk=self.kwargs['questionnaire_item_id']
        )
        context['questionnaire_item'] = questionnaire_item
        context['available_rules'] = QuestionnaireItemRule.objects.filter(
            questionnaire_item=questionnaire_item
        ).order_by('rule_order')
        return context

    def get_success_url(self):
        return reverse('questionnaire_item_rule_groups_list', 
                      kwargs={'questionnaire_item_id': self.kwargs['questionnaire_item_id']})

class QuestionnaireItemRuleGroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for updating an existing rule group.
    """
    model = QuestionnaireItemRuleGroup
    form_class = QuestionnaireItemRuleGroupForm
    template_name = 'promapp/questionnaire_item_rule_group_form.html'
    permission_required = 'promapp.change_questionnaireitemrulegroup'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaire_item'] = self.object.questionnaire_item
        context['available_rules'] = QuestionnaireItemRule.objects.filter(
            questionnaire_item=self.object.questionnaire_item
        ).order_by('rule_order')
        return context

    def get_success_url(self):
        return reverse('questionnaire_item_rule_groups_list', 
                      kwargs={'questionnaire_item_id': self.object.questionnaire_item.id})

class QuestionnaireItemRuleGroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    View for deleting a rule group.
    """
    model = QuestionnaireItemRuleGroup
    permission_required = 'promapp.delete_questionnaireitemrulegroup'

    def get_success_url(self):
        return reverse('questionnaire_item_rule_groups_list', 
                      kwargs={'questionnaire_item_id': self.object.questionnaire_item.id})

# HTMX Views for Rule Forms
def validate_dependent_item(request):
    """Validate the selected dependent item and return appropriate feedback."""
    item_id = request.GET.get('dependent_item')
    if not item_id:
        return HttpResponse(_("Please select a dependent item."))
    
    try:
        item = QuestionnaireItem.objects.get(id=item_id)
        return HttpResponse(_("Selected item: {}").format(item.item.name))
    except QuestionnaireItem.DoesNotExist:
        return HttpResponse(_("Invalid item selected."))

def validate_rule_operator(request):
    """Validate the selected operator and return appropriate feedback."""
    operator = request.GET.get('operator')
    dependent_item_id = request.GET.get('dependent_item')
    
    if not operator:
        return HttpResponse(_("Please select an operator."))
    
    try:
        dependent_item = QuestionnaireItem.objects.get(id=dependent_item_id)
        response_type = dependent_item.item.response_type
        
        # Return appropriate feedback based on response type
        if response_type in ['Number', 'Likert', 'Range']:
            return HttpResponse(_("Valid operator for numeric comparison."))
        else:
            return HttpResponse(_("Valid operator for text comparison."))
    except QuestionnaireItem.DoesNotExist:
        return HttpResponse(_("Invalid dependent item."))

def validate_comparison_value(request):
    """Validate the comparison value based on the dependent item's response type."""
    value = request.GET.get('comparison_value')
    dependent_item_id = request.GET.get('dependent_item')
    
    if not value:
        return HttpResponse(_("Please enter a comparison value."))
    
    try:
        dependent_item = QuestionnaireItem.objects.get(id=dependent_item_id)
        response_type = dependent_item.item.response_type
        
        if response_type == 'Number':
            try:
                float(value)
                return HttpResponse(_("Valid numeric value."))
            except ValueError:
                return HttpResponse(_("Please enter a valid number."))
        elif response_type == 'Likert':
            try:
                float_value = float(value)
                likert_options = dependent_item.item.likert_response.likertscaleresponseoption_set.all()
                valid_values = [option.option_value for option in likert_options]
                if float_value in valid_values:
                    return HttpResponse(_("Valid Likert scale value."))
                else:
                    return HttpResponse(_("Please enter a valid Likert scale value."))
            except ValueError:
                return HttpResponse(_("Please enter a valid number."))
        elif response_type == 'Range':
            try:
                float_value = float(value)
                range_scale = dependent_item.item.range_response
                if range_scale.min_value <= float_value <= range_scale.max_value:
                    return HttpResponse(_("Valid range value."))
                else:
                    return HttpResponse(_("Value must be between {} and {}.").format(
                        range_scale.min_value, range_scale.max_value))
            except ValueError:
                return HttpResponse(_("Please enter a valid number."))
        else:
            return HttpResponse(_("Valid text value."))
    except QuestionnaireItem.DoesNotExist:
        return HttpResponse(_("Invalid dependent item."))

def validate_logical_operator(request):
    """Validate the logical operator selection."""
    operator = request.GET.get('logical_operator')
    if not operator:
        return HttpResponse(_("Please select a logical operator."))
    return HttpResponse(_("Valid logical operator."))

def validate_rule_order(request):
    """Validate the rule order."""
    order = request.GET.get('rule_order')
    if not order:
        return HttpResponse(_("Please enter a rule order."))
    try:
        order_num = int(order)
        if order_num < 1:
            return HttpResponse(_("Order must be greater than 0."))
        return HttpResponse(_("Valid rule order."))
    except ValueError:
        return HttpResponse(_("Please enter a valid number."))

def validate_group_order(request):
    """Validate the group order."""
    order = request.GET.get('group_order')
    if not order:
        return HttpResponse(_("Please enter a group order."))
    try:
        order_num = int(order)
        if order_num < 1:
            return HttpResponse(_("Order must be greater than 0."))
        return HttpResponse(_("Valid group order."))
    except ValueError:
        return HttpResponse(_("Please enter a valid number."))

def validate_rule_selection(request):
    """Validate the selected rules for a rule group."""
    rule_ids = request.GET.getlist('rules')
    if not rule_ids:
        return HttpResponse(_("Please select at least one rule."))
    
    try:
        rules = QuestionnaireItemRule.objects.filter(id__in=rule_ids)
        if len(rules) != len(rule_ids):
            return HttpResponse(_("One or more invalid rules selected."))
        
        # Check if all rules belong to the same questionnaire item
        questionnaire_items = set(rule.questionnaire_item for rule in rules)
        if len(questionnaire_items) > 1:
            return HttpResponse(_("All rules must belong to the same questionnaire item."))
        
        return HttpResponse(_("Valid rule selection."))
    except Exception:
        return HttpResponse(_("Error validating rules."))

def rule_summary(request, questionnaire_item_id):
    """Return a summary of rules for a questionnaire item."""
    questionnaire_item = get_object_or_404(QuestionnaireItem, pk=questionnaire_item_id)
    rules = QuestionnaireItemRule.objects.filter(
        questionnaire_item=questionnaire_item
    ).order_by('rule_order')
    
    return render(request, 'promapp/partials/rule_summary.html', {
        'rules': rules
    })

def rule_group_summary(request, questionnaire_item_id):
    """Return a summary of rule groups for a questionnaire item."""
    questionnaire_item = get_object_or_404(QuestionnaireItem, pk=questionnaire_item_id)
    rule_groups = QuestionnaireItemRuleGroup.objects.filter(
        questionnaire_item=questionnaire_item
    ).order_by('group_order')
    
    return render(request, 'promapp/partials/rule_group_summary.html', {
        'rule_groups': rule_groups
    })

def save_question_numbers(request, pk):
    """View to handle saving question numbers via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method. Please use POST to update question numbers.'})
    
    try:
        questionnaire = get_object_or_404(Questionnaire, pk=pk)
        
        # Parse the JSON data
        data = json.loads(request.body)
        question_numbers = data.get('question_numbers', {})
        removed_items = data.get('removed_items', [])
        
        if not question_numbers and not removed_items:
            return JsonResponse({
                'success': False,
                'error': 'No changes provided. Please select questions to update or remove.'
            })
        
        # Get all questionnaire items
        questionnaire_items = QuestionnaireItem.objects.filter(
            questionnaire=questionnaire
        ).select_related('item')
        
        # Create a mapping of item IDs to questionnaire items
        item_map = {str(qi.item.id): qi for qi in questionnaire_items}
        
        # Track used question numbers
        used_numbers = set()
        
        # First pass: Validate all changes
        for item_id, new_number in question_numbers.items():
            if new_number in used_numbers:
                return JsonResponse({
                    'success': False,
                    'error': f'Duplicate question number {new_number} detected. Each question must have a unique number.'
                })
            used_numbers.add(new_number)
            
            if item_id in item_map:
                qi = item_map[item_id]
                if qi.question_number != new_number:
                    # Check for rule conflicts
                    affected_rules = QuestionnaireItemRule.objects.filter(
                        models.Q(
                            questionnaire_item=qi,
                            dependent_item__question_number__gte=new_number
                        ) |
                        models.Q(
                            dependent_item=qi,
                            questionnaire_item__question_number__lte=new_number
                        )
                    )
                    if affected_rules.exists():
                        rule_details = []
                        for rule in affected_rules:
                            rule_details.append(
                                f"- Rule for question '{rule.questionnaire_item.item.name}' "
                                f"based on question '{rule.dependent_item.item.name}'"
                            )
                        return JsonResponse({
                            'success': False,
                            'error': f'Cannot change question number for "{qi.item.name}" as it would invalidate the following rules:\n' + '\n'.join(rule_details)
                        })
        
        # Second pass: Apply all changes
        with transaction.atomic():
            # Update question numbers for remaining items
            for item_id, new_number in question_numbers.items():
                if item_id in item_map:
                    qi = item_map[item_id]
                    if qi.question_number != new_number:
                        qi.question_number = new_number
                        qi.save()
            
            # Remove items that are no longer in the list
            for item_id in removed_items:
                if item_id in item_map:
                    qi = item_map[item_id]
                    # Check if there are any rules depending on this item
                    dependent_rules = QuestionnaireItemRule.objects.filter(
                        dependent_item=qi
                    )
                    if dependent_rules.exists():
                        rule_details = []
                        for rule in dependent_rules:
                            rule_details.append(
                                f"- Question '{rule.questionnaire_item.item.name}' depends on this question"
                            )
                        return JsonResponse({
                            'success': False,
                            'error': f'Cannot remove question "{qi.item.name}" as it is referenced by the following rules:\n' + '\n'.join(rule_details)
                        })
                    # Check if this item has any rules
                    item_rules = QuestionnaireItemRule.objects.filter(
                        questionnaire_item=qi
                    )
                    if item_rules.exists():
                        rule_details = []
                        for rule in item_rules:
                            rule_details.append(
                                f"- Rule based on question '{rule.dependent_item.item.name}'"
                            )
                        return JsonResponse({
                            'success': False,
                            'error': f'Cannot remove question "{qi.item.name}" as it has the following rules:\n' + '\n'.join(rule_details)
                        })
                    # If no rules depend on this item and it has no rules, we can safely remove it
                    qi.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Question numbers updated successfully. All changes have been saved.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data. Please check the format of your request.'
        })
    except Questionnaire.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Questionnaire not found. Please refresh the page and try again.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An unexpected error occurred: {str(e)}. Please try again or contact support if the problem persists.'
        })

class QuestionnaireRulesView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View for managing rules for a questionnaire.
    """
    model = Questionnaire
    template_name = 'promapp/questionnaire_rules.html'
    context_object_name = 'questionnaire'
    permission_required = 'promapp.add_questionnaire'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questionnaire = self.get_object()
        
        # Prefetch rules and rule groups for all questionnaire items
        raw_items = QuestionnaireItem.objects.filter(
            questionnaire=questionnaire
        ).order_by('question_number').prefetch_related(
            Prefetch('visibility_rules', queryset=QuestionnaireItemRule.objects.order_by('rule_order')),
            Prefetch('rule_groups', queryset=QuestionnaireItemRuleGroup.objects.order_by('group_order').prefetch_related('rules'))
        )
        
        questionnaire_items_structured = []
        for item in raw_items:
            rules = list(item.visibility_rules.all())
            groups = list(item.rule_groups.all())
            grouped_rule_ids = set()
            for group in groups:
                grouped_rule_ids.update(r.id for r in group.rules.all())
            ungrouped_rules = [r for r in rules if r.id not in grouped_rule_ids]
            questionnaire_items_structured.append({
                'item': item,
                'rules': ungrouped_rules,
                'rule_groups': groups,
            })
        
        context['questionnaire_items_structured'] = questionnaire_items_structured
        return context

def evaluate_question_rules(request, questionnaire_item_id):
    """
    View to evaluate rules for a questionnaire item.
    Returns JSON response indicating whether the question should be shown.
    """
    logger = logging.getLogger("promapp.rules")
    try:
        questionnaire_item = get_object_or_404(QuestionnaireItem, pk=questionnaire_item_id)
        responses = json.loads(request.body)
        logger.info(f"Evaluating rules for QuestionnaireItem {questionnaire_item_id} with responses: {responses}")
        
        # Get all rules and rule groups for this item
        rules = questionnaire_item.visibility_rules.all()
        rule_groups = questionnaire_item.rule_groups.all()
        
        # If no rules or groups, always show the question
        if not rules and not rule_groups:
            logger.info(f"No rules or rule groups for QuestionnaireItem {questionnaire_item_id}. Showing question.")
            return JsonResponse({'should_show': True})
        
        # Evaluate individual rules
        rule_results = []
        for rule in rules:
            dependent_response = responses.get(str(rule.dependent_item.id))
            logger.info(f"Evaluating rule: Dependent Q{rule.dependent_item.question_number}, Operator: {rule.operator}, Comparison: {rule.comparison_value}, User Response: {dependent_response}")
            if dependent_response is None:
                logger.info(f"No response for dependent item {rule.dependent_item.id}. Skipping rule.")
                continue
            
            try:
                if rule.dependent_item.item.response_type in ['Number', 'Likert', 'Range']:
                    dependent_value = float(dependent_response)
                    comparison_value = float(rule.comparison_value)
                else:
                    dependent_value = str(dependent_response)
                    comparison_value = str(rule.comparison_value)
                
                result = False
                if rule.operator == 'EQUALS':
                    result = dependent_value == comparison_value
                elif rule.operator == 'NOT_EQUALS':
                    result = dependent_value != comparison_value
                elif rule.operator == 'GREATER_THAN':
                    result = dependent_value > comparison_value
                elif rule.operator == 'LESS_THAN':
                    result = dependent_value < comparison_value
                elif rule.operator == 'GREATER_THAN_EQUALS':
                    result = dependent_value >= comparison_value
                elif rule.operator == 'LESS_THAN_EQUALS':
                    result = dependent_value <= comparison_value
                elif rule.operator == 'CONTAINS':
                    result = str(comparison_value) in str(dependent_value)
                elif rule.operator == 'NOT_CONTAINS':
                    result = str(comparison_value) not in str(dependent_value)
                logger.info(f"Rule result: {result}")
                rule_results.append((result, rule.logical_operator))
            except (ValueError, TypeError) as e:
                logger.warning(f"Error evaluating rule: {e}")
                continue
        
        # Evaluate rule groups
        group_results = []
        for group in rule_groups:
            group_rules = group.rules.all()
            if not group_rules:
                continue
            group_result = True
            for i, rule in enumerate(group_rules):
                dependent_response = responses.get(str(rule.dependent_item.id))
                logger.info(f"[Group {group.group_order}] Evaluating rule: Dependent Q{rule.dependent_item.question_number}, Operator: {rule.operator}, Comparison: {rule.comparison_value}, User Response: {dependent_response}")
                if dependent_response is None:
                    logger.info(f"[Group {group.group_order}] No response for dependent item {rule.dependent_item.id}. Skipping rule.")
                    continue
                try:
                    if rule.dependent_item.item.response_type in ['Number', 'Likert', 'Range']:
                        dependent_value = float(dependent_response)
                        comparison_value = float(rule.comparison_value)
                    else:
                        dependent_value = str(dependent_response)
                        comparison_value = str(rule.comparison_value)
                    result = False
                    if rule.operator == 'EQUALS':
                        result = dependent_value == comparison_value
                    elif rule.operator == 'NOT_EQUALS':
                        result = dependent_value != comparison_value
                    elif rule.operator == 'GREATER_THAN':
                        result = dependent_value > comparison_value
                    elif rule.operator == 'LESS_THAN':
                        result = dependent_value < comparison_value
                    elif rule.operator == 'GREATER_THAN_EQUALS':
                        result = dependent_value >= comparison_value
                    elif rule.operator == 'LESS_THAN_EQUALS':
                        result = dependent_value <= comparison_value
                    elif rule.operator == 'CONTAINS':
                        result = str(comparison_value) in str(dependent_value)
                    elif rule.operator == 'NOT_CONTAINS':
                        result = str(comparison_value) not in str(dependent_value)
                    logger.info(f"[Group {group.group_order}] Rule result: {result}")
                    if i > 0:
                        if rule.logical_operator == 'AND':
                            group_result = group_result and result
                        else:  # OR
                            group_result = group_result or result
                    else:
                        group_result = result
                except (ValueError, TypeError) as e:
                    logger.warning(f"[Group {group.group_order}] Error evaluating rule: {e}")
                    continue
            group_results.append(group_result)
        
        # Combine all results
        should_show = True
        if rule_results:
            current_result = rule_results[0][0]
            for i in range(1, len(rule_results)):
                result, operator = rule_results[i]
                if operator == 'AND':
                    current_result = current_result and result
                else:  # OR
                    current_result = current_result or result
            should_show = should_show and current_result
        if group_results:
            group_result = group_results[0]
            for result in group_results[1:]:
                group_result = group_result or result
            should_show = should_show and group_result
        logger.info(f"Final should_show for QuestionnaireItem {questionnaire_item_id}: {should_show}")
        return JsonResponse({'should_show': should_show})
    except Exception as e:
        logger.error(f"Error in evaluate_question_rules: {e}")
        return JsonResponse({'error': str(e)}, status=400)

# Translation Views
class ItemTranslationView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for managing translations of an Item.
    """
    model = Item
    form_class = ItemTranslationForm
    template_name = 'promapp/item_translation_form.html'
    permission_required = 'promapp.add_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        item = self.get_object()
        context['original_name'] = item.name
        context['original_media'] = item.media
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        item = self.get_object()
        try:
            translation = item.translations.get(language_code=current_language)
            kwargs['initial'] = {
                'name': translation.name,
                'media': translation.media
            }
        except item.translations.model.DoesNotExist:
            kwargs['initial'] = {
                'name': '',
                'media': ''
            }
        return kwargs

    def form_valid(self, form):
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        item = self.get_object()
        item.set_current_language(current_language)
        item.name = form.cleaned_data['name']
        item.media = form.cleaned_data['media']
        item.save()
        messages.success(self.request, _('Translation saved successfully.'))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('item_list')

class ItemTranslationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View for listing items with translation links.
    """
    model = Item
    template_name = 'promapp/item_translation_list.html'
    context_object_name = 'items'
    permission_required = 'promapp.add_item'

    def get_queryset(self):
        queryset = Item.objects.language(settings.LANGUAGE_CODE).distinct('id').order_by('id', 'translations__name')
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(translations__name__icontains=search)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        context['search_form'] = TranslationSearchForm(initial={'search': self.request.GET.get('search', '')})
        context['search_form'].fields['search'].widget.attrs['hx-get'] = reverse('item_translation_list')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        return context

    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/item_translation_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)

class QuestionnaireTranslationView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for managing translations of a Questionnaire.
    """
    model = Questionnaire
    form_class = QuestionnaireTranslationForm
    template_name = 'promapp/questionnaire_translation_form.html'
    permission_required = 'promapp.add_questionnaire'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        
        # Get the questionnaire instance
        questionnaire = self.get_object()
        
        # Get the original text in the default language
        context['original_name'] = questionnaire.name
        context['original_description'] = questionnaire.description
        
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        
        # Get the questionnaire instance
        questionnaire = self.get_object()
        
        # Try to get existing translation
        try:
            translation = questionnaire.translations.get(language_code=current_language)
            # If translation exists, use its values
            kwargs['initial'] = {
                'name': translation.name,
                'description': translation.description
            }
        except questionnaire.translations.model.DoesNotExist:
            # If no translation exists, use empty values
            kwargs['initial'] = {
                'name': '',
                'description': ''
            }
        
        return kwargs

    def form_valid(self, form):
        # Get the current language from the request
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        questionnaire = self.get_object()
        questionnaire.set_current_language(current_language)
        # Set translated fields
        questionnaire.name = form.cleaned_data['name']
        questionnaire.description = form.cleaned_data['description']
        questionnaire.save()  # This saves the translation for the current language only
        messages.success(self.request, _('Translation saved successfully.'))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('questionnaire_translation_list')

class QuestionnaireTranslationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View for listing questionnaires with translation links.
    """
    model = Questionnaire
    template_name = 'promapp/questionnaire_translation_list.html'
    context_object_name = 'questionnaires'
    permission_required = 'promapp.add_questionnaire'

    def get_queryset(self):
        queryset = Questionnaire.objects.language(settings.LANGUAGE_CODE).distinct('id').order_by('id', 'translations__name')
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(translations__name__icontains=search)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        context['search_form'] = TranslationSearchForm(initial={'search': self.request.GET.get('search', '')})
        context['search_form'].fields['search'].widget.attrs['hx-get'] = reverse('questionnaire_translation_list')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        return context

    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/questionnaire_translation_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)

class LikertScaleResponseOptionTranslationView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for managing translations of a LikertScaleResponseOption.
    """
    model = LikertScaleResponseOption
    form_class = LikertScaleResponseOptionTranslationForm
    template_name = 'promapp/likert_scale_response_option_translation_form.html'
    permission_required = 'promapp.add_likertscaleresponseoption'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        option = self.get_object()
        context['original_option_text'] = option.option_text
        context['original_option_media'] = option.option_media
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        option = self.get_object()
        try:
            translation = option.translations.get(language_code=current_language)
            kwargs['initial'] = {
                'option_text': translation.option_text,
                'option_media': translation.option_media
            }
        except option.translations.model.DoesNotExist:
            kwargs['initial'] = {
                'option_text': '',
                'option_media': None
            }
        return kwargs

    def form_valid(self, form):
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        option = self.get_object()
        option.set_current_language(current_language)
        option.option_text = form.cleaned_data['option_text']
        option.option_media = form.cleaned_data['option_media']
        option.save()
        messages.success(self.request, _('Translation saved successfully.'))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('likert_scale_list')
    
class LikertScaleResponseOptionTranslationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View for listing LikertScaleResponseOptions with translation links.
    """
    model = LikertScaleResponseOption
    template_name = 'promapp/likert_scale_response_option_translation_list.html'
    context_object_name = 'options'
    permission_required = 'promapp.add_likertscaleresponseoption'

    def get_queryset(self):
        queryset = LikertScaleResponseOption.objects.language(settings.LANGUAGE_CODE).distinct('id').order_by('id', 'translations__option_text')
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(translations__option_text__icontains=search)
            
        return queryset

    def get_context_data(self, **kwargs):   
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        context['search_form'] = TranslationSearchForm(initial={'search': self.request.GET.get('search', '')})
        context['search_form'].fields['search'].widget.attrs['hx-get'] = reverse('likert_scale_response_option_translation_list')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        return context

    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/likert_scale_response_option_translation_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)

class RangeScaleTranslationView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for managing translations of a RangeScale.
    """
    model = RangeScale
    form_class = RangeScaleTranslationForm
    template_name = 'promapp/range_scale_translation_form.html'
    permission_required = 'promapp.add_rangescale'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        scale = self.get_object()
        context['original_min_value_text'] = scale.min_value_text
        context['original_max_value_text'] = scale.max_value_text
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        scale = self.get_object()
        try:
            translation = scale.translations.get(language_code=current_language)
            kwargs['initial'] = {
                'min_value_text': translation.min_value_text,
                'max_value_text': translation.max_value_text
            }
        except scale.translations.model.DoesNotExist:
            kwargs['initial'] = {
                'min_value_text': '',
                'max_value_text': ''
            }
        return kwargs

    def form_valid(self, form):
        current_language = self.request.GET.get('language', settings.LANGUAGE_CODE)
        scale = self.get_object()
        scale.set_current_language(current_language)
        scale.min_value_text = form.cleaned_data['min_value_text']
        scale.max_value_text = form.cleaned_data['max_value_text']
        scale.save()
        messages.success(self.request, _('Translation saved successfully.'))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('range_scale_translation_list')

class RangeScaleTranslationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View for listing range scales with translation links.
    """
    model = RangeScale
    template_name = 'promapp/range_scale_translation_list.html'
    context_object_name = 'range_scales'
    permission_required = 'promapp.add_rangescale'

    def get_queryset(self):
        queryset = RangeScale.objects.language(settings.LANGUAGE_CODE).distinct('id').order_by('id', 'translations__min_value_text')
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(translations__min_value_text__icontains=search) |
                models.Q(translations__max_value_text__icontains=search)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        context['search_form'] = TranslationSearchForm(initial={'search': self.request.GET.get('search', '')})
        context['search_form'].fields['search'].widget.attrs['hx-get'] = reverse('range_scale_translation_list')
        context['is_htmx'] = bool(self.request.META.get('HTTP_HX_REQUEST'))
        return context

    def get(self, request, *args, **kwargs):
        # Check if this is an HTMX request
        if request.META.get('HTTP_HX_REQUEST'):
            # If it is an HTMX request, only return the table part
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            html = render_to_string('promapp/partials/range_scale_translation_list_table.html', context)
            return HttpResponse(html)
        
        # Otherwise, return the full page as usual
        return super().get(request, *args, **kwargs)

def switch_language(request):
    """
    View to switch the current language for translation.
    """
    language = request.GET.get('language')
    if language and language in [lang[0] for lang in settings.LANGUAGES]:
        # Just redirect with the language parameter
        next_url = request.GET.get('next', '/')
        if '?' in next_url:
            next_url += '&language=' + language
        else:
            next_url += '?language=' + language
        return redirect(next_url)
    return redirect(request.GET.get('next', '/'))

class TranslationsDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View for the translations dashboard.
    """
    template_name = 'promapp/translations_dashboard.html'
    permission_required = 'promapp.add_questionnaire'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_languages'] = settings.LANGUAGES
        context['current_language'] = self.request.GET.get('language', settings.LANGUAGE_CODE)
        return context

def search_construct_scales(request):
    """Search construct scales and return matching results as JSON."""
    search_query = request.GET.get('q', '')
    if not search_query:
        return JsonResponse({'results': []})
    
    scales = ConstructScale.objects.filter(name__icontains=search_query).order_by('name')[:10]
    results = [{'id': scale.id, 'text': scale.name} for scale in scales]
    return JsonResponse({'results': results})

class ConstructEquationView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for managing the equation of a construct scale.
    """
    model = ConstructScale
    form_class = ConstructEquationForm
    template_name = 'promapp/construct_equation_form.html'
    permission_required = 'promapp.change_constructscale'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        construct_scale = self.get_object()
        
        # Get all items associated with this construct scale
        items = Item.objects.filter(construct_scale=construct_scale).order_by('id')
        
        # Get valid items with their generated question numbers
        valid_items_with_numbers = construct_scale.get_valid_items_with_numbers()
        
        # Separate valid and invalid items
        valid_items = [item_data['item'] for item_data in valid_items_with_numbers]
        invalid_items = [item for item in items if item.response_type not in ['Number', 'Likert', 'Range']]
        
        # Add question numbers to the context for the template
        context['valid_items_with_numbers'] = valid_items_with_numbers
        context['valid_items'] = valid_items
        context['invalid_items'] = invalid_items
        return context

    def form_valid(self, form):
        try:
            # Get the cleaned data
            cleaned_data = form.cleaned_data
            construct_scale = form.save(commit=False)
            
            # Set the scale equation
            construct_scale.scale_equation = cleaned_data.get('scale_equation')
            
            # Validate the equation
            try:
                construct_scale.validate_scale_equation()
                construct_scale.save()
                messages.success(self.request, _('Equation saved successfully.'))
                return redirect('construct_scale_list')
            except ValidationError as e:
                # Format the validation error message
                error_message = str(e)
                if error_message.startswith('__all__:'):
                    error_message = error_message.replace('__all__:', '').strip()
                form.add_error('scale_equation', error_message)
                messages.error(self.request, error_message)
                return self.form_invalid(form)
                
        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Format and display form errors
        for field, errors in form.errors.items():
            for error in errors:
                # Remove any field prefix from the error message
                error_message = error
                if error_message.startswith(field + ':'):
                    error_message = error_message.replace(field + ':', '').strip()
                messages.error(self.request, error_message)
        return super().form_invalid(form)

class ConstructScaleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for updating a construct scale.
    """
    model = ConstructScale
    form_class = ConstructScaleForm
    template_name = 'promapp/construct_scale_form.html'
    permission_required = 'promapp.change_constructscale'

    def get_success_url(self):
        return reverse('construct_scale_list')

    def form_valid(self, form):
        messages.success(self.request, _('Construct scale updated successfully.'))
        return super().form_valid(form)

class ConstructScaleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    View for deleting a construct scale.
    """
    model = ConstructScale
    permission_required = 'promapp.delete_constructscale'

    def get_success_url(self):
        return reverse('construct_scale_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Construct scale deleted successfully.'))
        return super().delete(request, *args, **kwargs)

def validate_equation(request):
    """
    HTMX endpoint to validate an equation in real-time.
    """
    equation = request.GET.get('value', '')
    scale_id = request.GET.get('scale_id')
    
    try:
        # Normalize line endings and whitespace
        equation = equation.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        equation = ' '.join(equation.split())  # Normalize whitespace
        
        # Create a temporary ConstructScale instance
        temp_scale = ConstructScale(scale_equation=equation)
        
        # If we have a scale_id, get the actual scale to validate against its items
        if scale_id:
            try:
                actual_scale = ConstructScale.objects.get(id=scale_id)
                # Copy the items from the actual scale to our temp scale
                temp_scale.item_set = actual_scale.item_set
            except ConstructScale.DoesNotExist:
                pass
        
        temp_scale.validate_scale_equation()
        return HttpResponse('<div class="text-green-600">✓ Valid equation</div>')
    except ValidationError as e:
        return HttpResponse(f'<div class="text-red-600">✗ {str(e)}</div>')

def add_to_equation(request):
    """
    HTMX endpoint to add a question reference to the equation.
    """
    question = request.GET.get('question', '')
    if not question:
        return HttpResponse('')
    return HttpResponse(question)


