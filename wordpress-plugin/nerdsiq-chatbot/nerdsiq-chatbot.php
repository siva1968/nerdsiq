<?php
/**
 * Plugin Name: NerdsIQ Chatbot
 * Plugin URI: https://github.com/siva1968/nerdsiq
 * Description: AI-powered knowledge assistant chatbot for NerdsToGo
 * Version: 1.0.0
 * Author: NerdsToGo
 * License: GPL v2 or later
 * Text Domain: nerdsiq-chatbot
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Plugin constants
define('NERDSIQ_VERSION', '1.3.0');
define('NERDSIQ_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('NERDSIQ_PLUGIN_URL', plugin_dir_url(__FILE__));

// Include required files
require_once NERDSIQ_PLUGIN_DIR . 'includes/class-nerdsiq-api.php';
require_once NERDSIQ_PLUGIN_DIR . 'includes/class-nerdsiq-auth.php';
require_once NERDSIQ_PLUGIN_DIR . 'includes/class-nerdsiq-widget.php';

/**
 * Main plugin class
 */
class NerdsIQ_Chatbot {
    
    private static $instance = null;
    private $api;
    private $auth;
    private $widget;
    
    /**
     * Get singleton instance
     */
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * Constructor
     */
    private function __construct() {
        $this->api = new NerdsIQ_API();
        $this->auth = new NerdsIQ_Auth($this->api);
        $this->widget = new NerdsIQ_Widget($this->api, $this->auth);
        
        // Ensure NTG role exists (for existing installs)
        add_action('init', [$this, 'ensure_ntg_role']);
        
        // Hooks
        add_action('wp_enqueue_scripts', [$this, 'enqueue_assets']);
        add_action('wp_footer', [$this, 'render_widget']);
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue_admin_assets']);
        add_action('admin_init', [$this, 'register_settings']);
        
        // AJAX handlers
        add_action('wp_ajax_nerdsiq_login', [$this->auth, 'ajax_login']);
        add_action('wp_ajax_nopriv_nerdsiq_login', [$this->auth, 'ajax_login']);
        add_action('wp_ajax_nerdsiq_query', [$this->widget, 'ajax_query']);
        add_action('wp_ajax_nopriv_nerdsiq_query', [$this->widget, 'ajax_query']);
        
        // Page access restriction - redirect non-logged users
        add_action('template_redirect', [$this, 'restrict_page_access']);
        
        // Chat history AJAX handlers
        add_action('wp_ajax_nerdsiq_get_sessions', [$this, 'ajax_get_sessions']);
        add_action('wp_ajax_nerdsiq_get_history', [$this, 'ajax_get_history']);
        
        // Admin analytics AJAX handlers (proxies API calls through WordPress)
        add_action('wp_ajax_nerdsiq_analytics_overview', [$this, 'ajax_analytics_overview']);
        add_action('wp_ajax_nerdsiq_analytics_recent', [$this, 'ajax_analytics_recent']);
        
        // Log viewer AJAX handlers
        add_action('wp_ajax_nerdsiq_get_log_dates', [$this, 'ajax_get_log_dates']);
        add_action('wp_ajax_nerdsiq_get_daily_log', [$this, 'ajax_get_daily_log']);
        add_action('wp_ajax_nerdsiq_get_weekly_report', [$this, 'ajax_get_weekly_report']);
        add_action('wp_ajax_nerdsiq_test_email', [$this, 'ajax_test_email']);
        
        // Admin test connection AJAX handler
        add_action('wp_ajax_nerdsiq_test_connection', [$this, 'ajax_test_connection']);
        
        // Document viewer AJAX handler
        add_action('wp_ajax_nerdsiq_view_document', [$this, 'ajax_view_document']);
    }
    
