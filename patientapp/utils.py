from decimal import Decimal
from typing import Dict, List, Optional, Union, Tuple
from promapp.models import *
import logging
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Span, BoxAnnotation, FactorRange
from bokeh.embed import components
from bokeh.palettes import Category10
from datetime import datetime
from bokeh.models.formatters import DatetimeTickFormatter
import math
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import os
import pandas as pd
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Patient, Institution

# Set up plotting data logger
plotting_logger = logging.getLogger('plotting_data')
plotting_logger.setLevel(logging.INFO)

# Create file handler if it doesn't exist
if not plotting_logger.handlers:
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'plotting_data.log')
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    plotting_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

def get_patient_available_start_dates(patient):
    """Get all available start dates for a patient.
    
    Args:
        patient: Patient instance
        
    Returns:
        list: List of tuples (reference_key, display_name, date_value)
    """
    available_dates = []
    
    try:
        # Add registration date if available
        if patient.date_of_registration:
            available_dates.append((
                'date_of_registration',
                'Date of Registration',
                patient.date_of_registration
            ))
        
        # Fetch all diagnoses with related data in one optimized query
        # This reduces N+1 queries to just 1 query by using select_related and prefetch_related
        diagnoses = patient.diagnosis_set.select_related('diagnosis').prefetch_related(
            'treatment_set__treatment_type'
        ).all()
        
        # Process diagnoses and treatments
        for i, diagnosis in enumerate(diagnoses):
            diagnosis_name = diagnosis.diagnosis.diagnosis if diagnosis.diagnosis else f"Diagnosis {i+1}"
            
            # Add diagnosis date if available
            if diagnosis.date_of_diagnosis:
                available_dates.append((
                    f'date_of_diagnosis_{diagnosis.id}',
                    f'Date of Diagnosis: {diagnosis_name}',
                    diagnosis.date_of_diagnosis
                ))
            
            # Process treatments for this diagnosis (now prefetched, no additional queries)
            treatments = diagnosis.treatment_set.all()
            for j, treatment in enumerate(treatments):
                # Get treatment types (now prefetched, no additional queries)
                treatment_types = ", ".join([tt.treatment_type for tt in treatment.treatment_type.all()]) if treatment.treatment_type.exists() else f"Treatment {j+1}"
                
                # Add start date if available
                if treatment.date_of_start_of_treatment:
                    available_dates.append((
                        f'date_of_start_of_treatment_{treatment.id}',
                        f'Start of Treatment: {treatment_types} ({diagnosis_name})',
                        treatment.date_of_start_of_treatment
                    ))
                
                # Add end date if available
                if treatment.date_of_end_of_treatment:
                    available_dates.append((
                        f'date_of_end_of_treatment_{treatment.id}',
                        f'End of Treatment: {treatment_types} ({diagnosis_name})',
                        treatment.date_of_end_of_treatment
                    ))
        
        # Sort by date
        available_dates.sort(key=lambda x: x[2])
        
    except Exception as e:
        logger.error(f"Error getting available start dates for patient {patient.id}: {e}")
    
    return available_dates

def get_patient_start_date(patient, start_date_reference='date_of_registration'):
    """Get the start date for a patient based on the reference type.
    
    Args:
        patient: Patient instance
        start_date_reference: Type of start date reference key
        
    Returns:
        datetime.date or None: The start date or None if not available
    """
    try:
        if start_date_reference == 'date_of_registration':
            return patient.date_of_registration
        elif start_date_reference.startswith('date_of_diagnosis_'):
            # Extract diagnosis ID from reference
            diagnosis_id = start_date_reference.replace('date_of_diagnosis_', '')
            diagnosis = patient.diagnosis_set.filter(id=diagnosis_id, date_of_diagnosis__isnull=False).first()
            return diagnosis.date_of_diagnosis if diagnosis else None
        elif start_date_reference.startswith('date_of_start_of_treatment_'):
            # Extract treatment ID from reference
            treatment_id = start_date_reference.replace('date_of_start_of_treatment_', '')
            # Direct query with JOIN to avoid N+1 problem
            from promapp.models import Treatment
            treatment = Treatment.objects.filter(
                id=treatment_id,
                diagnosis__patient=patient,
                date_of_start_of_treatment__isnull=False
            ).first()
            return treatment.date_of_start_of_treatment if treatment else None
        elif start_date_reference.startswith('date_of_end_of_treatment_'):
            # Extract treatment ID from reference
            treatment_id = start_date_reference.replace('date_of_end_of_treatment_', '')
            # Direct query with JOIN to avoid N+1 problem
            from promapp.models import Treatment
            treatment = Treatment.objects.filter(
                id=treatment_id,
                diagnosis__patient=patient,
                date_of_end_of_treatment__isnull=False
            ).first()
            return treatment.date_of_end_of_treatment if treatment else None
        else:
            # Fallback to registration date
            return patient.date_of_registration
    except Exception as e:
        logger.error(f"Error getting start date for patient {patient.id}: {e}")
        return None

def calculate_time_interval_value(submission_date, start_date, interval_type='weeks'):
    """Calculate the time interval value from start date to submission date.
    
    Args:
        submission_date: datetime object of the submission
        start_date: date object of the start reference
        interval_type: Type of interval ('seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'years')
        
    Returns:
        float: The calculated interval value
    """
    if not start_date or not submission_date:
        return 0
    
    # Convert submission_date to date if it's datetime
    if hasattr(submission_date, 'date'):
        submission_date_only = submission_date.date()
    else:
        submission_date_only = submission_date
    
    # Calculate the difference using relativedelta for all interval types
    delta = relativedelta(submission_date_only, start_date)
    
    # Convert to total days for time-based calculations
    total_days = delta.years * 365.25 + delta.months * 30.44 + delta.days
    
    if interval_type == 'seconds':
        return total_days * 24 * 60 * 60
    elif interval_type == 'minutes':
        return total_days * 24 * 60
    elif interval_type == 'hours':
        return total_days * 24
    elif interval_type == 'days':
        return total_days
    elif interval_type == 'weeks':
        return total_days / 7
    elif interval_type == 'months':
        # Calculate total months with fractional part for days
        total_months = delta.years * 12 + delta.months
        day_fraction = delta.days / 30.44
        return total_months + day_fraction
    elif interval_type == 'years':
        # Calculate total years with fractional part for months and days
        total_years = delta.years
        month_fraction = delta.months / 12.0
        day_fraction = delta.days / 365.25
        return total_years + month_fraction + day_fraction
    
    return 0

def get_interval_label(interval_type):
    """Get the display label for the interval type.
    
    Args:
        interval_type: Type of interval
        
    Returns:
        str: Display label for the interval
    """
    labels = {
        'seconds': 'Seconds',
        'minutes': 'Minutes',
        'hours': 'Hours',
        'days': 'Days',
        'weeks': 'Weeks',
        'months': 'Months',
        'years': 'Years'
    }
    return labels.get(interval_type, 'Weeks')

def filter_positive_intervals(historical_responses, start_date, time_interval='weeks'):
    """Filter historical responses to only include those with non-negative time intervals.
    
    Args:
        historical_responses: List of response objects with submission dates
        start_date: The reference start date
        time_interval: Time interval type for calculation
        
    Returns:
        List: Filtered responses with only non-negative intervals
    """
    if not start_date:
        return historical_responses
    
    filtered_responses = []
    for response in historical_responses:
        interval_value = calculate_time_interval_value(
            response.questionnaire_submission.submission_date,
            start_date,
            time_interval
        )
        # Only include responses with non-negative intervals
        if interval_value >= 0:
            filtered_responses.append(response)
    
    return filtered_responses

def filter_positive_intervals_construct(historical_scores, start_date, time_interval='weeks'):
    """Filter historical construct scores to only include those with non-negative time intervals.
    
    Args:
        historical_scores: List of construct score objects with submission dates
        start_date: The reference start date
        time_interval: Time interval type for calculation
        
    Returns:
        List: Filtered scores with only non-negative intervals
    """
    if not start_date:
        return historical_scores
    
    filtered_scores = []
    for score in historical_scores:
        interval_value = calculate_time_interval_value(
            score.questionnaire_submission.submission_date,
            start_date,
            time_interval
        )
        # Only include scores with non-negative intervals
        if interval_value >= 0:
            filtered_scores.append(score)
    
    return filtered_scores

