import { Studio } from "@/components/Studio";
import data from "@/public/demo/valparai.json";
import type { DemoData } from "@/lib/types";

export default function Page() {
  return <Studio data={data as DemoData} />;
}
