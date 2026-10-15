# front-end-developer-test

# Zego

## About Us

At Zego, we understand that traditional motor insurance holds good drivers back.
It's too complicated, too expensive, and it doesn't reflect how well you actually drive.
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig economy workers to everyday car drivers, our customers are the driving force behind everything we do. We've sold tens of millions of policies and raised over $200 million in funding. And we’re only just getting started.

## Our Values

Zego is thoroughly committed to our values, which are the essence of our culture. Our values defined everything we do and how we do it.
They are the foundation of our company and the guiding principles for our employees. Our values are:

<table>
    <tr><td><img src="../doc/assets/blaze_a_trail.png?raw=true" alt="Blaze a trail" width=50></td><td><b>Blaze a trail</b></td><td>Emphasize curiosity and creativity to disrupt the industry through experimentation and evolution.</td></tr>
    <tr><td><img src="../doc/assets/drive_to_win.png?raw=true" alt="Drive to win" width=50></td><td><b>Drive to win</b></td><td>Strive for excellence by working smart, maintaining well-being, and fostering a safe, productive environment.</td></tr>
    <tr><td><img src="../doc/assets/take_the_wheel.png?raw=true" alt="Take the wheel" width=50></td><td><b>Take the wheel</b></td><td>Encourage ownership and trust, empowering individuals to fulfil commitments and prioritize customers.</td></tr>
    <tr><td><img src="../doc/assets/zego_before_ego.png?raw=true" alt="Zego before ego" width=50></td><td><b>Zego before ego</b></td><td>Promote unity by working as one team, celebrating diversity, and appreciating each individual's uniqueness.</td></tr>
</table>

## The Engineering Team

Zego puts technology first in its mission to define the future of the insurance industry.
By focusing on our customers' needs we're building the flexible and sustainable insurance products
and services that they deserve. And we do that by empowering a diverse, resourceful, and creative
team of engineers that thrive on challenge and innovation.

### How We Work

- **Collaboration & Knowledge Sharing** - Engineers at Zego work closely with cross-functional teams to gather requirements,
  deliver well-structured solutions, and contribute to code reviews to ensure high-quality output.
- Problem Solving & Innovation - We encourage analytical thinking and a proactive approach to tackling complex
  problems. Engineers are expected to contribute to discussions around optimization, scalability, and performance.
- **Continuous Learning & Growth** – At Zego, we provide engineers with abundant opportunities to learn, experiment and
  advance. We positively encourage the use of AI in our solutions as well as harnessing AI-powered tools to automate
  workflows, boost productivity and accelerate innovation. You’ll have our full support to refine your skills, stay
  ahead of best practices and explore the latest technologies that drive our products and services forward.
- **Ownership & Accountability** - Our team members take ownership of their work, ensuring that solutions are reliable,
  scalable, and aligned with business needs. We trust our engineers to take initiative and drive meaningful progress.

## Who should be taking this test?

This test has been created for all levels of developer, Junior through to Staff Engineer and everyone in between.
Ideally you have hands-on experience developing Next.js and Typescript solutions in a commercial setting. You have good problem-solving abilities, a passion for writing clean efficient, maintainable, scaleable code.

## The test: Server-Driven UI in Next.js (React) + TypeScript 🧪

You are tasked with building a basic **server-driven UI system** using **Next.js** and **TypeScript**. The client should render a simple form-driven UI based entirely on configuration data provided by a backend endpoint. The structure, layout, and component behaviour should all be dictated by the configuration.

### You must:

- Build a dynamic form renderer that consumes a config and displays a working UI.
- Support five core UI components:
  - Text (static label/paragraph)
  - Input (text field)
  - Dropdown (select menu)
  - Button (form submission)
  - Form (wrapper that handles submission and renders child components)
- Fetch the config from an API route (e.g. `/api/config`) and use it to drive rendering.
- On form submission, post form data to an API route (e.g. `/api/submit`) and log the field contents.

As this code might be deployed into production, please consider the following:

- **Error handling**: Handle potential errors in fetching the config and submitting the form.
- **Accessibility**: Ensure the UI is accessible (e.g. using ARIA roles, keyboard navigation).
- **Styling**: Use a CSS framework to style the components. You can use any styling approach you prefer (CSS modules, styled-components, etc.).
- **Testing**: Write unit tests for your components and integration tests for the form submission process.
- **Documentation**: Provide clear documentation on how to run the project, including setup instructions and any dependencies.
- **End to End Testing**: Think about your end to end test strategy. How would you test the flow of the application? What tools would you use? How would you ensure that the UI is rendered correctly based on the config? How would you ensure that your tests aren't brittle and won't fail as soon as the UI config is updated?

## The objective

This exercise gives you the opportunity to showcase your software design skills and coding craftsmanship. Start by presenting a high-level design that covers the full scope of your solution, then drill down into implementation details. We’ll evaluate how you organize your code and validate it through testing. Describe your problem-solving process - how you researched the domain, which tools you used to write and verify your code, and your overall development workflow. Be sure to include specifics about your IDE, any interactive AI tools (such as Copilot), and any other AI-powered utilities that played a role in your solution.
You might also consider how you would extend your code to handle more complex scenarios, such as adding more sophisticated components or how you would validate form data on the server before transitioning to another page. Also, feel free to set the repo up as you would a production project.

Extend this README to include a detailed discussion about your design decisions, the options you considered and
the trade-offs you made during the development process, and aspects you might have addressed or refined if not constrained by time.

# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@htmlene, @danyal-zego, @bogdangoie and @cypherlou) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.

# Solution: crawler dashboard

> **This app is not a solution to the front-end exercise above.** It's the web dashboard for the Python crawler
> exercise's HTTP API ([`../python/backend`](../python/backend/README.md)). It lives in this folder because it's the
> repo's front-end project.

