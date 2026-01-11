'use strict';

(function($) {
    const NerdsIQ = {
        token: localStorage.getItem('nerdsiq_token'),
        sessionId: localStorage.getItem('nerdsiq_session_id') || null,
        isOpen: false,
        
        init: function() {
            this.bindEvents();
            this.checkAuth();
        },
        
        bindEvents: function() {
            // Toggle chat window
            $(document).on('click', '.nerdsiq-toggle', () => {
                this.toggleChat();
            });
            
            // Login form
            $(document).on('submit', '.nerdsiq-login-form', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
            
            // Send message
            $(document).on('submit', '.nerdsiq-chat-form', (e) => {
                e.preventDefault();
                this.handleSend();
            });
            
            // Enter key to send
            $(document).on('keypress', '.nerdsiq-input', (e) => {
                if (e.which === 13 && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSend();
                }
            });
            
            // Logout
            $(document).on('click', '.nerdsiq-logout', () => {
                this.logout();
            });
        },
        
        toggleChat: function() {
            this.isOpen = !this.isOpen;
            $('.nerdsiq-toggle').toggleClass('active', this.isOpen);
            $('.nerdsiq-chat-window').toggleClass('open', this.isOpen);
            
            if (this.isOpen) {
                setTimeout(() => {
                    $('.nerdsiq-input').focus();
                }, 100);
            }
        },
        
        checkAuth: function() {
            if (this.token) {
                this.showChat();
            } else {
                this.showLogin();
            }
        },
        
        showLogin: function() {
            $('.nerdsiq-login').show();
            $('.nerdsiq-chat-content').hide();
        },
        
        showChat: function() {
            $('.nerdsiq-login').hide();
            $('.nerdsiq-chat-content').show();
        },
        
        handleLogin: async function() {
            const $form = $('.nerdsiq-login-form');
            const $button = $form.find('button');
            const $error = $('.nerdsiq-login__error');
            
            const username = $form.find('input[name="username"]').val();
            const password = $form.find('input[name="password"]').val();
            
            if (!username || !password) {
                $error.text('Please enter email and password').show();
                return;
            }
            
            $button.prop('disabled', true).text('Logging in...');
            $error.hide();
            
            try {
                const response = await $.ajax({
                    url: nerdsiq_ajax.ajax_url,
                    type: 'POST',
                    data: {
                        action: 'nerdsiq_login',
                        nonce: nerdsiq_ajax.nonce,
                        username: username,
                        password: password
                    }
                });
                
                if (response.success) {
                    this.token = response.data.token;
                    localStorage.setItem('nerdsiq_token', this.token);
                    this.sessionId = this.generateSessionId();
                    localStorage.setItem('nerdsiq_session_id', this.sessionId);
                    this.showChat();
                    this.addMessage('Hello! How can I help you today?', 'assistant');
                } else {
                    // Handle error response properly
                    let errorMsg = 'Login failed';
                    if (response.data && typeof response.data === 'object' && response.data.message) {
                        errorMsg = response.data.message;
                    } else if (typeof response.data === 'string') {
                        errorMsg = response.data;
                    }
                    $error.text(errorMsg).show();
                }
            } catch (error) {
                console.error('Login error:', error);
                let errorMsg = 'Connection error. Please try again.';
                if (error.responseJSON && error.responseJSON.data && error.responseJSON.data.message) {
                    errorMsg = error.responseJSON.data.message;
                }
                $error.text(errorMsg).show();
            } finally {
                $button.prop('disabled', false).text('Login');
            }
        },
        
        handleSend: async function() {
            const $input = $('.nerdsiq-input');
            const question = $input.val().trim();
            
            if (!question || !this.token) return;
            
            $input.val('').prop('disabled', true);
            $('.nerdsiq-send').prop('disabled', true);
            
            // Add user message
            this.addMessage(question, 'user');
            
            // Show typing indicator
            this.showTyping();
            
            try {
                const response = await $.ajax({
                    url: nerdsiq_ajax.ajax_url,
                    type: 'POST',
                    data: {
                        action: 'nerdsiq_query',
                        nonce: nerdsiq_ajax.nonce,
                        token: this.token,
                        question: question,
                        session_id: this.sessionId
                    }
                });
                
                this.hideTyping();
                
                if (response.success) {
                    this.sessionId = response.data.session_id;
                    localStorage.setItem('nerdsiq_session_id', this.sessionId);
                    this.addMessage(response.data.answer, 'assistant', response.data.sources);
                } else {
                    if (response.data.code === 'auth_expired') {
                        this.logout();
                        this.addMessage('Session expired. Please log in again.', 'assistant');
                    } else {
                        this.addMessage('Sorry, something went wrong. Please try again.', 'assistant');
                    }
                }
            } catch (error) {
                console.error('Query error:', error);
                this.hideTyping();
                this.addMessage('Connection error. Please try again.', 'assistant');
            } finally {
                $input.prop('disabled', false).focus();
                $('.nerdsiq-send').prop('disabled', false);
            }
        },
        
        addMessage: function(content, role, sources) {
            const $messages = $('.nerdsiq-messages');
            const escapedContent = this.escapeHtml(content);
            
            let html = `<div class="nerdsiq-message ${role}">${escapedContent}`;
            
            if (sources && sources.length > 0) {
                html += '<div class="nerdsiq-message__sources"><strong>Sources:</strong><br>';
                sources.forEach((source, i) => {
                    const displayUrl = source.length > 40 ? source.substring(0, 40) + '...' : source;
                    html += `<a href="${this.escapeHtml(source)}" target="_blank" rel="noopener">${this.escapeHtml(displayUrl)}</a>`;
                    if (i < sources.length - 1) html += '<br>';
                });
                html += '</div>';
            }
            
            html += '</div>';
            $messages.append(html);
            this.scrollToBottom();
        },
        
        showTyping: function() {
            const html = `
                <div class="nerdsiq-typing">
                    <span></span><span></span><span></span>
                </div>
            `;
            $('.nerdsiq-messages').append(html);
            this.scrollToBottom();
        },
        
        hideTyping: function() {
            $('.nerdsiq-typing').remove();
        },
        
        scrollToBottom: function() {
            const $messages = $('.nerdsiq-messages');
            $messages.scrollTop($messages[0].scrollHeight);
        },
        
        logout: function() {
            this.token = null;
            this.sessionId = null;
            localStorage.removeItem('nerdsiq_token');
            localStorage.removeItem('nerdsiq_session_id');
            $('.nerdsiq-messages').empty();
            this.showLogin();
        },
        
        generateSessionId: function() {
            return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        },
        
        escapeHtml: function(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    };
    
    $(document).ready(function() {
        NerdsIQ.init();
    });
})(jQuery);
