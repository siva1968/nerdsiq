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
?>

<div class="nerdsiq-widget">
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
            <div class="nerdsiq-header__logo">IQ</div>
            <div>
                <h3 class="nerdsiq-header__title">NerdsIQ</h3>
                <p class="nerdsiq-header__subtitle">AI Knowledge Assistant</p>
            </div>
        </div>
        
        <!-- Login Form -->
        <div class="nerdsiq-login">
            <h4 class="nerdsiq-login__title">Sign in to continue</h4>
            <form class="nerdsiq-login-form">
                <input 
                    type="email" 
                    name="username" 
                    class="nerdsiq-login__input" 
                    placeholder="Email address" 
                    required
                    autocomplete="email"
                >
                <input 
                    type="password" 
                    name="password" 
                    class="nerdsiq-login__input" 
                    placeholder="Password" 
                    required
                    autocomplete="current-password"
                >
                <button type="submit" class="nerdsiq-login__button">Login</button>
                <p class="nerdsiq-login__error" style="display: none;"></p>
            </form>
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
                        placeholder="Ask a question..." 
                        autocomplete="off"
                    >
                    <button type="submit" class="nerdsiq-send" aria-label="Send">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