The dashboard lets you:

- start a crawl, setting the URL, page budget, depth, concurrency and robots.txt handling;
- watch its status and statistics update while it runs;
- page through the pages it found (each with its links) and the distinct links;
- cancel it.

## Running it

The quickest way is Docker: `docker compose up --build` from the repo root starts both services (see
[Run everything with Docker](../README.md#run-everything-with-docker)). Without Docker:

You need the crawler API and the dashboard running side by side.

```bash
# terminal 1: the crawler API (Python 3.12+, uv)
cd python/backend
uv sync
uv run uvicorn crawler_api.main:app            # http://localhost:8000

# terminal 2: the dashboard (Node 24)
cd front-end
npm ci
npm run dev                                    # http://localhost:3000
```

The dashboard finds the crawler API through `CRAWLER_API_URL`, which defaults to `http://localhost:8000`. It's read on
the dashboard's server only:

```bash
CRAWLER_API_URL=http://crawler:9000 npm run dev
```

## How it works

```
 browser                          Next.js server (route handlers)             crawler API (FastAPI)
+---------------------+          +-------------------------------+          +--------------------+
| React client        |  /api/*  | GET/POST   /api/crawls        |  fetch   | /crawls ...        |
| components          | -------> | GET/DELETE /api/crawls/[id]   | -------> |                    |
| TanStack Query      | <------- | GET .../[id]/{status,pages,   | <------- |                    |
+---------------------+  same    |            links}             |  same    +--------------------+
                         status  +-------------------------------+  status
                         + body       502 if unreachable             + body
```

- **The browser only talks to the dashboard.** Route handlers under `src/app/api/crawls` call the crawler API from
  the server.
  - There's no CORS setup, and the crawler API's address never reaches the browser.
  - The handlers are an allow-list: only the seven crawl operations are exposed, and anything else is a Next.js 404.
- **Responses pass through unchanged.** Each handler returns the crawler API's status and body as they are, so its
  errors keep their meaning:
  - 404 for an unknown crawl;
  - 409 for cancelling a finished crawl;
  - 422 for an invalid request, which the form shows next to the right field.
- **An unreachable or slow backend** (10 s timeout) becomes a 502, which the pages explain. The crawl list keeps
  retrying, so it recovers on its own once the backend is back.
- **Polling only while something runs.**
  - A crawl's status is polled every second while it's `running`, and that stops when it finishes.
  - The crawl list refreshes every 2 s while any crawl is running.
  - The visible page of results refreshes while the crawl runs.
- **The API contract is generated, not hand-written.** `npm run gen:api` asks the backend for its OpenAPI schema (via
  `uv`) and generates `src/lib/api/schema.d.ts` with `openapi-typescript`. Both files are committed. CI regenerates
  them and fails on any difference, so a backend change can't silently drift from the UI's types.

```
src/
  app/
    page.tsx                   "/"            start form + crawl list
    crawls/[id]/page.tsx       "/crawls/:id"  crawl view (reads params inside Suspense)
    api/crawls/...             route handlers (one per crawl operation)
    providers.tsx              QueryClient (no retries for 4xx, one retry otherwise)
  components/                  StartCrawlForm, CrawlList, CrawlView, ResultsTabs, Paginator, ...
  lib/
    backend.ts                 server-only forward() to the crawler API
    client.ts                  typed browser calls + ApiError
    api/                       generated schema + friendly type aliases
  test/                        in-memory fake of /api (MSW) and render helpers
```

## Development

```bash
npm run dev          # dev server
npm test             # Vitest (watch); `npm test -- --run` for a single run
npm run lint         # ESLint
npm run typecheck    # next typegen && tsc --noEmit
npm run build        # production build
npm run gen:api      # regenerate src/lib/api from the backend (needs uv)
```

## Testing

There are 61 tests, using Vitest, React Testing Library and MSW. None of them need a network or a running backend.

- **Route handlers and the forwarder** run in Node, against an MSW stand-in for the crawler API. They cover:
  - status and body pass-through (200, 202, 404, 409, 422);
  - forwarding of query strings and bodies;
  - escaping of crawl ids;
  - 502 on a refused connection and on a timeout;
  - that only the expected route files exist.
- **Components** run in jsdom against `src/test/fakeApi.ts`, an in-memory fake of the dashboard's `/api`. Tests move
  its state forward (a crawl reports more pages, finishes, or the backend goes down) and assert what the user sees.
  Polling intervals are shortened in tests. "Polling stops" is asserted by counting requests, not by waiting on
  timers.

### End-to-end strategy

Browser end-to-end tests aren't included yet. This is how I'd add them with Playwright:

- **Run the real stack.** Playwright's `webServer` would start both the crawler API and `next start`. The crawler API
  would point at a small static site served by the test itself (a few HTML pages with known links), so crawls are
  fast and deterministic and never touch the internet.
- **Test user journeys, not markup.** For example: start a crawl, see it complete, open the links tab, and find the
  known links; or cancel a crawl of a deliberately slow page.
- **Select by role and accessible name**, the same queries the unit tests use. Avoid CSS classes or DOM structure,
  so styling changes don't break tests.
- **Wait for visible state** (`expect(...).toHaveText("completed")`, which retries) rather than fixed sleeps. Polling
  makes timing variable.
- **Keep the suite small.** It's there to prove the pieces are wired together; behaviour detail stays in the fast
  tests above.

## Limitations

- There's no authentication, and nothing stops a crawl from targeting internal network addresses. Both are inherited
  from the crawler API, which is meant for local or trusted use.
- Results are polled, not streamed. The crawler API doesn't stream yet.
- Two processes must run during development. A `docker compose` file starting both would be the next step.
