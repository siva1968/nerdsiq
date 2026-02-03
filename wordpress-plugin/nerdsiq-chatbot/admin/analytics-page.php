<?php
/**
 * Analytics Dashboard Page
 */

if (!defined('ABSPATH')) {
    exit;
}
?>

<div class="wrap nerdsiq-analytics">
    <h1>NerdsIQ Analytics</h1>
    
    <div class="nerdsiq-analytics-header">
        <div class="nerdsiq-period-selector">
            <label for="nerdsiq-period">Time Period:</label>
            <select id="nerdsiq-period">
                <option value="7">Last 7 days</option>
                <option value="30" selected>Last 30 days</option>
                <option value="90">Last 90 days</option>
                <option value="365">Last year</option>
            </select>
            <button type="button" id="nerdsiq-refresh" class="button button-secondary">
                <span class="dashicons dashicons-update"></span> Refresh
            </button>
        </div>
    </div>
    
    <!-- Stats Cards -->
    <div class="nerdsiq-stats-grid">
        <div class="nerdsiq-stat-card">
            <div class="nerdsiq-stat-icon queries">
                <span class="dashicons dashicons-format-chat"></span>
            </div>
            <div class="nerdsiq-stat-content">
                <h3 id="stat-total-queries">-</h3>
                <p>Total Queries</p>
            </div>
        </div>
        
        <div class="nerdsiq-stat-card">
            <div class="nerdsiq-stat-icon users">
                <span class="dashicons dashicons-groups"></span>
            </div>
            <div class="nerdsiq-stat-content">
                <h3 id="stat-unique-users">-</h3>
                <p>Active Users</p>
            </div>
        </div>
        
        <div class="nerdsiq-stat-card">
            <div class="nerdsiq-stat-icon time">
                <span class="dashicons dashicons-clock"></span>
            </div>
            <div class="nerdsiq-stat-content">
                <h3 id="stat-avg-response">-</h3>
                <p>Avg Response Time</p>
            </div>
        </div>
        
        <div class="nerdsiq-stat-card">
            <div class="nerdsiq-stat-icon success">
                <span class="dashicons dashicons-yes-alt"></span>
            </div>
            <div class="nerdsiq-stat-content">
                <h3 id="stat-success-rate">-</h3>
                <p>Success Rate</p>
            </div>
        </div>
        
        <div class="nerdsiq-stat-card">
            <div class="nerdsiq-stat-icon cache">
                <span class="dashicons dashicons-database"></span>
            </div>
            <div class="nerdsiq-stat-content">
                <h3 id="stat-cache-rate">-</h3>
                <p>Cache Hit Rate</p>
            </div>
        </div>
        
        <div class="nerdsiq-stat-card">
            <div class="nerdsiq-stat-icon sessions">
                <span class="dashicons dashicons-admin-comments"></span>
            </div>
            <div class="nerdsiq-stat-content">
                <h3 id="stat-total-sessions">-</h3>
                <p>Total Sessions</p>
            </div>
        </div>
    </div>
    
    <!-- Charts Row -->
    <div class="nerdsiq-charts-row">
        <div class="nerdsiq-chart-card">
            <h3>Queries Over Time</h3>
            <div class="nerdsiq-chart-container">
                <canvas id="queries-chart"></canvas>
            </div>
        </div>
        
        <div class="nerdsiq-chart-card">
            <h3>Usage by Hour</h3>
            <div class="nerdsiq-chart-container">
                <canvas id="hourly-chart"></canvas>
            </div>
        </div>
    </div>
    
    <!-- Tables Row -->
    <div class="nerdsiq-tables-row">
        <div class="nerdsiq-table-card">
            <h3>Top Users</h3>
            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Queries</th>
                    </tr>
                </thead>
                <tbody id="top-users-table">
                    <tr><td colspan="2">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="nerdsiq-table-card">
            <h3>Popular Questions</h3>
            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th>Question</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody id="popular-questions-table">
                    <tr><td colspan="2">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Recent Queries -->
    <div class="nerdsiq-recent-card">
        <h3>Recent Queries</h3>
        <table class="wp-list-table widefat fixed striped">
            <thead>
                <tr>
                    <th style="width: 15%;">Time</th>
                    <th style="width: 15%;">User</th>
                    <th style="width: 50%;">Question</th>
                    <th style="width: 10%;">Response</th>
                    <th style="width: 10%;">Status</th>
                </tr>
            </thead>
            <tbody id="recent-queries-table">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</div>

