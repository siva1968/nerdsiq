<?php
/**
 * NerdsIQ Chat Widget Handler
 */

if (!defined('ABSPATH')) {
    exit;
}

class NerdsIQ_Widget {
    
    private $api;
    private $auth;
    
    public function __construct($api, $auth) {
        $this->api = $api;
        $this->auth = $auth;
    }
    
    /**
     * AJAX query handler
     */
    public function ajax_query() {
        // Verify nonce
        if (!wp_verify_nonce($_POST['nonce'] ?? '', 'nerdsiq_nonce')) {
            wp_send_json_error(['message' => 'Invalid security token']);
            return;
        }
        
        // Get token from header
        $token = sanitize_text_field($_POST['token'] ?? '');
        if (empty($token)) {
            wp_send_json_error(['message' => 'Authentication required']);
            return;
        }
        
        // Sanitize inputs
        $question = sanitize_text_field($_POST['question'] ?? '');
        $session_id = sanitize_text_field($_POST['session_id'] ?? '');
        
        if (empty($question)) {
            wp_send_json_error(['message' => 'Question is required']);
            return;
        }
        
        if (empty($session_id)) {
            $session_id = wp_generate_uuid4();
        }
        
        // Call API
        $result = $this->api->query($question, $session_id, $token);
        
        if ($result['success']) {
            wp_send_json_success([
                'answer' => $result['data']['answer'] ?? '',
                'sources' => $result['data']['sources'] ?? [],
                'session_id' => $result['data']['session_id'] ?? $session_id,
            ]);
        } else {
            $message = $result['data']['detail'] ?? 'Query failed';
            
            // Check for auth errors
            if ($result['status_code'] === 401) {
                wp_send_json_error([
                    'message' => 'Session expired. Please log in again.',
                    'code' => 'auth_expired',
                ]);
                return;
            }
            
            wp_send_json_error(['message' => $message]);
        }
    }
}
