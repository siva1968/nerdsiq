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
define('NERDSIQ_VERSION', '1.0.0');
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
        
        // Hooks
        add_action('wp_enqueue_scripts', [$this, 'enqueue_assets']);
        add_action('wp_footer', [$this, 'render_widget']);
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        
        // AJAX handlers
        add_action('wp_ajax_nerdsiq_login', [$this->auth, 'ajax_login']);
        add_action('wp_ajax_nopriv_nerdsiq_login', [$this->auth, 'ajax_login']);
        add_action('wp_ajax_nerdsiq_query', [$this->widget, 'ajax_query']);
        add_action('wp_ajax_nopriv_nerdsiq_query', [$this->widget, 'ajax_query']);
    }
    
    /**
     * Enqueue frontend assets
     */
    public function enqueue_assets() {
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
        
        wp_localize_script('nerdsiq-chat', 'nerdsiq_ajax', [
            'ajax_url' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('nerdsiq_nonce'),
            'api_url' => get_option('nerdsiq_api_url', 'http://nerdsiq-api:8000'),
        ]);
    }
    
    /**
     * Render chat widget in footer
     */
    public function render_widget() {
        include NERDSIQ_PLUGIN_DIR . 'templates/chat-widget.php';
    }
    
    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_options_page(
            'NerdsIQ Settings',
            'NerdsIQ',
            'manage_options',
            'nerdsiq-settings',
            [$this, 'render_settings_page']
        );
    }
    
    /**
     * Register plugin settings
     */
    public function register_settings() {
        register_setting('nerdsiq_settings', 'nerdsiq_api_url');
        register_setting('nerdsiq_settings', 'nerdsiq_widget_enabled');
    }
    
    /**
     * Render settings page
     */
    public function render_settings_page() {
        include NERDSIQ_PLUGIN_DIR . 'admin/settings-page.php';
    }
}

// Initialize plugin
add_action('plugins_loaded', function() {
    NerdsIQ_Chatbot::get_instance();
});

// Activation hook
register_activation_hook(__FILE__, function() {
    // Set default options
    add_option('nerdsiq_api_url', 'http://nerdsiq-api:8000');
    add_option('nerdsiq_widget_enabled', '1');
});

// Deactivation hook
register_deactivation_hook(__FILE__, function() {
    // Cleanup if needed
});
