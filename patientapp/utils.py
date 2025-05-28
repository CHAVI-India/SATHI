from decimal import Decimal
from typing import Dict, List, Optional, Union
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
        
        # Add all diagnosis dates
        diagnoses = patient.diagnosis_set.filter(date_of_diagnosis__isnull=False).order_by('date_of_diagnosis')
        for i, diagnosis in enumerate(diagnoses):
            diagnosis_name = diagnosis.diagnosis.diagnosis if diagnosis.diagnosis else f"Diagnosis {i+1}"
            available_dates.append((
                f'date_of_diagnosis_{diagnosis.id}',
                f'Date of Diagnosis: {diagnosis_name}',
                diagnosis.date_of_diagnosis
            ))
        
        # Add all treatment start dates
        for diagnosis in patient.diagnosis_set.all():
            diagnosis_name = diagnosis.diagnosis.diagnosis if diagnosis.diagnosis else "Unknown Diagnosis"
            treatments = diagnosis.treatment_set.filter(date_of_start_of_treatment__isnull=False).order_by('date_of_start_of_treatment')
            for i, treatment in enumerate(treatments):
                treatment_types = ", ".join([tt.treatment_type for tt in treatment.treatment_type.all()]) if treatment.treatment_type.exists() else f"Treatment {i+1}"
                available_dates.append((
                    f'date_of_start_of_treatment_{treatment.id}',
                    f'Start of Treatment: {treatment_types} ({diagnosis_name})',
                    treatment.date_of_start_of_treatment
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
            # Find treatment across all diagnoses
            for diagnosis in patient.diagnosis_set.all():
                treatment = diagnosis.treatment_set.filter(id=treatment_id, date_of_start_of_treatment__isnull=False).first()
                if treatment:
                    return treatment.date_of_start_of_treatment
            return None
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
    
    # Calculate the difference
    if interval_type in ['seconds', 'minutes', 'hours', 'days', 'weeks']:
        # Use timedelta for these intervals
        delta = submission_date_only - start_date
        total_seconds = delta.total_seconds()
        
        if interval_type == 'seconds':
            return total_seconds
        elif interval_type == 'minutes':
            return total_seconds / 60
        elif interval_type == 'hours':
            return total_seconds / 3600
        elif interval_type == 'days':
            return delta.days
        elif interval_type == 'weeks':
            return delta.days / 7
    
    elif interval_type in ['months', 'years']:
        # Use relativedelta for months and years
        if interval_type == 'months':
            # Calculate months difference
            months = (submission_date_only.year - start_date.year) * 12 + (submission_date_only.month - start_date.month)
            # Add fractional part based on days
            days_in_month = 30.44  # Average days per month
            day_fraction = (submission_date_only.day - start_date.day) / days_in_month
            return months + day_fraction
        elif interval_type == 'years':
            # Calculate years difference
            years = submission_date_only.year - start_date.year
            # Add fractional part based on days
            start_of_year = start_date.replace(year=submission_date_only.year)
            if start_of_year <= submission_date_only:
                days_diff = (submission_date_only - start_of_year).days
            else:
                # Submission is before the anniversary date
                start_of_year = start_date.replace(year=submission_date_only.year - 1)
                days_diff = (submission_date_only - start_of_year).days
                years -= 1
            
            days_in_year = 365.25  # Average days per year
            return years + (days_diff / days_in_year)
    
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
                 patient=None, start_date_reference='date_of_registration', time_interval='weeks'):
        self.construct = construct
        self.score = current_score
        self.previous_score = previous_score
        self.score_change = self._calculate_score_change()
        self.patient = patient
        self.start_date_reference = start_date_reference
        self.time_interval = time_interval
        self.bokeh_plot = self._create_bokeh_plot(historical_scores)
        logger.info(f"Created ConstructScoreData for {construct.name}: score={current_score}, previous={previous_score}")

    def _calculate_score_change(self) -> Optional[float]:
        if self.score is not None and self.previous_score is not None:
            change = float(self.score) - float(self.previous_score)
            logger.debug(f"Calculated score change for {self.construct.name}: {change}")
            return change
        logger.debug(f"No score change calculated for {self.construct.name} - missing current or previous score")
        return None

    def _create_bokeh_plot(self, historical_scores: List[QuestionnaireConstructScore]) -> str:
        # Get start date for the patient
        start_date = None
        if self.patient:
            start_date = get_patient_start_date(self.patient, self.start_date_reference)
        
        # Filter out scores with negative intervals
        if start_date:
            filtered_scores = filter_positive_intervals_construct(historical_scores, start_date, self.time_interval)
        else:
            filtered_scores = historical_scores
        
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
        
        # Calculate x-axis range to ensure it starts from 0 or positive values
        if time_intervals:
            x_min = max(0, min(time_intervals) - 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else 0)
            x_max = max(time_intervals) + 0.1 * (max(time_intervals) - min(time_intervals)) if max(time_intervals) > min(time_intervals) else max(time_intervals) + 1
        else:
            x_min, x_max = 0, 1
        
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
        
        # Style the plot
        p.background_fill_color = "#ffffff"
        p.border_fill_color = "#ffffff"
        p.grid.grid_line_color = "#e5e7eb"
        p.grid.grid_line_width = 1
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.minor_tick_line_color = None
        
        # Add main line
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
        p.line(
            x='time_intervals',
            y='scores',
            source=source,
            line_width=2,
            line_color='#000000'
        )
        
        # Add scatter points
        p.scatter(
            x='time_intervals',
            y='scores',
            source=source,
            size=6,
            fill_color='#000000',
            line_color='#000000'
        )
        

        # Configure hover tool
        hover = HoverTool(
            tooltips=[
                ('Submission Date', '@submission_dates'),
                ('Time Interval', '@time_intervals{0.0}'),
                ('Score', '@scores{0.0}')
            ],
            mode='mouse',
            point_policy='follow_mouse'
        )
        p.add_tools(hover)
        
        # Get the plot components
        script, div = components(p)
        return script + div

    @staticmethod
    def is_important_construct(construct: ConstructScale, current_score: Optional[Decimal]) -> bool:
        logger.info(f"Checking if construct {construct.name} is important (score={current_score})")
        
        if not current_score:
            logger.info(f"Construct {construct.name} not important - no current score")
            return False

        score = float(current_score)
        logger.debug(f"Processing construct {construct.name}: score={score}, direction={construct.scale_better_score_direction}")
        
        # Check threshold score first
        if construct.scale_threshold_score:
            threshold = float(construct.scale_threshold_score)
            logger.debug(f"Using threshold score: {threshold}")
            
            if construct.scale_better_score_direction == 'Higher is Better':
                is_important = score <= threshold
                logger.info(f"Construct {construct.name} {'is' if is_important else 'is not'} important - score {score} {'<=' if is_important else '>'} threshold {threshold}")
                return is_important
            elif construct.scale_better_score_direction == 'Lower is Better':
                is_important = score >= threshold
                logger.info(f"Construct {construct.name} {'is' if is_important else 'is not'} important - score {score} {'>=' if is_important else '<'} threshold {threshold}")
                return is_important
        
        # Check normative score if threshold not available
        elif construct.scale_normative_score_mean:
            normative = float(construct.scale_normative_score_mean)
            logger.debug(f"Using normative score: {normative}")
            
            # If standard deviation available, use ±1/2 SD
            if construct.scale_normative_score_standard_deviation:
                sd = float(construct.scale_normative_score_standard_deviation)
                sd_threshold = sd / 2
                logger.debug(f"Using standard deviation: {sd}, threshold: ±{sd_threshold}")
                
                if construct.scale_better_score_direction == 'Higher is Better':
                    is_important = score <= (normative + sd_threshold)
                    logger.info(f"Construct {construct.name} {'is' if is_important else 'is not'} important - score {score} {'<=' if is_important else '>'} normative+sd_threshold {normative + sd_threshold}")
                    return is_important
                elif construct.scale_better_score_direction == 'Lower is Better':
                    is_important = score >= (normative - sd_threshold)
                    logger.info(f"Construct {construct.name} {'is' if is_important else 'is not'} important - score {score} {'>=' if is_important else '<'} normative-sd_threshold {normative - sd_threshold}")
                    return is_important
            
            # If no standard deviation, just compare with mean
            else:
                if construct.scale_better_score_direction == 'Higher is Better':
                    is_important = score <= normative
                    logger.info(f"Construct {construct.name} {'is' if is_important else 'is not'} important - score {score} {'<=' if is_important else '>'} normative {normative}")
                    return is_important
                elif construct.scale_better_score_direction == 'Lower is Better':
                    is_important = score >= normative
                    logger.info(f"Construct {construct.name} {'is' if is_important else 'is not'} important - score {score} {'>=' if is_important else '<'} normative {normative}")
                    return is_important
        
        logger.info(f"Construct {construct.name} not important - no applicable criteria met")
        return False

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
    
    # Get color map for options
    better_direction = item.item_better_score_direction or 'Higher is Better'
    color_map = item.likert_response.get_option_colors(better_direction)
    
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
    
    # Add data
    source = ColumnDataSource(data=dict(
        time_intervals=time_intervals,
        responses=option_texts,
        submission_dates=submission_dates
    ))
    
    # Add line and points
    p.line(
        x='time_intervals',
        y='responses',
        source=source,
        line_width=2,
        line_color='#000000'
    )
    
    p.scatter(
        x='time_intervals',
        y='responses',
        source=source,
        size=6,
        fill_color='#000000',
        line_color='#000000'
    )
    
    # Configure hover tool
    hover = HoverTool(
        tooltips=[
            ('Submission Date', '@submission_dates'),
            ('Time Interval', '@time_intervals{0.0}'),
            ('Response', '@responses')
        ],
        mode='mouse',
        point_policy='follow_mouse'
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
    
    # Add data
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
    
    # Add line and points
    p.line(
        x='time_intervals',
        y='values',
        source=source,
        line_width=2,
        line_color='#000000'
    )
    
    p.scatter(
        x='time_intervals',
        y='values',
        source=source,
        size=6,
        fill_color='#000000',
        line_color='#000000'
    )
    
    # Configure hover tool
    hover = HoverTool(
        tooltips=[
            ('Submission Date', '@submission_dates'),
            ('Time Interval', '@time_intervals{0.0}'),
            ('Value', '@values{0.0}')
        ],
        mode='mouse',
        point_policy='follow_mouse'
    )
    p.add_tools(hover)
    
    # Get the plot components
    script, div = components(p)
    return script + div

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