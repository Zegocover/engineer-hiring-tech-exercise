import net.ltgt.gradle.errorprone.errorprone

plugins {
    application
    checkstyle
    alias(libs.plugins.shadow)
    alias(libs.plugins.spotless)
    alias(libs.plugins.errorprone)
}

group = "com.hamzaali"
version = "0.1.0"

repositories {
    mavenCentral()
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

dependencies {
    errorprone(libs.errorprone.core)

    implementation(libs.jsoup)
    implementation(libs.picocli)

    testImplementation(platform(libs.junit.bom))
    testImplementation(libs.junit.jupiter)
    testImplementation(libs.assertj.core)
    testRuntimeOnly(libs.junit.platform.launcher)
}

application {
    mainClass = "com.hamzaali.crawler.Main"
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.compilerArgs.addAll(listOf("-Xlint:all", "-Werror"))
    options.errorprone.disableWarningsInGeneratedCode = true
}

spotless {
    java {
        palantirJavaFormat(libs.versions.palantir.java.format.get())
        trimTrailingWhitespace()
        endWithNewline()
    }
}

checkstyle {
    toolVersion = libs.versions.checkstyle.get()
    maxWarnings = 0
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        events("failed", "skipped")
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
}

tasks.shadowJar {
    archiveFileName = "crawler.jar"
}

tasks.build {
    dependsOn(tasks.shadowJar)
}
