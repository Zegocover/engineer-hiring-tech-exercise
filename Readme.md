### Prerequisites
1. Scala CLI [to install](https://scala-cli.virtuslab.org/install)
2. Java version >= 13

### Used libraries
1. [Jsoup](https://jsoup.org)
    - Parse html
    - Fetch http resource, better to replace with something
2. [ZIO + ZIO Streams](https://zio.dev)
    - Manage concurrency and parallelism

### Run
```shell
scala-cli . -- <url to parse>
```

### To Run test
```shell
scala-cli . test
```

### Improvements
1. Add DI. As application grows bigger with more dependencies it will become harder to maintain all of them in multiple places. 
2. Add configurable client with more option to handle, e.g. timeout, follow redirect, retries, error handling, domain.
3. Add configuration both for crawler and parser. This options can be in form of config file or passed as optional argument through command line.
4. Check what can be done with JS as many modern frontend frameworks generate elements.