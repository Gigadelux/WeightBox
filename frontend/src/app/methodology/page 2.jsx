import { Reveal } from "@/components/motion";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowUpRight,
  Cpu,
  Database,
  Layers,
  Scale,
} from "lucide-react";
export const metadata = { title: "Methodology" };

export default function Methodology() {
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
          Under the hood / Methodology
        </p>
        <h1>
          A fit estimate.
          <br />
          With its working shown
          <span className="heading-dot text-[var(--green)]">.</span>
        </h1>
        <p>
          WeightBox connects graphics cards with AI models to explore one
          practical question: is there enough video memory for the model’s
          weights?
        </p>
      </Reveal>
      <div className="document-grid grid grid-cols-[260px_minmax(0,_760px)] gap-15 [border-top:1px_solid_var(--line)] pt-8.75 max-[1190px]:grid-cols-[200px_minmax(0,_1fr)] max-[1190px]:gap-8.75 max-[850px]:grid-cols-[1fr]">
        <aside className="document-index flex flex-col gap-4.5 items-start text-[11px] text-[var(--muted)] sticky [top:30px] self-start max-[850px]:[position:static] max-[850px]:grid max-[850px]:grid-cols-[1fr_1fr] max-[850px]:gap-3.5 max-[850px]:pb-6.25 max-[850px]:[border-bottom:1px_solid_var(--line)] max-[620px]:text-[10px] max-[620px]:grid-cols-[1fr]">
          <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
            On this page
          </span>
          <a href="#memory">01 — Memory & quantization</a>
          <a href="#throughput">02 — Theoretical throughput</a>
          <a href="#comparisons">03 — Reading the comparisons</a>
          <a href="#project">04 — The project</a>
        </aside>
        <div className="document-content min-w-0">
          <section id="memory">
            <span className="section-symbol text-[var(--green)] block mb-4.25">
              <Layers size={23} />
            </span>
            <h2>Start with the weights.</h2>
            <p>
              We multiply the parameter count by the storage needed for each
              weight, then add a fixed 20% overhead allowance. All memory values
              use decimal gigabytes: 1 GB = 1,000,000,000 bytes.
            </p>
            <Reveal inView className="formula bg-[var(--surface)] py-6.25 px-7 my-6.25 mx-0 [border-left:2px_solid_#789067] max-[620px]:p-5">
              <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                Estimated memory / GB
              </span>
              <code>parameters × bytes per weight × 1.20 ÷ 10⁹</code>
            </Reveal>
            <div
              className="table-scroll overflow-x-auto [scrollbar-width:thin] [scrollbar-color:#c3cebc_transparent]"
              tabIndex={0}
              role="region"
              aria-label="Quantization assumptions"
            >
              <table className="data-table text-[11px] text-left">
                <thead>
                  <tr>
                    <th scope="col">Precision</th>
                    <th scope="col">Bytes / weight</th>
                    <th scope="col">Example: 7B parameters</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>FP16</td>
                    <td>2</td>
                    <td>16.8 GB</td>
                  </tr>
                  <tr>
                    <td>INT8</td>
                    <td>1</td>
                    <td>8.4 GB</td>
                  </tr>
                  <tr>
                    <td>INT4</td>
                    <td>0.5</td>
                    <td>4.2 GB</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p>
              The compatibility label shows the least quantization needed to fit
              within the GPU’s VRAM. If even INT4 exceeds memory, the model is
              marked <strong>Too large</strong>. Missing parameter counts
              produce <strong>Unknown</strong>, never a failed fit.
            </p>
            <div className="editorial-note [border-left:2px_solid_#b4a176] pt-1 pr-0 pb-1 pl-5.5 my-6.5 mx-0">
              <strong>Memory fit is only the first check.</strong>
              <p>
                The model doesn’t explicitly simulate context length, KV cache,
                batch size, activations, training, multi-GPU sharding, or
                runtime and kernel compatibility. The 20% allowance cannot cover
                every workload. Quantization may also affect quality and may not
                be available for every model.
              </p>
            </div>
            <p>
              FP16 headroom is GPU memory minus the FP16 footprint. A negative
              value means FP16 does not fit, even when a quantized version
              might.
            </p>
          </section>
          <section id="throughput">
            <span className="section-symbol text-[var(--green)] block mb-4.25">
              <Cpu size={23} />
            </span>
            <h2>An upper-level estimate, not a benchmark.</h2>
            <p>
              For models classified as generative, WeightBox estimates
              throughput by dividing memory bandwidth by the FP16 footprint. It
              assumes performance is limited by reading the weights.
            </p>
            <div className="formula bg-[var(--surface)] py-6.25 px-7 my-6.25 mx-0 [border-left:2px_solid_#789067] max-[620px]:p-5">
              <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                Theoretical FP16 throughput
              </span>
              <code>memory bandwidth / FP16 memory footprint</code>
            </div>
            <p>
              The result is a simplified bandwidth-based estimate. It excludes
              compute limits, framework overhead, context, batching, and
              scheduling. It is not a measured inference rate, and it does not
              predict INT8 or INT4 performance.
            </p>
            <p>
              Units follow the model’s domain: the warehouse uses tokens/sec or
              images/sec where applicable. Non-generative models show{" "}
              <strong>Not applicable</strong>; insufficient data shows{" "}
              <strong>Unknown</strong>. Throughput is kept inside model details
              so unlike units aren’t compared in one ranking.
            </p>
          </section>
          <section id="comparisons">
            <span className="section-symbol text-[var(--green)] block mb-4.25">
              <Scale size={23} />
            </span>
            <h2>Compare like with like.</h2>
            <h3>Models over time</h3>
            <p>
              The fit rate counts GPU–model pairs that fit at FP16, divided by
              pairs with known memory requirements. Each point groups models by
              release year and GPUs by architecture. Average headroom uses the
              sum of headroom divided by the number of known observations.
            </p>
            <h3>The memory trade-off</h3>
            <p>
              This analysis includes Language models released from 2020 onward.
              Each point groups GPUs by architecture and VRAM bucket, comparing
              their average memory with the number of distinct models that fit
              on at least one GPU in that group. Models per GB divides that
              distinct count by average VRAM.
            </p>
            <h3>Across AI domains</h3>
            <p>
              The percentage is the number of distinct models that fit at FP16
              on at least one GPU in a memory bucket, divided by models with
              known parameters in that domain. It does not mean that every GPU
              in the bucket fits those models. Distinct model counts across
              buckets or quantization tiers must not be added together.
            </p>
            <p>
              All three comparisons describe the full warehouse, independently
              of your selected GPU and model filters. The workbench’s summary,
              by contrast, always describes all models for your selected GPU.
            </p>
          </section>
          <section id="project">
            <span className="section-symbol text-[var(--green)] block mb-4.25">
              <Database size={23} />
            </span>
            <h2>A warehouse for asking better hardware questions.</h2>
            <p>
              WeightBox is a database systems project by Marco De Luca and
              Chrision Wynaar. It brings GPU specifications and notable AI
              models into a relational analytical warehouse, with a reproducible
              Python ETL pipeline and a Next.js workbench.
            </p>
            <p>
              The frontend reads PostgreSQL through server-side code. Model
              weights are not downloaded or executed, and selecting hardware
              does not run an inference workload. The dataset is a research
              snapshot, not a live catalogue or a manufacturer-verified
              specification sheet.
            </p>
            <Link
              className="button [border:1px_solid_var(--line)] py-2.75 px-4.25 inline-flex items-center justify-center gap-2 rounded-[4px] bg-[transparent] text-[11px] font-medium button-dark bg-[var(--forest)] [border-color:var(--forest)] text-[#f4faee]"
              href="/data"
            >
              Explore the dataset <ArrowUpRight size={16} />
            </Link>
          </section>
        </div>
      </div>
    </main>
  );
}
