/**
 * Theme switching mechanism for kweb UI.
 *
 * Three themes are supported: default, light and dark. The choice made in the
 * navbar dropdown is persisted in localStorage under 'kweb-theme'; when
 * nothing is stored the theme comes from the server rendered
 * data-default-theme attribute on <html> (KWEB_THEME), falling back to
 * 'default'. Only explicit menu selections are persisted, so a changed
 * KWEB_THEME still reaches users who never picked a theme.
 */
(function () {
    var THEME_KEY = 'kweb-theme';
    var DEFAULT_THEME = 'default';

    var THEMES = {
        'default': { icon: '\ud83c\udfa8', label: 'Default' },
        'light': { icon: '\u2600\ufe0f', label: 'Light' },
        'dark': { icon: '\ud83c\udf19', label: 'Dark' }
    };

    function isValidTheme(theme) {
        return Object.prototype.hasOwnProperty.call(THEMES, theme);
    }

    // Resolution order: stored choice, then server default, then 'default'
    function getStoredTheme() {
        var stored = null;
        try {
            stored = localStorage.getItem(THEME_KEY);
        } catch (e) {
            stored = null;
        }
        if (isValidTheme(stored)) {
            return stored;
        }
        var fallback = document.documentElement.getAttribute('data-default-theme');
        if (isValidTheme(fallback)) {
            return fallback;
        }
        return DEFAULT_THEME;
    }

    // Apply a theme: replace the theme-* class on <html> and update the toggle
    function applyTheme(theme) {
        if (!isValidTheme(theme)) {
            theme = DEFAULT_THEME;
        }
        var html = document.documentElement;
        var classes = html.className.split(/\s+/);
        var kept = [];
        for (var i = 0; i < classes.length; i++) {
            if (classes[i] && classes[i].indexOf('theme-') !== 0) {
                kept.push(classes[i]);
            }
        }
        kept.push('theme-' + theme);
        html.className = kept.join(' ');

        var info = THEMES[theme];
        var icon = document.getElementById('themeIcon');
        var label = document.getElementById('themeLabel');
        if (icon) {
            icon.textContent = info.icon;
        }
        if (label) {
            label.textContent = info.label;
        }
    }

    // Apply and (when requested) persist the choice
    function setTheme(theme, persist) {
        applyTheme(theme);
        if (persist) {
            try {
                localStorage.setItem(THEME_KEY, theme);
            } catch (e) {
                // localStorage may be disabled; the theme still applies for this page
            }
        }
    }

    // Wire up the theme dropdown links. The dropdown menu is a sibling of
    // #themeDropdown in templates/navbar.html, hence the adjacent combinator.
    function initThemeSelector() {
        var links = document.querySelectorAll('#themeDropdown + .dropdown-menu a[data-theme]');
        for (var i = 0; i < links.length; i++) {
            links[i].addEventListener('click', function (e) {
                e.preventDefault();
                var theme = this.getAttribute('data-theme');
                if (isValidTheme(theme)) {
                    setTheme(theme, true);
                }
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        setTheme(getStoredTheme(), false);
        initThemeSelector();
    });
})();
