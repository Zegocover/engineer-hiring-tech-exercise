import { CrawlList } from "@/components/CrawlList";
import { StartCrawlForm } from "@/components/StartCrawlForm";

export default function Home() {
  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-2xl font-semibold">Crawls</h1>
      <StartCrawlForm />
      <CrawlList />
    </div>
  );
}
