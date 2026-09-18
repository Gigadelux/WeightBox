import Link from "next/link";
export default function NotFound() {
  return (
    <main
      id="main"
      className="page-shell max-w-378 my-0 mx-auto pt-10.5 px-12 pb-16.25 max-[1190px]:px-7.5 max-[850px]:pt-7.5 max-[850px]:px-6 max-[850px]:pb-11.25 max-[620px]:pt-7 max-[620px]:px-4.5 max-[620px]:pb-8.75"
    >
      <div className="unavailable min-h-120 flex flex-col items-center justify-center text-center bg-[var(--paper)] [border:1px_solid_var(--line)] py-12 px-6 rounded-[6px]">
        <p className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
          404 / Off the workbench
        </p>
        <h1>This page isn’t here.</h1>
        <p>Let’s get you back to your hardware.</p>
        <Link
          className="button [border:1px_solid_var(--line)] py-2.75 px-4.25 inline-flex items-center justify-center gap-2 rounded-[4px] bg-[transparent] text-[11px] font-medium button-dark bg-[var(--forest)] [border-color:var(--forest)] text-[#f4faee]"
          href="/"
        >
          Open the workbench
        </Link>
      </div>
    </main>
  );
}
