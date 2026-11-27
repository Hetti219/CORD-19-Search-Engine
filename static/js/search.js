/**
 * search.js
 * Client-side behaviour for the results page.
 *
 * The sort and results-per-page controls navigate by rebuilding the current
 * query string. Building it here, in JavaScript, means no user-supplied
 * value is ever interpolated into a server-rendered script context, so a
 * query parameter cannot break out of the page.
 */
(function () {
    'use strict';

    /**
     * Navigate to /search with one parameter replaced.
     *
     * The current query string is reused so that the active filters survive
     * the change. The `page` parameter is dropped because the result set is
     * being re-ordered or re-sized and the old page number is no longer
     * meaningful.
     *
     * @param {string} key   Name of the parameter to replace.
     * @param {string} value New value for that parameter.
     */
    function navigateWithParam(key, value) {
        var params = new URLSearchParams(window.location.search);
        params.delete('page');
        params.set(key, value);
        window.location.href = '/search?' + params.toString();
    }

    /**
     * Bind a select element to a query string parameter.
     *
     * @param {string} id    Id of the select element.
     * @param {string} key   Name of the query string parameter it controls.
     */
    function bindSelect(id, key) {
        var element = document.getElementById(id);
        if (!element) {
            return;
        }
        element.addEventListener('change', function () {
            navigateWithParam(key, element.value);
        });
    }

    bindSelect('sort-select', 'sort');
    bindSelect('per-page-select', 'per_page');
})();
