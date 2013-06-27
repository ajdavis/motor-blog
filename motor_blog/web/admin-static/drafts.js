$(function() {
    /* Disable "add" buttons if "name" not entered. */
    $('.guest-access-token-form').each(function() {
        var $form = $(this),
            $submit = $('.guest-access-token-submit', $form);

        $('.guest-access-token-name-input', $form).keyup(function() {
            if ($(this).val()) {
                $submit.removeAttr('disabled');
            } else {
                $submit.attr('disabled', '');
            }
        });
    });

    /* Confirm before revoking. */
    $('.guest-url-delete-form').submit(function() {
        return confirm("Really revoke access?");
    });

    /* Copy-to-clipboard buttons. */
    $('.guest-url-copy-form').each(function() {
        var clip = new ZeroClipboard($('.copy-button', this)[0]);
        clip.on('complete', function() {
            var copy_message = $('.copy-message', this.parentNode);

            copy_message.animate({opacity: 1}, 1000, function() {
                copy_message.animate({opacity: 0});
            });
        });
    });
});
