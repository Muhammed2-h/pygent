# Browser Domain Instructions

When interacting with the browser, you must adhere to the following rules:

- **Observe before acting:** Always inspect the page state before taking action.
- **Prefer precise JS:** Use precise JavaScript execution over generic interactions when possible.
- **Avoid unnecessary DOM dumps:** Do not dump the entire DOM unless absolutely necessary; target specific elements instead.
- **Never guess selectors:** Always extract and use exact selectors based on the actual page structure, never guess them.
- **Separate navigation:** Treat navigation as a distinct step. Wait for the page to load completely before proceeding with subsequent actions.
- **Verify actions:** Always verify that an action produced the intended result (e.g., checking if an element appeared or URL changed).
- **Use CDP for difficult cases:** If standard automation fails, utilize the Chrome DevTools Protocol (CDP) for lower-level control.
- **Switch strategies after repeated failures:** If an approach fails multiple times, do not brute-force it. Re-evaluate and switch your strategy.
- **Ask user when blocked:** If you are completely blocked or require input to proceed (e.g., CAPTCHAs, 2FA), ask the user for assistance.
