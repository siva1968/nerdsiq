<?php
/**
 * NerdsIQ Authentication Handler
 */

if (!defined('ABSPATH')) {
    exit;
}

class NerdsIQ_Auth {
    
    private $api;
    
    public function __construct($api) {
        $this->api = $api;
    }
    
    /**
     * AJAX login handler
     */
    public function ajax_login() {
        // Verify nonce
        if (!wp_verify_nonce($_POST['nonce'] ?? '', 'nerdsiq_nonce')) {
            wp_send_json_error(['message' => 'Invalid security token']);
            return;
        }
        
        // Sanitize inputs
        $username = sanitize_email($_POST['username'] ?? '');
        $password = $_POST['password'] ?? '';
        
        if (empty($username) || empty($password)) {
            wp_send_json_error(['message' => 'Email and password are required']);
            return;
        }
        
        // Call API
        $result = $this->api->login($username, $password);
        
        if ($result['success'] && isset($result['data']['access_token'])) {
            wp_send_json_success([
                'token' => $result['data']['access_token'],
                'message' => 'Login successful',
            ]);
        } else {
            $message = $result['data']['detail'] ?? 'Login failed';
            wp_send_json_error(['message' => $message]);
        }
    }
    
    /**
     * Get stored token from session/cookie
     */
    public function get_token() {
        // Token is stored client-side in localStorage
        // This method is for server-side token handling if needed
        return null;
    }
    
    /**
     * Check if user is authenticated
     */
    public function is_authenticated() {
        // Authentication is handled client-side
        return false;
    }
}