    /**
     * AJAX handler for testing API connection
     */
    public function ajax_test_connection() {
        // Check admin permissions
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => 'Unauthorized'], 403);
        }
        
        $response = $this->api->request('health', 'GET');
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => $response['error'] ?? 'Unknown error']);
        }
    }
    
    /**
     * AJAX handler for viewing documents
     */
    public function ajax_view_document() {
        // Check if user can use NerdsIQ
        if (!$this->current_user_can_use_nerdsiq()) {
            wp_send_json_error(['message' => 'Unauthorized'], 403);
        }
        
        // Verify nonce
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'nerdsiq_nonce')) {
            wp_send_json_error(['message' => 'Invalid nonce'], 403);
        }
        
        // Check if document viewer is enabled
        if (get_option('nerdsiq_enable_document_viewer', '0') !== '1') {
            wp_send_json_error(['message' => 'Document viewer is disabled'], 403);
        }
        
        $document_url = isset($_POST['document_url']) ? sanitize_text_field($_POST['document_url']) : '';
        
        if (empty($document_url)) {
            wp_send_json_error(['message' => 'Document URL required'], 400);
        }
        
        // Get current user token
        $current_user = wp_get_current_user();
        $token = $this->api->get_wp_user_token($current_user);
        
        if (!$token) {
            wp_send_json_error(['message' => 'Failed to authenticate'], 401);
        }
        
        // Call backend API to fetch document
        $response = $this->api->request(
            'api/v1/documents/view',
            'POST',
            ['document_url' => $document_url],
            $token
        );
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => $response['error'] ?? 'Failed to load document'], 500);
        }
    }
    
    /**
     * Ensure NTG role exists (for existing installations)
     */
    public function ensure_ntg_role() {
        if (!get_role('ntg')) {
            add_role(
                'ntg',
                'NTG Staff',
                [
                    'read' => true,
                    'use_nerdsiq' => true,
                ]
            );
        }
        
        // Ensure NTG role has the capability
        $ntg_role = get_role('ntg');
        if ($ntg_role && !$ntg_role->has_cap('use_nerdsiq')) {
            $ntg_role->add_cap('use_nerdsiq');
        }
    }
    
    /**
     * AJAX handler for getting user's chat sessions
     */
    public function ajax_get_sessions() {
        if (!$this->current_user_can_use_nerdsiq()) {
            wp_send_json_error(['message' => 'Unauthorized'], 403);
        }
        
        $current_user = wp_get_current_user();
        $token = $this->api->get_wp_user_token($current_user);
        
        if (!$token) {
            wp_send_json_error(['message' => 'Failed to authenticate'], 401);
        }
        
        $response = $this->api->request(
            'api/v1/chat/sessions?limit=20',
            'GET',
            null,
            $token
        );
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => 'Failed to load sessions'], 500);
        }
    }
    
    /**
     * AJAX handler for getting chat history for a session
     */
    public function ajax_get_history() {
        if (!$this->current_user_can_use_nerdsiq()) {
            wp_send_json_error(['message' => 'Unauthorized'], 403);
        }
        
        $session_id = isset($_GET['session_id']) ? sanitize_text_field($_GET['session_id']) : '';
        if (empty($session_id)) {
            wp_send_json_error(['message' => 'Session ID required'], 400);
        }
        
        $current_user = wp_get_current_user();
        $token = $this->api->get_wp_user_token($current_user);
        
        if (!$token) {
            wp_send_json_error(['message' => 'Failed to authenticate'], 401);
        }
        
        $response = $this->api->request(
            'api/v1/chat/history?session_id=' . urlencode($session_id),
            'GET',
            null,
            $token
        );
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => 'Failed to load history'], 500);
        }
    }
    
    /**
     * AJAX handler for analytics overview (admin only)
     */
    public function ajax_analytics_overview() {
        // Verify user is admin
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => 'Unauthorized'], 403);
        }
        
        $days = isset($_GET['days']) ? intval($_GET['days']) : 30;
        $days = max(1, min(365, $days));
        
        $current_user = wp_get_current_user();
        $token = NerdsIQ_API::get_admin_token();
        
        if (!$token) {
            wp_send_json_error(['message' => 'Failed to authenticate with API'], 401);
        }
        
        $response = $this->api->request(
            'api/v1/analytics/overview?days=' . $days,
            'GET',
            null,
            $token
        );
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error([
                'message' => 'Failed to load analytics',
                'error' => $response['error'] ?? 'Unknown error'
            ], 500);
        }
    }
    
    /**
     * AJAX handler for recent queries (admin only)
     */
    public function ajax_analytics_recent() {
        // Verify user is admin
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => 'Unauthorized'], 403);
        }
        
        $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 20;
        $limit = max(1, min(100, $limit));
        
        $token = NerdsIQ_API::get_admin_token();
        
        if (!$token) {
            wp_send_json_error(['message' => 'Failed to authenticate with API'], 401);
        }
        
        $response = $this->api->request(
            'api/v1/analytics/recent-queries?limit=' . $limit,
            'GET',
            null,
            $token
        );
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error([
                'message' => 'Failed to load recent queries',
                'error' => $response['error'] ?? 'Unknown error'
            ], 500);
        }
    }
    
    /**
     * Check if current user can use NerdsIQ
     */
    public function current_user_can_use_nerdsiq() {
        // Not logged in = no access
        if (!is_user_logged_in()) {
            return false;
        }
        
        // Check for the custom capability
        return current_user_can('use_nerdsiq');
    }
    
    /**
     * Enqueue frontend assets
     */
    public function enqueue_assets() {
        // Only load assets for users who can use NerdsIQ
        if (!$this->current_user_can_use_nerdsiq()) {
            return;
        }
        
        wp_enqueue_style(
            'nerdsiq-style',
            NERDSIQ_PLUGIN_URL . 'assets/css/nerdsiq-style.css',
            [],
            NERDSIQ_VERSION
        );
        
        wp_enqueue_script(
            'nerdsiq-chat',
            NERDSIQ_PLUGIN_URL . 'assets/js/nerdsiq-chat.js',
            ['jquery'],
            NERDSIQ_VERSION,
            true
        );
        
        // Get SSO token for logged-in WordPress users
        $sso_token = '';
        $user_name = '';
        $is_logged_in = is_user_logged_in();
        
        if ($is_logged_in) {
            $current_user = wp_get_current_user();
            $user_name = $current_user->display_name;
            $sso_token = $this->api->get_wp_user_token($current_user);
        }
        
        wp_localize_script('nerdsiq-chat', 'nerdsiq_ajax', [
            'ajax_url' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('nerdsiq_nonce'),
            'api_url' => get_option('nerdsiq_api_url', 'http://nerdsiq-api:8000'),
            'is_logged_in' => $is_logged_in,
            'sso_token' => $sso_token,
            'user_name' => $user_name,
            'enable_document_viewer' => get_option('nerdsiq_enable_document_viewer', '0') === '1',
        ]);
    }
    
    /**
     * Render chat widget in footer
     */
    public function render_widget() {
        // Only render for users who can use NerdsIQ
        if (!$this->current_user_can_use_nerdsiq()) {
            return;
        }
        
        // Check page display settings
        if (!$this->should_show_on_current_page()) {
            return;
        }
        
        include NERDSIQ_PLUGIN_DIR . 'templates/chat-widget.php';
    }
    
    /**
     * Check if widget should show on current page
     */
    private function should_show_on_current_page() {
        $display_mode = get_option('nerdsiq_display_mode', 'all');
        
        // Show on all pages
        if ($display_mode === 'all') {
            return true;
        }
        
        $selected_pages = get_option('nerdsiq_selected_pages', []);
        if (!is_array($selected_pages)) {
            $selected_pages = [];
        }
        
        // Convert to integers for comparison
        $selected_pages = array_map('intval', $selected_pages);
        
        // Get current page/post ID
        $current_id = 0;
        if (is_singular()) {
            $current_id = get_the_ID();
        } elseif (is_home() || is_front_page()) {
            // For blog page or front page
            $current_id = get_option('page_on_front') ?: get_option('page_for_posts') ?: 0;
        }
        
        if ($display_mode === 'include') {
            // Only show on selected pages
            return in_array($current_id, $selected_pages, true);
        } elseif ($display_mode === 'exclude') {
            // Show everywhere except selected pages
            return !in_array($current_id, $selected_pages, true);
        }
        
        return true;
    }
    
    /**
     * Restrict page access - redirect non-logged users to login
     */
    public function restrict_page_access() {
        // Only check if restriction is enabled
        if (get_option('nerdsiq_restrict_pages', '0') !== '1') {
            return;
        }
        
        // Only apply when display mode is 'include'
        $display_mode = get_option('nerdsiq_display_mode', 'all');
        if ($display_mode !== 'include') {
            return;
        }
        
        // Skip for logged-in users
        if (is_user_logged_in()) {
            return;
        }
        
        // Skip for admin pages and login
        if (is_admin()) {
            return;
        }
        
        $selected_pages = get_option('nerdsiq_selected_pages', []);
        if (!is_array($selected_pages) || empty($selected_pages)) {
            return;
        }
        
        $selected_pages = array_map('intval', $selected_pages);
        
        // Get current page/post ID using queried object
        $current_id = get_queried_object_id();
        
        // Debug log
        error_log("NerdsIQ Restrict: current_id=$current_id, selected_pages=" . implode(',', $selected_pages));
        
        // If current page is in the restricted list, redirect to login
        if ($current_id > 0 && in_array($current_id, $selected_pages, true)) {
            $redirect_url = wp_login_url(get_permalink($current_id));
            wp_safe_redirect($redirect_url);
            exit;
        }
    }
    
    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        // Main menu page
        add_menu_page(
            'NerdsIQ',
            'NerdsIQ',
            'manage_options',
            'nerdsiq',
            [$this, 'render_analytics_page'],
            'dashicons-format-chat',
            30
        );
        
        // Analytics submenu
        add_submenu_page(
            'nerdsiq',
            'Analytics',
            'Analytics',
            'manage_options',
            'nerdsiq',
            [$this, 'render_analytics_page']
        );
        
        // Settings submenu
        add_submenu_page(
            'nerdsiq',
            'Settings',
            'Settings',
            'manage_options',
            'nerdsiq-settings',
            [$this, 'render_settings_page']
        );
        
        // Logs submenu
        add_submenu_page(
            'nerdsiq',
            'Daily Logs',
            'Daily Logs', 
            'manage_options',
            'nerdsiq-logs',
            [$this, 'render_logs_page']
        );
    }
    
    /**
     * Enqueue admin assets
     */
    public function enqueue_admin_assets($hook) {
        // Only load on NerdsIQ settings page
        if ($hook !== 'nerdsiq_page_nerdsiq-settings') {
            return;
        }
        
        // Enqueue Select2 from CDN
        wp_enqueue_style(
            'select2',
            'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
            [],
            '4.1.0'
        );
        
        wp_enqueue_script(
            'select2',
            'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
            ['jquery'],
            '4.1.0',
            true
        );
    }
    
    /**
     * Render analytics page
     */
    public function render_analytics_page() {
        include NERDSIQ_PLUGIN_DIR . 'admin/analytics-page.php';
    }
    
    /**
     * Register plugin settings
     */
    public function register_settings() {
        register_setting('nerdsiq_settings', 'nerdsiq_api_url');
        register_setting('nerdsiq_settings', 'nerdsiq_widget_enabled');
        register_setting('nerdsiq_settings', 'nerdsiq_wp_auth_secret');
        register_setting('nerdsiq_settings', 'nerdsiq_openai_model', [
            'type' => 'string',
            'sanitize_callback' => [$this, 'sanitize_openai_model'],
            'default' => 'gpt-4o',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_allowed_roles', [
            'type' => 'array',
            'sanitize_callback' => [$this, 'sanitize_roles'],
            'default' => ['administrator'],
        ]);
        
        // Page display settings
        register_setting('nerdsiq_settings', 'nerdsiq_display_mode', [
            'type' => 'string',
            'sanitize_callback' => [$this, 'sanitize_display_mode'],
            'default' => 'all',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_selected_pages', [
            'type' => 'array',
            'sanitize_callback' => [$this, 'sanitize_selected_pages'],
            'default' => [],
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_restrict_pages', [
            'type' => 'string',
            'sanitize_callback' => [$this, 'sanitize_checkbox'],
            'default' => '0',
        ]);
        
        // Appearance settings
        register_setting('nerdsiq_settings', 'nerdsiq_primary_color', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_hex_color',
            'default' => '#0047AC',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_accent_color', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_hex_color',
            'default' => '#FFD301',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_widget_position', [
            'type' => 'string',
            'sanitize_callback' => [$this, 'sanitize_widget_position'],
            'default' => 'bottom-right',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_bottom_padding', [
            'type' => 'integer',
            'sanitize_callback' => 'absint',
            'default' => 20,
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_side_padding', [
            'type' => 'integer',
            'sanitize_callback' => 'absint',
            'default' => 20,
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_enable_document_viewer', [
            'type' => 'string',
            'sanitize_callback' => [$this, 'sanitize_checkbox'],
            'default' => '0',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_header_title', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default' => 'NerdsIQ',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_header_subtitle', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default' => 'AI Knowledge Assistant',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_welcome_message', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default' => 'Hello! How can I help you today?',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_logo_text', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default' => 'IQ',
        ]);
        register_setting('nerdsiq_settings', 'nerdsiq_input_placeholder', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default' => 'Ask a question...',
        ]);
    }
    
    /**
     * Sanitize widget position
     */
    public function sanitize_widget_position($position) {
        return in_array($position, ['bottom-right', 'bottom-left']) ? $position : 'bottom-right';
    }
    
    /**
     * Sanitize roles array
     */
    public function sanitize_roles($roles) {
        if (!is_array($roles)) {
            return ['administrator'];
        }
        
        // Update capabilities based on selected roles
        $this->update_role_capabilities($roles);
        
        return array_map('sanitize_text_field', $roles);
    }
    
    /**
     * Sanitize OpenAI model selection
     */
    public function sanitize_openai_model($model) {
        $allowed_models = ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'];
        return in_array($model, $allowed_models) ? $model : 'gpt-4o';
    }
    
    /**
     * Sanitize display mode
     */
    public function sanitize_display_mode($mode) {
        return in_array($mode, ['all', 'include', 'exclude']) ? $mode : 'all';
    }
    
    /**
     * Sanitize selected pages array
     */
    public function sanitize_selected_pages($pages) {
        if (!is_array($pages)) {
            return [];
        }
        return array_map('absint', $pages);
    }
    
    /**
     * Sanitize checkbox value
     */
    public function sanitize_checkbox($value) {
        return $value === '1' ? '1' : '0';
    }
    
    /**
     * Update role capabilities based on settings
     */
    public function update_role_capabilities($allowed_roles) {
        global $wp_roles;
        
        if (!isset($wp_roles)) {
            $wp_roles = new WP_Roles();
        }
        
        // Remove capability from all roles first
        foreach ($wp_roles->roles as $role_name => $role_info) {
            $role = get_role($role_name);
            if ($role) {
                $role->remove_cap('use_nerdsiq');
            }
        }
        
        // Add capability to allowed roles
        foreach ($allowed_roles as $role_name) {
            $role = get_role($role_name);
            if ($role) {
                $role->add_cap('use_nerdsiq');
            }
        }
    }
    
    /**
     * Render settings page
     */
    public function render_settings_page() {
        include NERDSIQ_PLUGIN_DIR . 'admin/settings-page.php';
    }
    
    /**
     * Render logs page
     */
    public function render_logs_page() {
        include NERDSIQ_PLUGIN_DIR . 'admin/logs-page.php';
    }
    
    /**
     * AJAX handler to get available log dates
     */
    public function ajax_get_log_dates() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => 'Unauthorized']);
        }
        
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'nerdsiq_nonce')) {
            wp_send_json_error(['message' => 'Invalid nonce']);
        }
        
        $response = $this->api->request('logs/dates', 'GET');
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => $response['error'] ?? 'Failed to fetch log dates']);
        }
    }
    
    /**
     * AJAX handler to get daily log
     */
    public function ajax_get_daily_log() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => 'Unauthorized']);
        }
        
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'nerdsiq_nonce')) {
            wp_send_json_error(['message' => 'Invalid nonce']);
        }
        
        $date = sanitize_text_field($_POST['date'] ?? '');
        if (empty($date)) {
            wp_send_json_error(['message' => 'Date required']);
        }
        
        $response = $this->api->request('logs/daily/' . $date, 'GET');
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => $response['error'] ?? 'Failed to fetch daily log']);
        }
    }
    
    /**
     * AJAX handler to get weekly report
     */
    public function ajax_get_weekly_report() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => 'Unauthorized']);
        }
        
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'nerdsiq_nonce')) {
            wp_send_json_error(['message' => 'Invalid nonce']);
        }
        
        $end_date = sanitize_text_field($_POST['end_date'] ?? '');
        
        $endpoint = 'logs/weekly';
        if (!empty($end_date)) {
            $endpoint .= '?end_date=' . urlencode($end_date);
        }
        
        $response = $this->api->request($endpoint, 'GET');
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => $response['error'] ?? 'Failed to fetch weekly report']);
        }
    }
    
    /**
     * AJAX handler to test email notifications
     */
    public function ajax_test_email() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => 'Unauthorized']);
        }
        
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'nerdsiq_nonce')) {
            wp_send_json_error(['message' => 'Invalid nonce']);
        }
        
        $response = $this->api->request('logs/test-email', 'POST', []);
        
        if ($response['success']) {
            wp_send_json_success($response['data']);
        } else {
            wp_send_json_error(['message' => $response['error'] ?? 'Failed to send test email']);
        }
    }
}

