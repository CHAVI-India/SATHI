from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime, timedelta
from .models import QuestionnairePatientSchedule, PatientQuestionnaire, Questionnaire
import json


class QuestionnaireScheduleForm(forms.Form):
    """
    Form for scheduling questionnaires for a patient.
    Allows selecting multiple questionnaires and multiple dates.
    """
    questionnaires = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'schedule-questionnaire-checkbox'
        }),
        label=_('Select Questionnaires to Schedule'),
        help_text=_('Select one or more questionnaires to schedule')
    )
    
    scheduled_dates = forms.CharField(
        required=True,
        widget=forms.HiddenInput(attrs={
            'id': 'scheduled-dates-input',
            'class': 'scheduled-dates-field'
        }),
        label=_('Scheduled Dates'),
        help_text=_('Dates will be stored here from the calendar widget')
    )
    
    def __init__(self, patient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient
        
        # Get assigned questionnaires for this patient
        assigned_pqs = PatientQuestionnaire.objects.filter(
            patient=patient
        ).select_related('questionnaire')
        
        # Build choices with questionnaire info
        choices = []
        self.questionnaire_intervals = {}
        
        for pq in assigned_pqs:
            questionnaire = pq.questionnaire
            # Get translated name
            questionnaire_name = questionnaire.safe_translation_getter('name', any_language=True) or str(questionnaire.id)
            
            # Store interval for validation
            self.questionnaire_intervals[str(pq.id)] = questionnaire.questionnaire_answer_interval
            
            # Format interval for display
            interval_seconds = questionnaire.questionnaire_answer_interval
            if interval_seconds == 0:
                interval_display = _('No interval restriction')
            elif interval_seconds < 3600:
                minutes = interval_seconds // 60
                interval_display = _(f'{minutes} minute(s)')
            elif interval_seconds < 86400:
                hours = interval_seconds // 3600
                interval_display = _(f'{hours} hour(s)')
            else:
                days = interval_seconds // 86400
                interval_display = _(f'{days} day(s)')
            
            label = f"{questionnaire_name} - Interval: {interval_display}"
            choices.append((str(pq.id), label))
        
        self.fields['questionnaires'].choices = choices
        
        # Store intervals as JSON in a data attribute for JavaScript
        self.questionnaire_intervals_json = json.dumps(self.questionnaire_intervals)
    
    def clean_scheduled_dates(self):
        """
        Validate that scheduled dates are provided and in correct format.
        Expected format: JSON array of ISO datetime strings
        """
        dates_json = self.cleaned_data.get('scheduled_dates', '')
        
        if not dates_json:
            raise ValidationError(_('Please select at least one date for scheduling.'))
        
        try:
            dates_list = json.loads(dates_json)
        except json.JSONDecodeError:
            raise ValidationError(_('Invalid date format. Please use the calendar widget.'))
        
        if not dates_list or not isinstance(dates_list, list):
            raise ValidationError(_('Please select at least one date for scheduling.'))
        
        # Parse and validate dates
        parsed_dates = []
        for date_str in dates_list:
            try:
                # Parse ISO format datetime
                parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Make timezone aware if needed
                if timezone.is_naive(parsed_date):
                    parsed_date = timezone.make_aware(parsed_date)
                
                parsed_dates.append(parsed_date)
            except (ValueError, AttributeError) as e:
                raise ValidationError(_(f'Invalid date format: {date_str}'))
        
        # Sort dates chronologically
        parsed_dates.sort()
        
        # Store parsed dates for later use
        self.cleaned_dates = parsed_dates
        
        return dates_json
    
    def clean(self):
        """
        Validate that selected dates respect questionnaire answer intervals.
        """
        cleaned_data = super().clean()
        questionnaires = cleaned_data.get('questionnaires', [])
        
        if not hasattr(self, 'cleaned_dates'):
            return cleaned_data
        
        # Validate intervals for each questionnaire
        for pq_id in questionnaires:
            interval_seconds = self.questionnaire_intervals.get(pq_id, 0)
            
            if interval_seconds > 0 and len(self.cleaned_dates) > 1:
                # Check that successive dates respect the interval
                for i in range(len(self.cleaned_dates) - 1):
                    date1 = self.cleaned_dates[i]
                    date2 = self.cleaned_dates[i + 1]
                    
                    time_diff = (date2 - date1).total_seconds()
                    
                    if time_diff < interval_seconds:
                        # Get questionnaire name for error message
                        pq = PatientQuestionnaire.objects.get(id=pq_id)
                        questionnaire_name = pq.questionnaire.safe_translation_getter('name', any_language=True) or 'Questionnaire'
                        
                        # Format interval for error message
                        if interval_seconds < 3600:
                            minutes = interval_seconds // 60
                            interval_display = _(f'{minutes} minute(s)')
                        elif interval_seconds < 86400:
                            hours = interval_seconds // 3600
                            interval_display = _(f'{hours} hour(s)')
                        else:
                            days = interval_seconds // 86400
                            interval_display = _(f'{days} day(s)')
                        
                        raise ValidationError(
                            _(f'The questionnaire "{questionnaire_name}" requires a minimum interval of {interval_display} between successive dates. '
                              f'The dates {date1.strftime("%Y-%m-%d %H:%M")} and {date2.strftime("%Y-%m-%d %H:%M")} are too close together.')
                        )
        
        return cleaned_data
    
    def save(self):
        """
        Create schedule entries for selected questionnaires and dates.
        Returns the number of schedules created.
        """
        questionnaires = self.cleaned_data['questionnaires']
        
        schedules_created = 0
        
        for pq_id in questionnaires:
            pq = PatientQuestionnaire.objects.get(id=pq_id)
            
            for scheduled_datetime in self.cleaned_dates:
                # Check if schedule already exists for this datetime
                existing = QuestionnairePatientSchedule.objects.filter(
                    patient_questionnaire=pq,
                    date_assessment=scheduled_datetime
                ).exists()
                
                if not existing:
                    QuestionnairePatientSchedule.objects.create(
                        patient_questionnaire=pq,
                        date_assessment=scheduled_datetime
                    )
                    schedules_created += 1
        
        return schedules_created
