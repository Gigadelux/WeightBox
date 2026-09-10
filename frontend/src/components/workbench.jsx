"use client";

import { Fragment, useEffect, useRef, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
} from "@headlessui/react";
import NumberFlow from "@number-flow/react";
import * as m from "framer-motion/m";
import { Expandable, useMotionTiming, useEntrance } from "./motion";
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Cpu,
  Info,
  Layers,
  Link2,
  Search,
  SlidersHorizontal,
  X,
  LoaderCircle,
} from "lucide-react";
import { GpuIllustration } from "./gpu-illustration";
import { filterUrl, PAGE_SIZE, SORTS, STATUSES } from "@/lib/filters.mjs";
import { compact, compatibility, integer, number } from "@/lib/format.mjs";

function GpuPicker({ gpus, gpu, onChange, disabled }) {
  const [query, setQuery] = useState("");
  const options = gpus.filter((item) =>
    `${item.name} ${item.manufacturer} ${item.vram} GB ${item.year}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <div className="gpu-picker">
      <label
        className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2"
        htmlFor="gpu-picker"
      >
        Your graphics card
      </label>
      <Combobox
        value={gpu}
        by="key"
        onChange={(value) => value && onChange(value.key)}
        onClose={() => setQuery("")}
        disabled={disabled}
        virtual={{ options }}
      >
        <div className="gpu-input-wrap flex items-center [border:1px_solid_var(--line)] rounded-[5px] bg-[var(--paper)] pl-3">
          <Search size={16} />
          <ComboboxInput
            id="gpu-picker"
            displayValue={(value) => value?.name || ""}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search graphics cards…"
            autoComplete="off"
          />
          <ComboboxButton aria-label="Choose graphics card">
            <ChevronDown size={17} />
          </ComboboxButton>
        </div>
        <ComboboxOptions
          anchor="bottom start"
          className="gpu-options [--anchor-gap:7px] [--anchor-padding:16px] w-[max(var(--input-width),_310px)] max-w-[calc(100vw_-_32px)] max-h-85 overflow-y-auto [z-index:50] bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[5px] p-1.25 [box-shadow:0_12px_30px_#00000040]"
        >
          {options.length ? (
            ({ option }) => (
              <ComboboxOption
                value={option}
                className="gpu-option py-2.5 px-3 flex justify-between items-center gap-3 [cursor:pointer] w-full"
              >
                <div>
                  <strong>{option.name}</strong>
                  <span>
                    {option.manufacturer} · {number(option.vram)} GB ·{" "}
                    {option.year || "Year unknown"}
                  </span>
                </div>
                <Check
                  size={16}
                  className="option-check [visibility:hidden] text-[var(--green)]"
                />
              </ComboboxOption>
            )
          ) : (
            <div className="picker-empty py-5 px-3 text-[var(--muted)] text-[12px]">
              No graphics cards match “{query}”.
            </div>
          )}
        </ComboboxOptions>
      </Combobox>
      <span className="picker-hint block mt-1.75 mx-0 mb-5 text-[10px] text-[var(--muted)] max-[620px]:mb-3.75">
        {integer(gpus.length)} GPUs in the dataset
      </span>
    </div>
  );
}
function HardwarePanel({ gpu, summary }) {
  const scope = useEntrance(gpu.key);
  return (
    <>
      <div ref={scope} className="hardware-card bg-[var(--forest)] text-[#edf4e7] rounded-[7px] overflow-hidden relative max-[620px]:grid max-[620px]:grid-cols-[1fr_1fr]">
        <div className="hardware-card-top flex justify-between items-center gap-3 pt-5 px-4.75 pb-0 text-[#b9cbb8] font-mono text-[8px] leading-[normal] uppercase tracking-[.06em] max-[850px]:px-3.75 max-[850px]:text-[7px] max-[620px]:[grid-column:1/-1] max-[620px]:text-[8px] max-[620px]:pt-4.5 max-[620px]:px-5 max-[620px]:pb-0">
          <span>
            <Cpu size={14} /> Selected hardware
          </span>
          <span>{gpu.manufacturer}</span>
        </div>
        <GpuIllustration />
        <div className="hardware-name pt-0 px-6 pb-5.25 max-[1190px]:px-5 max-[620px]:[grid-column:1] max-[620px]:[grid-row:2] max-[620px]:pt-5.5 max-[620px]:pr-0 max-[620px]:pb-4.5 max-[620px]:pl-5 max-[620px]:[z-index:1]">
          <span className="hardware-year font-mono text-[9px] leading-[normal] tracking-[.08em] uppercase text-[#bbd0ba] max-[620px]:text-[8px]">
            {gpu.year || "Year unknown"} / {gpu.memory}
          </span>
          <h2>{gpu.name}</h2>
          <div className="vram-display flex gap-2 items-center mt-4.25 max-[620px]:mt-4.25">
            <NumberFlow value={gpu.vram} />{" "}
            <span>
              GB<span>VIDEO MEMORY</span>
            </span>
          </div>
        </div>
        <dl className="hardware-specs m-0 pt-0 px-6 pb-3.5 max-[850px]:px-4.5 max-[620px]:[grid-column:1/-1] max-[620px]:grid max-[620px]:grid-cols-[1fr_1fr_1fr] max-[620px]:gap-3 max-[620px]:pt-0 max-[620px]:px-5 max-[620px]:pb-3">
          <div>
            <dt>Architecture</dt>
            <dd>{gpu.architecture}</dd>
          </div>
          <div>
            <dt>Memory bandwidth</dt>
            <dd>
              {number(gpu.bandwidth)} <span>GB/s</span>
            </dd>
          </div>
          <div>
            <dt>Memory bus</dt>
            <dd>{gpu.bus == null ? "Unknown" : `${gpu.bus} bit`}</dd>
          </div>
        </dl>
        <div className="hardware-caption bg-[#102d2166] [border-top:1px_solid_#ffffff10] flex items-center gap-1.75 py-3.25 px-6 text-[#c0d1ba] font-mono text-[8px] leading-[normal] max-[850px]:px-4.5 max-[850px]:text-[7px] max-[620px]:[grid-column:1/-1] max-[620px]:px-5 max-[620px]:text-[8px]">
          <span className="tiny-square w-1.25 h-1.25 bg-[var(--green)] inline-block shrink-0" />{" "}
          Dataset-derived specifications
        </div>
      </div>
      {(gpu.estimated || gpu.suspect) && (
        <div className="data-note flex items-start gap-2 pt-3.5 px-0.5 pb-0 text-[#e0bc7f] text-[11px] leading-[1.7]">
          <Info size={15} />
          <p>
            {gpu.suspect
              ? "This record has a specification quality flag. "
              : ""}
            {gpu.estimated
              ? "Bandwidth uses an imputed memory specification. "
              : ""}
            <Link href="/data">See data limitations</Link>.
          </p>
        </div>
      )}
      <div className="rail-note py-5.75 px-0.75 [border-bottom:1px_solid_var(--line)] max-[620px]:pt-4.25 max-[620px]:px-0.5 max-[620px]:pb-0 max-[620px]:[border:0]">
        <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
          A little headroom helps
        </span>
        <p>
          Memory estimates include a 20% overhead allowance. Real workloads can
          need more.
        </p>
        <Link href="/methodology">
          How we calculate fit <ArrowUpRight size={15} />
        </Link>
      </div>
      <div className="rail-total py-4.75 px-0.75 max-[620px]:hidden">
        <span>Possible fits, including quantization</span>
        <strong>
          {integer(summary.fp16 + summary.int8 + summary.int4)}{" "}
          <span>/ {integer(summary.total)}</span>
        </strong>
      </div>
    </>
  );
}
function Summary({ summary, active, onSelect, disabled }) {
  const transition = useMotionTiming(0.18);
  const cards = [
    {
      key: "fp16",
      title: "Fits at FP16",
      value: summary.fp16,
      detail: "No quantization needed",
      icon: Check,
      tone: "fit",
    },
    {
      key: "quantized",
      title: "Needs quantization",
      value: summary.int8 + summary.int4,
      detail: `${summary.int8} at INT8 · ${summary.int4} at INT4`,
      icon: Layers,
      tone: "quantized",
    },
    {
      key: "too_large",
      title: "Too large",
      value: summary.too_large,
      detail: "Exceeds VRAM at INT4",
      icon: X,
      tone: "too-large",
    },
    {
      key: "unknown",
      title: "Unknown",
      value: summary.unknown,
      detail: "Parameter count missing",
      icon: CircleHelp,
      tone: "unknown",
    },
  ];
  return (
    <section
      className="compatibility-summary grid grid-cols-[repeat(4,_minmax(0,_1fr))] [border:1px_solid_var(--line)] bg-[var(--paper)] rounded-[6px] overflow-hidden max-[850px]:grid-cols-[1fr_1fr]"
      aria-label="Compatibility across all models on selected GPU"
    >
      {cards.map(({ key, title, value, detail, icon: Icon, tone }) => (
        <m.button
          key={key}
          whileTap={transition.duration && !disabled ? { scale: 0.975 } : undefined}
          transition={transition}
          className={`summary-item min-w-0 text-left bg-[transparent] [border:0] [border-right:1px_solid_var(--line)] pt-4.5 px-4.25 pb-3.25 relative max-[1190px]:pt-3.5 max-[1190px]:px-2.75 max-[1190px]:pb-2.75 max-[850px]:p-3 max-[620px]:pt-3.75 max-[620px]:px-4 max-[620px]:pb-3 ${tone}`}
          aria-pressed={active === key}
          disabled={disabled}
          onClick={() => onSelect(active === key ? "all" : key)}
        >
          <span className="summary-label text-[10px] font-medium flex items-center gap-1.5 whitespace-nowrap max-[1190px]:text-[9px] max-[1190px]:gap-1 max-[850px]:text-[10px] max-[620px]:text-[10px]">
            <span className="status-square text-[var(--status-color)] w-4.5 h-4.5 bg-[var(--status-bg)] grid place-items-center rounded-[3px]">
              <Icon size={13} />
            </span>
            {title}
          </span>
          <span className="summary-value text-[37px] tracking-[-1.5px] leading-[1.5] font-medium block mt-1.5 max-[1190px]:text-[33px] max-[850px]:text-[29px] max-[850px]:leading-[1.3] max-[620px]:text-[35px] max-[620px]:my-1 max-[620px]:mx-0">
            <NumberFlow value={value} />
          </span>
          <span className="summary-detail block text-[var(--muted)] text-[9px] whitespace-nowrap max-[1190px]:text-[8px] max-[1190px]:whitespace-normal max-[1190px]:min-h-6 max-[850px]:text-[8px] max-[850px]:min-h-0 max-[620px]:text-[9px]">
            {detail}
          </span>
          <span className="summary-meter h-0.75 rounded-[2px] bg-[var(--surface)] block mt-3.5 overflow-hidden max-[850px]:mt-2.25">
            <span style={{ width: `${(value / summary.total) * 100}%` }} />
          </span>
        </m.button>
      ))}
    </section>
  );
}
function ModelRow({ model, expanded, onExpand, gpu }) {
  const status = compatibility(model.quantization);
  const quantFootprint =
    model.footprint == null
      ? null
      : model.footprint /
        (model.quantization === "8-bit"
          ? 2
          : model.quantization === "4-bit"
            ? 4
            : 1);
  return (
    <Fragment>
      <tr className={expanded ? "row-expanded bg-[var(--hover)]" : ""}>
        <td>
          <button
            className="model-name block [border:0] bg-[none] p-0 text-left text-[11px] font-semibold leading-[1.5] [overflow-wrap:anywhere] max-[620px]:min-h-7.5 max-[620px]:flex max-[620px]:items-center"
            onClick={onExpand}
            aria-expanded={expanded}
            aria-controls={`model-${model.id}`}
          >
            {model.name}
          </button>
          <span className="model-org block text-[var(--muted)] text-[9px] mt-0.75 [overflow-wrap:anywhere]">
            {model.organization} <span>· {model.year}</span>
          </span>
        </td>
        <td>
          <span className="domain-label text-[9px] text-[var(--muted)]">
            {model.domain}
          </span>
        </td>
        <td className="numeric text-right font-mono whitespace-nowrap">
          {compact(model.parameters)}
        </td>
        <td className="numeric text-right font-mono whitespace-nowrap">
          {model.footprint == null ? (
            <span className="muted text-[var(--muted)]">Unknown</span>
          ) : (
            <>
              {number(model.footprint, 2)}{" "}
              <span className="unit text-[8px] text-[var(--muted)]">GB</span>
            </>
          )}
        </td>
        <td>
          <span
            className={`status-badge inline-flex items-center gap-1.25 bg-[var(--status-bg)] text-[var(--status-color)] text-[9px] font-medium whitespace-nowrap py-1 px-1.75 rounded-[3px] ${status.tone}`}
          >
            <span />
            {status.label}
          </span>
        </td>
        <td>
          <button
            className="icon-button [border:1px_solid_var(--line)] bg-[transparent] rounded-[4px] w-7.5 h-7.5 inline-grid place-items-center expand-button [border:0] h-7.5 w-6.25 text-[var(--muted)] max-[620px]:w-10 max-[620px]:h-10"
            aria-label={`${expanded ? "Hide" : "Show"} details for ${model.name}`}
            aria-expanded={expanded}
            aria-controls={`model-${model.id}`}
            onClick={onExpand}
          >
            <ChevronDown size={16} />
          </button>
        </td>
      </tr>
        <tr id={`model-${model.id}`} className="model-details bg-[var(--surface)]" aria-hidden={!expanded} inert={!expanded}>
          <td colSpan={6}>
            <Expandable open={expanded}>
            <div className="px-5.5 pt-4.5 pb-5 [border-bottom:1px_solid_var(--line)]">
            <div className="model-details-heading flex justify-between items-baseline gap-3.75">
              <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
                Memory estimate / {model.name}
              </span>
              <Link href="/methodology">
                Read the assumptions <ArrowUpRight size={13} />
              </Link>
            </div>
            <dl>
              <div>
                <dt>FP16 footprint</dt>
                <dd>
                  {model.footprint == null
                    ? "Unknown"
                    : `${number(model.footprint, 3)} GB`}
                </dd>
              </div>
              <div>
                <dt>FP16 headroom</dt>
                <dd>
                  {model.headroom == null
                    ? "Unknown"
                    : `${number(model.headroom, 3)} GB`}
                </dd>
              </div>
              <div>
                <dt>Smallest change to fit</dt>
                <dd>
                  {model.quantization == null
                    ? "Unknown"
                    : model.quantization === "does-not-fit"
                      ? "Does not fit at INT4"
                      : model.quantization === "none"
                        ? "FP16 · no change"
                        : `${status.label} · ${number(quantFootprint, 3)} GB`}
                </dd>
              </div>
              <div>
                <dt>Theoretical FP16 throughput</dt>
                <dd>
                  {!model.is_generative
                    ? "Not applicable"
                    : model.throughput == null
                      ? "Unknown"
                      : `${number(model.throughput)} ${model.throughput_unit}`}
                </dd>
              </div>
            </dl>
            <p>
              {model.quantization && model.quantization !== "none"
                ? `The FP16 estimate exceeds this GPU’s ${number(gpu.vram)} GB. `
                : ""}
              Throughput is a bandwidth-only FP16 estimate, not a benchmark or a
              quantized performance prediction. Memory fit does not guarantee
              runtime support.
            </p>
            </div>
            </Expandable>
          </td>
        </tr>
    </Fragment>
  );
}
function ModelResults({ data, pending, navigate }) {
  const transition = useMotionTiming(0.2);
  const { filters, models, pages, total, gpu } = data;
  const [expanded, setExpanded] = useState(null);
  const [draft, setDraft] = useState(filters.q);
  const [previousQuery, setPreviousQuery] = useState(filters.q);
  // Back/forward navigation restores the visible search without remounting the focused input.
  if (previousQuery !== filters.q) {
    setPreviousQuery(filters.q);
    setDraft(filters.q);
  }
  const filtered = filters.q || filters.domain || filters.status !== "all";
  function clearFilters() {
    setDraft("");
    setExpanded(null);
    navigate({ q: "", domain: "", status: "all", page: 1 });
  }
  return (
    <m.section
      initial={false}
      animate={{ opacity: pending ? 0.65 : 1 }}
      transition={transition}
      className="results-panel [border:1px_solid_var(--line)] bg-[var(--paper)] rounded-[6px] overflow-hidden"
      aria-labelledby="models-heading"
    >
      <div className="results-heading pt-5.75 px-5.5 pb-4.75 flex justify-between items-center gap-2.5 max-[850px]:p-4.5 max-[850px]:items-start max-[620px]:py-5 max-[620px]:px-4">
        <div>
          <span className="eyebrow font-mono text-[10px] leading-[1.5] tracking-[.11em] uppercase text-[var(--muted)] flex items-center gap-2">
            Model compatibility
          </span>
          <h2 id="models-heading">
            Meet your next model
            <span className="heading-dot text-[var(--green)]">.</span>
          </h2>
        </div>
        <span
          className="results-count font-mono text-[10px] leading-[normal] text-[var(--muted)] whitespace-nowrap max-[850px]:text-[8px] max-[850px]:mt-0.5 max-[620px]:mt-1"
          role="status"
        >
          {integer(total)} {filtered ? "matching" : "models"}
        </span>
      </div>
      <form
        className="model-filters pt-0 px-5.5 pb-4.25 flex gap-2.25 max-[1190px]:flex-wrap max-[1190px]:px-4.5 max-[620px]:pt-0 max-[620px]:px-4 max-[620px]:pb-3.75 max-[620px]:gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          navigate({ q: draft.trim(), page: 1 });
        }}
      >
        <div className="model-search flex items-center gap-2 pt-0 pr-2 pb-0 pl-2.75 flex-1 min-w-0 [border:1px_solid_var(--line)] bg-[var(--canvas)] rounded-[4px] max-[1190px]:[flex-basis:100%]">
          <Search size={16} />
          <input
            aria-label="Search models or organizations"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            maxLength={120}
            placeholder="Find a model or organization…"
          />
          <button
            className="search-submit [border:0] bg-[var(--surface)] rounded-[3px] grid place-items-center h-6.5 w-6.75 shrink-0 max-[620px]:h-8.5 max-[620px]:w-8.5"
            type="submit"
            disabled={pending}
            aria-label="Search models"
          >
            <ArrowDownRight size={16} />
          </button>
        </div>
        <label className="select-wrap inline-flex items-center relative [border:1px_solid_var(--line)] rounded-[4px] bg-[var(--paper)]">
          <span className="sr-only">Model domain</span>
          <select
            value={filters.domain}
            onChange={(event) =>
              navigate({ domain: event.target.value, page: 1 })
            }
            disabled={pending}
          >
            <option value="">All domains</option>
            {!data.domains.includes(filters.domain) && filters.domain && (
              <option value={filters.domain}>{filters.domain}</option>
            )}
            {data.domains.map((domain) => (
              <option key={domain}>{domain}</option>
            ))}
          </select>
          <ChevronDown size={14} />
        </label>
        <label className="select-wrap inline-flex items-center relative [border:1px_solid_var(--line)] rounded-[4px] bg-[var(--paper)]">
          <span className="sr-only">Compatibility filter</span>
          <select
            value={filters.status}
            onChange={(event) =>
              navigate({ status: event.target.value, page: 1 })
            }
            disabled={pending}
          >
            {Object.entries(STATUSES).map(([value, label]) => (
              <option value={value} key={value}>
                {label}
              </option>
            ))}
          </select>
          <ChevronDown size={14} />
        </label>
      </form>
      <div className="table-toolbar [border-top:1px_solid_var(--line)] py-2.25 px-5.5 flex items-center justify-between gap-3 text-[var(--muted)] text-[9px] max-[850px]:flex-wrap max-[620px]:px-4 max-[620px]:text-[9px] max-[620px]:gap-1.25">
        <span>
          Estimates for <strong>{gpu.name}</strong>
        </span>
        <label>
          <SlidersHorizontal size={13} />
          <span className="sr-only">Sort models</span>
          <select
            value={filters.sort}
            disabled={pending}
            onChange={(event) =>
              navigate({ sort: event.target.value, page: 1 })
            }
          >
            {Object.entries(SORTS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {models.length ? (
        <div
          className="table-scroll relative overflow-x-auto [scrollbar-width:thin] [scrollbar-color:#c3cebc_transparent]"
          tabIndex={0}
          role="region"
          aria-label="Model compatibility table, scroll horizontally on small screens"
        >
          <table className="model-table text-left max-[1190px]:min-w-152.5">
            <thead>
              <tr>
                <th scope="col">Model / organization</th>
                <th scope="col">Domain</th>
                <th
                  scope="col"
                  className="numeric text-right font-mono whitespace-nowrap"
                >
                  Parameters
                </th>
                <th
                  scope="col"
                  className="numeric text-right font-mono whitespace-nowrap"
                >
                  FP16 memory
                </th>
                <th scope="col">Compatibility</th>
                <th scope="col">
                  <span className="sr-only">Details</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <ModelRow
                  key={model.id}
                  model={model}
                  gpu={gpu}
                  expanded={expanded === model.id}
                  onExpand={() =>
                    setExpanded(expanded === model.id ? null : model.id)
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-results text-center py-15 px-6 text-[var(--muted)]">
          <Search size={26} />
          <h3>No models on this shelf.</h3>
          <p>Try another search, domain, or compatibility filter.</p>
          <button
            className="button [border:1px_solid_var(--line)] py-2.75 px-4.25 inline-flex items-center justify-center gap-2 rounded-[4px] bg-[transparent] text-[11px] font-medium"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        </div>
      )}
      <div className="pagination py-3.5 px-5.5 flex justify-between items-center gap-3.75 text-[var(--muted)] text-[9px] max-[850px]:flex-wrap max-[850px]:px-4.5 max-[620px]:py-3 max-[620px]:px-4 max-[620px]:gap-2 max-[620px]:text-[9px]">
        <span>
          {total
            ? `${integer((filters.page - 1) * PAGE_SIZE + 1)}–${integer(Math.min(filters.page * PAGE_SIZE, total))} of ${integer(total)} models`
            : "0 models"}
          {filtered && (
            <button
              className="text-button bg-[none] [border:0] p-0 text-[var(--green)] text-[10px] font-medium inline-flex items-center gap-1.25 min-h-7.5"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          )}
        </span>
        <div>
          <button
            className="icon-button [border:1px_solid_var(--line)] bg-[transparent] rounded-[4px] w-7.5 h-7.5 inline-grid place-items-center"
            aria-label="Previous page"
            disabled={pending || filters.page <= 1}
            onClick={() => navigate({ page: filters.page - 1 })}
          >
            <ChevronLeft size={16} />
          </button>
          <span>
            Page {filters.page} of {pages}
          </span>
          <button
            className="icon-button [border:1px_solid_var(--line)] bg-[transparent] rounded-[4px] w-7.5 h-7.5 inline-grid place-items-center"
            aria-label="Next page"
            disabled={pending || filters.page >= pages}
            onClick={() => navigate({ page: filters.page + 1 })}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      <div className="table-footnote flex items-center gap-2 bg-[var(--surface)] py-3.25 px-5.5 text-[9px] text-[var(--muted)] [border-top:1px_solid_var(--line)] max-[620px]:items-start max-[620px]:py-3.25 max-[620px]:px-4 max-[620px]:text-[9px] max-[620px]:leading-[1.8]">
        <Info size={14} />
        <p>
          Memory fit is a starting point, not a runtime guarantee.{" "}
          <Link href="/methodology">Understand the estimates</Link>.
        </p>
      </div>
    </m.section>
  );
}
export function Workbench({ data }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [share, setShare] = useState("");
  const shareTimer = useRef(null);
  useEffect(() => () => clearTimeout(shareTimer.current), []);
  function navigate(changes) {
    startTransition(() =>
      router.push(filterUrl(data.filters, changes), { scroll: false }),
    );
  }
  async function copyLink() {
    try {
      await navigator.clipboard.writeText(
        `${window.location.origin}${filterUrl(data.filters)}`,
      );
      setShare("Link copied");
    } catch {
      setShare("Copy the URL from your address bar");
    }
    clearTimeout(shareTimer.current);
    shareTimer.current = setTimeout(() => setShare(""), 4000);
  }
  return (
    <div
      className={`workbench-grid grid grid-cols-[284px_minmax(0,_1fr)] [align-items:start] gap-7.5 relative min-[1500px]:grid-cols-[300px_minmax(0,_1fr)] min-[1500px]:gap-8.5 max-[1190px]:grid-cols-[250px_minmax(0,_1fr)] max-[1190px]:gap-5.5 max-[850px]:grid-cols-[220px_minmax(0,_1fr)] max-[850px]:gap-5 max-[620px]:grid-cols-[1fr] max-[620px]:gap-6 ${pending ? "is-pending" : ""}`}
      aria-busy={pending}
    >
      <aside className="hardware-rail" aria-label="Hardware selection">
        <GpuPicker
          gpus={data.gpus}
          gpu={data.gpu}
          onChange={(gpu) => navigate({ gpu, page: 1 })}
          disabled={pending}
        />
        {data.gpu && <HardwarePanel gpu={data.gpu} summary={data.summary} />}
      </aside>
      <div className="workbench-main">
        <div className="workbench-meta min-h-6.25 mb-3.25 flex items-center justify-between relative gap-2.5 text-[10px] max-[850px]:text-[9px] max-[850px]:flex-wrap max-[850px]:min-h-9.25 max-[850px]:mb-2.5 max-[620px]:text-[10px] max-[620px]:mb-2.5">
          <span>
            <span className="live-dot w-1.25 h-1.25 bg-[var(--green)] rounded-[50%]" />
            {pending
              ? "Updating your workbench…"
              : "Connected to the warehouse"}
          </span>
          <button
            className="text-button bg-[none] [border:0] p-0 text-[var(--green)] text-[10px] font-medium inline-flex items-center gap-1.25 min-h-7.5"
            onClick={copyLink}
          >
            <Link2 size={14} />
            Share this view
          </button>
          <span
            className="share-message absolute [top:32px] [right:0] bg-[var(--forest)] text-[white] rounded-[4px] text-[11px] [z-index:4] py-2 px-3"
            role="status"
          >
            {share}
          </span>
        </div>
        {data.gpu ? (
          <>
            <Summary
              summary={data.summary}
              active={data.filters.status}
              onSelect={(status) => navigate({ status, page: 1 })}
              disabled={pending}
            />
            <p className="summary-scope mt-2.25 mx-0.25 mb-6 text-[var(--muted)] text-[9px] max-[620px]:text-[9px] max-[620px]:leading-[1.7] max-[620px]:mb-5.75">
              All {integer(data.summary.total)} models on your selected GPU.
              Select a category to filter the results.
            </p>
            <ModelResults data={data} pending={pending} navigate={navigate} />
          </>
        ) : (
          <div className="empty-results text-center py-15 px-6 text-[var(--muted)] invalid-gpu bg-[var(--paper)] [border:1px_solid_var(--line)] rounded-[6px]">
            <Cpu size={30} />
            <h2>This GPU isn’t in the dataset.</h2>
            <p>
              The shared selection may be outdated. Choose a graphics card to
              start exploring.
            </p>
          </div>
        )}
      </div>
      <div className="pending-indicator" role="status">
        {pending && (
          <>
            <LoaderCircle className="spin" size={16} />
            Updating hardware and models…
          </>
        )}
      </div>
    </div>
  );
}
