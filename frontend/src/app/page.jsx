import { Reveal } from "@/components/motion";
import { Suspense } from "react";
import { getWorkbench, getAnalytics } from "@/lib/warehouse";
import { Workbench } from "@/components/workbench";
import { Analytics } from "@/components/analytics";
import { Unavailable } from "@/components/states";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function HardwareAnalytics() {
  const data = await getAnalytics();
  return <Analytics data={data} />;
}
export default async function Home({ searchParams }) {
  let data;
  try {
    data = await getWorkbench(await searchParams);
  } catch {
    console.error("WeightBox: workbench data is unavailable");
  }
  return (
    <main
      id="main"
      className="page-shell max-w-378 my-0 mx-auto pt-10.5 px-12 pb-16.25 max-[1190px]:px-7.5 max-[850px]:pt-7.5 max-[850px]:px-6 max-[850px]:pb-11.25 max-[620px]:pt-7 max-[620px]:px-4.5 max-[620px]:pb-8.75"
    >
      <Reveal className="page-heading flex justify-between items-center mb-8.75 max-[620px]:mb-6.75">
        <div>
          <p className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
            <span className="tiny-square w-1.25 h-1.25 bg-[var(--green)] inline-block shrink-0" />{" "}
            The hardware workbench
          </p>
          <h1>
            What fits on your GPU
            <span className="heading-dot text-[var(--green)]">?</span>
          </h1>
          <p className="page-intro text-[var(--muted)] text-[13px] max-[620px]:text-[12px] max-[620px]:leading-[1.8] max-[620px]:max-w-70">
            Pick your hardware. Find your models. Understand the trade-offs.
          </p>
        </div>
        <span
          className="heading-index font-mono text-[9px] leading-[1.8] tracking-[.12em] text-[var(--muted)] pl-4.5 [border-left:1px_solid_var(--line)] max-[850px]:hidden"
          aria-hidden="true"
        >
          WB / 001
          <br />
          MEMORY EXPLORER
        </span>
      </Reveal>
      {data ? (
        <>
          <Workbench data={data} />
          <Suspense
            fallback={
              <section
                className="analytics-loading h-110 mt-15 skeleton"
                aria-label="Loading hardware comparisons"
              />
            }
          >
            <HardwareAnalytics />
          </Suspense>
        </>
      ) : (
        <Unavailable />
      )}
    </main>
  );
}