def calculate_percentage(value: Optional[Decimal], max_value: Optional[Decimal]) -> float:
    """Calculate the percentage of a value relative to a maximum value.
    
    Args:
        value (Optional[Decimal]): The current value
        max_value (Optional[Decimal]): The maximum possible value
        
    Returns:
        float: The percentage (0-100) or 0 if calculation fails
    """
    try:
        if value is None or max_value is None or max_value == 0:
            return 0
        return (float(value) / float(max_value)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

class ConstructScoreData:
    def __init__(self, construct: ConstructScale, current_score: Optional[Decimal],
                 previous_score: Optional[Decimal], historical_scores: List[QuestionnaireConstructScore],
                 patient=None, start_date_reference='date_of_registration', time_interval='weeks',
                 aggregated_statistics=None, aggregation_metadata=None, aggregation_type='median_iqr'):
        self.construct = construct
        self.score = current_score
        self.previous_score = previous_score
        self.score_change = self._calculate_score_change()
        self.patient = patient
        self.start_date_reference = start_date_reference
        self.time_interval = time_interval
        self.aggregated_statistics = aggregated_statistics or {}
        self.aggregation_metadata = aggregation_metadata or {}
        self.aggregation_type = aggregation_type
        self.bokeh_plot = self._create_bokeh_plot(historical_scores)
        
        # Generate clinical significance explanations
        self.current_score_explanation = self._generate_current_score_explanation()
        self.score_change_explanation = self._generate_score_change_explanation()
        self.clinical_significance_summary = self._generate_clinical_significance_summary()
        
        logger.info(f"Created ConstructScoreData for {construct.name}: score={current_score}, previous={previous_score}, aggregated_intervals={len(self.aggregated_statistics)}, has_metadata={bool(self.aggregation_metadata)}")

    def _calculate_score_change(self) -> Optional[float]:
        if self.score is not None and self.previous_score is not None:
            change = float(self.score) - float(self.previous_score)
            logger.debug(f"Calculated score change for {self.construct.name}: {change}")
            return change
        logger.debug(f"No score change calculated for {self.construct.name} - missing current or previous score")
        return None

    def _is_current_score_clinically_significant(self) -> Tuple[bool, str]:
        """
        Determine if the current score is clinically significant based on the rules.
        Returns (is_significant, explanation)
        """
        if not self.score:
            return False, ""
        
        score = float(self.score)
        direction = self.construct.scale_better_score_direction or 'Higher is Better'
        
        # Get available parameters
        threshold = self.construct.scale_threshold_score
        mid = self.construct.scale_minimum_clinical_important_difference
        normative = self.construct.scale_normative_score_mean
        normative_sd = self.construct.scale_normative_score_standard_deviation
        
        logger.debug(f"Checking current score significance for {self.construct.name}: score={score}, direction={direction}, threshold={threshold}, mid={mid}, normative={normative}, sd={normative_sd}")
        
        # Apply rules based on direction
        if direction == 'Higher is Better':
            return self._check_higher_is_better_current(score, threshold, mid, normative, normative_sd)
        elif direction == 'Lower is Better':
            return self._check_lower_is_better_current(score, threshold, mid, normative, normative_sd)
        elif direction == 'Middle is Better':
            return self._check_middle_is_better_current(score, threshold, mid, normative, normative_sd)
        
        return False, ""

    def _check_higher_is_better_current(self, score, threshold, mid, normative, normative_sd):
        """Check current score significance for 'Higher is Better' direction"""
        
        # Rule 1: Threshold + MID + Normative + SD available
        if threshold and mid and normative and normative_sd:
            threshold_val = float(threshold)
            mid_val = float(mid)
            threshold_with_mid = threshold_val - mid_val
            if score <= threshold_with_mid:
                difference = threshold_val - score
                times_mid = difference / mid_val
                return True, f"Current score ({score:.1f}) is below threshold ({threshold_val:.1f}) by {difference:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Rule 2: Threshold + MID available (Normative NA)
        elif threshold and mid:
            threshold_val = float(threshold)
            mid_val = float(mid)
            threshold_with_mid = threshold_val - mid_val
            if score <= threshold_with_mid:
                difference = threshold_val - score
                times_mid = difference / mid_val
                return True, f"Current score ({score:.1f}) is below threshold ({threshold_val:.1f}) by {difference:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Rule 3: Threshold + Normative + SD available (MID NA)
        elif threshold and normative and normative_sd:
            normative_val = float(normative)
            sd_val = float(normative_sd)
            threshold_with_sd = normative_val - 0.5 * sd_val
            if score <= threshold_with_sd:
                difference = normative_val - score
                times_sd = difference / sd_val
                return True, f"Current score ({score:.1f}) is below normative mean ({normative_val:.1f}) by {difference:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Rule 4: Normative + SD available (Threshold + MID NA)
        elif normative and normative_sd:
            normative_val = float(normative)
            sd_val = float(normative_sd)
            threshold_with_sd = normative_val - 0.5 * sd_val
            if score <= threshold_with_sd:
                difference = normative_val - score
                times_sd = difference / sd_val
                return True, f"Current score ({score:.1f}) is below normative mean ({normative_val:.1f}) by {difference:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Rule 5: Threshold + Normative available (MID + SD NA)
        elif threshold and normative:
            threshold_val = float(threshold)
            if score < threshold_val:
                difference = threshold_val - score
                return True, f"Current score ({score:.1f}) is below threshold ({threshold_val:.1f}) by {difference:.1f}"
        
        # Rule 6: Normative available (Threshold + MID + SD NA)
        elif normative:
            normative_val = float(normative)
            if score < normative_val:
                difference = normative_val - score
                return True, f"Current score ({score:.1f}) is below normative mean ({normative_val:.1f}) by {difference:.1f}"
        
        return False, ""

    def _check_lower_is_better_current(self, score, threshold, mid, normative, normative_sd):
        """Check current score significance for 'Lower is Better' direction"""
        
        # Rule 1: Threshold + MID + Normative + SD available
        if threshold and mid and normative and normative_sd:
            threshold_val = float(threshold)
            mid_val = float(mid)
            threshold_with_mid = threshold_val + mid_val
            if score >= threshold_with_mid:
                difference = score - threshold_val
                times_mid = difference / mid_val
                return True, f"Current score ({score:.1f}) is above threshold ({threshold_val:.1f}) by {difference:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Rule 2: Threshold + MID available (Normative NA)
        elif threshold and mid:
            threshold_val = float(threshold)
            mid_val = float(mid)
            threshold_with_mid = threshold_val + mid_val
            if score >= threshold_with_mid:
                difference = score - threshold_val
                times_mid = difference / mid_val
                return True, f"Current score ({score:.1f}) is above threshold ({threshold_val:.1f}) by {difference:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Rule 3: Threshold + Normative + SD available (MID NA)
        elif threshold and normative and normative_sd:
            normative_val = float(normative)
            sd_val = float(normative_sd)
            threshold_with_sd = normative_val + 0.5 * sd_val
            if score >= threshold_with_sd:
                difference = score - normative_val
                times_sd = difference / sd_val
                return True, f"Current score ({score:.1f}) is above normative mean ({normative_val:.1f}) by {difference:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Rule 4: Normative + SD available (Threshold + MID NA)
        elif normative and normative_sd:
            normative_val = float(normative)
            sd_val = float(normative_sd)
            threshold_with_sd = normative_val + 0.5 * sd_val
            if score >= threshold_with_sd:
                difference = score - normative_val
                times_sd = difference / sd_val
                return True, f"Current score ({score:.1f}) is above normative mean ({normative_val:.1f}) by {difference:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Rule 5: Threshold + Normative available (MID + SD NA)
        elif threshold and normative:
            threshold_val = float(threshold)
            if score > threshold_val:
                difference = score - threshold_val
                return True, f"Current score ({score:.1f}) is above threshold ({threshold_val:.1f}) by {difference:.1f}"
        
        # Rule 6: Normative available (Threshold + MID + SD NA)
        elif normative:
            normative_val = float(normative)
            if score > normative_val:
                difference = score - normative_val
                return True, f"Current score ({score:.1f}) is above normative mean ({normative_val:.1f}) by {difference:.1f}"
        
        return False, ""

    def _check_middle_is_better_current(self, score, threshold, mid, normative, normative_sd):
        """Check current score significance for 'Middle is Better' direction"""
        
        # Rule 1: Threshold + MID + Normative + SD available
        if threshold and mid and normative and normative_sd:
            threshold_val = float(threshold)
            mid_val = float(mid)
            difference = abs(score - threshold_val)
            if difference >= mid_val:
                times_mid = difference / mid_val
                direction = "above" if score > threshold_val else "below"
                return True, f"Current score ({score:.1f}) is {direction} threshold ({threshold_val:.1f}) by {difference:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Rule 2: Threshold + MID available (Normative NA)
        elif threshold and mid:
            threshold_val = float(threshold)
            mid_val = float(mid)
            difference = abs(score - threshold_val)
            if difference >= mid_val:
                times_mid = difference / mid_val
                direction = "above" if score > threshold_val else "below"
                return True, f"Current score ({score:.1f}) is {direction} threshold ({threshold_val:.1f}) by {difference:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Rule 3: Threshold + Normative + SD available (MID NA)
        elif threshold and normative and normative_sd:
            normative_val = float(normative)
            sd_val = float(normative_sd)
            difference = abs(score - normative_val)
            if difference >= (0.5 * sd_val):
                times_sd = difference / sd_val
                direction = "above" if score > normative_val else "below"
                return True, f"Current score ({score:.1f}) is {direction} normative mean ({normative_val:.1f}) by {difference:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Rule 4: Normative + SD available (Threshold + MID NA)
        elif normative and normative_sd:
            normative_val = float(normative)
            sd_val = float(normative_sd)
            difference = abs(score - normative_val)
            if difference >= (0.5 * sd_val):
                times_sd = difference / sd_val
                direction = "above" if score > normative_val else "below"
                return True, f"Current score ({score:.1f}) is {direction} normative mean ({normative_val:.1f}) by {difference:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Rule 5: Threshold + Normative available (MID + SD NA)
        elif threshold and normative:
            threshold_val = float(threshold)
            if score != threshold_val:  # Any difference
                difference = abs(score - threshold_val)
                direction = "above" if score > threshold_val else "below"
                return True, f"Current score ({score:.1f}) is {direction} threshold ({threshold_val:.1f}) by {difference:.1f}"
        
        # Rule 6: Normative available (Threshold + MID + SD NA)
        elif normative:
            normative_val = float(normative)
            if score != normative_val:  # Any difference
                difference = abs(score - normative_val)
                direction = "above" if score > normative_val else "below"
                return True, f"Current score ({score:.1f}) is {direction} normative mean ({normative_val:.1f}) by {difference:.1f}"
        
        return False, ""

    def _is_score_change_clinically_significant(self) -> Tuple[bool, str]:
        """
        Determine if the score change is clinically significant based on the rules.
        Returns (is_significant, explanation)
        """
        if not self.score_change or not self.previous_score:
            return False, ""
        
        direction = self.construct.scale_better_score_direction or 'Higher is Better'
        mid = self.construct.scale_minimum_clinical_important_difference
        normative_sd = self.construct.scale_normative_score_standard_deviation
        
        change = abs(self.score_change)
        prev_score = float(self.previous_score)
        
        logger.debug(f"Checking score change significance for {self.construct.name}: change={self.score_change}, direction={direction}, mid={mid}, sd={normative_sd}")
        
        # Apply rules based on direction
        if direction == 'Higher is Better':
            return self._check_higher_is_better_change(prev_score, mid, normative_sd)
        elif direction == 'Lower is Better':
            return self._check_lower_is_better_change(prev_score, mid, normative_sd)
        elif direction == 'Middle is Better':
            return self._check_middle_is_better_change(prev_score, mid, normative_sd)
        
        return False, ""

    def _check_higher_is_better_change(self, prev_score, mid, normative_sd):
        """Check score change significance for 'Higher is Better' direction"""
        change = self.score_change
        change_magnitude = abs(change)
        
        # MID takes precedence if available
        if mid:
            mid_val = float(mid)
            if change < -mid_val:  # Current score is lower than previous by MID or more
                times_mid = change_magnitude / mid_val
                return True, f"Score decreased by {change_magnitude:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Use 1 SD if MID not available but SD is available
        elif normative_sd:
            sd_val = float(normative_sd)
            if change < -sd_val:  # Current score is lower than previous by 1 SD or more
                times_sd = change_magnitude / sd_val
                return True, f"Score decreased by {change_magnitude:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Use 10% change if neither MID nor SD available
        else:
            threshold_change = abs(prev_score * 0.1)
            if change < -threshold_change:  # Current score is lower by 10% or more
                percent_change = abs(change/prev_score*100)
                return True, f"Score decreased by {change_magnitude:.1f} ({percent_change:.1f}%), exceeding 10% threshold ({threshold_change:.1f})"
        
        return False, ""

    def _check_lower_is_better_change(self, prev_score, mid, normative_sd):
        """Check score change significance for 'Lower is Better' direction"""
        change = self.score_change
        change_magnitude = abs(change)
        
        # MID takes precedence if available
        if mid:
            mid_val = float(mid)
            if change > mid_val:  # Current score is higher than previous by MID or more
                times_mid = change / mid_val
                return True, f"Score increased by {change:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Use 1 SD if MID not available but SD is available
        elif normative_sd:
            sd_val = float(normative_sd)
            if change > sd_val:  # Current score is higher than previous by 1 SD or more
                times_sd = change / sd_val
                return True, f"Score increased by {change:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Use 10% change if neither MID nor SD available
        else:
            threshold_change = abs(prev_score * 0.1)
            if change > threshold_change:  # Current score is higher by 10% or more
                percent_change = change/prev_score*100
                return True, f"Score increased by {change:.1f} ({percent_change:.1f}%), exceeding 10% threshold ({threshold_change:.1f})"
        
        return False, ""

    def _check_middle_is_better_change(self, prev_score, mid, normative_sd):
        """Check score change significance for 'Middle is Better' direction"""
        change = self.score_change
        change_magnitude = abs(change)
        
        # MID takes precedence if available
        if mid:
            mid_val = float(mid)
            if change_magnitude >= mid_val:  # Change in either direction by MID or more
                times_mid = change_magnitude / mid_val
                direction = "increased" if change > 0 else "decreased"
                return True, f"Score {direction} by {change_magnitude:.1f}, which is {times_mid:.2f} times the MID ({mid_val:.1f})"
        
        # Use 1 SD if MID not available but SD is available
        elif normative_sd:
            sd_val = float(normative_sd)
            if change_magnitude >= sd_val:  # Change in either direction by 1 SD or more
                times_sd = change_magnitude / sd_val
                direction = "increased" if change > 0 else "decreased"
                return True, f"Score {direction} by {change_magnitude:.1f}, which is {times_sd:.2f} times the SD ({sd_val:.1f})"
        
        # Use 10% change if neither MID nor SD available
        else:
            threshold_change = abs(prev_score * 0.1)
            if change_magnitude >= threshold_change:  # Change in either direction by 10% or more
                percent_change = abs(change/prev_score*100)
                direction = "increased" if change > 0 else "decreased"
                return True, f"Score {direction} by {change_magnitude:.1f} ({percent_change:.1f}%), exceeding 10% threshold ({threshold_change:.1f})"
        
        return False, ""

    def _generate_current_score_explanation(self) -> str:
        """Generate explanation for why the current score is clinically significant"""
        is_significant, explanation = self._is_current_score_clinically_significant()
        return explanation if is_significant else ""

    def _generate_score_change_explanation(self) -> str:
        """Generate explanation for why the score change is clinically significant"""
        is_significant, explanation = self._is_score_change_clinically_significant()
        return explanation if is_significant else ""

    def _generate_clinical_significance_summary(self) -> str:
        """Generate a comprehensive clinical significance summary"""
        current_significant, current_explanation = self._is_current_score_clinically_significant()
        change_significant, change_explanation = self._is_score_change_clinically_significant()
        
        explanations = []
        
        if current_significant:
            explanations.append(current_explanation)
        
        if change_significant:
            explanations.append(change_explanation)
        
        if explanations:
            return ". ".join(explanations) + "."
        
        return ""

    def is_clinically_significant(self) -> bool:
        """Check if this construct score is clinically significant for any reason"""
        current_significant, _ = self._is_current_score_clinically_significant()
        change_significant, _ = self._is_score_change_clinically_significant()
        return current_significant or change_significant

    def _get_aggregation_display_name(self) -> str:
        """Get a user-friendly display name for the aggregation type."""
        aggregation_names = {
            'median_iqr': 'Median with IQR',
            'mean_95ci': 'Mean with 95% CI',
            'mean_0.5sd': 'Mean ± 0.5 SD',
            'mean_1sd': 'Mean ± 1 SD',
            'mean_2sd': 'Mean ± 2 SD',
            'mean_2.5sd': 'Mean ± 2.5 SD'
        }
        return aggregation_names.get(self.aggregation_type, 'Population Data')

    def _create_bokeh_plot(self, historical_scores: List[QuestionnaireConstructScore]) -> str:
        # Get start date for the patient
        start_date = None
        if self.patient:
            start_date = get_patient_start_date(self.patient, self.start_date_reference)
        
        plotting_logger.info("="*80)
        plotting_logger.info(f"PLOTTING DATA for {self.construct.name}")
        plotting_logger.info("="*80)
        plotting_logger.info(f"Patient: {self.patient.name if self.patient else 'Unknown'}")
        plotting_logger.info(f"Start Date: {start_date}")
        plotting_logger.info(f"Time Interval Type: {self.time_interval}")
        plotting_logger.info(f"Number of Historical Scores: {len(historical_scores)}")
        
        # Filter out scores with negative intervals
        if start_date:
            filtered_scores = filter_positive_intervals_construct(historical_scores, start_date, self.time_interval)
        else:
            filtered_scores = historical_scores
        
        plotting_logger.info(f"Filtered Scores (non-negative intervals): {len(filtered_scores)}")
        
        # Prepare data with time intervals and submission dates for tooltip
        time_intervals = []
        submission_dates = []
        for score in reversed(filtered_scores):
            # Convert UTC time to local timezone
            local_time = timezone.localtime(score.questionnaire_submission.submission_date)
            submission_dates.append(local_time.strftime('%d/%m/%y'))
            
            # Calculate time interval from start date
            if start_date:
                interval_value = calculate_time_interval_value(
                    score.questionnaire_submission.submission_date,
                    start_date,
                    self.time_interval
                )
                time_intervals.append(interval_value)
            else:
                time_intervals.append(0)
        
        scores = [float(score.score) if score.score is not None else None for score in reversed(filtered_scores)]
        
        # Log individual patient data in tabular format
        plotting_logger.info("\nINDIVIDUAL PATIENT DATA:")
        if time_intervals:
            # Create DataFrame for nice tabular output
            df_individual = pd.DataFrame({
                'Time_Interval': [f"{x:.2f}" for x in time_intervals],
                'Score': [f"{x:.1f}" if x is not None else "N/A" for x in scores],
                'Submission_Date': submission_dates
            })
            plotting_logger.info(f"\n{df_individual.to_string(index=False)}")
        else:
            plotting_logger.info("No individual data available")
        
        # Calculate x-axis range to ensure it starts from 0 or positive values
        if time_intervals:
            x_min = max(0, min(time_intervals) - 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else 0)
            x_max = max(time_intervals) + 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else max(time_intervals) + 1
        else:
            x_min, x_max = 0, 1
        
        plotting_logger.info(f"\nX-axis range: {x_min:.2f} to {x_max:.2f}")
        
        # If we have aggregated data, extend the range to include all aggregated intervals
        if self.aggregated_statistics:
            agg_intervals = list(self.aggregated_statistics.keys())
            if agg_intervals:
                x_min = max(0, min(x_min, min(agg_intervals) - 0.1 * (max(agg_intervals) - min(agg_intervals)) if max(agg_intervals) > min(agg_intervals) else 0))
                x_max = max(x_max, max(agg_intervals) + 0.1 * (max(agg_intervals) - min(agg_intervals)) if max(agg_intervals) > min(agg_intervals) else max(agg_intervals) + 1)
            
            # Log aggregated data in tabular format
            plotting_logger.info("\nAGGREGATED POPULATION DATA:")
            plotting_logger.info(f"Number of time intervals with aggregated data: {len(self.aggregated_statistics)}")
            
            # Create DataFrame for aggregated statistics
            agg_data = []
            for interval, stats in sorted(self.aggregated_statistics.items()):
                agg_data.append({
                    'Time_Interval': f"{interval:.1f}",
                    'Central': f"{stats['central']:.2f}",
                    'Lower_Bound': f"{stats['lower']:.2f}",
                    'Upper_Bound': f"{stats['upper']:.2f}",
                    'Sample_Size': stats['n']
                })
            
            if agg_data:
                df_agg = pd.DataFrame(agg_data)
                plotting_logger.info(f"\n{df_agg.to_string(index=False)}")
            
            plotting_logger.info(f"Extended X-axis range: {x_min:.2f} to {x_max:.2f}")
        else:
            plotting_logger.info("\nNO AGGREGATED DATA AVAILABLE")
        
        # Create figure with linear x-axis for time intervals
        interval_label = get_interval_label(self.time_interval)
        p = figure(
            width=400,
            height=200,
            tools="pan,box_zoom,reset",
            toolbar_location=None,
            sizing_mode="scale_width",
            x_axis_label=f"Time ({interval_label})",
            x_range=(x_min, x_max)
        )
        
        plotting_logger.info(f"\nPLOT CONFIGURATION:")
        plotting_logger.info(f"X-axis label: Time ({interval_label})")
        plotting_logger.info(f"Plot size: 400x200")
        plotting_logger.info(f"Tools: pan, box_zoom, reset")
        
        # Style the plot
        p.background_fill_color = "#ffffff"
        p.border_fill_color = "#ffffff"
        p.grid.grid_line_color = "#e5e7eb"
        p.grid.grid_line_width = 1
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.minor_tick_line_color = None
        
        # Add main line and points for individual patient
        source = ColumnDataSource(data=dict(
            time_intervals=time_intervals,
            scores=scores,
            submission_dates=submission_dates
        ))

        # Add threshold line if available
        if self.construct.scale_threshold_score:
            threshold = Span(
                location=float(self.construct.scale_threshold_score),
                dimension='width',
                line_color='#f97316',
                line_dash='solid',
                line_width=1
            )
            p.add_layout(threshold)
            plotting_logger.info(f"Added threshold line at: {self.construct.scale_threshold_score}")
        
        # Add normative line and band if available
        if self.construct.scale_normative_score_mean:
            normative = Span(
                location=float(self.construct.scale_normative_score_mean),
                dimension='width',
                line_color='#1e3a8a',
                line_dash='solid',
                line_width=1
            )
            p.add_layout(normative)
            plotting_logger.info(f"Added normative line at: {self.construct.scale_normative_score_mean}")
            
            # Add standard deviation band if available
            if self.construct.scale_normative_score_standard_deviation:
                sd = float(self.construct.scale_normative_score_standard_deviation)
                mean = float(self.construct.scale_normative_score_mean)
                band = BoxAnnotation(
                    bottom=mean - sd,
                    top=mean + sd,
                    fill_color='#1e3a8a',
                    fill_alpha=0.1,
                    line_width=0
                )
                p.add_layout(band)
                plotting_logger.info(f"Added normative band: {mean - sd:.2f} to {mean + sd:.2f}")

        # Add aggregated data if available
        if self.aggregated_statistics:
            # Prepare aggregated data
            agg_intervals = sorted(self.aggregated_statistics.keys())
            agg_central = [self.aggregated_statistics[interval]['central'] for interval in agg_intervals]
            agg_lower = [self.aggregated_statistics[interval]['lower'] for interval in agg_intervals]
            agg_upper = [self.aggregated_statistics[interval]['upper'] for interval in agg_intervals]
            agg_n = [self.aggregated_statistics[interval]['n'] for interval in agg_intervals]
            
            # Log aggregated plot arrays in tabular format
            plotting_logger.info("\nAGGREGATED PLOT DATA ARRAYS:")
            plot_data = []
            for i, interval in enumerate(agg_intervals):
                plot_data.append({
                    'Array_Index': i,
                    'Time_Interval': f"{interval:.1f}",
                    'Central_Value': f"{agg_central[i]:.2f}",
                    'Lower_Bound': f"{agg_lower[i]:.2f}",
                    'Upper_Bound': f"{agg_upper[i]:.2f}",
                    'Sample_Size': agg_n[i]
                })
            
            df_plot = pd.DataFrame(plot_data)
            plotting_logger.info(f"\n{df_plot.to_string(index=False)}")
            
            # Create data source for aggregated data
            agg_source = ColumnDataSource(data=dict(
                time_intervals=agg_intervals,
                central=agg_central,
                lower=agg_lower,
                upper=agg_upper,
                n=agg_n
            ))
            
            # Add aggregated central line (dotted gray)
            p.line(
                x='time_intervals',
                y='central',
                source=agg_source,
                line_width=2,
                line_color='#6b7280',
                line_dash='dotted',
                alpha=0.8
            )
            
            # Add aggregated points
            agg_scatter = p.scatter(
                x='time_intervals',
                y='central',
                source=agg_source,
                size=4,
                fill_color='#6b7280',
                line_color='#6b7280',
                alpha=0.8
            )
            
            # Add error bars for dispersion
            from bokeh.models import Whisker
            whisker = Whisker(
                source=agg_source,
                base='time_intervals',
                upper='upper',
                lower='lower',
                line_color='#6b7280',
                line_alpha=0.6,
                line_width=1
            )
            p.add_layout(whisker)
            
            plotting_logger.info("Added population line, points, and error bars")
            
            # Determine aggregation display name
            aggregation_display_name = self._get_aggregation_display_name()
            
            # Add hover tool for aggregated data
            agg_hover = HoverTool(
                tooltips=[
                    ('Time Interval', f'@time_intervals{{0.1}} {get_interval_label(self.time_interval).lower()}'),
                    ('Aggregation Type', aggregation_display_name),
                    ('Central Value', '@central{0.1}'),
                    ('Lower Bound', '@lower{0.1}'),
                    ('Upper Bound', '@upper{0.1}'),
                    ('Sample Size', '@n patients')
                ],
                mode='mouse',
                point_policy='follow_mouse',
                renderers=[agg_scatter]
            )
            p.add_tools(agg_hover)

        # Add individual patient line and points (on top of aggregated data)
        p.line(
            x='time_intervals',
            y='scores',
            source=source,
            line_width=2,
            line_color='#000000'
        )
        
        # Add scatter points
        individual_scatter = p.scatter(
            x='time_intervals',
            y='scores',
            source=source,
            size=6,
            fill_color='#000000',
            line_color='#000000'
        )
        
        plotting_logger.info("Added individual patient line and points (black)")

        # Configure hover tool for individual data
        individual_hover = HoverTool(
            tooltips=[
                ('Submission Date', '@submission_dates'),
                ('Time Interval', f'@time_intervals{{0.1}} {get_interval_label(self.time_interval).lower()}'),
                ('Score', '@scores{0.1}')
            ],
            mode='mouse',
            point_policy='follow_mouse',
            renderers=[individual_scatter]
        )
        p.add_tools(individual_hover)
        
        plotting_logger.info("Added hover tooltips for individual data")
        plotting_logger.info("="*80)
        plotting_logger.info(f"END PLOTTING DATA for {self.construct.name}")
        plotting_logger.info("="*80)
        
        # Get the plot components
        script, div = components(p)
        return script + div

    @staticmethod
    def is_important_construct(construct: ConstructScale, current_score: Optional[Decimal]) -> bool:
        """
        Determine if a construct is important based on the comprehensive clinical significance rules.
        This method creates a temporary ConstructScoreData object to leverage the full significance logic.
        """
        logger.info(f"Checking if construct {construct.name} is important (score={current_score})")
        
        if not current_score:
            logger.info(f"Construct {construct.name} not important - no current score")
            return False

        # Create a temporary ConstructScoreData instance to use the comprehensive significance logic
        temp_score_data = ConstructScoreData.__new__(ConstructScoreData)
        temp_score_data.construct = construct
        temp_score_data.score = current_score
        temp_score_data.previous_score = None  # We don't have previous score context here
        temp_score_data.score_change = None
        
        # Check if the current score is clinically significant
        is_significant, explanation = temp_score_data._is_current_score_clinically_significant()
        
        logger.info(f"Construct {construct.name} {'is' if is_significant else 'is not'} important - {explanation if explanation else 'no applicable criteria met'}")
        return is_significant

def create_item_response_plot(historical_responses: List['QuestionnaireItemResponse'], item: 'Item',
                             patient=None, start_date_reference='date_of_registration', time_interval='weeks') -> str:
    """Create a Bokeh plot for item responses over time.
    
    Args:
        historical_responses (List[QuestionnaireItemResponse]): List of historical responses
        item (Item): The item being plotted
        patient: Patient instance for start date calculation
        start_date_reference: Reference date type for time calculation
        time_interval: Time interval type for x-axis
        
    Returns:
        str: HTML string containing the Bokeh plot components
    """
    logger.debug(f"create_item_response_plot called for item {item.id}, type: {item.response_type}, has likert_response: {bool(item.likert_response)}, has range_response: {bool(item.range_response)}")
    if item.response_type == 'Likert' and item.likert_response:
        return create_likert_response_plot(historical_responses, item, patient, start_date_reference, time_interval)
    else:
        return create_numeric_response_plot(historical_responses, item, patient, start_date_reference, time_interval)

def create_likert_response_plot(historical_responses: List['QuestionnaireItemResponse'], item: 'Item',
                               patient=None, start_date_reference='date_of_registration', time_interval='weeks') -> str:
    """Create a Bokeh plot specifically for Likert responses.
    
    Args:
        historical_responses (List[QuestionnaireItemResponse]): List of historical responses
        item (Item): The item being plotted
        patient: Patient instance for start date calculation
        start_date_reference: Reference date type for time calculation
        time_interval: Time interval type for x-axis
        
    Returns:
        str: HTML string containing the Bokeh plot components
    """
    # Get all options ordered by their value
    options = list(item.likert_response.likertscaleresponseoption_set.all().order_by('option_value'))
    option_map = {str(opt.option_value): opt.option_text for opt in options}
    y_range = [opt.option_text for opt in options]
    
    # === OPTIMIZATION: Calculate colors in Python instead of using get_option_colors ===
    # Avoid additional database query by calculating colors directly
    better_direction = item.item_better_score_direction or 'Higher is Better'
    n_options = len(options)
    if n_options > 0:
        # Get colors from viridis palette
        colors = item.likert_response.get_viridis_colors(n_options)
        
        # Create mapping of option values to colors
        color_map = {}
        for i, option in enumerate(options):
            if better_direction == 'Higher is Better':
                # Higher values get lighter colors
                color_map[str(option.option_value)] = colors[i]
            else:
                # Lower values get lighter colors
                color_map[str(option.option_value)] = colors[-(i+1)]
    else:
        color_map = {}
    
    # Get start date for the patient
    start_date = None
    if patient:
        start_date = get_patient_start_date(patient, start_date_reference)
    
    # Filter out responses with negative intervals
    if start_date:
        filtered_responses = filter_positive_intervals(historical_responses, start_date, time_interval)
    else:
        filtered_responses = historical_responses
    
    # Prepare data
    time_intervals = []
    submission_dates = []
    option_texts = []
    for response in reversed(filtered_responses):
        local_time = timezone.localtime(response.questionnaire_submission.submission_date)
        submission_dates.append(local_time.strftime('%d/%m/%y'))
        
        # Calculate time interval from start date
        if start_date:
            interval_value = calculate_time_interval_value(
                response.questionnaire_submission.submission_date,
                start_date,
                time_interval
            )
            time_intervals.append(interval_value)
        else:
            time_intervals.append(0)
            
        option_text = option_map.get(str(response.response_value), '')
        option_texts.append(option_text)
    
    # Calculate x-axis range to ensure it starts from 0 or positive values
    if time_intervals:
        x_min = max(0, min(time_intervals) - 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else 0)
        x_max = max(time_intervals) + 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else max(time_intervals) + 1
    else:
        x_min, x_max = 0, 1
    
    # Create figure with linear x-axis for time intervals
    interval_label = get_interval_label(time_interval)
    p = figure(
        width=400,
        height=200,
        tools="pan,box_zoom,reset",
        toolbar_location=None,
        sizing_mode="scale_width",
        x_axis_label=f"Time ({interval_label})",
        y_range=FactorRange(factors=y_range),
        x_range=(x_min, x_max)
    )
    
    # Style the plot
    p.background_fill_color = "#ffffff"
    p.border_fill_color = "#ffffff"
    p.grid.grid_line_color = "#e5e7eb"
    p.grid.grid_line_width = 1
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.axis.minor_tick_line_color = None
    
    # Format axes
    p.yaxis.major_label_orientation = math.pi/4
    
    # Add colored strips for each option
    n = len(options)
    for i, option in enumerate(options):
        color = color_map.get(str(option.option_value), '#ffffff')
        if i == 0:
            # First option: extend to bottom
            bottom = -0.5
            top = 0.5
        elif i == n - 1:
            # Last option: extend to top
            bottom = i - 0.5
            top = i + 0.5
        else:
            bottom = i - 0.5
            top = i + 0.5
        box = BoxAnnotation(
            bottom=bottom,
            top=top,
            fill_color=color,
            fill_alpha=0.2,
            line_width=0
        )
        p.add_layout(box)
    
    # Add data for individual patient
    source = ColumnDataSource(data=dict(
        time_intervals=time_intervals,
        responses=option_texts,
        submission_dates=submission_dates
    ))
    
    # Add individual patient line and points (on top of aggregated data)
    p.line(
        x='time_intervals',
        y='responses',
        source=source,
        line_width=2,
        line_color='#000000'
    )
    
    individual_scatter = p.scatter(
        x='time_intervals',
        y='responses',
        source=source,
        size=6,
        fill_color='#000000',
        line_color='#000000'
    )
    
    # Configure hover tool for individual data
    hover = HoverTool(
        tooltips=[
            ('Submission Date', '@submission_dates'),
            ('Time Interval', '@time_intervals{0.0}'),
            ('Response', '@responses')
        ],
        mode='mouse',
        point_policy='follow_mouse',
        renderers=[individual_scatter]
    )
    p.add_tools(hover)
    
    # Get the plot components
    script, div = components(p)
    return script + div

def create_numeric_response_plot(historical_responses: List['QuestionnaireItemResponse'], item: 'Item',
                                patient=None, start_date_reference='date_of_registration', time_interval='weeks') -> str:
    """Create a Bokeh plot for numeric responses.
    
    Args:
        historical_responses (List[QuestionnaireItemResponse]): List of historical responses
        item (Item): The item being plotted
        patient: Patient instance for start date calculation
        start_date_reference: Reference date type for time calculation
        time_interval: Time interval type for x-axis
        
    Returns:
        str: HTML string containing the Bokeh plot components
    """
    # Get start date for the patient
    start_date = None
    if patient:
        start_date = get_patient_start_date(patient, start_date_reference)
    
    # Filter out responses with negative intervals
    if start_date:
        filtered_responses = filter_positive_intervals(historical_responses, start_date, time_interval)
    else:
        filtered_responses = historical_responses
    
    # Prepare data
    time_intervals = []
    submission_dates = []
    values = []
    for response in reversed(filtered_responses):
        local_time = timezone.localtime(response.questionnaire_submission.submission_date)
        submission_dates.append(local_time.strftime('%d/%m/%y'))
        
        # Calculate time interval from start date
        if start_date:
            interval_value = calculate_time_interval_value(
                response.questionnaire_submission.submission_date,
                start_date,
                time_interval
            )
            time_intervals.append(interval_value)
        else:
            time_intervals.append(0)
            
        try:
            value = float(response.response_value) if response.response_value else None
            values.append(value)
        except (ValueError, TypeError):
            values.append(None)
    
    logger.debug(f"Numeric plot for item {item.id}: Time intervals: {time_intervals}")
    logger.debug(f"Numeric plot for item {item.id}: Values: {values}")
    logger.debug(f"Numeric plot for item {item.id}: Threshold: {item.item_threshold_score}, Normative Mean: {item.item_normative_score_mean}, SD: {item.item_normative_score_standard_deviation}")

    # Calculate x-axis range to ensure it starts from 0 or positive values
    if time_intervals:
        x_min = max(0, min(time_intervals) - 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else 0)
        x_max = max(time_intervals) + 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else max(time_intervals) + 1
    else:
        x_min, x_max = 0, 1
    
    # Create figure with linear x-axis for time intervals
    interval_label = get_interval_label(time_interval)
    p = figure(
        width=400,
        height=200,
        tools="pan,box_zoom,reset",
        toolbar_location=None,
        sizing_mode="scale_width",
        x_axis_label=f"Time ({interval_label})",
        x_range=(x_min, x_max)
    )
    
    # Style the plot
    p.background_fill_color = "#ffffff"
    p.border_fill_color = "#ffffff"
    p.grid.grid_line_color = "#e5e7eb"
    p.grid.grid_line_width = 1
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.axis.minor_tick_line_color = None
    
    # Add data for individual patient
    source = ColumnDataSource(data=dict(
        time_intervals=time_intervals,
        values=values,
        submission_dates=submission_dates
    ))
    
    # Add threshold line if available
    if item.item_threshold_score:
        threshold = Span(
            location=float(item.item_threshold_score),
            dimension='width',
            line_color='#f97316',
            line_dash='solid',
            line_width=1
        )
        p.add_layout(threshold)
    
    # Add normative line and band if available
    if item.item_normative_score_mean:
        normative = Span(
            location=float(item.item_normative_score_mean),
            dimension='width',
            line_color='#1e3a8a',
            line_dash='solid',
            line_width=1
        )
        p.add_layout(normative)
        
        if item.item_normative_score_standard_deviation:
            sd = float(item.item_normative_score_standard_deviation)
            mean = float(item.item_normative_score_mean)
            band = BoxAnnotation(
                bottom=mean - sd,
                top=mean + sd,
                fill_color='#1e3a8a',
                fill_alpha=0.1,
                line_width=0
            )
            p.add_layout(band)
    
    # Add individual patient line and points (on top of aggregated data)
    p.line(
        x='time_intervals',
        y='values',
        source=source,
        line_width=2,
        line_color='#000000'
    )
    
    individual_scatter = p.scatter(
        x='time_intervals',
        y='values',
        source=source,
        size=6,
        fill_color='#000000',
        line_color='#000000'
    )
    
    # Configure hover tool for individual data
    hover = HoverTool(
        tooltips=[
            ('Submission Date', '@submission_dates'),
            ('Time Interval', '@time_intervals{0.0}'),
            ('Value', '@values{0.0}')
        ],
        mode='mouse',
        point_policy='follow_mouse',
        renderers=[individual_scatter]
    )
    p.add_tools(hover)
    
    # Get the plot components
    script, div = components(p)
    return script + div

def get_patient_start_date_for_aggregation(patient, start_date_reference='date_of_registration'):
    """Get the start date for a patient for aggregation purposes.
    
    For aggregation, we use the same diagnosis/treatment type but allow different dates:
    - If start_date_reference is a specific diagnosis, use that same diagnosis type's date
    - If start_date_reference is a specific treatment, use that same treatment type's date
    - Otherwise use the exact reference
    
    Args:
        patient: Patient instance
        start_date_reference: Type of start date reference key
        
    Returns:
        datetime.date or None: The start date or None if not available
    """
    try:
        if start_date_reference == 'date_of_registration':
            return patient.date_of_registration
        elif start_date_reference.startswith('date_of_diagnosis_'):
            # Extract the diagnosis ID from the reference to get the diagnosis type
            diagnosis_id = start_date_reference.replace('date_of_diagnosis_', '')
            try:
                # Get the diagnosis type from the reference diagnosis
                from promapp.models import Diagnosis
                reference_diagnosis = Diagnosis.objects.get(id=diagnosis_id)
                diagnosis_list_id = reference_diagnosis.diagnosis_id
                
                # Find this patient's diagnosis of the same type
                patient_diagnosis = patient.diagnosis_set.filter(
                    diagnosis_id=diagnosis_list_id,
                    date_of_diagnosis__isnull=False
                ).order_by('date_of_diagnosis').first()
                
                return patient_diagnosis.date_of_diagnosis if patient_diagnosis else None
            except:
                # If we can't find the specific diagnosis type, return None
                return None
        elif start_date_reference.startswith('date_of_start_of_treatment_'):
            # Extract the treatment ID from the reference to get the treatment type
            treatment_id = start_date_reference.replace('date_of_start_of_treatment_', '')
            try:
                # Get the treatment types from the reference treatment
                from promapp.models import Treatment
                reference_treatment = Treatment.objects.get(id=treatment_id)
                treatment_type_ids = list(reference_treatment.treatment_type.values_list('id', flat=True))
                
                # Find this patient's treatment with the same types
                for diagnosis in patient.diagnosis_set.all():
                    patient_treatment = diagnosis.treatment_set.filter(
                        treatment_type__id__in=treatment_type_ids,
                        date_of_start_of_treatment__isnull=False
                    ).order_by('date_of_start_of_treatment').first()
                    if patient_treatment:
                        return patient_treatment.date_of_start_of_treatment
                return None
            except:
                # If we can't find the specific treatment type, return None
                return None
        elif start_date_reference.startswith('date_of_end_of_treatment_'):
            # Extract the treatment ID from the reference to get the treatment type
            treatment_id = start_date_reference.replace('date_of_end_of_treatment_', '')
            try:
                # Get the treatment types from the reference treatment
                from promapp.models import Treatment
                reference_treatment = Treatment.objects.get(id=treatment_id)
                treatment_type_ids = list(reference_treatment.treatment_type.values_list('id', flat=True))
                
                # Find this patient's treatment with the same types
                for diagnosis in patient.diagnosis_set.all():
                    patient_treatment = diagnosis.treatment_set.filter(
                        treatment_type__id__in=treatment_type_ids,
                        date_of_end_of_treatment__isnull=False
                    ).order_by('date_of_end_of_treatment').first()
                    if patient_treatment:
                        return patient_treatment.date_of_end_of_treatment
                return None
            except:
                # If we can't find the specific treatment type, return None
                return None
        else:
            # Fallback to exact reference for other types
            return get_patient_start_date(patient, start_date_reference)
    except Exception as e:
        logger.error(f"Error getting aggregation start date for patient {patient.id}: {e}")
        return None

def get_filtered_patients_for_aggregation(exclude_patient, patient_filter_gender=None, 
                                        patient_filter_diagnosis=None, patient_filter_treatment=None,
                                        patient_filter_min_age=None, patient_filter_max_age=None):
    """Get patients for aggregation based on filtering criteria, excluding the current patient.
    
    Args:
        exclude_patient: Patient instance to exclude from aggregation
        patient_filter_gender: Gender filter ('match', specific gender, or None for all)
        patient_filter_diagnosis: Diagnosis filter ('match', specific diagnosis ID, or None for all)
        patient_filter_treatment: Treatment filter ('match', specific treatment type ID, or None for all)
        patient_filter_min_age: Minimum age filter (integer or None)
        patient_filter_max_age: Maximum age filter (integer or None)
        
    Returns:
        QuerySet: Filtered patients excluding the current patient
    """
    from patientapp.models import Patient
    
    # Start with all patients except the current one
    patients = Patient.objects.exclude(id=exclude_patient.id)
    
    # Apply gender filter
    if patient_filter_gender:
        if patient_filter_gender == 'match':
            patients = patients.filter(gender=exclude_patient.gender)
        else:
            patients = patients.filter(gender=patient_filter_gender)
    
    # Apply diagnosis filter
    if patient_filter_diagnosis:
        if patient_filter_diagnosis == 'match':
            # Get all diagnosis IDs for the current patient
            patient_diagnosis_ids = exclude_patient.diagnosis_set.values_list('diagnosis_id', flat=True)
            if patient_diagnosis_ids:
                patients = patients.filter(diagnosis__diagnosis_id__in=patient_diagnosis_ids).distinct()
        else:
            patients = patients.filter(diagnosis__diagnosis_id=patient_filter_diagnosis).distinct()
    
    # Apply treatment filter
    if patient_filter_treatment:
        if patient_filter_treatment == 'match':
            # Get all treatment type IDs for the current patient
            patient_treatment_type_ids = []
            for diagnosis in exclude_patient.diagnosis_set.all():
                treatment_type_ids = diagnosis.treatment_set.values_list('treatment_type__id', flat=True)
                patient_treatment_type_ids.extend(treatment_type_ids)
            
            if patient_treatment_type_ids:
                patients = patients.filter(
                    diagnosis__treatment__treatment_type__id__in=patient_treatment_type_ids
                ).distinct()
        else:
            patients = patients.filter(
                diagnosis__treatment__treatment_type__id=patient_filter_treatment
            ).distinct()
    
    # Apply age filters if specified
    if patient_filter_min_age is not None or patient_filter_max_age is not None:
        # Filter patients based on age
        # Get patient IDs that match age criteria
        matching_patient_ids = []
        for patient in patients:
            age = calculate_patient_age(patient)
            if age is not None:
                age_matches = True
                
                # Check minimum age
                if patient_filter_min_age is not None and age < patient_filter_min_age:
                    age_matches = False
                
                # Check maximum age
                if patient_filter_max_age is not None and age > patient_filter_max_age:
                    age_matches = False
                
                if age_matches:
                    matching_patient_ids.append(patient.id)
        
        # Filter queryset to only include patients with matching ages
        patients = patients.filter(id__in=matching_patient_ids)
    
    return patients

def aggregate_construct_scores_by_time_interval(construct, patients_queryset, start_date_reference, 
                                              time_interval, max_time_interval_filter=None, 
                                              reference_time_intervals=None):
    """Aggregate construct scores from multiple patients by time intervals.
    
    For each reference time interval from the index patient, find the most recent
    observation from other patients that is at or before each reference time point.
    
    Args:
        construct: ConstructScale instance
        patients_queryset: QuerySet of patients to include in aggregation
        start_date_reference: Reference date type for time calculation
        time_interval: Time interval type for grouping
        max_time_interval_filter: Optional maximum time interval (relative to start date) for filtering submissions
        reference_time_intervals: List of reference time intervals from index patient
        
    Returns:
        tuple: (aggregated_data dict, metadata dict)
    """
    from promapp.models import QuestionnaireConstructScore
    
    plotting_logger.info("="*80)
    plotting_logger.info(f"AGGREGATION DATA for {construct.name}")
    plotting_logger.info("="*80)
    plotting_logger.info(f"Patients in aggregation: {patients_queryset.count()}")
    plotting_logger.info(f"Start date reference: {start_date_reference}")
    plotting_logger.info(f"Time interval: {time_interval}")
    plotting_logger.info(f"Max time interval filter: {max_time_interval_filter}")
    plotting_logger.info(f"Reference time intervals from index patient: {reference_time_intervals}")
    
    if not reference_time_intervals:
        plotting_logger.info("No reference time intervals provided - returning empty aggregation")
        return {}, {
            'total_eligible_patients': patients_queryset.count(),
            'contributing_patients': 0,
            'total_responses': 0,
            'time_intervals_count': 0,
            'time_range': 'N/A'
        }
    
    aggregated_data = {}
    patients_with_data = 0
    total_scores_processed = 0
    patient_data_list = []
    contributing_patients = set()
    
    for patient in patients_queryset:
        # Get start date for this patient
        start_date = get_patient_start_date_for_aggregation(patient, start_date_reference)
        if not start_date:
            continue
            
        # Get construct scores for this patient
        scores_query = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission__patient=patient,
            construct=construct
        ).select_related('questionnaire_submission')
        
        # Apply max time interval filter if specified
        if max_time_interval_filter is not None:
            # Filter scores based on relative time intervals from patient's start date
            filtered_score_ids = []
            for score in scores_query:
                interval_value = calculate_time_interval_value(
                    score.questionnaire_submission.submission_date,
                    start_date,
                    time_interval
                )
                if interval_value <= max_time_interval_filter:
                    filtered_score_ids.append(score.id)
            
            scores_query = scores_query.filter(id__in=filtered_score_ids)
        
        # Filter out scores with negative time intervals
        scores = list(scores_query)
        filtered_scores = filter_positive_intervals_construct(scores, start_date, time_interval)
        
        if not filtered_scores:
            continue
        
        patients_with_data += 1
        patient_scores = []
        patient_contributed = False
        
        # Calculate time intervals for all scores from this patient
        patient_time_data = []
        for score in filtered_scores:
            if score.score is None:
                continue
                
            interval_value = calculate_time_interval_value(
                score.questionnaire_submission.submission_date,
                start_date,
                time_interval
            )
            patient_time_data.append({
                'interval': interval_value,
                'score': float(score.score),
                'submission_date': score.questionnaire_submission.submission_date
            })
        
        # Sort by time interval
        patient_time_data.sort(key=lambda x: x['interval'])
        
        # For each reference time interval, find the most recent observation at or before that time
        for ref_interval in reference_time_intervals:
            # Find all observations at or before this reference time
            eligible_observations = [obs for obs in patient_time_data if obs['interval'] <= ref_interval]
            
            if eligible_observations:
                # Get the most recent observation (highest interval ≤ ref_interval)
                most_recent = max(eligible_observations, key=lambda x: x['interval'])
                
                if ref_interval not in aggregated_data:
                    aggregated_data[ref_interval] = []
                
                aggregated_data[ref_interval].append(most_recent['score'])
                total_scores_processed += 1
                patient_contributed = True
                
                # Store for patient-level logging
                patient_scores.append({
                    'Reference_Interval': f"{ref_interval:.2f}",
                    'Patient_Interval': f"{most_recent['interval']:.2f}",
                    'Score': f"{most_recent['score']:.1f}",
                    'Submission_Date': most_recent['submission_date'].strftime('%Y-%m-%d %H:%M')
                })
            else:
                # No observations at or before this reference time
                patient_scores.append({
                    'Reference_Interval': f"{ref_interval:.2f}",
                    'Patient_Interval': 'No data ≤ ref time',
                    'Score': 'N/A',
                    'Submission_Date': 'N/A'
                })
        
        # Track patients that actually contributed data
        if patient_contributed:
            contributing_patients.add(patient.id)
        
        # Add patient data to list for tabular logging
        if patient_scores:
            patient_data_list.append({
                'patient': patient,
                'start_date': start_date,
                'scores': patient_scores,
                'score_count': len([s for s in patient_scores if s['Score'] != 'N/A'])
            })
    
    # Log patient-level data in tables
    plotting_logger.info("\nPATIENT-LEVEL AGGREGATION DATA:")
    plotting_logger.info(f"Patients with data: {patients_with_data}")
    plotting_logger.info(f"Total scores processed: {total_scores_processed}")
    
    for patient_data in patient_data_list[:5]:  # Show first 5 patients as example
        plotting_logger.info(f"\nPatient: {patient_data['patient'].name} (Start: {patient_data['start_date']})")
        plotting_logger.info(f"Scores count: {patient_data['score_count']}")
        
        if patient_data['scores']:
            df_patient = pd.DataFrame(patient_data['scores'])
            plotting_logger.info(f"\n{df_patient.to_string(index=False)}")
    
    if len(patient_data_list) > 5:
        plotting_logger.info(f"\n... and {len(patient_data_list) - 5} more patients with data")
    
    # Log aggregated data summary in tabular format
    plotting_logger.info("\nAGGREGATED DATA SUMMARY:")
    plotting_logger.info(f"Reference intervals with data: {len(aggregated_data)}")
    
    if aggregated_data:
        summary_data = []
        for interval, values in sorted(aggregated_data.items()):
            summary_data.append({
                'Reference_Interval': f"{interval:.2f}",
                'Score_Count': len(values),
                'Min_Score': f"{min(values):.1f}",
                'Max_Score': f"{max(values):.1f}",
                'Mean_Score': f"{sum(values)/len(values):.2f}",
                'Scores': f"[{', '.join([f'{v:.1f}' for v in sorted(values)])}]"
            })
        
        df_summary = pd.DataFrame(summary_data)
        plotting_logger.info(f"\n{df_summary.to_string(index=False)}")
    else:
        plotting_logger.info("No aggregated data available")
    
    # Calculate time interval range
    time_intervals = sorted(aggregated_data.keys()) if aggregated_data else []
    time_range = None
    if time_intervals:
        min_interval = min(time_intervals)
        max_interval = max(time_intervals)
        if min_interval == max_interval:
            time_range = f"{min_interval:.1f}"
        else:
            time_range = f"{min_interval:.1f} - {max_interval:.1f}"
    
    # Create metadata with detailed patient information
    patient_details = {
        'contributing': [],
        'non_contributing': []
    }
    
    # Add patient details to metadata
    for patient_data in patient_data_list:
        patient_info = {
            'id': patient_data['patient'].id,
            'name': patient_data['patient'].name,
            'start_date': patient_data['start_date'].strftime('%Y-%m-%d'),
            'score_count': patient_data['score_count']
        }
        
        if patient_data['patient'].id in contributing_patients:
            patient_details['contributing'].append(patient_info)
        else:
            patient_details['non_contributing'].append(patient_info)
    
    # Add non-contributing patients (those without any scores in the dataset)
    for patient in patients_queryset:
        if patient.id not in [p['patient'].id for p in patient_data_list]:
            start_date = get_patient_start_date_for_aggregation(patient, start_date_reference)
            patient_details['non_contributing'].append({
                'id': patient.id,
                'name': patient.name,
                'start_date': start_date.strftime('%Y-%m-%d') if start_date else 'N/A',
                'score_count': 0
            })
    
    metadata = {
        'total_eligible_patients': patients_queryset.count(),
        'contributing_patients': len(contributing_patients),
        'total_responses': total_scores_processed,
        'time_intervals_count': len(time_intervals),
        'time_range': time_range or 'N/A',
        'time_interval_unit': get_interval_label(time_interval).lower(),
        'patient_details': patient_details
    }
    
    plotting_logger.info("="*80)
    plotting_logger.info(f"AGGREGATION METADATA: {metadata['contributing_patients']}/{metadata['total_eligible_patients']} patients contributed {metadata['total_responses']} scores across {metadata['time_intervals_count']} intervals")
    plotting_logger.info("="*80)
    
    return aggregated_data, metadata

