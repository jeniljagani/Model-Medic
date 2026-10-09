// Handle messages from the extension
window.addEventListener('message', event => {
    const message = event.data;
    switch (message.command) {
        case 'setLoading':
            setLoading(true);
            break;
        case 'renderData':
            setLoading(false);
            renderData(message.data);
            break;
        case 'error':
            setLoading(false);
            renderError(message.error);
            break;
    }
});

function setLoading(isLoading) {
    const loadingEl = document.getElementById('loading');
    const contentEl = document.getElementById('content');
    
    if (isLoading) {
        loadingEl.classList.remove('hidden');
        contentEl.classList.add('hidden');
    } else {
        loadingEl.classList.add('hidden');
        contentEl.classList.remove('hidden');
    }
}

function renderError(error) {
    const contentEl = document.getElementById('content');
    contentEl.innerHTML = `
        <div style="color: var(--severity-critical); padding: 20px;">
            <h2>Analysis Failed</h2>
            <pre style="white-space: pre-wrap; font-family: monospace;">${escapeHtml(error)}</pre>
        </div>
    `;
    contentEl.classList.remove('hidden');
}

function renderData(data) {
    // Header
    if (data.dataset && data.dataset.name) {
        document.getElementById('hdr-dataset').textContent = data.dataset.name;
    } else if (data.dataset && data.dataset.dataset_name) {
        document.getElementById('hdr-dataset').textContent = data.dataset.dataset_name;
    }

    if (data.dataset && data.dataset.target) {
        document.getElementById('hdr-target').textContent = data.dataset.target;
    } else {
        document.getElementById('hdr-target').textContent = 'target';
    }
    
    if (data.model) {
        document.getElementById('hdr-model').textContent = data.model.model_name || '-';
        document.getElementById('hdr-task').textContent = data.model.task_type || '-';
    }

    // Summary Cards
    if (data.dataset && data.dataset.health_score !== undefined) {
        document.getElementById('val-health').textContent = `${data.dataset.health_score}/100`;
    }
    
    // Performance
    let testMetricVal = '-';
    let trainMetricVal = '-';
    if (data.model && data.model.task_type === 'regression') {
        document.getElementById('lbl-test-metric').textContent = 'Test R²';
        document.getElementById('lbl-train-metric').textContent = 'Train R²';
        if (data.performance?.test_metrics?.r2 !== undefined) testMetricVal = data.performance.test_metrics.r2.toFixed(4);
        if (data.performance?.train_metrics?.r2 !== undefined) trainMetricVal = data.performance.train_metrics.r2.toFixed(4);
    } else {
        document.getElementById('lbl-test-metric').textContent = 'Test F1';
        document.getElementById('lbl-train-metric').textContent = 'Train F1';
        if (data.performance?.test_metrics?.f1 !== undefined) testMetricVal = data.performance.test_metrics.f1.toFixed(4);
        if (data.performance?.train_metrics?.f1 !== undefined) trainMetricVal = data.performance.train_metrics.f1.toFixed(4);
    }
    document.getElementById('val-test-metric').textContent = testMetricVal;
    document.getElementById('val-train-metric').textContent = trainMetricVal;

    if (data.findings) {
        document.getElementById('val-issues').textContent = data.findings.length;
    }

    // Diagnosis
    renderDiagnosis(data.findings || []);

    // Feature Diagnostics
    if (data.feature_diagnostics && data.feature_diagnostics.features) {
        renderFeatureDiagnostics(data.feature_diagnostics.features);
    }

    // Dataset Profile
    if (data.dataset) {
        renderDatasetProfile(data.dataset);
    }

    // Model Stability
    if (data.performance && data.performance.train_metrics && data.performance.test_metrics) {
        renderModelStability(data.performance, data.model?.task_type, data.findings || []);
    }

    // Recommendations
    renderRecommendations(data.recommendations || []);

    // Visualizations
    if (data.plots) {
        document.getElementById('visualizations-section').style.display = 'block';
        renderVisualizations(data.plots, data.model ? data.model.task_type : null);
    } else {
        document.getElementById('visualizations-section').style.display = 'none';
    }
}

