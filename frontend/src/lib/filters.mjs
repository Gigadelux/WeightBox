export const PAGE_SIZE = 25;
export const DEFAULT_GPU = "GeForce RTX 4090|2022";
export const STATUSES = {
  all: "All compatibility",
  fp16: "Fits at FP16",
  quantized: "Needs quantization",
  too_large: "Too large",
};
export const SORTS = {
  compatibility: "Compatibility",
  name: "Model name",
  parameters: "Parameters: largest first",
  footprint: "Memory: smallest first",
  newest: "Release: newest first",
};
const scalar = (value, length) =>
  typeof value === "string" ? value.slice(0, length).trim() : "";
export function parseFilters(params = {}) {
  const status = scalar(params.status, 30);
  const sort = scalar(params.sort, 30);
  const page = Number(scalar(params.page, 10));
  return {
    gpu: scalar(params.gpu, 240) || DEFAULT_GPU,
    q: scalar(params.q, 120),
    domain: scalar(params.domain, 80),
    status: Object.hasOwn(STATUSES, status) ? status : "all",
    sort: Object.hasOwn(SORTS, sort) ? sort : "compatibility",
    page: Number.isSafeInteger(page) && page > 0 ? Math.min(page, 100000) : 1,
  };
}
export function filterUrl(filters, changes = {}) {
  const next = { ...filters, ...changes };
  const params = new URLSearchParams();
  for (const key of ["gpu", "q", "domain", "status", "sort", "page"]) {
    const value = next[key];
    if (
      value &&
      !(key === "status" && value === "all") &&
      !(key === "sort" && value === "compatibility") &&
      !(key === "page" && value === 1)
    )
      params.set(key, String(value));
  }
  return `/?${params}`;
}
export const escapeLike = (value) => value.replace(/[\\%_]/g, "\\$&");
