'use strict';

(function($) {
    const NerdsIQ = {
        token: null,
        sessionId: localStorage.getItem('nerdsiq_session_id') || null,
        isOpen: false,
        isLoggedIn: false,
        historyLoaded: false,
        userName: '',
        welcomeMessage: 'Hello! How can I help you today?',
        
        init: function() {
            // Get welcome message from widget data attribute
            var $widget = $('.nerdsiq-widget');
            if ($widget.length && $widget.data('welcome-message')) {
                this.welcomeMessage = $widget.data('welcome-message');
            }
            
            // Check if we have SSO token from WordPress
            if (typeof nerdsiq_ajax !== 'undefined') {
                this.isLoggedIn = nerdsiq_ajax.is_logged_in;
                this.userName = nerdsiq_ajax.user_name || '';
                
                if (this.isLoggedIn && nerdsiq_ajax.sso_token) {
                    // Use SSO token from WordPress
                    this.token = nerdsiq_ajax.sso_token;
                    this.sessionId = this.sessionId || this.generateSessionId();
                    localStorage.setItem('nerdsiq_session_id', this.sessionId);
                }
            }
            
            this.bindEvents();
            this.checkAuth();
        },
        
        bindEvents: function() {
            // Toggle chat window
            $(document).on('click', '.nerdsiq-toggle', () => {
                this.toggleChat();
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
            
            // Clear chat / New chat
            $(document).on('click', '.nerdsiq-clear-chat, .nerdsiq-new-chat-btn', () => {
                this.clearChat();
            });
            
            // Close chat button (for mobile)
            $(document).on('click', '.nerdsiq-close-btn', () => {
                this.toggleChat();
            });
            
            // Maximize/Minimize toggle
            $(document).on('click', '.nerdsiq-maximize-btn', () => {
                this.toggleMaximize();
            });
            
            // Open history panel
            $(document).on('click', '.nerdsiq-history-btn', () => {
                this.openHistoryPanel();
            });
            
            // Close history panel
            $(document).on('click', '.nerdsiq-close-history', () => {
                this.closeHistoryPanel();
            });
            
            // Load a history session
            $(document).on('click', '.nerdsiq-history-item', (e) => {
                var sessionId = $(e.currentTarget).data('session-id');
                this.loadSession(sessionId);
            });
            
            // View document (if enabled)
            $(document).on('click', '.nerdsiq-view-doc', (e) => {
                e.preventDefault();
                const url = $(e.currentTarget).data('url');
                this.viewDocument(url);
            });
            
            // Close document modal
            $(document).on('click', '.nerdsiq-doc-modal-close, .nerdsiq-doc-modal-overlay', (e) => {
                if (e.target === e.currentTarget) {
                    this.closeDocumentModal();
                }
            });
        },
        
        toggleChat: function() {
            this.isOpen = !this.isOpen;
            $('.nerdsiq-toggle').toggleClass('active', this.isOpen);
            $('.nerdsiq-chat-window').toggleClass('open', this.isOpen);
            
            // Toggle body and html class for mobile full-screen mode (prevents horizontal scroll)
            $('html, body').toggleClass('nerdsiq-chat-open', this.isOpen);
            
            if (this.isOpen) {
                // Load current session history on first open
                if (this.sessionId && !this.historyLoaded) {
                    this.loadCurrentSessionHistory();
                }
                setTimeout(() => {
                    $('.nerdsiq-input').focus();
                }, 100);
            }
        },
        
        toggleMaximize: function() {
            var $window = $('.nerdsiq-chat-window');
            var $btn = $('.nerdsiq-maximize-btn');
            var isMaximized = $window.hasClass('maximized');
            
            $window.toggleClass('maximized', !isMaximized);
            $btn.find('.maximize-icon').toggle(isMaximized);
            $btn.find('.minimize-icon').toggle(!isMaximized);
            $btn.attr('title', isMaximized ? 'Maximize' : 'Minimize');
            $btn.attr('aria-label', isMaximized ? 'Maximize' : 'Minimize');
            
            // Scroll to bottom after resize
            setTimeout(() => {
                this.scrollToBottom();
            }, 100);
        },
        
        checkAuth: function() {
            if (this.token) {
                // User is authenticated via SSO
                this.showChat();
                // Load current session history if exists
                if (this.sessionId) {
                    this.loadCurrentSessionHistory();
                } else {
                    this.addMessage(this.welcomeMessage, 'assistant');
                }
            } else if (this.isLoggedIn) {
                // Logged in to WP but SSO failed (secret not configured)
                this.showSSOError();
            } else {
                // Not logged in to WordPress
                this.showLoginPrompt();
            }
        },
        
        showLoginPrompt: function() {
            $('.nerdsiq-login').show();
            $('.nerdsiq-chat-content').hide();
            $('.nerdsiq-login').html(`
                <div class="nerdsiq-login__message">
                    <p>Please log in to WordPress to use NerdsIQ.</p>
                    <a href="${this.getLoginUrl()}" class="nerdsiq-login__button">Log In</a>
                </div>
            `);
        },
        
        showSSOError: function() {
            $('.nerdsiq-login').show();
            $('.nerdsiq-chat-content').hide();
            $('.nerdsiq-login').html(`
                <div class="nerdsiq-login__message">
                    <p>SSO is not configured. Please contact your administrator.</p>
                </div>
            `);
        },
        
        getLoginUrl: function() {
            const currentUrl = encodeURIComponent(window.location.href);
            return '/wp-login.php?redirect_to=' + currentUrl;
        },
        
        showChat: function() {
            $('.nerdsiq-login').hide();
            $('.nerdsiq-chat-content').show();
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
                    if (response.data && response.data.code === 'auth_expired') {
                        this.addMessage('Session expired. Please refresh the page.', 'assistant');
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
            
            // For assistant messages, render markdown; for user messages, escape HTML
            let formattedContent;
            if (role === 'assistant') {
                formattedContent = this.renderMarkdown(content);
            } else {
                formattedContent = this.escapeHtml(content);
            }
            
            let html = `<div class="nerdsiq-message ${role}">${formattedContent}`;
            
            if (sources && sources.length > 0) {
                html += '<div class="nerdsiq-message__sources"><strong>Sources:</strong><br>';
                sources.forEach((source, i) => {
                    // Handle both old format (string) and new format (object with url and name)
                    let sourceUrl, sourceName;
                    if (typeof source === 'object' && source.url) {
                        sourceUrl = source.url;
                        sourceName = source.name || 'Document';
                    } else {
                        // Fallback for old string format
                        sourceUrl = source;
                        const fileName = source.split('/').pop().split('?')[0] || 'Document';
                        sourceName = decodeURIComponent(fileName).replace(/\+/g, ' ');
                    }
                    
                    // Check if document viewer is enabled
                    if (nerdsiq_ajax.enable_document_viewer) {
                        // Make it clickable to view document in modal
                        html += `<a href="#" class="nerdsiq-view-doc" data-url="${this.escapeHtml(sourceUrl)}">${this.escapeHtml(sourceName)}</a>`;
                    } else {
                        // Show as external link to Google Drive
                        html += `<a href="${this.escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer" style="color: #0047AC;">${this.escapeHtml(sourceName)}</a>`;
                    }
                    if (i < sources.length - 1) html += '<br>';
                });
                html += '</div>';
            }
            
            html += '</div>';
            $messages.append(html);
            this.scrollToBottom();
        },
        
        renderMarkdown: function(text) {
            // Simple markdown to HTML conversion
            // Process the raw text first, then sanitize appropriately
            
            var html = text;
            
            // Bold: **text** -> <strong>text</strong>
            // Use a simple pattern that matches **anything between asterisks**
            while (html.indexOf('**') !== -1) {
                var start = html.indexOf('**');
                var end = html.indexOf('**', start + 2);
                if (end === -1) break;
                
                var before = html.substring(0, start);
                var boldText = html.substring(start + 2, end);
                var after = html.substring(end + 2);
                
                // Escape the bold text content to prevent XSS
                boldText = this.escapeHtml(boldText);
                html = before + '<strong>' + boldText + '</strong>' + after;
            }
            
            // Now escape any remaining text that's not in HTML tags
            // Split by our strong tags and escape non-tag parts
            var parts = html.split(/(<strong>.*?<\/strong>)/g);
            html = parts.map(function(part) {
                if (part.startsWith('<strong>')) {
                    return part; // Already processed
                }
                return this.escapeHtml(part);
            }, this).join('');
            
            // Numbered lists: "1. " at start of line
            html = html.replace(/^(\d+)\.\s+/gm, '<li-marker>');
            
            // Convert newlines
            html = html.replace(/\n\n+/g, '<br><br>');
            html = html.replace(/\n/g, '<br>');
            
            // Convert list markers to proper list items
            if (html.indexOf('<li-marker>') !== -1) {
                var listParts = html.split('<li-marker>');
                html = listParts[0] + '<ol class="nerdsiq-list">';
                for (var i = 1; i < listParts.length; i++) {
                    // Find where this list item ends (next <br><br> or end)
                    var itemContent = listParts[i];
                    var breakIdx = itemContent.indexOf('<br><br>');
                    if (breakIdx !== -1) {
                        html += '<li>' + itemContent.substring(0, breakIdx) + '</li>';
                        html += '</ol>' + itemContent.substring(breakIdx);
                        // Check if there are more list items after
                        if (i < listParts.length - 1) {
                            html += '<ol class="nerdsiq-list">';
                        }
                    } else {
                        html += '<li>' + itemContent + '</li>';
                    }
                }
                if (!html.endsWith('</ol>')) {
                    html += '</ol>';
                }
            }
            
            // Clean up
            html = html.replace(/<br><\/li>/g, '</li>');
            html = html.replace(/<\/ol><br>/g, '</ol>');
            html = html.replace(/<ol class="nerdsiq-list"><\/ol>/g, '');
            
            return html;
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
        
        clearChat: function() {
            this.sessionId = this.generateSessionId();
            this.historyLoaded = false;
            localStorage.setItem('nerdsiq_session_id', this.sessionId);
            $('.nerdsiq-messages').empty();
            this.addMessage(this.welcomeMessage, 'assistant');
            this.closeHistoryPanel();
        },
        
        generateSessionId: function() {
            return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        },
        
        escapeHtml: function(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },
        
        // History methods
        openHistoryPanel: function() {
            $('.nerdsiq-history-panel').show();
            this.loadSessions();
        },
        
        closeHistoryPanel: function() {
            $('.nerdsiq-history-panel').hide();
        },
        
        loadSessions: function() {
            var self = this;
            $('.nerdsiq-history-list').html('<div class="nerdsiq-history-loading">Loading...</div>');
            
            $.ajax({
                url: nerdsiq_ajax.ajax_url,
                type: 'GET',
                data: {
                    action: 'nerdsiq_get_sessions'
                }
            }).done(function(response) {
                if (response.success && response.data.sessions) {
                    self.renderSessions(response.data.sessions);
                } else {
                    $('.nerdsiq-history-list').html('<div class="nerdsiq-history-empty">No chat history found</div>');
                }
            }).fail(function() {
                $('.nerdsiq-history-list').html('<div class="nerdsiq-history-empty">Failed to load history</div>');
            });
        },
        
        renderSessions: function(sessions) {
            if (sessions.length === 0) {
                $('.nerdsiq-history-list').html('<div class="nerdsiq-history-empty">No chat history yet</div>');
                return;
            }
            
            var html = '';
            var self = this;
            sessions.forEach(function(session) {
                var preview = session.last_message || 'No messages';
                var date = new Date(session.last_activity);
                var dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                
                html += '<div class="nerdsiq-history-item" data-session-id="' + self.escapeHtml(session.session_id) + '">';
                html += '<div class="nerdsiq-history-item__preview">' + self.escapeHtml(preview) + '</div>';
                html += '<div class="nerdsiq-history-item__meta">';
                html += '<span>' + session.message_count + ' messages</span>';
                html += '<span>' + dateStr + '</span>';
                html += '</div>';
                html += '</div>';
            });
            
            $('.nerdsiq-history-list').html(html);
        },
        
        loadSession: function(sessionId) {
            var self = this;
            this.sessionId = sessionId;
            this.historyLoaded = true;
            localStorage.setItem('nerdsiq_session_id', sessionId);
            
            this.closeHistoryPanel();
            $('.nerdsiq-messages').empty();
            this.showTyping();
            
            $.ajax({
                url: nerdsiq_ajax.ajax_url,
                type: 'GET',
                data: {
                    action: 'nerdsiq_get_history',
                    session_id: sessionId
                }
            }).done(function(response) {
                self.hideTyping();
                if (response.success && response.data.messages) {
                    response.data.messages.forEach(function(msg) {
                        self.addMessage(msg.content, msg.role, msg.sources);
                    });
                }
            }).fail(function() {
                self.hideTyping();
                self.addMessage('Failed to load chat history', 'assistant');
            });
        },
        
        loadCurrentSessionHistory: function() {
            if (!this.sessionId || this.historyLoaded) {
                if (!this.historyLoaded) {
                    this.addMessage(this.welcomeMessage, 'assistant');
                }
                return;
            }
            
            var self = this;
            this.historyLoaded = true;
            
            $.ajax({
                url: nerdsiq_ajax.ajax_url,
                type: 'GET',
                data: {
                    action: 'nerdsiq_get_history',
                    session_id: this.sessionId
                }
            }).done(function(response) {
                if (response.success && response.data.messages && response.data.messages.length > 0) {
                    response.data.messages.forEach(function(msg) {
                        self.addMessage(msg.content, msg.role, msg.sources);
                    });
                } else {
                    // No history for this session, show welcome
                    self.addMessage(self.welcomeMessage, 'assistant');
                }
            }).fail(function() {
                // Failed to load, just show welcome
                self.addMessage(self.welcomeMessage, 'assistant');
            });
        },
        
        viewDocument: function(url) {
            var self = this;
            
            // Create modal if it doesn't exist
            if ($('.nerdsiq-doc-modal').length === 0) {
                $('body').append(`
                    <div class="nerdsiq-doc-modal-overlay">
                        <div class="nerdsiq-doc-modal">
                            <div class="nerdsiq-doc-modal-header">
                                <h3>Document Viewer</h3>
                                <button class="nerdsiq-doc-modal-close">&times;</button>
                            </div>
                            <div class="nerdsiq-doc-modal-content">
                                <div class="nerdsiq-doc-loading">Loading document...</div>
                                <iframe class="nerdsiq-doc-iframe" style="display:none;"></iframe>
                            </div>
                        </div>
                    </div>
                `);
            }
            
            $('.nerdsiq-doc-modal-overlay').fadeIn(200);
            $('.nerdsiq-doc-loading').show();
            $('.nerdsiq-doc-iframe').hide();
            
            // Fetch document via WordPress AJAX
            $.ajax({
                url: nerdsiq_ajax.ajax_url,
                type: 'POST',
                data: {
                    action: 'nerdsiq_view_document',
                    nonce: nerdsiq_ajax.nonce,
                    document_url: url
                },
                timeout: 30000
            }).done(function(response) {
                if (response.success && response.data.content) {
                    $('.nerdsiq-doc-loading').hide();
                    $('.nerdsiq-doc-iframe')
                        .attr('srcdoc', response.data.content)
                        .show();
                } else {
                    $('.nerdsiq-doc-loading').html(
                        '<div style="color: red;">Failed to load document: ' + 
                        (response.data.message || 'Unknown error') + 
                        '</div>'
                    );
                }
            }).fail(function(xhr, status, error) {
                $('.nerdsiq-doc-loading').html(
                    '<div style="color: red;">Error loading document: ' + error + '</div>'
                );
            });
        },
        
        closeDocumentModal: function() {
            $('.nerdsiq-doc-modal-overlay').fadeOut(200);
            $('.nerdsiq-doc-iframe').attr('srcdoc', '');
        }
    };
    
    $(document).ready(function() {
        NerdsIQ.init();
    });
})(jQuery);
