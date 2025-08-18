import { test } from '@japa/runner'
import Crawler from '../../commands/crawler.js'

test.group('Console | Crawler Command', () => {
  test('should have correct command name and description', ({ assert }) => {
    assert.equal(Crawler.commandName, 'crawler')
    assert.equal(
      Crawler.description,
      'Crawls a website from a base URL, staying on the same domain'
    )
  })

  test('should have correct help information', ({ assert }) => {
    assert.isArray(Crawler.help)
    assert.lengthOf(Crawler.help, 2)
    assert.include(Crawler.help[0], 'Usage: node ace crawler <baseURL>')
    assert.include(Crawler.help[1], 'Example: node ace crawler https://www.zego.com')
  })

  test('should have correct command options', ({ assert }) => {
    assert.isDefined(Crawler.options)
    assert.isObject(Crawler.options)
  })

  test('should have correct static properties', ({ assert }) => {
    assert.isDefined(Crawler.commandName)
    assert.isDefined(Crawler.description)
    assert.isDefined(Crawler.help)
    assert.isDefined(Crawler.options)
  })
})
