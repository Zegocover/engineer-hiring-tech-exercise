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