function renderDiagnosis(findings) {
    const priorityContainer = document.getElementById('priority-findings-container');
    const deepContainer = document.getElementById('deep-diagnostics-container');
    priorityContainer.innerHTML = '';
    deepContainer.innerHTML = '';
    
    let high = 0;
    let med = 0;
    let low = 0;

    findings.forEach((finding, index) => {
        if (finding.severity === 'CRITICAL' || finding.severity === 'HIGH') high++;
        else if (finding.severity === 'MEDIUM') med++;
        else low++;

        const severityClass = `severity-${finding.severity}`;
        const card = document.createElement('div');
        card.className = `diag-card ${severityClass}`;
        
        // Use a slug of the problem as the ID for linking
        const problemSlug = (finding.problem || '').toLowerCase().replace(/[^a-z0-9]+/g, '-');
        card.id = `finding-${problemSlug}-${index}`;
        
        let evidenceHtml = '';
        if (finding.evidence && Object.keys(finding.evidence).length > 0) {
            const formatted = formatEvidence(finding);
            evidenceHtml = `
                <button class="diag-evidence-btn" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block'">View Evidence</button>
                <div class="diag-evidence-content" id="evidence-${problemSlug}-${index}">
                    ${formatted}
                </div>
            `;
        } else if (finding.explanation || (finding.recommendations && finding.recommendations.length > 0)) {
            // Even without numerical evidence, show explanation/actions if available
            const formatted = formatEvidence(finding);
            evidenceHtml = `
                <button class="diag-evidence-btn" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block'">View Details</button>
                <div class="diag-evidence-content" id="evidence-${problemSlug}-${index}">
                    ${formatted}
                </div>
            `;
        }

        card.innerHTML = `
            <div class="diag-header">
                <span class="severity-indicator"></span>
                <span>${escapeHtml(finding.problem)}</span>
            </div>
            <div class="diag-confidence">Confidence: ${(finding.confidence * 100).toFixed(0)}%</div>
            ${evidenceHtml}
        `;
        
        if (finding.severity === 'CRITICAL' || finding.severity === 'HIGH') {
            priorityContainer.appendChild(card);
        } else {
            deepContainer.appendChild(card);
        }
    });

    document.getElementById('val-high-issues').textContent = high;
    document.getElementById('val-medium-issues').textContent = med;
    document.getElementById('val-low-issues').textContent = low;
    document.getElementById('val-total-issues').textContent = findings.length;

    if (high > 0) {
        document.getElementById('priority-findings-section').style.display = 'block';
    } else {
        document.getElementById('priority-findings-section').style.display = 'none';
    }
}

