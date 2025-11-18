ThisBuild / version := "0.1.0"

ThisBuild / scalaVersion := "2.13.17"

assembly / mainClass := Some("app.CrawlerApp")

ThisBuild / assemblyMergeStrategy := {
  case PathList("javax", "servlet", xs @ _*)         => MergeStrategy.first
  case PathList(ps @ _*) if ps.last endsWith "module-info.class" => MergeStrategy.first
  case "application.conf"                            => MergeStrategy.concat
  case "unwanted.txt"                                => MergeStrategy.discard
  case x =>
    val oldStrategy = (ThisBuild / assemblyMergeStrategy).value
    oldStrategy(x)
}

val AkkaVersion = "2.10.11"
val AkkaHttpVersion = "10.7.3"

libraryDependencies ++= Seq(
  "com.lihaoyi" %% "os-lib" % "0.11.6",

  "com.softwaremill.sttp.client4" %% "core" % "4.0.13",
  "com.lihaoyi" %% "requests" % "0.9.0",
  "net.ruippeixotog" %% "scala-scraper" % "3.2.0",
  "org.typelevel" %% "cats-core" % "2.13.0",

  "org.scalatest" %% "scalatest" % "3.2.19" % "test"
)

lazy val root = (project in file("."))
  .settings(
    name := "web-crawler-cli-app"
  )
