from decimal import Decimal
from typing import Dict, List, Optional, Union
from promapp.models import ConstructScale, QuestionnaireConstructScore
import logging

logger = logging.getLogger(__name__)

class ConstructScoreData:
    def __init__(self, construct: ConstructScale, current_score: Optional[Decimal], 
                 previous_score: Optional[Decimal], historical_scores: List[QuestionnaireConstructScore]):
        self.construct = construct
        self.score = current_score
        self.previous_score = previous_score
        self.score_change = self._calculate_score_change()
        self.plot_data = self._prepare_plot_data(historical_scores)
        logger.info(f"Created ConstructScoreData for {construct.name}: score={current_score}, previous={previous_score}")

    def _calculate_score_change(self) -> Optional[float]:
        if self.score is not None and self.previous_score is not None:
            change = float(self.score) - float(self.previous_score)
            logger.debug(f"Calculated score change for {self.construct.name}: {change}")
            return change
        logger.debug(f"No score change calculated for {self.construct.name} - missing current or previous score")
        return None

    def _prepare_plot_data(self, historical_scores: List[QuestionnaireConstructScore]) -> Dict:
        plot_data = {
            'dates': [score.questionnaire_submission.submission_date.strftime('%Y-%m-%d') 
                     for score in reversed(historical_scores)],
            'scores': [float(score.score) if score.score is not None else None 
                      for score in reversed(historical_scores)],
            'threshold': float(self.construct.scale_threshold_score) 
                        if self.construct.scale_threshold_score else None,
            'normative': float(self.construct.scale_normative_score_mean) 
                        if self.construct.scale_normative_score_mean else None,
            'normative_sd': float(self.construct.scale_normative_score_standard_deviation) 
                           if self.construct.scale_normative_score_standard_deviation else None
        }
        logger.debug(f"Prepared plot data for {self.construct.name}: {plot_data}")
        return plot_data

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