def calculate_aggregation_statistics(aggregated_data, aggregation_type='median_iqr'):
    """Calculate aggregation statistics for each time interval.
    
    Args:
        aggregated_data: Dict mapping time intervals to lists of values
        aggregation_type: Type of aggregation to perform
        
    Returns:
        dict: Statistics for each time interval
    """
    import numpy as np
    from scipy import stats
    
    plotting_logger.info("="*80)
    plotting_logger.info("STATISTICS CALCULATION")
    plotting_logger.info("="*80)
    plotting_logger.info(f"Aggregation type: {aggregation_type}")
    plotting_logger.info(f"Input data intervals: {len(aggregated_data)}")
    
    statistics = {}
    calculation_data = []
    
    for interval, values in aggregated_data.items():
        if not values or len(values) < 2:  # Need at least 2 values for meaningful statistics
            calculation_data.append({
                'Time_Interval': f"{interval:.1f}",
                'Value_Count': len(values),
                'Status': 'Skipped (need ≥2 values)',
                'Central': 'N/A',
                'Lower': 'N/A',
                'Upper': 'N/A',
                'Values': f"[{', '.join([f'{v:.1f}' for v in values]) if values else 'None'}]"
            })
            continue
            
        values_array = np.array(values)
        n = len(values)
        
        if aggregation_type == 'median_iqr':
            median = np.median(values_array)
            q25 = np.percentile(values_array, 25)
            q75 = np.percentile(values_array, 75)
            statistics[interval] = {
                'central': median,
                'lower': q25,
                'upper': q75,
                'n': n
            }
            calculation_data.append({
                'Time_Interval': f"{interval:.1f}",
                'Value_Count': n,
                'Status': 'Calculated',
                'Central': f"{median:.2f} (median)",
                'Lower': f"{q25:.2f} (Q25)",
                'Upper': f"{q75:.2f} (Q75)",
                'Values': f"[{', '.join([f'{v:.1f}' for v in sorted(values)])}]"
            })
            
        elif aggregation_type == 'mean_95ci':
            mean = np.mean(values_array)
            sem = stats.sem(values_array)  # Standard error of mean
            ci = stats.t.interval(0.95, n-1, loc=mean, scale=sem)
            statistics[interval] = {
                'central': mean,
                'lower': ci[0],
                'upper': ci[1],
                'n': n
            }
            calculation_data.append({
                'Time_Interval': f"{interval:.1f}",
                'Value_Count': n,
                'Status': 'Calculated',
                'Central': f"{mean:.2f} (mean)",
                'Lower': f"{ci[0]:.2f} (95% CI lower)",
                'Upper': f"{ci[1]:.2f} (95% CI upper)",
                'Values': f"[{', '.join([f'{v:.1f}' for v in sorted(values)])}]"
            })
            
        elif aggregation_type.startswith('mean_'):
            mean = np.mean(values_array)
            std = np.std(values_array, ddof=1)  # Sample standard deviation
            
            # Extract the multiplier from the aggregation type
            if aggregation_type == 'mean_0.5sd':
                multiplier = 0.5
            elif aggregation_type == 'mean_1sd':
                multiplier = 1.0
            elif aggregation_type == 'mean_2sd':
                multiplier = 2.0
            elif aggregation_type == 'mean_2.5sd':
                multiplier = 2.5
            else:
                multiplier = 1.0
                
            statistics[interval] = {
                'central': mean,
                'lower': mean - (multiplier * std),
                'upper': mean + (multiplier * std),
                'n': n
            }
            calculation_data.append({
                'Time_Interval': f"{interval:.1f}",
                'Value_Count': n,
                'Status': 'Calculated',
                'Central': f"{mean:.2f} (mean)",
                'Lower': f"{mean - (multiplier * std):.2f} (-{multiplier}SD)",
                'Upper': f"{mean + (multiplier * std):.2f} (+{multiplier}SD)",
                'Values': f"[{', '.join([f'{v:.1f}' for v in sorted(values)])}]"
            })
    
    # Log calculation results in tabular format
    plotting_logger.info("\nSTATISTICS CALCULATION RESULTS:")
    if calculation_data:
        df_calc = pd.DataFrame(calculation_data)
        plotting_logger.info(f"\n{df_calc.to_string(index=False)}")
    else:
        plotting_logger.info("No calculation data available")
    
    # Log final statistics summary
    plotting_logger.info(f"\nFINAL STATISTICS SUMMARY:")
    plotting_logger.info(f"Valid intervals with statistics: {len(statistics)}")
    
    if statistics:
        final_stats = []
        for interval, stats_dict in sorted(statistics.items()):
            final_stats.append({
                'Time_Interval': f"{interval:.1f}",
                'Central': f"{stats_dict['central']:.2f}",
                'Lower_Bound': f"{stats_dict['lower']:.2f}",
                'Upper_Bound': f"{stats_dict['upper']:.2f}",
                'Sample_Size': stats_dict['n'],
                'Range_Width': f"{stats_dict['upper'] - stats_dict['lower']:.2f}"
            })
        
        df_final = pd.DataFrame(final_stats)
        plotting_logger.info(f"\n{df_final.to_string(index=False)}")
    else:
        plotting_logger.info("No valid statistics calculated")
    
    plotting_logger.info("="*80)
    plotting_logger.info("END STATISTICS CALCULATION")
    plotting_logger.info("="*80)
    
    return statistics

