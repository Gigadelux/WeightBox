"use client";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Database, RotateCw } from "lucide-react";
export function Unavailable({
  onRetry,
  title = "The workbench is waiting for data.",
  detail = "The warehouse is unavailable or hasn’t finished loading. Your selection is saved; try again once the database is ready.",
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <div
      className="unavailable min-h-120 flex flex-col items-center justify-center text-center bg-[var(--paper)] [border:1px_solid_var(--line)] py-12 px-6 rounded-[6px]"
      role="status"
    >
      <span className="state-icon w-16.5 h-16.5 grid place-items-center [border:1px_solid_var(--line)] text-[var(--green)] rounded-[8px] mb-5.5">
        <Database size={28} />
      </span>
      <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
        Connection interrupted
      </span>
      <h2>{title}</h2>
      <p>{detail}</p>
      <button
        className="button [border:1px_solid_var(--line)] py-2.75 px-4.25 inline-flex items-center justify-center gap-2 rounded-[4px] bg-[transparent] text-[11px] font-medium button-dark bg-[var(--forest)] [border-color:var(--forest)] text-[#f4faee]"
        disabled={pending}
        onClick={() =>
          startTransition(() => (onRetry ? onRetry() : router.refresh()))
        }
      >
        <RotateCw size={16} className={pending ? "spin" : ""} />
        {pending ? "Connecting…" : "Try again"}
      </button>
    </div>
  );
}
export function WorkbenchSkeleton() {
  return (
    <main
      id="main"
      className="page-shell max-w-378 my-0 mx-auto pt-10.5 px-12 pb-16.25 max-[1190px]:px-7.5 max-[850px]:pt-7.5 max-[850px]:px-6 max-[850px]:pb-11.25 max-[620px]:pt-7 max-[620px]:px-4.5 max-[620px]:pb-8.75"
      aria-busy="true"
      aria-label="Loading the workbench"
    >
      <div className="skeleton skeleton-heading w-[55%] h-20 mb-10" />
      <div className="workbench-grid grid grid-cols-[284px_minmax(0,_1fr)] [align-items:start] gap-7.5 relative min-[1500px]:grid-cols-[300px_minmax(0,_1fr)] min-[1500px]:gap-8.5 max-[1190px]:grid-cols-[250px_minmax(0,_1fr)] max-[1190px]:gap-5.5 max-[850px]:grid-cols-[220px_minmax(0,_1fr)] max-[850px]:gap-5 max-[620px]:grid-cols-[1fr] max-[620px]:gap-6">
        <div className="skeleton skeleton-rail h-140" />
        <div>
          <div className="skeleton skeleton-summary h-40 mb-6.25" />
          <div className="skeleton skeleton-results h-150" />
        </div>
      </div>
      <span className="sr-only">Loading hardware and model compatibility…</span>
    </main>
  );
}
