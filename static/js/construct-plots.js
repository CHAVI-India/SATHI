function initializeConstructPlot(plotId, plotData) {
    const layout = {
        margin: { t: 0, r: 0, b: 0, l: 0 },
        showlegend: false,
        hovermode: 'x unified',
        xaxis: { showgrid: false, showticklabels: false },
        yaxis: { showgrid: true, gridcolor: '#e5e7eb' },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
    };

    // Add threshold line if available
    if (plotData.threshold) {
        layout.shapes = [{
            type: 'line',
            x0: 0,
            x1: 1,
            y0: plotData.threshold,
            y1: plotData.threshold,
            line: {
                color: '#f97316',
                width: 1,
                dash: 'dash'
            }
        }];
    }

    // Add normative score line if available
    if (plotData.normative) {
        layout.shapes = layout.shapes || [];
        layout.shapes.push({
            type: 'line',
            x0: 0,
            x1: 1,
            y0: plotData.normative,
            y1: plotData.normative,
            line: {
                color: '#1e3a8a',
                width: 1,
                dash: 'dash'
            }
        });

        // Add standard deviation band if available
        if (plotData.normative_sd) {
            layout.shapes.push({
                type: 'rect',
                x0: 0,
                x1: 1,
                y0: plotData.normative - plotData.normative_sd,
                y1: plotData.normative + plotData.normative_sd,
                fillcolor: '#1e3a8a',
                opacity: 0.1,
                line: { width: 0 }
            });
        }
    }

    Plotly.newPlot(plotId, [{
        x: plotData.dates,
        y: plotData.scores,
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#000000', width: 2 },
        marker: { size: 6 }
    }], layout, {
        responsive: true,
        displayModeBar: false
    });
}

// Initialize all plots when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Find all plot containers
    const plotContainers = document.querySelectorAll('[id^="plot-"]');
    
    // Initialize each plot
    plotContainers.forEach(container => {
        const plotId = container.id;
        const plotData = JSON.parse(container.dataset.plotData);
        initializeConstructPlot(plotId, plotData);
    });
}); 