// Friendly names for the crawler API models generated in schema.d.ts.
import type { components } from "./schema";

type Schemas = components["schemas"];

export type CrawlRequest = Schemas["CrawlRequest"];
export type CrawlSummary = Schemas["CrawlSummary"];
export type CrawlDetail = Schemas["CrawlDetail"];
export type CrawlStatus = Schemas["CrawlStatus"];
export type JobStatus = Schemas["JobStatus"];
export type Stats = Schemas["Stats"];
export type Limits = Schemas["Limits"];
export type Page = Schemas["Page"];
export type PageList = Schemas["PageList"];
export type LinkList = Schemas["LinkList"];
export type ValidationError = Schemas["ValidationError"];

/**
 * Body of any error response from the crawler API or the dashboard's own API.
 *
 * 422 responses carry a list of validation errors; 404, 409 and the
 * dashboard's 502 carry a message. Only the 422 shape is in the OpenAPI schema.
 */
export type ErrorBody = { detail: string | ValidationError[] };
