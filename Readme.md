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