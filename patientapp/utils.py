from decimal import Decimal
from typing import Dict, List, Optional, Union
from promapp.models import ConstructScale, QuestionnaireConstructScore
import logging
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Span, BoxAnnotation
from bokeh.embed import components
from bokeh.palettes import Category10
from datetime import datetime

logger = logging.getLogger(__name__)

class ConstructScoreData:
    def __init__(self, construct: ConstructScale, current_score: Optional[Decimal], 
                 previous_score: Optional[Decimal], historical_scores: List[QuestionnaireConstructScore]):
        self.construct = construct
        self.score = current_score
        self.previous_score = previous_score
        self.score_change = self._calculate_score_change()
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
        # Prepare data
        dates = [score.questionnaire_submission.submission_date for score in reversed(historical_scores)]
        scores = [float(score.score) if score.score is not None else None for score in reversed(historical_scores)]
        
        # Create figure
        p = figure(
            width=400,
            height=200,
            tools="hover,pan,box_zoom,reset",
            toolbar_location=None,
            sizing_mode="scale_width"
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
            dates=dates,
            scores=scores
        ))
        
        p.line(
            x='dates',
            y='scores',
            source=source,
            line_width=2,
            line_color='#000000'
        )
        
        # Add scatter points
        p.scatter(
            x='dates',
            y='scores',
            source=source,
            size=6,
            fill_color='#000000',
            line_color='#000000'
        )
        
        # Add threshold line if available
        if self.construct.scale_threshold_score:
            threshold = Span(
                location=float(self.construct.scale_threshold_score),
                dimension='width',
                line_color='#f97316',
                line_dash='dashed',
                line_width=1
            )
            p.add_layout(threshold)
        
        # Add normative line and band if available
        if self.construct.scale_normative_score_mean:
            normative = Span(
                location=float(self.construct.scale_normative_score_mean),
                dimension='width',
                line_color='#1e3a8a',
                line_dash='dotted',
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
        
        # Configure hover tool
        hover = HoverTool(
            tooltips=[
                ('Date', '@dates{%F}'),
                ('Score', '@scores{0.0}')
            ],
            formatters={
                '@dates': 'datetime'
            }
        )
        p.add_tools(hover)
        
        # Get the plot components
        script, div = components(p)
        return div

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