<?php
/**
 * NerdsIQ API Client
 */

if (!defined('ABSPATH')) {
    exit;
}

class NerdsIQ_API {
    
    private $api_url;
    private $wp_auth_secret;
    
    public function __construct() {
        $this->api_url = get_option('nerdsiq_api_url', 'http://nerdsiq-api:8000');
        $this->wp_auth_secret = get_option('nerdsiq_wp_auth_secret', '');
    }
    
    /**
     * Make API request
     */
    public function request($endpoint, $method = 'GET', $data = null, $token = null) {
        $url = trailingslashit($this->api_url) . ltrim($endpoint, '/');
        
        $args = [
            'method' => $method,
            'timeout' => 30,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
            ],
        ];
        
        if ($token) {
            $args['headers']['Authorization'] = 'Bearer ' . $token;
        }
        
        if ($data && in_array($method, ['POST', 'PUT', 'PATCH'])) {
            $args['body'] = wp_json_encode($data);
        }
        
        $response = wp_remote_request($url, $args);
        
        if (is_wp_error($response)) {
            return [
                'success' => false,
                'error' => $response->get_error_message(),
            ];
        }
        
        $status_code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        return [
            'success' => $status_code >= 200 && $status_code < 300,
            'status_code' => $status_code,
            'data' => $data,
        ];
    }
    
    /**
     * Get token for WordPress user via SSO
     */
    public function get_wp_user_token($user) {
        if (!$user || !$this->wp_auth_secret) {
            return false;
        }
        
        $response = $this->request('api/v1/auth/wp-sso', 'POST', [
            'email' => $user->user_email,
            'wp_user_id' => $user->ID,
            'display_name' => $user->display_name,
            'wp_secret' => $this->wp_auth_secret,
        ]);
        
        if ($response['success'] && isset($response['data']['access_token'])) {
            return $response['data']['access_token'];
        }
        
        return false;
    }
    
    /**
     * Login user (legacy - kept for compatibility)
     */
    public function login($username, $password) {
        return $this->request('api/v1/auth/login/json', 'POST', [
            'username' => $username,
            'password' => $password,
        ]);
    }
    
    /**
     * Query RAG
     */
    public function query($question, $session_id, $token, $model = null) {
        $data = [
            'question' => $question,
            'session_id' => $session_id,
        ];
        
        if ($model) {
            $data['model'] = $model;
        }
        
        return $this->request('api/v1/chat/query', 'POST', $data, $token);
    }
    
    /**
     * Get chat history
     */
    public function get_history($session_id, $token) {
        return $this->request('api/v1/chat/history?session_id=' . urlencode($session_id), 'GET', null, $token);
    }
    
    /**
     * Health check
     */
    public function health_check() {
        return $this->request('health');
    }
    
    /**
     * Get admin token for analytics (static method for use in templates)
     */
    public static function get_admin_token() {
        $current_user = wp_get_current_user();
        if (!$current_user || !current_user_can('manage_options')) {
            return '';
        }
        
        $api = new self();
        $token = $api->get_wp_user_token($current_user);
        
        return $token ?: '';
    }
}
