function isNumeric(binding) {
  return /(?:integer|decimal|double|float|long|int)$/u.test(binding?.datatype ?? "")
    || (binding?.type === "literal" && /^-?\d+(?:\.\d+)?$/u.test(binding.value));
}

function compareValues(left, right) {
  if (isNumeric(left) && isNumeric(right)) return Number(left.value) - Number(right.value);
  if (/dateTime$/u.test(left?.datatype ?? "") && /dateTime$/u.test(right?.datatype ?? "")) {
    return new Date(left.value).valueOf() - new Date(right.value).valueOf();
  }
  return String(left.value).localeCompare(String(right.value), "en", {
    numeric: true,
    sensitivity: "base",
  });
}

export function sortBindings(bindings, column, direction = "desc") {
  if (!Array.isArray(bindings)) throw new TypeError("bindings must be an array");
  if (typeof column !== "string" || !column) throw new TypeError("column is required");
  if (!["asc", "desc"].includes(direction)) throw new RangeError(`Unsupported sort direction: ${direction}`);

  return bindings.map((row, index) => ({ row, index })).sort((left, right) => {
    const leftBinding = left.row[column];
    const rightBinding = right.row[column];
    if (!leftBinding && !rightBinding) return left.index - right.index;
    if (!leftBinding) return 1;
    if (!rightBinding) return -1;
    const comparison = compareValues(leftBinding, rightBinding);
    return comparison === 0
      ? left.index - right.index
      : direction === "desc" ? -comparison : comparison;
  }).map(({ row }) => row);
}
