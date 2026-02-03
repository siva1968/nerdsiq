<?php
/**
 * Chat Widget Template
 */

if (!defined('ABSPATH')) {
    exit;
}

$widget_enabled = get_option('nerdsiq_widget_enabled', '1');
if ($widget_enabled !== '1') {
    return;
}

// Get appearance settings
$primary_color = get_option('nerdsiq_primary_color', '#0047AC');
$accent_color = get_option('nerdsiq_accent_color', '#FFD301');
$widget_position = get_option('nerdsiq_widget_position', 'bottom-right');
$bottom_padding = intval(get_option('nerdsiq_bottom_padding', '20'));
$side_padding = intval(get_option('nerdsiq_side_padding', '20'));
$header_title = get_option('nerdsiq_header_title', 'NerdsIQ');
$header_subtitle = get_option('nerdsiq_header_subtitle', 'AI Knowledge Assistant');
$welcome_message = get_option('nerdsiq_welcome_message', 'Hello! How can I help you today?');
$logo_text = get_option('nerdsiq_logo_text', 'IQ');
$input_placeholder = get_option('nerdsiq_input_placeholder', 'Ask a question...');

// Replace {name} placeholder in welcome message
$current_user = wp_get_current_user();
$user_name = $current_user->display_name ? $current_user->display_name : 'there';
$welcome_message = str_replace('{name}', esc_html($user_name), $welcome_message);
?>

<style>
:root {
    --nerdsiq-primary: <?php echo esc_attr($primary_color); ?>;
    --nerdsiq-accent: <?php echo esc_attr($accent_color); ?>;
    --nerdsiq-bottom-padding: <?php echo esc_attr($bottom_padding); ?>px;
    --nerdsiq-side-padding: <?php echo esc_attr($side_padding); ?>px;
}
</style>

<div class="nerdsiq-widget position-<?php echo esc_attr($widget_position); ?>" 
     data-welcome-message="<?php echo esc_attr($welcome_message); ?>">
    <!-- Toggle Button -->
    <button class="nerdsiq-toggle" aria-label="Toggle chat">
        <svg class="chat-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
            <path d="M7 9h10v2H7zm0-3h10v2H7zm0 6h7v2H7z"/>
        </svg>
        <svg class="close-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
    </button>
    
    <!-- Chat Window -->
    <div class="nerdsiq-chat-window">
        <!-- Header -->
        <div class="nerdsiq-header">
            <div class="nerdsiq-header__logo"><?php echo esc_html($logo_text); ?></div>
            <div>
                <h3 class="nerdsiq-header__title"><?php echo esc_html($header_title); ?></h3>
                <p class="nerdsiq-header__subtitle"><?php echo esc_html($header_subtitle); ?></p>
            </div>
            <div class="nerdsiq-header__actions">
                <button type="button" class="nerdsiq-history-btn" aria-label="Chat history" title="Chat history">
                    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
                        <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
                    </svg>
                </button>
                <button type="button" class="nerdsiq-maximize-btn" aria-label="Maximize" title="Maximize">
                    <svg class="maximize-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
                        <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                    </svg>
                    <svg class="minimize-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" style="display:none;">
                        <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
                    </svg>
                </button>
                <button type="button" class="nerdsiq-new-chat-btn" aria-label="New chat" title="New chat">
                    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
                        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                    </svg>
                </button>
                <button type="button" class="nerdsiq-close-btn" aria-label="Close chat" title="Close">
                    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            </div>
        </div>
        
        <!-- History Panel (hidden by default) -->
        <div class="nerdsiq-history-panel" style="display: none;">
            <div class="nerdsiq-history-header">
                <h4>Chat History</h4>
                <button type="button" class="nerdsiq-close-history" aria-label="Close history">×</button>
            </div>
            <div class="nerdsiq-history-list">
                <div class="nerdsiq-history-loading">Loading...</div>
            </div>
        </div>
        
        <!-- Login/SSO Area (dynamically populated by JS) -->
        <div class="nerdsiq-login" style="display: none;">
            <!-- Will show login prompt or SSO error via JavaScript -->
        </div>
        
        <!-- Chat Content -->
        <div class="nerdsiq-chat-content" style="display: none;">
            <!-- Messages -->
            <div class="nerdsiq-messages"></div>
            
            <!-- Input Area -->
            <div class="nerdsiq-input-area">
                <form class="nerdsiq-chat-form" style="display: flex; gap: 8px; flex: 1;">
                    <input 
                        type="text" 
                        class="nerdsiq-input" 
                        placeholder="<?php echo esc_attr($input_placeholder); ?>" 
                        autocomplete="off"
                    >
                    <button type="submit" class="nerdsiq-send" aria-label="Send">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </form>
                <button type="button" class="nerdsiq-clear-chat" aria-label="Clear chat" title="Clear chat">
                    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="18" height="18">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            </div>
        </div>
    </div>
</div>
