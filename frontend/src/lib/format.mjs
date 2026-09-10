export const integer = (value) =>
  new Intl.NumberFormat("en-US").format(value ?? 0);
export function number(value, digits = 1) {
  return value == null
    ? "Unknown"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(
        value,
      );
}
export function compact(value) {
  return value == null
    ? "Unknown"
    : new Intl.NumberFormat("en-US", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(value);
}
export function compatibility(value) {
  return (
    {
      none: { label: "Fits at FP16", tone: "fit" },
      "8-bit": { label: "Needs INT8", tone: "quantized" },
      "4-bit": { label: "Needs INT4", tone: "quantized" },
      "does-not-fit": { label: "Too large", tone: "too-large" },
    }[value] || { label: "Unknown", tone: "unknown" }
  );
}
export const bucketOrder = (value) =>
  Number(value.match(/[\d.]+/)?.[0] || 0) + (value.startsWith(">") ? 0.1 : 0);
