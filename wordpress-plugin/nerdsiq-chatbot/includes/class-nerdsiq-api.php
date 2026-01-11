<?php
/**
 * NerdsIQ API Client
 */

if (!defined('ABSPATH')) {
    exit;
}

class NerdsIQ_API {
    
    private $api_url;
    
    public function __construct() {
        $this->api_url = get_option('nerdsiq_api_url', 'http://nerdsiq-api:8000');
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
     * Login user
     */
    public function login($username, $password) {
        return $this->request('api/v1/auth/login', 'POST', [
            'username' => $username,
            'password' => $password,
        ]);
    }
    
    /**
     * Query RAG
     */
    public function query($question, $session_id, $token) {
        return $this->request('api/v1/chat/query', 'POST', [
            'question' => $question,
            'session_id' => $session_id,
        ], $token);
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
}
