FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY . .
RUN ./gradlew --no-daemon shadowJar

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/build/libs/crawler.jar /app/crawler.jar
ENTRYPOINT ["java", "-jar", "/app/crawler.jar"]
