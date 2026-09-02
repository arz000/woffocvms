/**
 * Dark Mode Initialization Script
 * 
 * This script runs as soon as the <head> of the document is parsed.
 * It checks the user's localStorage for a saved theme preference, or falls back
 * to their operating system's system-wide dark mode preference.
 * 
 * By applying the 'dark' class to the <html> element immediately, we prevent
 * the "Flash of Unstyled Content" (FOUC), avoiding a bright white screen 
 * briefly appearing before the CSS loads.
 */

if (localStorage.getItem('darkMode') === 'true' || 
    (!('darkMode' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    // Enable Dark Mode
    document.documentElement.classList.add('dark');
} else {
    // Disable Dark Mode
    document.documentElement.classList.remove('dark');
}
