/**
 * HCP Result UI JavaScript
 * Handles plot initialization, HTMX interactions, and UI state management
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all plots on page load
    initializeAllPlots();
    
    // Re-initialize plots after HTMX updates
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.detail.target.id === 'results-container') {
            initializeAllPlots();
        }
    });
    
    // Handle HTMX errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX Error:', evt.detail);
        showNotification('Error loading data. Please try again.', 'error');
    });
});

/**
 * Initialize all plots on the page
 */
function initializeAllPlots() {
    // Initialize important construct plots
    document.querySelectorAll('[id^="plot-data-"]').forEach(function(script) {
        try {
            const data = JSON.parse(script.textContent);
            initializeConstructPlot(data);
        } catch (error) {
            console.error('Error parsing construct plot data:', error);
        }
    });
    
    // Initialize item plots
    document.querySelectorAll('[id^="numeric-plot-data-"], [id^="range-plot-data-"], [id^="likert-plot-data-"]').forEach(function(script) {
        try {
            const data = JSON.parse(script.textContent);
            initializeItemPlot(data);
        } catch (error) {
            console.error('Error parsing item plot data:', error);
        }
    });
    
    // Initialize sparklines
    document.querySelectorAll('[id^="sparkline-data-"]').forEach(function(script) {
        try {
            const data = JSON.parse(script.textContent);
            initializeSparkline(data);
        } catch (error) {
            console.error('Error parsing sparkline data:', error);
        }
    });
}

/**
 * Initialize construct score plots (for important constructs)
 */
function initializeConstructPlot(data) {
    const plotDiv = document.getElementById(data.plotId);
    if (!plotDiv) return;
    
    const dates = data.historicalData.map(d => d.date);
    const scores = data.historicalData.map(d => d.score);
    const hoverTexts = data.historicalData.map(d => 
        `Date: ${d.submissionDate}<br>Score: ${d.score !== null ? d.score.toFixed(1) : 'Missing'}`
    );
    
    const traces = [{
        x: dates,
        y: scores,
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#000000', width: 3 },
        marker: { 
            color: '#000000', 
            size: 8,
            symbol: scores.map(s => s === null ? 'x' : 'circle')
        },
        name: data.constructName,
        hovertemplate: '%{text}<extra></extra>',
        text: hoverTexts,
        connectgaps: false
    }];
    
    // Add threshold line
    if (data.thresholdScore !== null) {
        traces.push({
            x: dates,
            y: Array(dates.length).fill(data.thresholdScore),
            type: 'scatter',
            mode: 'lines',
            line: { color: '#f97316', width: 2, dash: 'dash' },
            name: 'Threshold',
            hovertemplate: `Threshold: ${data.thresholdScore.toFixed(1)}<extra></extra>`
        });
    }
    
    // Add normative line
    if (data.normativeMean !== null) {
        traces.push({
            x: dates,
            y: Array(dates.length).fill(data.normativeMean),
            type: 'scatter',
            mode: 'lines',
            line: { color: '#1e3a8a', width: 2, dash: 'dot' },
            name: 'Normative',
            hovertemplate: `Normative: ${data.normativeMean.toFixed(1)}<extra></extra>`
        });
        
        // Add normative band if SD available
        if (data.normativeSD !== null) {
            traces.push({
                x: dates.concat(dates.slice().reverse()),
                y: Array(dates.length).fill(data.normativeMean + data.normativeSD)
                    .concat(Array(dates.length).fill(data.normativeMean - data.normativeSD)),
                fill: 'toself',
                fillcolor: 'rgba(30, 58, 138, 0.1)',
                line: { color: 'transparent' },
                name: '±1 SD',
                showlegend: false,
                hoverinfo: 'skip'
            });
        }
    }
    
    const layout = getPlotLayout('Submission Date', 'Score');
    const config = getPlotConfig();
    
    Plotly.newPlot(data.plotId, traces, layout, config);
}

/**
 * Initialize item-specific plots (numeric, range, Likert)
 */
