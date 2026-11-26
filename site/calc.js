// Gross value change in SGD, minus any costs the user enters. Returns null when it can't be worked out.
function valueChange(buySgd, sellUsd, multiplier, fx, costSgd) {
  if (!sellUsd || !(fx > 0) || !(multiplier > 0) || !(buySgd > 0)) return null;
  const paid = buySgd + (costSgd || 0);
  const value = sellUsd * multiplier * fx;
  return { value, change: value - paid, pct: (value - paid) / paid * 100 };
}
if (typeof module !== 'undefined') module.exports = { valueChange };
