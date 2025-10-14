# Requirements

1. Java version > 17
2. Docker

# How to run

Go to the root of project and execute the command below

```shell
./gradlew bootBuildImage --imageName=crawler:latest
```

Please bear in mind Java path should be available (Java needs to be installed) to be able to run `./gradlew`

Once the docker image is pushed to local registry you can simply run the command line as follows

```shell
docker run crawler:latest https://www.example.com/
```

or if you want to specify how many concurrent requests initiate execute as follows

```shell
docker run crawler:latest https://www.example.com/ 50
```

That means 50 concurrent requests, default is 50

# How to run tests

Just simply execute the command below

```shell
./gradlew test
```

# Assumptions
1. Only public domain will be crawler and not local ones
2. URL should be in full form of it means having scheme, host, and full domain such as https://www.google.com
3. Base domain is based on the domain you give as the standard of internet, means https://google.com is different from https://www.google.com

# Improvements

1. I made the application to retry on too many requests (HTTP status 429) but due to lack of time, I did skip handling
   other errors and simple just showing error happened
2. I have not put stop count for instance say visit 1000 unique links and then stop or how many level of url can be
   crawler, therefor, if you pass https://www.google.com then literally if will search for all www.google.com endpoint
3. As the result is printed directly to console, I did not use the log4j to log the result as it will add additional fields which is not what I wanted, but as the improvement we could save the result of crawler to a file which then it distinguish it from the normal log 