// Initialize plugin
add_action('plugins_loaded', function() {
    NerdsIQ_Chatbot::get_instance();
});

// Activation hook
register_activation_hook(__FILE__, function() {
    // Create the NTG (NerdsToGo) custom role if it doesn't exist
    if (!get_role('ntg')) {
        add_role(
            'ntg',
            'NTG Staff',
            [
                'read' => true,
                'use_nerdsiq' => true,
            ]
        );
    }
    
    // Set default options
    add_option('nerdsiq_api_url', 'http://nerdsiq-api:8000');
    add_option('nerdsiq_widget_enabled', '1');
    add_option('nerdsiq_wp_auth_secret', '');
    add_option('nerdsiq_allowed_roles', ['administrator', 'ntg']);
    
    // Add capability to administrator by default
    $admin_role = get_role('administrator');
    if ($admin_role) {
        $admin_role->add_cap('use_nerdsiq');
    }
    
    // Add capability to NTG role
    $ntg_role = get_role('ntg');
    if ($ntg_role) {
        $ntg_role->add_cap('use_nerdsiq');
    }
});

// Deactivation hook
register_deactivation_hook(__FILE__, function() {
    // Remove the capability from all roles
    global $wp_roles;
    
    if (!isset($wp_roles)) {
        $wp_roles = new WP_Roles();
    }
    
    foreach ($wp_roles->roles as $role_name => $role_info) {
        $role = get_role($role_name);
        if ($role) {
            $role->remove_cap('use_nerdsiq');
        }
    }
    
    // Note: We don't remove the NTG role on deactivation to preserve user assignments
    // To fully remove, use uninstall.php or manual cleanup
});
