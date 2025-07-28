# Server-Driven Dynamic Form in Next.js + TypeScript

## 💻 How to run the project

```bash
cd front-end/dynamic-form
npm install
npm run dev
```

## ⚙️ Core dependencies

- React Hook Form – Lightweight form state management

- Chakra UI – Component library used for styling, layout, and a11y support

- React Query – Handles API data fetching and caching

- Jest & React Testing Library – Testing framework and utilities

- Next.js – App router used for routing and SSR/SSG

## Testing strategy

I’ve written some simplified page-level integration tests that validate the form renders correctly from a config and accepts input.

If this were a production app, I would also:

- Write component-level tests for all field types (e.g., Input, Dropdown)

- Use Mock Service Worker (MSW) to mock API endpoints at runtime

- Add unhappy path coverage: missing config, validation errors, network failure

- Run E2E tests with Playwright or Cypress to simulate user interaction and validate real backend responses (including redirects and success screens)

## Server-side rendering

I fetch the config in getServerSideProps to:

- Mimic production-style SSR usage

- Allow dynamic config per request

- Help with caching, SEO, and quicker TTFB

While calling internal APIs from GSSP is generally discouraged (as it adds unnecessary overhead), I’ve done so here intentionally to simulate an external config API. In a production system, I’d use a shared data layer or service abstraction to avoid redundant requests.

React Query is initialized with initialData from GSSP, but for completeness, hydration could be improved with dehydrate/hydrate.

## Validation (Frontend + Backend)

Although not fully implemented here due to time constraints, I would use a shared yup schema for:

Frontend validation via React Hook Form + zodResolver

Backend schema checking to ensure incoming payloads are typed and secure

This approach guarantees consistent validation across client/server and reduces drift over time.

## App router vs Page router

I used the Page Router for speed of development. In a larger project, I’d carefully consider:

- Streaming vs SSR trade-offs
- File structure preferences
- Middleware requirements

## State persistence (incomplete form recovery)

To improve UX, I would allow the user to return to a partially-completed form by:

- Saving draft form data to localStorage

- Optionally POSTing partial submissions to a backend endpoint

- Reading draft data back into defaultValues when the form is mounted

## Config versioning

To avoid breaking in-progress forms when the config changes, I’d include a version key on the form config. Submitted data would include this version number, allowing the backend to:

- Reject invalid combinations

- Perform migrations

- Maintain compatibility

## Accessibility (A11y)

Accessibility was a focus throughout:

I ensured fields use proper labels, roles, and keyboard support (in part due to Chakra + Ark UI primitives)

Tests assert field presence via getByLabelText, which guarantees semantic connections between <label> and controls

The Select dropdown uses accessible primitives from Chakra’s underlying @zag-js system

Further improvements (e.g., automated a11y tests, screen reader audit) would be completed before production.

## Use of AI tools

ChatGPT – Used for research, refactoring suggestions, and this write-up

VS Code – With ESLint, Prettier, and Copilot inline suggestions

All AI-assisted code was reviewed, corrected, and manually integrated into the final solution.

## Areas for future extension

More component types: date picker, multi-select, file upload, conditional groups

Multi-step forms: wizard-style config with progress indicators and per-step validation

Form analytics: tracking dropout rate or average completion time

Admin config UI: A CMS-like editor to manage form configs visually

Preview mode: Allow previewing form from config before publishing

Conditional fields as part of validation: For example if a field depending on a certain value of another field

Validation of post body when received by backend. This could use the validation rules set out in the config