function initializeItemPlot(data) {
    const plotDiv = document.getElementById(data.plotId);
    if (!plotDiv) return;
    
    const dates = data.historicalData.map(d => d.date);
    let traces = [];
    
    if (data.responseType === 'Likert') {
        // Likert scale plot with colored background
        const values = data.historicalData.map(d => d.value);
        const hoverTexts = data.historicalData.map(d => 
            `Date: ${d.submissionDate}<br>Response: ${d.value !== null ? d.value.toFixed(1) : 'Missing'}`
        );
        
        // Create background shapes for Likert options
        const shapes = [];
        if (data.likertOptions && data.likertOptions.length > 0) {
            const sortedOptions = data.likertOptions.sort((a, b) => a.value - b.value);
            const minVal = Math.min(...sortedOptions.map(o => o.value));
            const maxVal = Math.max(...sortedOptions.map(o => o.value));
            const range = maxVal - minVal;
            
            sortedOptions.forEach((option, index) => {
                const intensity = data.direction === 'Higher is Better' 
                    ? (option.value - minVal) / range
                    : (maxVal - option.value) / range;
                
                const color = getViridisColor(intensity);
                
                shapes.push({
                    type: 'rect',
                    xref: 'paper',
                    yref: 'y',
                    x0: 0,
                    x1: 1,
                    y0: option.value - 0.25,
                    y1: option.value + 0.25,
                    fillcolor: color,
                    opacity: 0.3,
                    line: { width: 0 }
                });
            });
        }
        
        traces.push({
            x: dates,
            y: values,
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#000000', width: 3 },
            marker: { 
                color: '#000000', 
                size: 8,
                symbol: values.map(v => v === null ? 'x' : 'circle')
            },
            name: data.itemName,
            hovertemplate: '%{text}<extra></extra>',
            text: hoverTexts,
            connectgaps: false
        });
        
        const layout = getPlotLayout('Submission Date', 'Response Value', shapes);
        const config = getPlotConfig();
        
        Plotly.newPlot(data.plotId, traces, layout, config);
        
    } else {
        // Numeric/Range plot
        const values = data.historicalData.map(d => d.value);
        const hoverTexts = data.historicalData.map(d => 
            `Date: ${d.submissionDate}<br>Value: ${d.value !== null ? d.value.toFixed(1) : 'Missing'}`
        );
        
        traces.push({
            x: dates,
            y: values,
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#000000', width: 3 },
            marker: { 
                color: '#000000', 
                size: 8,
                symbol: values.map(v => v === null ? 'x' : 'circle')
            },
            name: data.itemName,
            hovertemplate: '%{text}<extra></extra>',
            text: hoverTexts,
            connectgaps: false
        });
        
        // Add reference lines
        addReferenceLines(traces, dates, data);
        
        const layout = getPlotLayout('Submission Date', 'Value');
        const config = getPlotConfig();
        
        Plotly.newPlot(data.plotId, traces, layout, config);
    }
}

/**
 * Initialize sparkline plots for construct fieldsets
 */
function initializeSparkline(data) {
    const plotDiv = document.getElementById(data.plotId);
    if (!plotDiv) return;
    
    const dates = data.historicalData.map(d => d.date);
    const scores = data.historicalData.map(d => d.score);
    
    const trace = {
        x: dates,
        y: scores,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#3b82f6', width: 2 },
        hoverinfo: 'skip',
        connectgaps: false
    };
    
    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { l: 0, r: 0, t: 0, b: 0 },
        xaxis: { 
            visible: false,
            showgrid: false,
            zeroline: false
        },
        yaxis: { 
            visible: false,
            showgrid: false,
            zeroline: false
        },
        showlegend: false
    };
    
    const config = {
        displayModeBar: false,
        responsive: true,
        staticPlot: true
    };
    
    Plotly.newPlot(data.plotId, [trace], layout, config);
}

/**
 * Add reference lines (threshold, normative) to traces
 */
function addReferenceLines(traces, dates, data) {
    // Add threshold line
    if (data.thresholdScore !== null) {
        traces.push({
            x: dates,
            y: Array(dates.length).fill(data.thresholdScore),
            type: 'scatter',
            mode: 'lines',
            line: { color: '#f97316', width: 2, dash: 'dash' },
            name: 'Threshold',
            hovertemplate: `Threshold: ${data.thresholdScore.toFixed(1)}<extra></extra>`
        });
    }
    
    // Add normative line
    if (data.normativeMean !== null) {
        traces.push({
            x: dates,
            y: Array(dates.length).fill(data.normativeMean),
            type: 'scatter',
            mode: 'lines',
            line: { color: '#1e3a8a', width: 2, dash: 'dot' },
            name: 'Normative',
            hovertemplate: `Normative: ${data.normativeMean.toFixed(1)}<extra></extra>`
        });
        
        // Add normative band if SD available
        if (data.normativeSD !== null) {
            traces.push({
                x: dates.concat(dates.slice().reverse()),
                y: Array(dates.length).fill(data.normativeMean + data.normativeSD)
                    .concat(Array(dates.length).fill(data.normativeMean - data.normativeSD)),
                fill: 'toself',
                fillcolor: 'rgba(30, 58, 138, 0.1)',
                line: { color: 'transparent' },
                name: '±1 SD',
                showlegend: false,
                hoverinfo: 'skip'
            });
        }
    }
}

