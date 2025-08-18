import { test } from '@japa/runner'
import Webpage from '#models/webpage'
import MockAdapter from 'axios-mock-adapter'
import axios from 'axios'

const MOCK_BASE_URL = 'https://example.com'

const MOCK_HTML_CONTENT = `
  <html lang="en">
    <head><title>Test Page</title></head>
    <body>
      <a href="/about">About Us</a>
      <a href="https://example.com/contact">Contact</a>
      <a href="https://example.com/contact#form">Contact Form</a>
      <a href="https://external.com/other">External Link</a>
      <a href="mailto:test@example.com">Email Us</a>
      <a href="/about">Duplicate About</a>
      <a href="/valid-relative-url"></a>
    </body>
  </html>
`

test.group('Webpage Model', (group) => {
  let mock: MockAdapter
  group.each.setup(() => {
    mock = new MockAdapter(axios)
  })

  group.each.teardown(() => mock.restore())

  test('constructor should correctly initialize with a valid URL', ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)

    assert.instanceOf(page.url, URL)
    assert.equal(page.url.href, `${MOCK_BASE_URL}/`)
  })

  test('constructor should throw for an invalid URL', ({ assert }) => {
    assert.throws(() => new Webpage('not-a-valid-url'), 'Invalid URL')
  })

  test('load() should fetch and store HTML content', async ({ assert }) => {
    mock.onGet(`${MOCK_BASE_URL}/`).reply(200, MOCK_HTML_CONTENT, { 'content-type': 'text/html' })

    const page = new Webpage(MOCK_BASE_URL)
    await page.load()

    assert.equal(page.htmlContent, MOCK_HTML_CONTENT)
  })

  test('load() should not store content for non-HTML responses', async ({ assert }) => {
    mock
      .onGet(`${MOCK_BASE_URL}/`)
      .reply(200, { message: 'hi' }, { 'content-type': 'application/json' })

    const page = new Webpage(MOCK_BASE_URL)
    await page.load()

    assert.isEmpty(page.htmlContent)
  })

  test('load() should throw if the network request fails', async ({ assert }) => {
    mock.onGet(`${MOCK_BASE_URL}/`).networkError()

    const page = new Webpage(MOCK_BASE_URL)

    await assert.rejects(async () => {
      await page.load()
    }, 'Network Error')
  })

  test('getLinks() should return an empty array if HTML is not loaded', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)
    const links = await page.getLinks()

    assert.deepEqual(links, [])
  })

  test('getLinks() should extract, normalize, and avoid duplicates', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)
    page.htmlContent = MOCK_HTML_CONTENT

    const links = await page.getLinks()

    assert.lengthOf(links, 3)
    assert.include(links, 'https://example.com/contact')
    assert.include(links, 'https://example.com/about')
  })

  test('getLinks() should not include external links', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)
    page.htmlContent = MOCK_HTML_CONTENT

    const links = await page.getLinks()

    assert.notInclude(links, 'https://external.com/other')
  })

  test('getLinks() should ignore empty href attributes', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)
    page.htmlContent = '<body><a href="">Empty Href</a><a href="/about"></a></body>'

    const links = await page.getLinks()

    assert.lengthOf(links, 1)
    assert.include(links, 'https://example.com/about')
  })
})
