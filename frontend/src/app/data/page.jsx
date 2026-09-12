import { Reveal } from "@/components/motion";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Database } from "lucide-react";
import { getDataSummary } from "@/lib/warehouse";
import { integer } from "@/lib/format.mjs";
import { Unavailable } from "@/components/states";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const metadata = { title: "The dataset" };
function date(value) {
  return value
    ? new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      }).format(new Date(value)) + " UTC"
    : "Not checked";
}
export default async function DataPage() {
  let data;
  try {
    data = await getDataSummary();
  } catch {
    console.error("WeightBox: dataset summary is unavailable");
  }
  return (
    <main
      id="main"
      className="page-shell max-w-378 my-0 mx-auto pt-10.5 px-12 pb-16.25 max-[1190px]:px-7.5 max-[850px]:pt-7.5 max-[850px]:px-6 max-[850px]:pb-11.25 max-[620px]:pt-7 max-[620px]:px-4.5 max-[620px]:pb-8.75 document-page"
    >
      <Link
        className="back-link inline-flex items-center gap-1.75 text-[var(--muted)] text-[11px] mb-8.5 max-[620px]:mb-6.25 max-[620px]:min-h-8"
        href="/"
      >
        <ArrowLeft size={15} /> Back to the workbench
      </Link>
      <Reveal className="document-heading mb-12 max-w-200 max-[620px]:mb-8.75">
        <p className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
          Evidence, not guesswork / The dataset
        </p>
        <h1>
          Every number
          <br />
          starts somewhere<span className="heading-dot text-[var(--green)]">.</span>
        </h1>
        <p>
          Two source datasets. One compatibility warehouse. Here’s what’s
          included, what’s missing, and what has been checked.
        </p>
      </Reveal>
      {data ? (
        <>
          <Reveal stagger inView className="dataset-metrics grid grid-cols-[repeat(3,_1fr)] [border-top:1px_solid_var(--line)] [border-bottom:1px_solid_var(--line)] mt-2.5 mx-0 mb-8.5 py-7.5 px-0 max-[620px]:py-5 max-[620px]:px-0">
            {[
              [data.gpus, "Graphics cards", "Cleaned hardware records"],
              [data.models, "AI models", "Retained in the warehouse"],
              [data.pairs, "GPU × model pairs", "One record per combination"],
            ].map(([value, title, note]) => (
              <div key={title}>
                <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                  {title}
                </span>
                <strong>{integer(value)}</strong>
                <p>{note}</p>
              </div>
            ))}
          </Reveal>
          <div className="dataset-grid grid grid-cols-[1.1fr_1fr] gap-6 max-[850px]:grid-cols-[1fr]">
            <section className="chart-panel bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[6px] p-6.5 min-w-0 max-[620px]:py-5.25 max-[620px]:px-4.25">
              <div className="chart-heading flex justify-between items-start gap-5 mb-5 max-[620px]:flex-wrap max-[620px]:gap-3 max-[620px]:mb-3">
                <div>
                  <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                    Provenance
                  </span>
                  <h2>From source to workbench.</h2>
                  <p>
                    Latest recorded source loads. Loading a snapshot does not
                    make its contents current.
                  </p>
                </div>
                <Database size={23} />
              </div>
              <div className="source-list">
                {data.loads.map((load) => (
                  <div key={load.ods_table}>
                    <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                      {load.ods_table.includes("gpu") ? "Hardware" : "Models"}
                    </span>
                    <h3>{load.file_name}</h3>
                    <p>
                      {integer(load.row_count)} source rows · Loaded{" "}
                      {date(load.loaded_at)}
                    </p>
                  </div>
                ))}
              </div>
              <p className="chart-caption text-[10px] leading-[1.8] text-[var(--muted)] mt-3.5 max-w-212.5">
                GPU records come from the project’s TechPowerUp-derived
                graphics-card dataset; model records come from the notable AI
                models snapshot. The ETL removes rejected and duplicate records,
                keeps eligible GPUs from 2016 onward, and builds compatibility
                estimates. These retained models are evaluated against GPUs for
                compatibility; evaluation does not guarantee that a model fits.
                See the repository’s dataset documentation for source
                attribution and transformation rules.
              </p>
            </section>
            <section className="chart-panel bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[6px] p-6.5 min-w-0 max-[620px]:py-5.25 max-[620px]:px-4.25">
              <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                Read with context
              </span>
              <h2>The gaps are visible.</h2>
              <ul className="quality-list p-0 my-3.75 mx-0 list-none">
                <li>
                  <strong>{integer(data.estimated)}</strong>
                  <div>
                    <h3>GPUs with estimated bandwidth</h3>
                    <p>A missing memory specification was imputed.</p>
                  </div>
                </li>
                <li>
                  <strong>{integer(data.suspect)}</strong>
                  <div>
                    <h3>GPUs with specification flags</h3>
                    <p>The ETL identified a plausibility concern.</p>
                  </div>
                </li>
              </ul>
              <p className="chart-caption text-[10px] leading-[1.8] text-[var(--muted)] mt-3.5 max-w-212.5">
                Unflagged records can still contain source errors or imperfect
                architecture mappings. Specifications are dataset-derived, not
                manufacturer-verified. The two GPU quality categories may
                overlap.
                {data.unknown > 0 && (
                  <> Fit cannot be determined for {integer(data.unknown)} retained models without valid parameter counts.</>
                )}
              </p>
            </section>
          </div>
          <section className="chart-panel bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[6px] p-6.5 min-w-0 max-[620px]:py-5.25 max-[620px]:px-4.25 validation-panel mt-6">
            <div className="chart-heading flex justify-between items-start gap-5 mb-5 max-[620px]:flex-wrap max-[620px]:gap-3 max-[620px]:mb-3">
              <div>
                <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                  Warehouse validation
                </span>
                <h2>Missing values, accounted for.</h2>
                <p>
                  These checks validate the warehouse’s NULL rules. They do not
                  certify the source specifications or real-world performance.
                </p>
              </div>
              <span
                className={`status-badge inline-flex items-center gap-1.25 bg-[var(--status-bg)] text-[var(--status-color)] text-[9px] font-medium whitespace-nowrap py-1 px-1.75 rounded-[3px] ${data.validators.length === 6 && data.validators.every((row) => row.status === "pass") ? "fit" : "quantized"}`}
              >
                {data.validators.filter((row) => row.status === "pass").length}{" "}
                / 6 checks passed
              </span>
            </div>
            <div
              className="table-scroll overflow-x-auto [scrollbar-width:thin] [scrollbar-color:#c3cebc_transparent]"
              tabIndex={0}
              role="region"
              aria-label="Warehouse validation results"
            >
              <table className="data-table text-[11px] text-left">
                <thead>
                  <tr>
                    <th scope="col">Measure</th>
                    <th scope="col">Status</th>
                    <th scope="col">Known values</th>
                    <th scope="col">Missing values</th>
                    <th scope="col">Last checked</th>
                  </tr>
                </thead>
                <tbody>
                  {data.validators.map((row) => (
                    <tr key={row.attribute}>
                      <td>{row.attribute.replaceAll("_", " ")}</td>
                      <td>
                        <span
                          className={`status-badge inline-flex items-center gap-1.25 bg-[var(--status-bg)] text-[var(--status-color)] text-[9px] font-medium whitespace-nowrap py-1 px-1.75 rounded-[3px] ${row.status === "pass" ? "fit" : "quantized"}`}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td>{integer(row.not_null_count)}</td>
                      <td>{integer(row.null_count)}</td>
                      <td>{date(row.checked_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="dataset-domains grid grid-cols-[1fr_2fr] gap-10 mt-11.5 max-[850px]:grid-cols-[1fr] max-[850px]:gap-6.25">
            <div>
              <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                A broad view of AI
              </span>
              <h2>Beyond language models.</h2>
              <p>All domains are available in the model explorer.</p>
            </div>
            <ul>
              {data.domains.map((domain) => (
                <li key={domain.name}>
                  <Link href={`/?domain=${encodeURIComponent(domain.name)}`}>
                    <span>{domain.name}</span>
                    <strong>{integer(domain.total)}</strong>
                    <ArrowUpRight size={14} />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : (
        <Unavailable title="The dataset summary is unavailable." />
      )}
    </main>
  );
}
