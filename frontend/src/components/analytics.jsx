"use client";

import { useState } from "react";
import { Reveal } from "./motion";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import {
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronDown,
  Table2,
} from "lucide-react";
import Link from "next/link";
import { bucketOrder, integer, number } from "@/lib/format.mjs";

const colors = ["#a7ce98", "#e0bc7f", "#b9ade0"];
function ChartData({ label, headings, rows }) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="chart-data [border-top:1px_solid_var(--line)] mt-4.75 pt-1"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        <Table2 size={13} />
        {label} <ChevronDown size={13} />
      </summary>
      {open && (
        <div
          className="table-scroll overflow-x-auto [scrollbar-width:thin] [scrollbar-color:#c3cebc_transparent]"
          tabIndex={0}
          role="region"
          aria-label={label}
        >
          <table className="data-table text-[11px] text-left">
            <thead>
              <tr>
                {headings.map((heading) => (
                  <th key={heading} scope="col">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  );
}
function ChartEmpty({ failed = false }) {
  return (
    <div className="chart-empty min-h-61.25 flex flex-col items-center justify-center gap-3 text-[var(--muted)] text-center text-[12px]">
      <ChartNoAxesCombined size={25} />
      <p>
        {failed
          ? "This comparison is temporarily unavailable."
          : "No observations for this selection."}
      </p>
      {failed && (
        <p className="muted text-[var(--muted)]">
          Reload the page to try again. Your model results are still available.
        </p>
      )}
    </div>
  );
}
function ChartSelect({ label, value, onChange, children }) {
  return (
    <label className="chart-select inline-flex flex-col gap-1.25 text-[9px] text-[var(--muted)] mb-3 max-[620px]:mb-2">
      <span>{label}</span>
      <span className="select-wrap inline-flex items-center relative [border:1px_solid_var(--line)] rounded-[4px] bg-[var(--paper)]">
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          {children}
        </select>
        <ChevronDown size={13} />
      </span>
    </label>
  );
}

function Timeline({ rows }) {
  const architectures = [
    ...new Set((rows || []).map((row) => row.architecture)),
  ].sort();
  const defaults = ["Ampere", "RDNA 2", "Ada Lovelace"].filter((name) =>
    architectures.includes(name),
  );
  const [selected, setSelected] = useState(() => {
    const initial = defaults.length ? defaults : architectures.slice(0, 3);
    return [initial[0] || "", initial[1] || "", initial[2] || ""];
  });
  const [since, setSince] = useState("2000");
  const points = (rows || []).filter(
    (row) => row.year >= Number(since) && selected.includes(row.architecture),
  );
  const chartRows = [...new Set(points.map((row) => row.year))].map((year) => ({
    year,
    ...Object.fromEntries(
      points
        .filter((row) => row.year === year)
        .map((row) => [row.architecture, row.rate]),
    ),
  }));
  return (
    <article className="chart-panel bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[6px] p-6.5 min-w-0 max-[620px]:py-5.25 max-[620px]:px-4.25 timeline-panel">
      <div className="chart-heading flex justify-between items-start gap-5 mb-5 max-[620px]:flex-wrap max-[620px]:gap-3 max-[620px]:mb-3">
        <div>
          <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
            01 / Models over time
          </span>
          <h3>As models grow, what still fits?</h3>
          <p>FP16 fit rate by model release year and GPU architecture.</p>
        </div>
        <ChartSelect label="Model releases" value={since} onChange={setSince}>
          <option value="0">All years</option>
          <option value="2000">Since 2000</option>
          <option value="2010">Since 2010</option>
          <option value="2020">Since 2020</option>
        </ChartSelect>
      </div>
      {rows ? (
        <>
          <div className="architecture-controls flex flex-wrap gap-6.25 mb-3.75 max-[620px]:gap-[9px_18px] max-[620px]:mb-3">
            {[0, 1, 2].map((i) => (
              <label key={i}>
                <span
                  className="legend-line h-0.5 w-4.25 max-[620px]:w-3.25"
                  style={{ background: colors[i] }}
                />
                <span className="sr-only">Comparison architecture {i + 1}</span>
                <select
                  value={selected[i] || ""}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSelected((current) =>
                      current.map((name, index) =>
                        index === i ? value : name,
                      ),
                    );
                  }}
                >
                  <option value="">No comparison</option>
                  {architectures.map((name) => (
                    <option
                      key={name}
                      value={name}
                      disabled={selected.includes(name) && selected[i] !== name}
                    >
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          {points.length ? (
            <div
              className="chart-plot w-full min-w-0"
              role="img"
              aria-label="Line chart: percentage of known GPU–model pairs that fit at FP16. Exact values are in the data table below."
            >
              <ResponsiveContainer width="100%" height={245} minWidth={0}>
                <LineChart
                  data={chartRows}
                  margin={{ top: 12, right: 18, bottom: 2, left: -18 }}
                  accessibilityLayer
                >
                  <CartesianGrid
                    vertical={false}
                    stroke="var(--line)"
                    strokeDasharray="3 5"
                  />
                  <XAxis
                    dataKey="year"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: "var(--muted)" }}
                    minTickGap={40}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tickFormatter={(value) => `${value}%`}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: "var(--muted)" }}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 4,
                      borderColor: "var(--line)",
                      backgroundColor: "var(--paper)",
                      color: "var(--ink)",
                      fontSize: 12,
                    }}
                    formatter={(value, name) => [`${number(value)}%`, name]}
                    labelFormatter={(year) => `Models released in ${year}`}
                  />
                  {selected.map(
                    (name, i) =>
                      name && (
                        <Line
                          key={`${i}-${name}`}
                          dataKey={name}
                          stroke={colors[i]}
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 4 }}
                          connectNulls={false}
                          isAnimationActive={false}
                        />
                      ),
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <ChartEmpty />
          )}
          <p className="chart-caption text-[10px] leading-[1.8] text-[var(--muted)] mt-3.5 max-w-212.5">
            Counts GPU–model pairs with known parameters. A 60% rate means 60%
            of those pairs fit; it is not the share of unique models. Gaps mean
            no known observations.
          </p>
          <ChartData
            label="Explore the timeline data"
            headings={[
              "Model year",
              "Architecture",
              "Pairs that fit",
              "Known pairs",
              "Fit rate",
              "Avg. FP16 headroom",
            ]}
            rows={points.map((row) => [
              row.year,
              row.architecture,
              integer(row.fits),
              integer(row.known),
              `${number(row.rate)}%`,
              `${number(row.headroom)} GB`,
            ])}
          />
        </>
      ) : (
        <ChartEmpty failed />
      )}
    </article>
  );
}
function TradeoffTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="custom-tooltip bg-[var(--paper)] [border:1px_solid_var(--line)] py-3 px-4 rounded-[4px] text-[11px] [box-shadow:0_3px_12px_#00000040] flex flex-col gap-1">
      <strong>{row.architecture}</strong>
      <span>{row.vram_bucket} GB bucket</span>
      <span>{number(row.vram)} GB average VRAM</span>
      <span>{integer(row.models)} FP16 model fits</span>
      <span>{number(row.efficiency, 2)} models per GB</span>
    </div>
  );
}
function Tradeoff({ rows }) {
  const architectures = [
    ...new Set((rows || []).map((row) => row.architecture)),
  ].sort();
  const [architecture, setArchitecture] = useState("");
  const points = (rows || []).filter(
    (row) => !architecture || row.architecture === architecture,
  );
  return (
    <article className="chart-panel bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[6px] p-6.5 min-w-0 max-[620px]:py-5.25 max-[620px]:px-4.25">
      <div className="chart-heading flex justify-between items-start gap-5 mb-5 max-[620px]:flex-wrap max-[620px]:gap-3 max-[620px]:mb-3">
        <div>
          <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
            02 / The memory trade-off
          </span>
          <h3>More memory. More possibilities.</h3>
          <p>Language models released from 2020 onward · FP16.</p>
        </div>
      </div>
      {rows ? (
        <>
          <ChartSelect
            label="Architecture"
            value={architecture}
            onChange={setArchitecture}
          >
            <option value="">All architectures</option>
            {architectures.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </ChartSelect>
          {points.length ? (
            <>
              <div className="axis-caption font-mono text-[8px] leading-[normal] text-[var(--muted)] tracking-[.04em] mt-1">
                DISTINCT MODELS THAT FIT
              </div>
              <div
                className="chart-plot w-full min-w-0"
                role="img"
                aria-label="Scatter chart comparing average GPU memory and distinct language models that fit. Exact observations are available in the data table below."
              >
                <ResponsiveContainer width="100%" height={260} minWidth={0}>
                  <ScatterChart
                    margin={{ top: 10, right: 15, bottom: 20, left: -16 }}
                    accessibilityLayer
                  >
                    <CartesianGrid stroke="var(--line)" strokeDasharray="3 5" />
                    <XAxis
                      dataKey="vram"
                      type="number"
                      name="Average VRAM"
                      unit=" GB"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 10, fill: "var(--muted)" }}
                    />
                    <YAxis
                      dataKey="models"
                      type="number"
                      name="FP16 fits"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 10, fill: "var(--muted)" }}
                    />
                    <ZAxis range={[45, 45]} />
                    <Tooltip
                      content={<TradeoffTooltip />}
                      cursor={{ strokeDasharray: "3 3" }}
                    />
                    <Scatter
                      data={points}
                      fill="#a7ce98"
                      fillOpacity={0.65}
                      stroke="#beddb2"
                      isAnimationActive={false}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              <div className="axis-caption font-mono text-[8px] leading-[normal] text-[var(--muted)] tracking-[.04em] mt-1 axis-bottom text-right mt-[-18px]">
                AVERAGE VRAM PER GPU / GB
              </div>
            </>
          ) : (
            <ChartEmpty />
          )}
          <p className="chart-caption text-[10px] leading-[1.8] text-[var(--muted)] mt-3.5 max-w-212.5">
            Each point is an architecture × VRAM bucket. A model counts if it
            fits on at least one GPU in that group. This comparison does not
            measure cost or speed.
          </p>
          <ChartData
            label="Explore the memory data"
            headings={[
              "Architecture",
              "VRAM bucket (GB)",
              "Avg. VRAM (GB)",
              "FP16 model fits",
              "Models per GB",
            ]}
            rows={points.map((row) => [
              row.architecture,
              row.vram_bucket,
              number(row.vram),
              integer(row.models),
              number(row.efficiency, 2),
            ])}
          />
        </>
      ) : (
        <ChartEmpty failed />
      )}
    </article>
  );
}
function DomainAccessibility({ rows }) {
  const buckets = [...new Set((rows || []).map((row) => row.vram_bucket))].sort(
    (a, b) => bucketOrder(a) - bucketOrder(b),
  );
  const [bucket, setBucket] = useState(
    buckets.find((value) => value.includes("24")) || buckets[0] || "",
  );
  const points = (rows || [])
    .filter((row) => row.vram_bucket === bucket)
    .sort(
      (a, b) =>
        (b.rate || 0) - (a.rate || 0) || a.domain.localeCompare(b.domain),
    );
  return (
    <article className="chart-panel bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[6px] p-6.5 min-w-0 max-[620px]:py-5.25 max-[620px]:px-4.25">
      <div className="chart-heading flex justify-between items-start gap-5 mb-5 max-[620px]:flex-wrap max-[620px]:gap-3 max-[620px]:mb-3">
        <div>
          <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
            03 / Across AI domains
          </span>
          <h3>A little room for every field.</h3>
          <p>Models accessible without quantization · FP16.</p>
        </div>
      </div>
      {rows ? (
        <>
          <ChartSelect
            label="GPU memory bucket"
            value={bucket}
            onChange={setBucket}
          >
            {buckets.map((value) => (
              <option key={value} value={value}>
                {value} GB
              </option>
            ))}
          </ChartSelect>
          {points.length ? (
            <ul
              className="domain-bars list-none p-0 mt-3 mx-0 mb-0"
              aria-label={`FP16 accessibility by domain for ${bucket} GB GPUs`}
            >
              {points.map((row) => (
                <li key={row.domain}>
                  <span>{row.domain}</span>
                  <span
                    className="domain-bar bg-[var(--surface)] h-2 rounded-[1px] overflow-hidden"
                    aria-hidden="true"
                  >
                    <span style={{ width: `${row.rate || 0}%` }} />
                  </span>
                  <strong>
                    {row.rate == null ? "Unknown" : `${number(row.rate, 0)}%`}
                  </strong>
                  <span className="sr-only">
                    : {row.fits} of {row.total} models with known parameters
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <ChartEmpty />
          )}
          <p className="chart-caption text-[10px] leading-[1.8] text-[var(--muted)] mt-3.5 max-w-212.5">
            Share of models with known parameters that fit on at least one GPU
            in this memory bucket. Models with unknown parameters are excluded.
          </p>
          <ChartData
            label="Explore the domain data"
            headings={[
              "Domain",
              "Models that fit",
              "Known models",
              "FP16 accessibility",
            ]}
            rows={points.map((row) => [
              row.domain,
              integer(row.fits),
              integer(row.total),
              `${number(row.rate)}%`,
            ])}
          />
        </>
      ) : (
        <ChartEmpty failed />
      )}
    </article>
  );
}
export function Analytics({ data }) {
  return (
    <section
      className="analytics mt-16 max-[620px]:mt-10.5"
      aria-labelledby="analytics-heading"
    >
      <div className="section-heading flex justify-between items-end gap-6 mb-6 max-[850px]:items-start max-[620px]:block max-[620px]:mb-5">
        <div>
          <p className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
            Step back. See the bigger picture.
          </p>
          <Reveal inView><h2 id="analytics-heading">
            Beyond a single GPU
            <span className="heading-dot text-[var(--green)]">.</span>
          </h2></Reveal>
          <p>
            Explore the full warehouse. These comparisons are independent of the
            model filters above.
          </p>
        </div>
        <Link href="/methodology">
          The thinking behind the numbers <ArrowUpRight size={16} />
        </Link>
      </div>
      <Timeline rows={data.timeline} />
      <div className="analytics-pair grid grid-cols-[1fr_1fr] [align-items:start] gap-5.5 mt-5.5 max-[850px]:grid-cols-[1fr]">
        <Tradeoff rows={data.tradeoff} />
        <DomainAccessibility rows={data.domains} />
      </div>
    </section>
  );
}
