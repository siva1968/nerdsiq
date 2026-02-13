<?php
/**
 * NerdsIQ Settings Page
 */

if (!defined('ABSPATH')) {
    exit;
}

// Check permissions
if (!current_user_can('manage_options')) {
    return;
}

// Save settings message
$saved = isset($_GET['settings-updated']);
?>

<div class="wrap">
    <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
    
    <?php if ($saved): ?>
        <div class="notice notice-success is-dismissible">
            <p>Settings saved successfully.</p>
        </div>
    <?php endif; ?>
    
    <form method="post" action="options.php">
        <?php settings_fields('nerdsiq_settings'); ?>
        
        <table class="form-table" role="presentation">
            <tr>
                <th scope="row">
                    <label for="nerdsiq_api_url">API URL</label>
                </th>
                <td>
                    <input 
                        type="url" 
                        id="nerdsiq_api_url" 
                        name="nerdsiq_api_url" 
                        value="<?php echo esc_attr(get_option('nerdsiq_api_url', 'http://nerdsiq-api:8000')); ?>" 
                        class="regular-text"
                    >
                    <p class="description">
                        The URL of the NerdsIQ API backend. Use <code>http://nerdsiq-api:8000</code> for Docker or <code>http://localhost:8000</code> for local development.
                    </p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_widget_enabled">Enable Widget</label>
                </th>
                <td>
                    <label>
                        <input 
                            type="checkbox" 
                            id="nerdsiq_widget_enabled" 
                            name="nerdsiq_widget_enabled" 
                            value="1" 
                            <?php checked(get_option('nerdsiq_widget_enabled', '1'), '1'); ?>
                        >
                        Show the chat widget on the frontend
                    </label>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_openai_model">AI Model</label>
                </th>
                <td>
                    <?php $current_model = get_option('nerdsiq_openai_model', 'gpt-4o-mini'); ?>
                    <select id="nerdsiq_openai_model" name="nerdsiq_openai_model" class="regular-text">
                        <option value="gpt-4o" <?php selected($current_model, 'gpt-4o'); ?>>
                            GPT-4o (Most Accurate - $5/1M tokens)
                        </option>
                        <option value="gpt-4o-mini" <?php selected($current_model, 'gpt-4o-mini'); ?>>
                            GPT-4o Mini (Fast &amp; Cheap - $0.15/1M tokens)
                        </option>
                        <option value="o1" <?php selected($current_model, 'o1'); ?>>
                            o1 (Complex Reasoning - $15/1M tokens)
                        </option>
                        <option value="o1-mini" <?php selected($current_model, 'o1-mini'); ?>>
                            o1 Mini (Balanced Reasoning - $3/1M tokens)
                        </option>
                        <option value="gpt-4-turbo" <?php selected($current_model, 'gpt-4-turbo'); ?>>
                            GPT-4 Turbo (Legacy - $10/1M tokens)
                        </option>
                        <option value="gpt-3.5-turbo" <?php selected($current_model, 'gpt-3.5-turbo'); ?>>
                            GPT-3.5 Turbo (Basic - $0.50/1M tokens)
                        </option>
                    </select>
                    <p class="description">
                        Select the OpenAI model for generating answers. GPT-4o provides the best accuracy, 
                        while GPT-4o Mini is faster and cheaper for simple queries.
                    </p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_wp_auth_secret">WordPress SSO Secret</label>
                </th>
                <td>
                    <input 
                        type="password" 
                        id="nerdsiq_wp_auth_secret" 
                        name="nerdsiq_wp_auth_secret" 
                        value="<?php echo esc_attr(get_option('nerdsiq_wp_auth_secret', '')); ?>" 
                        class="regular-text"
                        autocomplete="new-password"
                    >
                    <p class="description">
                        Shared secret for WordPress SSO. Must match the <code>WP_AUTH_SECRET</code> in the API backend .env file.
                        When configured, logged-in WordPress users are automatically authenticated with NerdsIQ.
                    </p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label>Allowed Roles</label>
                </th>
                <td>
                    <?php
                    $allowed_roles = get_option('nerdsiq_allowed_roles', ['administrator']);
                    // Ensure $allowed_roles is always an array
                    if (!is_array($allowed_roles)) {
                        $allowed_roles = ['administrator'];
                    }
                    $all_roles = wp_roles()->roles;
                    ?>
                    <fieldset>
                        <legend class="screen-reader-text">Allowed Roles</legend>
                        <?php foreach ($all_roles as $role_slug => $role_info): ?>
                            <label style="display: block; margin-bottom: 8px;">
                                <input 
                                    type="checkbox" 
                                    name="nerdsiq_allowed_roles[]" 
                                    value="<?php echo esc_attr($role_slug); ?>"
                                    <?php checked(in_array($role_slug, $allowed_roles)); ?>
                                >
                                <?php echo esc_html(translate_user_role($role_info['name'])); ?>
                            </label>
                        <?php endforeach; ?>
                    </fieldset>
                    <p class="description">
                        Select which WordPress roles can access the NerdsIQ chatbot. 
                        Only users with these roles will see the chat widget.
                    </p>
                </td>
            </tr>
        </table>
        
        <h2 class="title">Page Display Settings</h2>
        <p>Control which pages and posts show the chat widget.</p>
        <table class="form-table" role="presentation">
            <tr>
                <th scope="row">
                    <label for="nerdsiq_display_mode">Display Mode</label>
                </th>
                <td>
                    <?php $display_mode = get_option('nerdsiq_display_mode', 'all'); ?>
                    <select id="nerdsiq_display_mode" name="nerdsiq_display_mode">
                        <option value="all" <?php selected($display_mode, 'all'); ?>>
                            Show on all pages
                        </option>
                        <option value="include" <?php selected($display_mode, 'include'); ?>>
                            Show only on selected pages
                        </option>
                        <option value="exclude" <?php selected($display_mode, 'exclude'); ?>>
                            Hide on selected pages
                        </option>
                    </select>
                    <p class="description">
                        Choose how the widget should be displayed across your site.
                    </p>
                </td>
            </tr>
            <tr id="nerdsiq-pages-row" style="<?php echo $display_mode === 'all' ? 'display:none;' : ''; ?>">
                <th scope="row">
                    <label>Select Pages/Posts</label>
                </th>
                <td>
                    <?php
                    $selected_pages = get_option('nerdsiq_selected_pages', []);
                    if (!is_array($selected_pages)) {
                        $selected_pages = [];
                    }
                    $selected_pages = array_map('intval', $selected_pages);
                    
                    // Get all pages
                    $pages = get_pages(['sort_column' => 'menu_order,post_title']);
                    // Get all published posts
                    $posts = get_posts([
                        'post_type' => 'post',
                        'post_status' => 'publish',
                        'numberposts' => -1,
                        'orderby' => 'title',
                        'order' => 'ASC',
                    ]);
                    ?>
                    
                    <select 
                        id="nerdsiq_selected_pages" 
                        name="nerdsiq_selected_pages[]" 
                        multiple="multiple" 
                        class="nerdsiq-select2"
                        style="width: 100%; max-width: 500px;"
                    >
                        <?php if (!empty($pages)): ?>
                            <optgroup label="Pages">
                                <?php foreach ($pages as $page): ?>
                                    <option 
                                        value="<?php echo esc_attr($page->ID); ?>"
                                        <?php selected(in_array($page->ID, $selected_pages, true)); ?>
                                    >
                                        <?php echo esc_html($page->post_title); ?> (<?php echo esc_html($page->post_name); ?>)
                                    </option>
                                <?php endforeach; ?>
                            </optgroup>
                        <?php endif; ?>
                        
                        <?php if (!empty($posts)): ?>
                            <optgroup label="Posts">
                                <?php foreach ($posts as $post): ?>
                                    <option 
                                        value="<?php echo esc_attr($post->ID); ?>"
                                        <?php selected(in_array($post->ID, $selected_pages, true)); ?>
                                    >
                                        <?php echo esc_html($post->post_title); ?>
                                    </option>
                                <?php endforeach; ?>
                            </optgroup>
                        <?php endif; ?>
                    </select>
                    
                    <p class="description">
                        <?php if ($display_mode === 'include'): ?>
                            The chat widget will <strong>only</strong> appear on the selected pages/posts.
                        <?php else: ?>
                            The chat widget will appear on <strong>all pages except</strong> the selected ones.
                        <?php endif; ?>
                    </p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_restrict_pages">Restrict Page Access</label>
                </th>
                <td>
                    <label>
                        <input 
                            type="checkbox" 
                            id="nerdsiq_restrict_pages" 
                            name="nerdsiq_restrict_pages" 
                            value="1" 
                            <?php checked(get_option('nerdsiq_restrict_pages', '0'), '1'); ?>
                        >
                        Require login to access selected pages
                    </label>
                    <p class="description">
                        When enabled, visitors who are not logged in will be redirected to the WordPress login page 
                        when trying to access the pages selected above (in "include" mode only).
                    </p>
                </td>
            </tr>
        </table>
        
        <script>
        jQuery(document).ready(function($) {
            // Initialize Select2 for page/post selection
            if ($.fn.select2) {
                $('.nerdsiq-select2').select2({
                    placeholder: 'Search and select pages/posts...',
                    allowClear: true,
                    width: '100%'
                });
            }
            
            // Toggle pages row based on display mode
            $('#nerdsiq_display_mode').on('change', function() {
                var mode = $(this).val();
                if (mode === 'all') {
                    $('#nerdsiq-pages-row').hide();
                } else {
                    $('#nerdsiq-pages-row').show();
                }
            });
        });
        </script>
        
        <h2 class="title">Appearance Settings</h2>
        <table class="form-table" role="presentation">
            <tr>
                <th scope="row">
                    <label for="nerdsiq_primary_color">Primary Color</label>
                </th>
                <td>
                    <input 
                        type="color" 
                        id="nerdsiq_primary_color" 
                        name="nerdsiq_primary_color" 
                        value="<?php echo esc_attr(get_option('nerdsiq_primary_color', '#0047AC')); ?>"
                    >
                    <input 
                        type="text" 
                        value="<?php echo esc_attr(get_option('nerdsiq_primary_color', '#0047AC')); ?>"
                        class="small-text"
                        id="nerdsiq_primary_color_text"
                        pattern="^#[0-9A-Fa-f]{6}$"
                    >
                    <p class="description">Main color for header, buttons, and user messages. Default: #0047AC (NerdsToGo blue)</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_accent_color">Accent Color</label>
                </th>
                <td>
                    <input 
                        type="color" 
                        id="nerdsiq_accent_color" 
                        name="nerdsiq_accent_color" 
                        value="<?php echo esc_attr(get_option('nerdsiq_accent_color', '#FFD301')); ?>"
                    >
                    <input 
                        type="text" 
                        value="<?php echo esc_attr(get_option('nerdsiq_accent_color', '#FFD301')); ?>"
                        class="small-text"
                        id="nerdsiq_accent_color_text"
                        pattern="^#[0-9A-Fa-f]{6}$"
                    >
                    <p class="description">Accent color for logo badge. Default: #FFD301 (NerdsToGo yellow)</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_widget_position">Widget Position</label>
                </th>
                <td>
                    <select id="nerdsiq_widget_position" name="nerdsiq_widget_position">
                        <option value="bottom-right" <?php selected(get_option('nerdsiq_widget_position', 'bottom-right'), 'bottom-right'); ?>>Bottom Right</option>
                        <option value="bottom-left" <?php selected(get_option('nerdsiq_widget_position', 'bottom-right'), 'bottom-left'); ?>>Bottom Left</option>
                    </select>
                    <p class="description">Where the chat widget appears on the screen.</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_bottom_padding">Bottom Padding</label>
                </th>
                <td>
                    <input 
                        type="number" 
                        id="nerdsiq_bottom_padding" 
                        name="nerdsiq_bottom_padding" 
                        value="<?php echo esc_attr(get_option('nerdsiq_bottom_padding', '20')); ?>"
                        min="0"
                        max="500"
                        style="width: 80px;"
                    > px
                    <p class="description">Distance from the bottom of the screen. Default: 20px. Increase if you have a footer bar or other elements.</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_side_padding">Side Padding</label>
                </th>
                <td>
                    <input 
                        type="number" 
                        id="nerdsiq_side_padding" 
                        name="nerdsiq_side_padding" 
                        value="<?php echo esc_attr(get_option('nerdsiq_side_padding', '20')); ?>"
                        min="0"
                        max="500"
                        style="width: 80px;"
                    > px
                    <p class="description">Distance from the left or right edge. Default: 20px.</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_header_title">Header Title</label>
                </th>
                <td>
                    <input 
                        type="text" 
                        id="nerdsiq_header_title" 
                        name="nerdsiq_header_title" 
                        value="<?php echo esc_attr(get_option('nerdsiq_header_title', 'NerdsIQ')); ?>"
                        class="regular-text"
                    >
                    <p class="description">The title displayed in the chat widget header.</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_header_subtitle">Header Subtitle</label>
                </th>
                <td>
                    <input 
                        type="text" 
                        id="nerdsiq_header_subtitle" 
                        name="nerdsiq_header_subtitle" 
                        value="<?php echo esc_attr(get_option('nerdsiq_header_subtitle', 'AI Knowledge Assistant')); ?>"
                        class="regular-text"
                    >
                    <p class="description">The subtitle displayed below the title.</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_welcome_message">Welcome Message</label>
                </th>
                <td>
                    <input 
                        type="text" 
                        id="nerdsiq_welcome_message" 
                        name="nerdsiq_welcome_message" 
                        value="<?php echo esc_attr(get_option('nerdsiq_welcome_message', 'Hello! How can I help you today?')); ?>"
                        class="large-text"
                    >
                    <p class="description">The first message shown when a user opens the chat. Use {name} to include the user's name.</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_logo_text">Logo Badge Text</label>
                </th>
                <td>
                    <input 
                        type="text" 
                        id="nerdsiq_logo_text" 
                        name="nerdsiq_logo_text" 
                        value="<?php echo esc_attr(get_option('nerdsiq_logo_text', 'IQ')); ?>"
                        class="small-text"
                        maxlength="3"
                    >
                    <p class="description">Short text (1-3 characters) shown in the logo badge.</p>
                </td>
            </tr>
            <tr>
                <th scope="row">
                    <label for="nerdsiq_input_placeholder">Input Placeholder</label>
                </th>
                <td>
                    <input 
                        type="text" 
                        id="nerdsiq_input_placeholder" 
                        name="nerdsiq_input_placeholder" 
                        value="<?php echo esc_attr(get_option('nerdsiq_input_placeholder', 'Ask a question...')); ?>"
                        class="regular-text"
                    >
                    <p class="description">Placeholder text in the message input field.</p>
                </td>
            </tr>
        </table>
        
        <h2 class="title">Document Access Settings</h2>
        <p>Control how users can view source documents referenced in chat responses.</p>
        <table class="form-table" role="presentation">
            <tr>
                <th scope="row">
                    <label for="nerdsiq_enable_document_viewer">Enable Document Viewer</label>
                </th>
                <td>
                    <label>
                        <input 
                            type="checkbox" 
                            id="nerdsiq_enable_document_viewer" 
                            name="nerdsiq_enable_document_viewer" 
                            value="1" 
                            <?php checked(get_option('nerdsiq_enable_document_viewer', '0'), '1'); ?>
                        >
                        Allow users to view source documents directly in the chat
                    </label>
                    <p class="description">
                        When enabled, users can click on source links to view the full Google Drive documents without needing Google Drive access. 
                        The backend API will fetch and display documents using its service account credentials. 
                        When disabled, source links will only show document names (not clickable).
                    </p>
                </td>
            </tr>
        </table>
        
        <?php submit_button('Save Settings'); ?>
    </form>
    
    <hr>
    
    <h2>Widget Preview</h2>
    <div id="nerdsiq-preview" style="position: relative; height: 400px; background: #f0f0f0; border-radius: 8px; padding: 20px;">
        <div id="nerdsiq-preview-widget" style="position: absolute; bottom: 20px; right: 20px;">
            <div style="width: 380px; background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); overflow: hidden;">
                <div id="preview-header" style="padding: 16px 20px; display: flex; align-items: center; gap: 12px; color: white;">
                    <div id="preview-logo" style="width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;"></div>
                    <div>
                        <div id="preview-title" style="font-size: 18px; font-weight: 600;"></div>
                        <div id="preview-subtitle" style="font-size: 12px; opacity: 0.8;"></div>
                    </div>
                </div>
                <div style="padding: 16px; min-height: 150px;">
                    <div id="preview-message" style="background: #f5f5f5; padding: 12px 16px; border-radius: 16px; font-size: 14px; max-width: 85%;"></div>
                </div>
                <div style="padding: 12px 16px; border-top: 1px solid #e5e5e5; display: flex; gap: 8px;">
                    <input type="text" id="preview-input" style="flex: 1; padding: 10px 14px; border: 1px solid #e5e5e5; border-radius: 24px; font-size: 14px;" disabled>
                    <button id="preview-send" style="width: 40px; height: 40px; border-radius: 50%; border: none; color: white; cursor: pointer;">
                        <svg viewBox="0 0 24 24" style="width: 18px; height: 18px; fill: white;"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <hr>
    
    <h2>Connection Test</h2>
    <p>
        <button type="button" id="nerdsiq-test-connection" class="button button-secondary">
            Test API Connection
        </button>
        <span id="nerdsiq-test-result" style="margin-left: 10px;"></span>
    </p>
    
    <script>
    jQuery(document).ready(function($) {
        // Connection test via WordPress AJAX
        $('#nerdsiq-test-connection').on('click', function() {
            var $button = $(this);
            var $result = $('#nerdsiq-test-result');
            
            $button.prop('disabled', true).text('Testing...');
            $result.text('');
            
            $.ajax({
                url: ajaxurl,
                method: 'POST',
                data: {
                    action: 'nerdsiq_test_connection'
                },
                timeout: 15000
            }).done(function(response) {
                if (response.success) {
                    $result.html('<span style="color: green;">✓ Connected successfully! Status: ' + response.data.status + '</span>');
                } else {
                    $result.html('<span style="color: red;">✗ Connection failed: ' + response.data.message + '</span>');
                }
            }).fail(function(xhr, status, error) {
                $result.html('<span style="color: red;">✗ Connection failed: ' + (error || status) + '</span>');
            }).always(function() {
                $button.prop('disabled', false).text('Test API Connection');
            });
        });
        
        // Color picker sync
        $('#nerdsiq_primary_color').on('input', function() {
            $('#nerdsiq_primary_color_text').val($(this).val());
            updatePreview();
        });
        $('#nerdsiq_primary_color_text').on('input', function() {
            if (/^#[0-9A-Fa-f]{6}$/.test($(this).val())) {
                $('#nerdsiq_primary_color').val($(this).val());
                updatePreview();
            }
        });
        
        $('#nerdsiq_accent_color').on('input', function() {
            $('#nerdsiq_accent_color_text').val($(this).val());
            updatePreview();
        });
        $('#nerdsiq_accent_color_text').on('input', function() {
            if (/^#[0-9A-Fa-f]{6}$/.test($(this).val())) {
                $('#nerdsiq_accent_color').val($(this).val());
                updatePreview();
            }
        });
        
        // Live preview updates
        $('#nerdsiq_header_title, #nerdsiq_header_subtitle, #nerdsiq_welcome_message, #nerdsiq_logo_text, #nerdsiq_input_placeholder, #nerdsiq_widget_position').on('input change', updatePreview);
        
        function updatePreview() {
            var primaryColor = $('#nerdsiq_primary_color').val();
            var accentColor = $('#nerdsiq_accent_color').val();
            var title = $('#nerdsiq_header_title').val() || 'NerdsIQ';
            var subtitle = $('#nerdsiq_header_subtitle').val() || 'AI Knowledge Assistant';
            var welcomeMessage = $('#nerdsiq_welcome_message').val() || 'Hello! How can I help you today?';
            var logoText = $('#nerdsiq_logo_text').val() || 'IQ';
            var placeholder = $('#nerdsiq_input_placeholder').val() || 'Ask a question...';
            var position = $('#nerdsiq_widget_position').val();
            
            // Update preview
            $('#preview-header').css('background', primaryColor);
            $('#preview-logo').css('background', accentColor).css('color', '#333').text(logoText);
            $('#preview-title').text(title);
            $('#preview-subtitle').text(subtitle);
            $('#preview-message').text(welcomeMessage.replace('{name}', 'User'));
            $('#preview-input').attr('placeholder', placeholder);
            $('#preview-send').css('background', primaryColor);
            
            // Update position
            var $widget = $('#nerdsiq-preview-widget');
            if (position === 'bottom-left') {
                $widget.css({ left: '20px', right: 'auto' });
            } else {
                $widget.css({ left: 'auto', right: '20px' });
            }
        }
        
        // Initial preview
        updatePreview();
    });
    </script>
</div>
