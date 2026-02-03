$(document).ready(function () {
    const $parserTypeField = $('#id_parser_type');

    // Direct date field parser fields
    const $directFields = [
        $('#id_json_path').parent(),
        $('#id_date_format').parent(),
    ];

    // Multi-field constructor parser fields
    const $multiFields = [
        $('#id_year_field').parent(),
        $('#id_month_field').parent(),
        $('#id_day_field').parent(),
    ];

    function togglePanels() {
        if ($parserTypeField.length === 0) return;

        if ($parserTypeField.val() === 'direct_date_field') {
            $directFields.forEach(f => f.show());
            $multiFields.forEach(f => f.hide());
        } else if ($parserTypeField.val() === 'multi_field_constructor') {
            $directFields.forEach(f => f.hide());
            $multiFields.forEach(f => f.show());
        } else {
            // Show all fields if parser type is not set
            $directFields.forEach(f => f.show());
            $multiFields.forEach(f => f.show());
        }
    }

    $parserTypeField.change(togglePanels);
    togglePanels(); // Initial call
});
