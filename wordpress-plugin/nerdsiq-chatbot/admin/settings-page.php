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
        </table>
        
        <?php submit_button('Save Settings'); ?>
    </form>
    
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
        $('#nerdsiq-test-connection').on('click', function() {
            var $button = $(this);
            var $result = $('#nerdsiq-test-result');
            
            $button.prop('disabled', true).text('Testing...');
            $result.text('');
            
            $.ajax({
                url: '<?php echo esc_url(get_option('nerdsiq_api_url', 'http://nerdsiq-api:8000')); ?>/health',
                method: 'GET',
                timeout: 10000
            }).done(function(response) {
                $result.html('<span style="color: green;">✓ Connected successfully! Status: ' + response.status + '</span>');
            }).fail(function(xhr, status, error) {
                $result.html('<span style="color: red;">✗ Connection failed: ' + (error || status) + '</span>');
            }).always(function() {
                $button.prop('disabled', false).text('Test API Connection');
            });
        });
    });
    </script>
</div>
