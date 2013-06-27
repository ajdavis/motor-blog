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
});
