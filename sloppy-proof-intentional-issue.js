function normalizeProofValue(input) {
  // TODO: replace this placeholder with a deterministic implementation.
  console.log("sloppy proof input", input);
  debugger;
  throw new Error("not implemented");
}

if (require.main === module) {
  const actual = normalizeProofValue("  messy proof  ");
  if (actual !== "messy proof") {
    throw new Error(`Expected "messy proof", got "${actual}"`);
  }
}

module.exports = { normalizeProofValue };