function renderFeatureDiagnostics(features) {
    const tbody = document.getElementById('feature-diagnostics-body');
    tbody.innerHTML = '';
    
    features.forEach(f => {
        let badgeClass = 'severity-INFO';
        if (f.status.includes('Dominant') || f.status.includes('Identifier') || f.status.includes('Leakage')) {
            badgeClass = 'severity-CRITICAL';
        } else if (f.status.includes('High') || f.status.includes('Warning')) {
            badgeClass = 'severity-MEDIUM';
        }
        
        let displayStatus = f.status;
        if (badgeClass === 'severity-CRITICAL') displayStatus = `🚨 ${f.status}`;
        else if (badgeClass === 'severity-MEDIUM') displayStatus = `⚠️ ${f.status}`;
        else displayStatus = `✓ ${f.status}`;
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(f.name)}</td>
            <td>${(f.normalized_importance * 100).toFixed(1)}%</td>
            <td><span class="status-badge ${badgeClass}" style="color: var(--${badgeClass === 'severity-CRITICAL' ? 'severity-critical' : (badgeClass === 'severity-MEDIUM' ? 'severity-medium' : 'text-muted')})">${escapeHtml(displayStatus)}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderDatasetProfile(dataset) {
    const tbody = document.getElementById('profile-table-body');
    tbody.innerHTML = '';

    const addRow = (label, value) => {
        if (value === undefined || value === null || value === '') return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <th>${escapeHtml(label)}</th>
            <td>${value}</td>
        `;
        tbody.appendChild(tr);
    };

    addRow('Rows', dataset.rows);
    addRow('Columns', dataset.columns);
    
    if (dataset.missing_values && typeof dataset.missing_values === 'object') {
        addRow('Missing Cells', dataset.missing_values.total || 0);
    }
    
    if (dataset.duplicates && typeof dataset.duplicates === 'object') {
        addRow('Duplicate Rows', dataset.duplicates.count || 0);
    }

    if (dataset.high_cardinality && dataset.high_cardinality.length > 0) {
        addRow('High-cardinality features', dataset.high_cardinality.map(f => `<span class="feature-tag">${escapeHtml(f)}</span>`).join(' '));
    }
    
    if (dataset.suspicious_dtypes && dataset.suspicious_dtypes.length > 0) {
        addRow('Suspicious dtypes', dataset.suspicious_dtypes.map(f => `<span class="feature-tag">${escapeHtml(f.column)}</span>`).join(' '));
    }
    
    if (dataset.target_derived_names && dataset.target_derived_names.length > 0) {
        addRow('Target-derived features', dataset.target_derived_names.map(f => `<span class="feature-tag">${escapeHtml(f)}</span>`).join(' '));
    }
}

function renderModelStability(performance, taskType, findings) {
    const section = document.getElementById('model-stability-section');
    const tbody = document.getElementById('model-stability-body');
    tbody.innerHTML = '';

    const addRow = (label, value) => {
        if (value === undefined) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <th>${escapeHtml(label)}</th>
            <td>${escapeHtml(String(value))}</td>
        `;
        tbody.appendChild(tr);
    };

    const metric = taskType === 'classification' ? 'f1' : 'r2';
    
    let hasStability = false;
    if (performance.train_metrics && performance.test_metrics) {
        const trMetric = performance.train_metrics[metric];
        const teMetric = performance.test_metrics[metric];
        if (trMetric !== undefined && teMetric !== undefined) {
            addRow('Train Performance', trMetric.toFixed(4));
            addRow('Test Performance', teMetric.toFixed(4));
            addRow('Train/Test Gap', (trMetric - teMetric).toFixed(4));
            hasStability = true;
        }
    }
    
    const overfit = findings.find(f => f.problem === 'OVERFITTING' && f.evidence && f.evidence.cv_std !== undefined);
    if (overfit) {
        addRow('CV Std', overfit.evidence.cv_std.toFixed(4));
        addRow('Status', '⚠️ UNSTABLE (Overfitting)');
        hasStability = true;
    } else {
        const good = findings.find(f => f.problem === 'GOOD GENERALIZATION');
        if (good) {
            addRow('Status', '✓ STABLE');
            hasStability = true;
        }
    }

    if (hasStability) {
        section.style.display = 'block';
    } else {
        section.style.display = 'none';
    }
}

function renderRecommendations(recs) {
    const container = document.getElementById('recommendations-container');
    container.innerHTML = '';

    recs.forEach(rec => {
        const severityClass = `severity-${rec.priority}`;
        const card = document.createElement('div');
        card.className = `rec-card ${severityClass}`;
        
        let priorityIndicator = 'INFO';
        if (rec.priority === 'CRITICAL' || rec.priority === 'HIGH') priorityIndicator = '🚨 HIGH';
        else if (rec.priority === 'MEDIUM') priorityIndicator = '⚠️ MEDIUM';
        else if (rec.priority === 'LOW') priorityIndicator = '⚠️ LOW';

        let linkHtml = '';
        if (rec.related_problems && rec.related_problems.length > 0) {
            // Find the first related problem ID that exists
            const targetSlug = rec.related_problems[0].toLowerCase().replace(/[^a-z0-9]+/g, '-');
            linkHtml = `<div class="rec-evidence-link" onclick="scrollToFinding('${targetSlug}')">View related evidence</div>`;
        }

        card.innerHTML = `
            <div class="rec-header">
                <span class="severity-indicator"></span>
                <span>${priorityIndicator}</span>
            </div>
            <div style="font-weight: bold; margin-bottom: 10px;">${escapeHtml(rec.title)}</div>
            <div class="rec-reason">Why: ${escapeHtml(rec.reason)}</div>
            ${linkHtml}
        `;
        container.appendChild(card);
    });
}

function renderVisualizations(plots, taskType) {
    const container = document.getElementById('visualizations-container');
    container.innerHTML = '';
    
    const plotDefinitions = [];
    
    if (taskType === 'classification') {
        plotDefinitions.push({ key: 'feature_importance', title: 'Feature Importance' });
        plotDefinitions.push({ key: 'confusion_matrix', title: 'Confusion Matrix' });
        plotDefinitions.push({ key: 'roc_curve', title: 'ROC Curve' });
        plotDefinitions.push({ key: 'correlation_heatmap', title: 'Correlation Heatmap' });
    } else if (taskType === 'regression') {
        plotDefinitions.push({ key: 'feature_importance', title: 'Feature Importance' });
        plotDefinitions.push({ key: 'correlation_heatmap', title: 'Correlation Heatmap' });
        plotDefinitions.push({ key: 'actual_vs_predicted', title: 'Actual vs Predicted' });
    } else {
        plotDefinitions.push({ key: 'feature_importance', title: 'Feature Importance' });
        plotDefinitions.push({ key: 'correlation_heatmap', title: 'Correlation Heatmap' });
    }

    plotDefinitions.forEach(def => {
        const card = document.createElement('div');
        card.className = 'plot-card';
        
        let contentHtml = '';
        if (plots && plots[def.key]) {
            const plotSrc = normalizePlotSrc(plots[def.key]);
            contentHtml = `<img src="${plotSrc}" class="plot-image" alt="${def.title}" onerror="this.onerror=null; this.outerHTML='<div class=\\'plot-unavailable\\'>Visualization unavailable</div>';">`;
        } else {
            contentHtml = `<div class="plot-unavailable">${def.title} unavailable for this dataset.</div>`;
        }

        card.innerHTML = `
            <h3>${def.title}</h3>
            ${contentHtml}
        `;
        container.appendChild(card);
    });
}

// Collapsible logic
document.getElementById('dataset-profile-header').addEventListener('click', function() {
    this.parentElement.classList.toggle('collapsed');
});

function normalizePlotSrc(value) {
    if (typeof value !== 'string') return '';
    if (value.startsWith('data:image/')) {
        return value;
    }
    return `data:image/png;base64,${value}`;
}

// Utility
function escapeHtml(unsafe) {
    return (unsafe || '').toString()
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Phase 5: Formatting specific evidence
function formatEvidence(finding) {
    let evidenceHtml = '';
    const ev = finding.evidence || {};
    
    // Convert a number to a pretty percentage
    const toPct = val => val !== undefined ? (val * 100).toFixed(1) + '%' : '-';
    
    if (Object.keys(ev).length > 0) {
        evidenceHtml += '<table class="diag-evidence-table"><tbody>';
        
        const addRow = (k, v) => {
            evidenceHtml += `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v)}</td></tr>`;
        };
        
        if (finding.problem === 'FEATURE DOMINANCE') {
            addRow('Top Feature', ev.top_feature);
            addRow('Importance', toPct(ev.importance_percentage / 100)); // already a percentage
            addRow('Total Importance', toPct(ev.total_importance));
            addRow('Dominance Threshold', toPct(ev.dominance_threshold));
        } else if (finding.problem === 'IDENTIFIER-LIKE FEATURE') {
            addRow('Feature', ev.feature);
            addRow('Importance', toPct(ev.importance));
            if (ev.uniqueness_ratio !== undefined) {
                addRow('Uniqueness', toPct(ev.uniqueness_ratio));
            }
            addRow('Pattern', ev.is_id_name ? 'identifier-like name' : 'near-unique values');
        } else if (finding.problem === 'FEATURE REDUNDANCY') {
            addRow('Redundant Features', (ev.features || []).join(', '));
            addRow('Correlation', (ev.correlation || 0).toFixed(3));
            addRow('Correlation Threshold', ev.correlation_threshold || '0.90');
        } else if (finding.problem === 'DISTRIBUTION SHIFT') {
            addRow('Feature', ev.feature);
            addRow('KS Statistic', (ev.ks_stat || 0).toFixed(3));
        } else if (finding.problem === 'OVERFITTING' || finding.problem === 'UNDERFITTING' || finding.problem === 'GOOD GENERALIZATION') {
            if (ev.train_f1 !== undefined) addRow('Train F1', ev.train_f1.toFixed(4));
            if (ev.test_f1 !== undefined) addRow('Test F1', ev.test_f1.toFixed(4));
            if (ev.train_rmse !== undefined) addRow('Train RMSE', ev.train_rmse.toFixed(4));
            if (ev.test_rmse !== undefined) addRow('Test RMSE', ev.test_rmse.toFixed(4));
            if (ev.gap !== undefined) addRow('Train/Test Gap', ev.gap.toFixed(4));
            if (ev.cv_std !== undefined) addRow('CV Std', ev.cv_std.toFixed(4));
        } else if (finding.problem.includes('LEAKAGE')) {
            if (ev.feature) addRow('Feature', ev.feature);
            if (ev.overlap_pct !== undefined) addRow('Overlap', toPct(ev.overlap_pct));
            if (ev.metric) addRow('Suspicious Metric', `${ev.metric} = ${ev.value}`);
        } else if (finding.problem.includes('CLASS IMBALANCE')) {
            if (ev.minority_class !== undefined) addRow('Minority Class', ev.minority_class);
            if (ev.class_percentage !== undefined) {
                addRow('Minority Class %', toPct(ev.class_percentage / 100));
                addRow('Majority Class %', toPct((100 - ev.class_percentage) / 100));
            }
            if (ev.minority_recall !== undefined) addRow('Minority Recall', ev.minority_recall.toFixed(4));
            if (ev.minority_f1 !== undefined) addRow('Minority F1', ev.minority_f1.toFixed(4));
        } else {
            // Fallback
            for (const [k, v] of Object.entries(ev)) {
                if (typeof v === 'object') {
                    addRow(k, JSON.stringify(v));
                } else {
                    addRow(k, v);
                }
            }
        }
        
        evidenceHtml += '</tbody></table>';
    }
    
    let explainHtml = '';
    if (finding.explanation) {
        explainHtml += `
            <div class="diag-explanation">
                <strong>Why this matters:</strong> ${escapeHtml(finding.explanation)}
            </div>
        `;
    }
    
    let actionHtml = '';
    if (finding.recommendations && finding.recommendations.length > 0) {
        actionHtml += `
            <div class="diag-action-section">
                <strong>What should I do?</strong>
                <ul class="diag-action-list">
                    ${finding.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    return explainHtml + evidenceHtml + actionHtml;
}

function scrollToFinding(problemSlug) {
    // Find any card that starts with the slug (since we appended index)
    const cards = document.querySelectorAll('.diag-card');
    for (let i = 0; i < cards.length; i++) {
        if (cards[i].id && cards[i].id.startsWith(`finding-${problemSlug}`)) {
            // Scroll to it
            cards[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Expand the evidence
            const btn = cards[i].querySelector('.diag-evidence-btn');
            const content = cards[i].querySelector('.diag-evidence-content');
            if (btn && content && content.style.display !== 'block') {
                content.style.display = 'block';
            }
            
            // Highlight briefly
            cards[i].style.transition = 'background-color 0.5s';
            const oldBg = cards[i].style.backgroundColor;
            cards[i].style.backgroundColor = 'rgba(255, 255, 0, 0.1)';
            setTimeout(() => {
                cards[i].style.backgroundColor = oldBg;
            }, 1500);
            
            break;
        }
    }
}
