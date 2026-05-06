from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def abs_value(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        divisor = float(arg)
        if divisor == 0:
            return 0
        return float(value) / divisor
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def get_latest_aggregated_stat(aggregated_statistics):
    """Get the latest (most recent time interval) aggregated statistic"""
    if not aggregated_statistics or not isinstance(aggregated_statistics, dict):
        return None
    
    # Get the maximum time interval key
    max_interval = max(aggregated_statistics.keys())
    return aggregated_statistics[max_interval]


@register.filter
def get_clinical_status(score_data):
    """
    Determine clinical status for a construct score.
    Returns: 'concerning', 'favorable', or 'stable'
    """
    try:
        if not score_data or not score_data.score:
            return 'stable'
        
        score = float(score_data.score)
        construct = score_data.construct
        direction = construct.scale_better_score_direction or 'Higher is Better'
        threshold = construct.scale_threshold_score
        
        # Check if score is concerning based on direction and threshold
        if threshold is not None:
            threshold_val = float(threshold)
            if direction == 'Higher is Better':
                if score < threshold_val:
                    return 'concerning'
                else:
                    return 'favorable'
            elif direction == 'Lower is Better':
                if score > threshold_val:
                    return 'concerning'
                else:
                    return 'favorable'
        
        # If no threshold, check if clinically significant
        if hasattr(score_data, 'is_clinically_significant') and score_data.is_clinically_significant():
            return 'concerning'
        
        return 'stable'
    except Exception:
        return 'stable'


@register.filter
def generate_simplified_summary(score_data, item_responses_grouped=None):
    """
    Generate a simplified, natural language summary for print reports.
    
    Example output:
    "The neurological problems score is 33.3, which is stable since the last visit but 
    significantly above the normal threshold of 9.0. Most people in the reference group 
    score 0.0, meaning this patient scores much higher than typical. This elevated 
    score needs clinical attention."
    """
    try:
        if not score_data or not score_data.score:
            return "No score data available."
        
        construct = score_data.construct
        score = float(score_data.score)
        score_formatted = f"{score:.1f}"
        
        direction = construct.scale_better_score_direction or 'Higher is Better'
        threshold = construct.scale_threshold_score
        normative = construct.scale_normative_score_mean
        normative_sd = construct.scale_normative_score_standard_deviation
        mid = construct.scale_minimum_clinical_important_difference
        
        construct_name = construct.name
        
        # Start building the summary
        parts = []
        
        # Opening sentence with score
        parts.append(f"The {construct_name} score is {score_formatted}")
        
        # Score change information
        change_text = ""
        if score_data.score_change is not None and score_data.previous_score is not None:
            change = float(score_data.score_change)
            change_abs = abs(change)
            
            # Determine if change is clinically significant using MID
            is_significant_change = False
            if mid and float(mid) > 0:
                is_significant_change = change_abs >= float(mid)
            
            if change == 0:
                change_text = ", which is stable since the last visit"
            else:
                change_desc = ""
                if direction == 'Higher is Better':
                    if change > 0:
                        change_desc = "improved" if is_significant_change else "slightly improved"
                    else:
                        change_desc = "worsened" if is_significant_change else "slightly worsened"
                elif direction == 'Lower is Better':
                    if change < 0:
                        change_desc = "improved" if is_significant_change else "slightly improved"
                    else:
                        change_desc = "worsened" if is_significant_change else "slightly worsened"
                else:  # Middle is Better
                    if is_significant_change:
                        change_desc = "changed significantly"
                    else:
                        change_desc = "remained relatively stable"
                
                change_text = f", which has {change_desc} by {change_abs:.1f} points since the last visit"
        else:
            change_text = ", which is the first measurement for this assessment"
        
        parts.append(change_text)
        
        # Threshold comparison
        threshold_text = ""
        if threshold is not None:
            threshold_val = float(threshold)
            diff = abs(score - threshold_val)
            
            if direction == 'Higher is Better':
                if score < threshold_val:
                    threshold_text = f" and is significantly below the normal threshold of {threshold_val:.1f}"
                elif score > threshold_val:
                    above_by = score - threshold_val
                    threshold_text = f" but significantly above the normal threshold of {threshold_val:.1f}"
                else:
                    threshold_text = f" and is at the threshold of {threshold_val:.1f}"
            elif direction == 'Lower is Better':
                if score > threshold_val:
                    threshold_text = f" but significantly above the normal threshold of {threshold_val:.1f}"
                elif score < threshold_val:
                    threshold_text = f" and is well below the normal threshold of {threshold_val:.1f}"
                else:
                    threshold_text = f" and is at the threshold of {threshold_val:.1f}"
            
            # Add clinical attention note
            if direction == 'Higher is Better' and score < threshold_val:
                threshold_text += ". This low score needs clinical attention"
            elif direction == 'Lower is Better' and score > threshold_val:
                threshold_text += ". This elevated score needs clinical attention"
        
        parts.append(threshold_text)
        
        # Normative comparison
        normative_text = ""
        if normative is not None:
            normative_val = float(normative)
            diff_from_norm = score - normative_val
            diff_abs = abs(diff_from_norm)
            
            # Determine if difference is significant
            is_significant_norm = False
            if normative_sd and float(normative_sd) > 0:
                sd_val = float(normative_sd)
                is_significant_norm = diff_abs >= (0.5 * sd_val)
            
            if is_significant_norm or diff_abs > 0.1:  # Include if significant or any meaningful difference
                # Get the typical reference population score description
                if score_data.aggregated_statistics:
                    # Use actual aggregated data
                    latest_agg = get_latest_aggregated_stat(score_data.aggregated_statistics)
                    if latest_agg:
                        pop_score = float(latest_agg['central'])
                        pop_n = latest_agg['n']
                        
                        if abs(score - pop_score) > 0.5:
                            if score > pop_score:
                                if direction == 'Higher is Better':
                                    normative_text = f" Most people in the reference group score around {pop_score:.1f}, meaning this patient scores better than typical."
                                else:
                                    normative_text = f" Most people in the reference group score around {pop_score:.1f}, meaning this patient scores much higher than typical. This elevated score needs clinical attention."
                            else:
                                if direction == 'Higher is Better':
                                    normative_text = f" Most people in the reference group score around {pop_score:.1f}, meaning this patient scores lower than typical. This low score needs clinical attention."
                                else:
                                    normative_text = f" Most people in the reference group score around {pop_score:.1f}, meaning this patient scores better than typical."
                else:
                    # Use normative mean as reference
                    if abs(diff_from_norm) > 0.5:
                        if diff_from_norm > 0:
                            if direction == 'Higher is Better':
                                normative_text = f" Most people typically score around {normative_val:.1f}, meaning this patient scores better than average."
                            elif direction == 'Lower is Better':
                                normative_text = f" Most people typically score around {normative_val:.1f}, meaning this patient scores much higher than typical. This elevated score needs clinical attention."
                            else:
                                normative_text = f" Most people typically score around {normative_val:.1f}, meaning this patient scores differently from typical."
                        else:
                            if direction == 'Higher is Better':
                                normative_text = f" Most people typically score around {normative_val:.1f}, meaning this patient scores lower than average. This low score needs clinical attention."
                            elif direction == 'Lower is Better':
                                normative_text = f" Most people typically score around {normative_val:.1f}, meaning this patient scores better than average."
                            else:
                                normative_text = f" Most people typically score around {normative_val:.1f}, meaning this patient scores differently from typical."
        
        parts.append(normative_text)
        
        # Item-level summary if available
        item_text = ""
        if item_responses_grouped:
            for group in item_responses_grouped:
                if hasattr(group, 'get') and group.get('construct') and str(group['construct'].id) == str(construct.id):
                    worsened = group.get('worsened_items', [])
                    improved = group.get('improved_items', [])
                    
                    if worsened and len(worsened) > 0:
                        if len(worsened) == 1:
                            item_text = f" The item '{worsened[0].questionnaire_item.item.name}' has worsened and may be driving this score."
                        else:
                            item_names = [item.questionnaire_item.item.name for item in worsened[:3]]
                            item_text = f" Items that have worsened include: {', '.join(item_names)}"
                            if len(worsened) > 3:
                                item_text += f" and {len(worsened) - 3} others."
                            else:
                                item_text += "."
                    elif improved and len(improved) > 0:
                        if len(improved) == 1:
                            item_text = f" The item '{improved[0].questionnaire_item.item.name}' has improved."
                        else:
                            item_names = [item.questionnaire_item.item.name for item in improved[:3]]
                            item_text = f" Items that have improved include: {', '.join(item_names)}"
                            if len(improved) > 3:
                                item_text += f" and {len(improved) - 3} others."
                            else:
                                item_text += "."
                    break
        
        parts.append(item_text)
        
        # Combine all parts
        summary = "".join(parts)
        
        # Clean up and finalize
        summary = summary.replace("..", ".").replace(".,", ",").strip()
        if not summary.endswith("."):
            summary += "."
        
        return summary
        
    except Exception as e:
        # Return basic summary on error
        try:
            return f"The {score_data.construct.name} score is {float(score_data.score):.1f}."
        except:
            return "Score data available."