<style>
.nerdsiq-analytics {
    max-width: 1400px;
}

.nerdsiq-analytics-header {
    margin: 20px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.nerdsiq-period-selector {
    display: flex;
    align-items: center;
    gap: 10px;
}

.nerdsiq-period-selector select {
    padding: 5px 10px;
}

.nerdsiq-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.nerdsiq-stat-card {
    background: #fff;
    border: 1px solid #c3c4c7;
    border-radius: 8px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 15px;
}

.nerdsiq-stat-icon {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.nerdsiq-stat-icon .dashicons {
    font-size: 24px;
    width: 24px;
    height: 24px;
    color: #fff;
}

.nerdsiq-stat-icon.queries { background: #0047AC; }
.nerdsiq-stat-icon.users { background: #2271b1; }
.nerdsiq-stat-icon.time { background: #9b59b6; }
.nerdsiq-stat-icon.success { background: #27ae60; }
.nerdsiq-stat-icon.cache { background: #f39c12; }
.nerdsiq-stat-icon.sessions { background: #e74c3c; }

.nerdsiq-stat-content h3 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
    color: #1d2327;
}

.nerdsiq-stat-content p {
    margin: 5px 0 0;
    color: #646970;
    font-size: 13px;
}

.nerdsiq-charts-row,
.nerdsiq-tables-row {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-bottom: 30px;
}

.nerdsiq-chart-card,
.nerdsiq-table-card,
.nerdsiq-recent-card {
    background: #fff;
    border: 1px solid #c3c4c7;
    border-radius: 8px;
    padding: 20px;
}

.nerdsiq-chart-card h3,
.nerdsiq-table-card h3,
.nerdsiq-recent-card h3 {
    margin: 0 0 15px;
    font-size: 16px;
    color: #1d2327;
}

.nerdsiq-chart-container {
    height: 250px;
    position: relative;
}

.nerdsiq-table-card table {
    margin: 0;
}

.nerdsiq-recent-card {
    margin-bottom: 30px;
}

@media (max-width: 1024px) {
    .nerdsiq-charts-row,
    .nerdsiq-tables-row {
        grid-template-columns: 1fr;
    }
}

/* Loading state */
.nerdsiq-loading {
    opacity: 0.5;
    pointer-events: none;
}

/* Status badges */
.nerdsiq-status {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
}

.nerdsiq-status.success {
    background: #d4edda;
    color: #155724;
}

.nerdsiq-status.error {
    background: #f8d7da;
    color: #721c24;
}

.nerdsiq-status.cached {
    background: #fff3cd;
    color: #856404;
}
</style>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
jQuery(document).ready(function($) {
    let queriesChart = null;
    let hourlyChart = null;
    
    // Use WordPress AJAX URL (proxies through PHP to avoid CORS/network issues)
    const ajaxUrl = '<?php echo esc_url(admin_url('admin-ajax.php')); ?>';
    
    function loadAnalytics() {
        const days = $('#nerdsiq-period').val();
        
        $('.nerdsiq-analytics').addClass('nerdsiq-loading');
        
        // Load overview data via WordPress AJAX proxy
        $.ajax({
            url: ajaxUrl,
            method: 'GET',
            data: {
                action: 'nerdsiq_analytics_overview',
                days: days
            }
        }).done(function(response) {
            if (response.success) {
                const data = response.data;
                updateStats(data.stats);
                updateQueriesChart(data.queries_per_day);
                updateHourlyChart(data.hourly_distribution);
                updateTopUsers(data.top_users);
                updatePopularQuestions(data.popular_questions);
            } else {
                console.error('Failed to load analytics:', response.data);
                alert('Failed to load analytics: ' + (response.data.message || 'Unknown error'));
            }
        }).fail(function(xhr) {
            console.error('Failed to load analytics:', xhr);
            alert('Failed to load analytics. Please check your connection.');
        }).always(function() {
            $('.nerdsiq-analytics').removeClass('nerdsiq-loading');
        });
        
        // Load recent queries via WordPress AJAX proxy
        $.ajax({
            url: ajaxUrl,
            method: 'GET',
            data: {
                action: 'nerdsiq_analytics_recent',
                limit: 20
            }
        }).done(function(response) {
            if (response.success) {
                updateRecentQueries(response.data);
            }
        });
    }
    
    function updateStats(stats) {
        $('#stat-total-queries').text(stats.total_queries.toLocaleString());
        $('#stat-unique-users').text(stats.unique_users.toLocaleString());
        $('#stat-avg-response').text(formatMs(stats.avg_response_time_ms));
        $('#stat-success-rate').text(stats.success_rate + '%');
        $('#stat-cache-rate').text(stats.cache_hit_rate + '%');
        $('#stat-total-sessions').text(stats.total_sessions.toLocaleString());
    }
    
    function formatMs(ms) {
        if (ms < 1000) return Math.round(ms) + 'ms';
        return (ms / 1000).toFixed(2) + 's';
    }
    
    function updateQueriesChart(data) {
        const ctx = document.getElementById('queries-chart').getContext('2d');
        
        if (queriesChart) {
            queriesChart.destroy();
        }
        
        queriesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Queries',
                    data: data.map(d => d.count),
                    borderColor: '#0047AC',
                    backgroundColor: 'rgba(0, 71, 172, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
    
    function updateHourlyChart(data) {
        const ctx = document.getElementById('hourly-chart').getContext('2d');
        
        if (hourlyChart) {
            hourlyChart.destroy();
        }
        
        hourlyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.hour + ':00'),
                datasets: [{
                    label: 'Queries',
                    data: data.map(d => d.count),
                    backgroundColor: '#FFD301',
                    borderColor: '#0047AC',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
    
    function updateTopUsers(users) {
        const tbody = $('#top-users-table');
        if (users.length === 0) {
            tbody.html('<tr><td colspan="2">No data available</td></tr>');
            return;
        }
        
        let html = '';
        users.forEach(user => {
            html += '<tr>';
            html += '<td>' + escapeHtml(user.email) + '</td>';
            html += '<td>' + user.query_count + '</td>';
            html += '</tr>';
        });
        tbody.html(html);
    }
    
    function updatePopularQuestions(questions) {
        const tbody = $('#popular-questions-table');
        if (questions.length === 0) {
            tbody.html('<tr><td colspan="2">No data available</td></tr>');
            return;
        }
        
        let html = '';
        questions.forEach(q => {
            html += '<tr>';
            html += '<td>' + escapeHtml(q.question) + '</td>';
            html += '<td>' + q.count + '</td>';
            html += '</tr>';
        });
        tbody.html(html);
    }
    
    function updateRecentQueries(queries) {
        const tbody = $('#recent-queries-table');
        if (queries.length === 0) {
            tbody.html('<tr><td colspan="5">No queries yet</td></tr>');
            return;
        }
        
        let html = '';
        queries.forEach(q => {
            const date = new Date(q.created_at);
            const timeStr = date.toLocaleString();
            
            let statusClass = 'success';
            let statusText = 'OK';
            if (q.had_error) {
                statusClass = 'error';
                statusText = 'Error';
            } else if (q.was_cached) {
                statusClass = 'cached';
                statusText = 'Cached';
            }
            
            html += '<tr>';
            html += '<td>' + timeStr + '</td>';
            html += '<td>' + escapeHtml(q.email) + '</td>';
            html += '<td>' + escapeHtml(q.question) + '</td>';
            html += '<td>' + (q.response_time_ms ? formatMs(q.response_time_ms) : '-') + '</td>';
            html += '<td><span class="nerdsiq-status ' + statusClass + '">' + statusText + '</span></td>';
            html += '</tr>';
        });
        tbody.html(html);
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Event handlers
    $('#nerdsiq-period').on('change', loadAnalytics);
    $('#nerdsiq-refresh').on('click', loadAnalytics);
    
    // Initial load
    loadAnalytics();
});
</script>
