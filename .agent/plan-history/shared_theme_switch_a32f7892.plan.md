---
name: Shared theme switch
overview: "Make the login page and the admin portal use the same theme control as the frontend sidebar: sun on the left, switch in the middle, moon on the right, with the active side in the highlight color and the other side grey."
todos: []
isProject: false
---

# Shared sun-switch-moon theme control

The frontend sidebar already defines the control in [`frontend/src/static/js/components/page-layout/sidebar/SidebarThemeSwitcher.tsx`](frontend/src/static/js/components/page-layout/sidebar/SidebarThemeSwitcher.tsx): sun, then a checkbox that is checked in dark mode, then moon. The active icon uses `--theme-color`; the other uses the grey icon color ([`PageSidebar.scss`](frontend/src/static/js/components/page-layout/PageSidebar.scss)).

The login card in [`templates/account/auth_card.html`](templates/account/auth_card.html) shows only one icon that swaps, plus a switch. The admin bar in [`templates/admin/base.html`](templates/admin/base.html) is a single sun/moon button with no switch. Both will use the sidebar layout. The stored choice stays `MediaCMS[mediacms][theme][mode]`, so the login page, the public site, and the admin portal keep the same mode.

## Control

Add [`templates/includes/theme_mode_switch.html`](templates/includes/theme_mode_switch.html) and include it from the login card and the admin navbar:

- Sun on the visual left, switch, moon on the visual right. The control itself is `dir="ltr"` so that order does not flip when the rest of the page is right-to-left. The login header row still places this whole control on the opposite side of the title.
- Checkbox checked means dark mode.
- Both icons stay visible. Light mode highlights the sun. Dark mode highlights the moon. The other icon is grey.
- The switch knob uses the same highlight when dark mode is on, matching `.checkbox-switcher` in the sidebar.

Highlight color is `var(--theme-color, var(--primary))`, so the public site keeps its theme color and the admin uses its primary color. Grey is the existing muted icon color on each surface.

## Wiring

- Login script in [`templates/account/auth_card.html`](templates/account/auth_card.html) keeps writing the shared mode and toggling `body.dark_theme` and `html.theme-darkly`. It only sets the checkbox; CSS chooses the highlighted icon. Remove the single swapping sun/moon icon.
- Admin script in [`templates/admin/includes/theme_mode.html`](templates/admin/includes/theme_mode.html) stops swapping `fa-sun` / `fa-moon`. It sets the same checkbox and still toggles the Jazzmin dark stylesheet. Clicking the switch changes the mode the same way the current button does.

Styles go in the login card (so the page is correct before a frontend rebuild) and in [`frontend/src/static/css/styles.scss`](frontend/src/static/css/styles.scss), plus a compact copy in [`static/jazzmin/css/main.css`](static/jazzmin/css/main.css) so the admin bar can show the same control without the frontend stylesheet.