def calculate_aggregation_metadata(aggregated_data, patients_queryset, construct_or_item):
    """Calculate metadata about the aggregation including patient and response counts.
    
    Args:
        aggregated_data: Dict mapping time intervals to lists of values
        patients_queryset: QuerySet of patients included in aggregation
        construct_or_item: The construct or item being aggregated
        
    Returns:
        dict: Metadata about the aggregation
    """
    total_responses = sum(len(values) for values in aggregated_data.values())
    total_eligible_patients = patients_queryset.count()
    
    # Calculate unique patients that contributed data from the actual aggregated data
    # Since aggregated_data contains the actual responses used, we can count unique contributions
    contributing_patients = 0
    if aggregated_data:
        # Each value in aggregated_data represents a response from a patient
        # The number of contributing patients is estimated by the maximum number of responses
        # across all time intervals (since a patient can contribute to multiple intervals)
        max_responses_per_interval = max(len(values) for values in aggregated_data.values()) if aggregated_data else 0
        
        # For a more accurate count, we need to consider that the same patients may contribute
        # to multiple intervals. A reasonable estimate is the maximum responses in any single interval
        # as this represents the minimum number of unique patients contributing
        contributing_patients = max_responses_per_interval
        
        # However, for a more conservative and realistic estimate, we can use
        # the average number of responses across intervals, as this better represents
        # the typical patient contribution pattern
        if aggregated_data:
            avg_responses = total_responses / len(aggregated_data)
            contributing_patients = min(int(avg_responses) + 1, total_eligible_patients)
    
    # Calculate time interval range
    time_intervals = sorted(aggregated_data.keys()) if aggregated_data else []
    time_range = None
    if time_intervals:
        min_interval = min(time_intervals)
        max_interval = max(time_intervals)
        if min_interval == max_interval:
            time_range = f"{min_interval:.1f}"
        else:
            time_range = f"{min_interval:.1f} - {max_interval:.1f}"
    
    return {
        'total_eligible_patients': total_eligible_patients,
        'contributing_patients': contributing_patients,
        'total_responses': total_responses,
        'time_intervals_count': len(time_intervals),
        'time_range': time_range
    }