/**
 * Get standard plot layout configuration
 */
function getPlotLayout(xTitle, yTitle, shapes = []) {
    return {
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff',
        font: { family: 'Inter, system-ui, sans-serif', size: 12 },
        margin: { l: 40, r: 20, t: 40, b: 40 },
        xaxis: {
            gridcolor: '#e5e7eb',
            gridwidth: 1,
            showgrid: true,
            zeroline: false,
            title: xTitle
        },
        yaxis: {
            gridcolor: '#e5e7eb', 
            gridwidth: 1,
            showgrid: true,
            zeroline: false,
            title: yTitle
        },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1
        },
        shapes: shapes
    };
}

/**
 * Get standard plot configuration
 */
function getPlotConfig() {
    return {
        displayModeBar: true,
        modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d', 'autoScale2d'],
        displaylogo: false,
        responsive: true
    };
}

/**
 * Get viridis color for given intensity (0-1)
 */
function getViridisColor(intensity) {
    // Simplified viridis color scale
    const colors = [
        '#440154', '#482777', '#3f4a8a', '#31678e', '#26838f',
        '#1f9d8a', '#6cce5a', '#b6de2b', '#fee825'
    ];
    
    const index = Math.floor(intensity * (colors.length - 1));
    return colors[Math.min(index, colors.length - 1)];
}

/**
 * Fieldset toggle functions
 */
function toggleFieldset(constructId) {
    const content = document.getElementById(`fieldset-content-${constructId}`);
    const icon = document.querySelector(`[data-construct="${constructId}"]`);
    
    if (content && icon) {
        content.classList.toggle('hidden');
        icon.classList.toggle('rotate-180');
    }
}

function expandAllFieldsets() {
    document.querySelectorAll('.fieldset-content').forEach(content => {
        content.classList.remove('hidden');
    });
    document.querySelectorAll('.fieldset-toggle-icon').forEach(icon => {
        icon.classList.remove('rotate-180');
    });
}

function collapseAllFieldsets() {
    document.querySelectorAll('.fieldset-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.querySelectorAll('.fieldset-toggle-icon').forEach(icon => {
        icon.classList.add('rotate-180');
    });
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${
        type === 'error' ? 'bg-red-100 border border-red-400 text-red-700' :
        type === 'success' ? 'bg-green-100 border border-green-400 text-green-700' :
        'bg-blue-100 border border-blue-400 text-blue-700'
    }`;
    notification.textContent = message;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

/**
 * Print the results page
 */
function printResults() {
    window.print();
}

/**
 * Handle questionnaire filter change - update results after submission dropdown is updated
 */
function updateResultsAfterQuestionnaireFilter(selectElement) {
    const questionnaireId = selectElement.value;
    
    // Listen for the submission dropdown update to complete
    const handleSubmissionDropdownUpdate = function(evt) {
        if (evt.detail.target.id === 'submission-date') {
            // Remove this event listener since we only want it to fire once
            document.body.removeEventListener('htmx:afterSwap', handleSubmissionDropdownUpdate);
            
            // Now update the results with the filtered questionnaire
            const submissionSelect = document.getElementById('submission-date');
            const submissionCountSelect = document.getElementById('submission-count');
            
            if (submissionSelect && submissionCountSelect) {
                const submissionCount = submissionCountSelect.value;
                
                // Get the first submission date from the updated dropdown
                let submissionDate = '';
                if (submissionSelect.options.length > 0 && submissionSelect.options[0].value) {
                    submissionDate = submissionSelect.options[0].value;
                    submissionSelect.selectedIndex = 0; // Select the first option
                }
                
                // Build the URL with parameters
                const patientId = selectElement.getAttribute('hx-get').match(/patient\/([^\/]+)\//)[1];
                const url = `/promapp/hcp/patient/${patientId}/update-submission-data/`;
                const params = new URLSearchParams();
                
                if (questionnaireId) params.append('questionnaire_id', questionnaireId);
                if (submissionDate) params.append('submission_date', submissionDate);
                if (submissionCount) params.append('submission_count', submissionCount);
                
                // Make HTMX request to update results
                htmx.ajax('GET', `${url}?${params.toString()}`, {
                    target: '#results-container',
                    swap: 'innerHTML'
                });
            }
        }
    };
    
    // Add the event listener for this specific update
    document.body.addEventListener('htmx:afterSwap', handleSubmissionDropdownUpdate);
}

// Export functions for global access
window.toggleFieldset = toggleFieldset;
window.expandAllFieldsets = expandAllFieldsets;
window.collapseAllFieldsets = collapseAllFieldsets;
window.printResults = printResults; 