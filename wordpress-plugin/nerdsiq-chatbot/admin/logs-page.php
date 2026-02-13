<?php
/**
 * NerdsIQ Daily Logs Admin Page
 * 
 * @package NerdsIQ_Chatbot
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}
?>

<div class="wrap">
    <h1>
        📋 NerdsIQ Daily Logs
        <button id="refresh-logs" class="page-title-action">Refresh</button>
        <button id="test-email" class="page-title-action">Test Email</button>
    </h1>
    
    <div id="log-loading" class="notice notice-info" style="display: none;">
        <p>⏳ Loading logs...</p>
    </div>
    
    <div id="log-error" class="notice notice-error" style="display: none;">
        <p id="log-error-message"></p>
    </div>
    
    <div id="log-success" class="notice notice-success" style="display: none;">
        <p id="log-success-message"></p>
    </div>
    
    <div class="nerdsiq-logs-container">
        
        <!-- Date Selector -->
        <div class="card" style="margin-bottom: 20px;">
            <h3>📅 Select Date</h3>
            <div class="log-date-selector">
                <select id="log-date-select" style="width: 200px; margin-right: 10px;">
                    <option value="">Select a date...</option>
                </select>
                <button id="load-daily-log" class="button button-primary">View Daily Log</button>
                <button id="load-weekly-report" class="button button-secondary" style="margin-left: 10px;">Weekly Report</button>
            </div>
        </div>
        
        <!-- Quick Stats -->
        <div id="quick-stats" class="card" style="margin-bottom: 20px; display: none;">
            <h3>📊 Quick Stats</h3>
            <div id="stats-content"></div>
        </div>
        
        <!-- Log Content -->
        <div id="log-content" class="card" style="display: none;">
            <div id="log-header">
                <h3 id="log-title">📝 Log Details</h3>
            </div>
            <div id="log-body">
                <div id="log-summary"></div>
                <div id="log-details"></div>
                <div id="log-errors"></div>
            </div>
        </div>
        
        <!-- Weekly Report -->
        <div id="weekly-report" class="card" style="display: none;">
            <h3>📊 Weekly Report</h3>
            <div id="weekly-content"></div>
        </div>
    </div>
</div>

<style>
.nerdsiq-logs-container .card {
    background: #fff;
    border: 1px solid #c3c4c7;
    border-radius: 4px;
    padding: 20px;
    box-shadow: 0 1px 1px rgba(0,0,0,.04);
}

.log-date-selector {
    display: flex;
    align-items: center;
    margin-top: 10px;
}

#log-body {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid #ddd;
    padding: 15px;
    background-color: #f9f9f9;
    border-radius: 4px;
}

.log-section {
    margin-bottom: 20px;
    padding: 15px;
    border-left: 4px solid #0073aa;
    background-color: #fff;
}

.log-section h4 {
    margin: 0 0 10px 0;
    color: #0073aa;
}

.log-errors {
    border-left-color: #d63638;
}

.log-errors h4 {
    color: #d63638;
}

.error-list {
    max-height: 200px;
    overflow-y: auto;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 3px;
    padding: 10px;
}

.error-item {
    padding: 8px;
    margin-bottom: 5px;
    background: #fff2f2;
    border: 1px solid #f8d7da;
    border-radius: 3px;
    font-size: 13px;
}

.error-timestamp {
    font-weight: bold;
    color: #721c24;
    margin-right: 10px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 15px 0;
}

.stat-item {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 6px;
    border: 1px solid #dee2e6;
    text-align: center;
}

.stat-number {
    font-size: 24px;
    font-weight: bold;
    color: #0073aa;
    display: block;
}

.stat-label {
    font-size: 14px;
    color: #666;
    margin-top: 5px;
}

.status-success { color: #00a32a; }
.status-warning { color: #dba617; }
.status-error { color: #d63638; }

.weekly-day {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    margin: 5px 0;
    background: #f8f9fa;
    border-radius: 4px;
    border-left: 4px solid #0073aa;
}

.weekly-day.has-errors {
    border-left-color: #d63638;
}

.weekly-day.no-activity {
    border-left-color: #ddd;
    opacity: 0.7;
}

.weekly-totals {
    background: #e7f3ff;
    padding: 15px;
    border-radius: 6px;
    margin-top: 20px;
    border: 2px solid #0073aa;
}

.weekly-totals h4 {
    margin: 0 0 10px 0;
    color: #0073aa;
}

.loading-spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #0073aa;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-right: 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>

<script>
jQuery(document).ready(function($) {
    let logDates = [];
    
    // Load available log dates on page load
    loadLogDates();
    
    // Event handlers
    $('#refresh-logs').on('click', loadLogDates);
    $('#load-daily-log').on('click', loadDailyLog);
    $('#load-weekly-report').on('click', loadWeeklyReport);
    $('#test-email').on('click', testEmailNotification);
    
    function showLoading() {
        $('#log-loading').show();
        $('#log-error').hide();
        $('#log-success').hide();
    }
    
    function hideLoading() {
        $('#log-loading').hide();
    }
    
    function showError(message) {
        hideLoading();
        $('#log-error-message').text(message);
        $('#log-error').show();
        $('#log-success').hide();
    }
    
    function showSuccess(message) {
        hideLoading();
        $('#log-success-message').text(message);
        $('#log-success').show();
        $('#log-error').hide();
    }
    
    function loadLogDates() {
        showLoading();
        
        $.post(ajaxurl, {
            action: 'nerdsiq_get_log_dates',
            nonce: '<?php echo wp_create_nonce('nerdsiq_nonce'); ?>'
        })
        .done(function(response) {
            hideLoading();
            
            if (response.success) {
                logDates = response.data.dates || [];
                populateDateSelect();
                showSuccess('Log dates loaded successfully');
            } else {
                showError(response.data.message || 'Failed to load log dates');
            }
        })
        .fail(function() {
            showError('Network error while loading log dates');
        });
    }
    
    function populateDateSelect() {
        const select = $('#log-date-select');
        select.empty();
        select.append('<option value="">Select a date...</option>');
        
        // Sort dates in descending order (newest first)
        logDates.sort().reverse();
        
        logDates.forEach(function(date) {
            select.append(`<option value="${date}">${date}</option>`);
        });
        
        // Show today's date by default if available
        const today = new Date().toISOString().split('T')[0];
        if (logDates.includes(today)) {
            select.val(today);
        } else if (logDates.length > 0) {
            select.val(logDates[0]);
        }
    }
    
    function loadDailyLog() {
        const selectedDate = $('#log-date-select').val();
        
        if (!selectedDate) {
            showError('Please select a date first');
            return;
        }
        
        showLoading();
        $('#log-content').hide();
        $('#weekly-report').hide();
        
        $.post(ajaxurl, {
            action: 'nerdsiq_get_daily_log',
            nonce: '<?php echo wp_create_nonce('nerdsiq_nonce'); ?>',
            date: selectedDate
        })
        .done(function(response) {
            hideLoading();
            
            if (response.success) {
                displayDailyLog(response.data, selectedDate);
                showSuccess('Daily log loaded successfully');
            } else {
                showError(response.data.message || 'Failed to load daily log');
            }
        })
        .fail(function() {
            showError('Network error while loading daily log');
        });
    }
    
    function displayDailyLog(data, date) {
        $('#log-title').text(`📝 Daily Log - ${date}`);
        
        // Clear previous content
        $('#log-summary, #log-details, #log-errors, #stats-content').empty();
        
        // Quick stats
        if (data.status) {
            const stats = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-number">${data.status.total_files_processed || 0}</span>
                        <div class="stat-label">Files Processed</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number status-success">${data.status.successful_files || 0}</span>
                        <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number status-error">${data.status.failed_files || 0}</span>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">${(data.status.total_chunks_added || 0).toLocaleString()}</span>
                        <div class="stat-label">Chunks Added</div>
                    </div>
                </div>
            `;
            $('#stats-content').html(stats);
            $('#quick-stats').show();
        }
        
        // Summary
        if (data.status && data.status.summary) {
            $('#log-summary').html(`
                <div class="log-section">
                    <h4>📊 Summary</h4>
                    <p>${data.status.summary}</p>
                </div>
            `);
        }
        
        // Processing details
        if (data.status) {
            const details = `
                <div class="log-section">
                    <h4>🔍 Processing Details</h4>
                    <ul>
                        <li><strong>Start Time:</strong> ${data.status.start_time || 'Unknown'}</li>
                        <li><strong>End Time:</strong> ${data.status.end_time || 'Unknown'}</li>
                        <li><strong>Processing Time:</strong> ${data.status.processing_time || 'Unknown'}</li>
                        <li><strong>Success Rate:</strong> ${calculateSuccessRate(data.status)}%</li>
                    </ul>
                </div>
            `;
            $('#log-details').html(details);
        }
        
        // Errors
        if (data.status && data.status.errors && data.status.errors.length > 0) {
            let errorsHtml = `
                <div class="log-section log-errors">
                    <h4>⚠️ Errors (${data.status.errors.length} total)</h4>
                    <div class="error-list">
            `;
            
            data.status.errors.slice(0, 20).forEach(function(error) {
                errorsHtml += `
                    <div class="error-item">
                        <span class="error-timestamp">${error.timestamp || 'Unknown'}</span>
                        <span class="error-message">${error.message || 'Unknown error'}</span>
                    </div>
                `;
            });
            
            if (data.status.errors.length > 20) {
                errorsHtml += `<p><em>... and ${data.status.errors.length - 20} more errors</em></p>`;
            }
            
            errorsHtml += '</div></div>';
            $('#log-errors').html(errorsHtml);
        }
        
        $('#log-content').show();
    }
    
    function calculateSuccessRate(status) {
        const total = status.total_files_processed || 0;
        const successful = status.successful_files || 0;
        
        if (total === 0) return 0;
        return Math.round((successful / total) * 100);
    }
    
    function loadWeeklyReport() {
        const endDate = $('#log-date-select').val();
        
        showLoading();
        $('#log-content').hide();
        $('#weekly-report').hide();
        
        $.post(ajaxurl, {
            action: 'nerdsiq_get_weekly_report',
            nonce: '<?php echo wp_create_nonce('nerdsiq_nonce'); ?>',
            end_date: endDate
        })
        .done(function(response) {
            hideLoading();
            
            if (response.success) {
                displayWeeklyReport(response.data);
                showSuccess('Weekly report loaded successfully');
            } else {
                showError(response.data.message || 'Failed to load weekly report');
            }
        })
        .fail(function() {
            showError('Network error while loading weekly report');
        });
    }
    
    function displayWeeklyReport(data) {
        let reportHtml = '';
        
        if (data.daily_reports && data.daily_reports.length > 0) {
            reportHtml += '<div class="weekly-days">';
            
            data.daily_reports.forEach(function(day) {
                const hasErrors = day.failed_files && day.failed_files > 0;
                const hasActivity = day.total_files_processed && day.total_files_processed > 0;
                const successRate = calculateSuccessRate(day);
                
                let dayClass = 'weekly-day';
                if (!hasActivity) {
                    dayClass += ' no-activity';
                } else if (hasErrors) {
                    dayClass += ' has-errors';
                }
                
                const statusIcon = hasActivity ? (hasErrors ? '⚠️' : '✅') : '⭕';
                
                reportHtml += `
                    <div class="${dayClass}">
                        <div>
                            <strong>${day.date}</strong>
                            ${hasActivity ? `- ${day.successful_files || 0} files, ${(day.total_chunks_added || 0).toLocaleString()} chunks` : '- No activity'}
                        </div>
                        <div>
                            ${statusIcon} ${hasActivity ? `${successRate}% success` : ''}
                        </div>
                    </div>
                `;
            });
            
            reportHtml += '</div>';
        }
        
        // Weekly totals
        if (data.totals) {
            reportHtml += `
                <div class="weekly-totals">
                    <h4>📊 Weekly Totals</h4>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-number">${data.totals.days_with_activity || 0}/7</span>
                            <div class="stat-label">Days Active</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">${(data.totals.total_files || 0).toLocaleString()}</span>
                            <div class="stat-label">Total Files</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number status-success">${(data.totals.successful_files || 0).toLocaleString()}</span>
                            <div class="stat-label">Successful</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number status-error">${(data.totals.failed_files || 0).toLocaleString()}</span>
                            <div class="stat-label">Failed</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">${(data.totals.total_chunks || 0).toLocaleString()}</span>
                            <div class="stat-label">Total Chunks</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">${calculateSuccessRate(data.totals)}%</span>
                            <div class="stat-label">Success Rate</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        $('#weekly-content').html(reportHtml);
        $('#weekly-report').show();
    }
    
    function testEmailNotification() {
        if (!confirm('Send a test email notification? This will send an email to all configured recipients.')) {
            return;
        }
        
        showLoading();
        
        $.post(ajaxurl, {
            action: 'nerdsiq_test_email',
            nonce: '<?php echo wp_create_nonce('nerdsiq_nonce'); ?>'
        })
        .done(function(response) {
            hideLoading();
            
            if (response.success) {
                showSuccess('Test email sent successfully! Check your inbox.');
            } else {
                showError(response.data.message || 'Failed to send test email');
            }
        })
        .fail(function() {
            showError('Network error while sending test email');
        });
    }
});
</script>