def get_plotting_log_file_path():
    """Get the path to the plotting data log file."""
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    return os.path.join(log_dir, 'plotting_data.log')

def clear_plotting_log():
    """Clear the plotting data log file."""
    log_file = get_plotting_log_file_path()
    try:
        with open(log_file, 'w') as f:
            f.write('')
        plotting_logger.info("Plotting data log file cleared")
        return True
    except Exception as e:
        logger.error(f"Error clearing plotting log: {e}")
        return False

def log_plotting_session_start(patient_name, constructs_count):
    """Log the start of a new plotting session."""
    plotting_logger.info("=" * 100)
    plotting_logger.info(f"NEW PLOTTING SESSION STARTED")
    plotting_logger.info(f"Patient: {patient_name}")
    plotting_logger.info(f"Number of constructs to plot: {constructs_count}")
    plotting_logger.info(f"Session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plotting_logger.info("=" * 100)

def calculate_patient_age(patient, reference_date=None):
    """Get the age of a patient.
    
    Args:
        patient: Patient instance
        reference_date: Date to calculate age at (not used, kept for compatibility)
        
    Returns:
        int or None: Age in years, or None if age is not available
    """
    if not hasattr(patient, 'age') or patient.age is None:
        return None
    
    try:
        return int(patient.age)
    except (ValueError, TypeError):
        logger.error(f"Error getting age for patient {patient.id}: invalid age value {patient.age}")
        return None

# Institution-based Access Control Utilities
def get_user_institution(user):
    """
    Get the institution for the current user if they are a provider.
    Returns None if the user is not a provider or has no institution.
    """
    try:
        return user.provider.institution
    except AttributeError:
        return None

def is_provider_user(user):
    """Check if the user is a provider (has a provider profile)."""
    try:
        return hasattr(user, 'provider') and user.provider is not None
    except AttributeError:
        return False

def filter_patients_by_institution(queryset, user):
    """
    Filter a Patient queryset based on the user's institution.
    If the user is a provider, only return patients from their institution.
    If the user is not a provider, return all patients (assuming they have appropriate permissions).
    """
    user_institution = get_user_institution(user)
    if user_institution:
        return queryset.filter(institution=user_institution)
    return queryset

def check_patient_access(user, patient):
    """
    Check if a user can access a specific patient.
    Raises PermissionDenied if access is not allowed.
    """
    user_institution = get_user_institution(user)
    if user_institution and patient.institution != user_institution:
        raise PermissionDenied(
            "You do not have permission to access patients from other institutions."
        )

def get_accessible_patient_or_404(user, pk):
    """
    Get a patient by pk, ensuring the user has access to it.
    Raises 404 if patient doesn't exist, PermissionDenied if no access.
    """
    patient = get_object_or_404(Patient, pk=pk)
    check_patient_access(user, patient)
    return patient

# Institution Filtering Mixin for Class-Based Views
class InstitutionFilterMixin:
    """
    Mixin for class-based views that automatically filters Patient querysets
    based on the user's institution.
    """
    
    def get_user_institution(self):
        """Get the institution for the current user."""
        return get_user_institution(self.request.user)
    
    def get_queryset(self):
        """Filter the queryset based on user's institution."""
        qs = super().get_queryset()
        
        # Only apply institution filtering if the model is Patient
        if hasattr(qs.model, 'institution'):
            qs = filter_patients_by_institution(qs, self.request.user)
        
        return qs
    
    def get_object(self, queryset=None):
        """
        Get the object, ensuring the user has access to it.
        This method is called by DetailView, UpdateView, DeleteView, etc.
        """
        obj = super().get_object(queryset)
        
        # Only check access if the object is a Patient
        if isinstance(obj, Patient):
            check_patient_access(self.request.user, obj)
        
        return obj