from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext as _
from .models import Questionnaire, Item, QuestionnaireItem, LikertScale, RangeScale, ConstructScale, ResponseTypeChoices, LikertScaleResponseOption, PatientQuestionnaire, QuestionnaireItemResponse, Patient
from .forms import (
    QuestionnaireForm, ItemForm, QuestionnaireItemForm, 
    LikertScaleForm, LikertScaleResponseOptionFormSet,
    ItemSelectionForm, ConstructScaleForm,
    LikertScaleResponseOptionForm, RangeScaleForm,
    QuestionnaireResponseForm
)
from django.utils.translation import get_language
from django.db import models
from django.core.exceptions import ValidationError

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
        current_language = get_language()
        items = Item.objects.language(current_language).filter(
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
        # Use translations__name instead of name for ordering
        current_language = get_language()
        context['available_items'] = Item.objects.language(current_language).all().order_by('construct_scale__name', 'translations__name')
        context['construct_scales'] = ConstructScale.objects.all().order_by('name')
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
        
        # Get all questionnaire items for this questionnaire
        questionnaire_items = QuestionnaireItem.objects.filter(questionnaire=questionnaire)
        
        # Create a mapping of item IDs to question numbers
        item_to_question_number = {str(qi.item.id): qi.question_number for qi in questionnaire_items}
        
        # Get all available items with proper translation handling
        current_language = get_language()
        available_items = Item.objects.language(current_language).all().order_by('construct_scale__name', 'translations__name')
        
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
        context['construct_scales'] = ConstructScale.objects.all().order_by('name')
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
            
            # Use getattr with default value instead of safe_translation_getter
            questionnaire_name = getattr(questionnaire, 'name', 'Questionnaire')
            messages.success(self.request, f"Questionnaire '{questionnaire_name}' updated successfully with {len(selected_items)} items.")
        else:
            messages.warning(self.request, "Questionnaire updated, but there was an issue with item selection.")
            
        return redirect(self.success_url)


class ItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Item
    template_name = 'promapp/item_list.html'
    context_object_name = 'items'
    permission_required = 'promapp.view_item'
    paginate_by = 25  # Show 25 items per page
    
    def get_queryset(self):
        current_language = get_language()
        queryset = Item.objects.language(current_language)
        
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
            
        return queryset.order_by('construct_scale__name', 'translations__name')
    
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
            return redirect('item_create')
    else:
        form = ConstructScaleForm()
    
    return render(request, 'promapp/construct_scale_form.html', {
        'form': form
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

class QuestionnaireResponseView(LoginRequiredMixin, DetailView):
    """
    View for handling questionnaire responses.
    This view allows patients to respond to questionnaires assigned to them.
    """
    model = PatientQuestionnaire
    template_name = 'promapp/questionnaire_response.html'
    context_object_name = 'patient_questionnaire'
    
    def get_queryset(self):
        # Only allow access to questionnaires assigned to the current patient
        return PatientQuestionnaire.objects.filter(
            patient__user=self.request.user,
            display_questionnaire=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_questionnaire = self.get_object()
        
        # Get all questionnaire items ordered by question number
        questionnaire_items = QuestionnaireItem.objects.filter(
            questionnaire=patient_questionnaire.questionnaire
        ).order_by('question_number')
        
        # Initialize the form with the questionnaire items
        context['form'] = QuestionnaireResponseForm(
            questionnaire_items=questionnaire_items
        )
        context['questionnaire_items'] = questionnaire_items
        
        return context
    
    def post(self, request, *args, **kwargs):
        patient_questionnaire = self.get_object()
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
                    # Create response objects for each answered question
                    for qi in questionnaire_items:
                        response_value = form.cleaned_data.get(f'response_{qi.id}')
                        if response_value:
                            QuestionnaireItemResponse.objects.create(
                                patient_questionnaire=patient_questionnaire,
                                questionnaire_item=qi,
                                response_value=str(response_value)
                            )
                
                messages.success(request, _('Your responses have been saved successfully.'))
                return redirect('patient_questionnaire_list')
                
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
    permission_required = 'promapp.change_patientquestionnaire'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Get all questionnaires
        current_language = get_language()
        all_questionnaires = Questionnaire.objects.language(current_language).all().order_by('translations__name')
        
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
            queryset = queryset.filter(
                models.Q(name__icontains=search_query) |
                models.Q(patient_id__icontains=search_query)
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
        # Only show questionnaires for the logged-in patient
        return PatientQuestionnaire.objects.filter(
            patient__user=self.request.user,
            display_questionnaire=True
        ).select_related('questionnaire')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = getattr(self.request.user, 'patient', None)
        return context
