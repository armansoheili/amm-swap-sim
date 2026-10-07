# amm-swap-sim

A constant-product AMM (x·y=k) simulator in pure Python — the math behind
Uniswap v2-style pools. Zero dependencies.

## What's in it

`amm.py` implements a `Pool` with:

- **Swaps** — the exact Uniswap v2 `getAmountOut` formula with the 0.3% fee
  (`amountIn·997·reserveOut / (reserveIn·1000 + amountIn·997)`), in both
  directions (A→B and B→A)
- **Spot price** — marginal price of A in terms of B (`reserveB / reserveA`)
- **Price impact** — how much a trade loses to slippage + fee versus an
  infinitesimal trade at the spot price
- **Liquidity** — `add_liquidity` mints LP shares (geometric mean on first
  deposit, proportional afterwards), `remove_liquidity` burns them and
  returns the proportional share of both reserves
- The invariant `k = reserveA · reserveB` visibly grows after every swap,
  because the fee stays in the pool

## Run the demo

```bash
python3 amm.py
```

Example output:

```
seeded: Pool(A=1000.0000, B=200000.0000, k=200000000.00, LP=14142.1356)
spot price: 1 A = 200.00 B

swap    1.0 A ->     199.20 B   impact:  0.40%
swap   10.0 A ->    1974.32 B   impact:  1.28%
swap  100.0 A ->   18132.22 B   impact:  9.34%
```

## Why it exists

Building-block crypto math: the constant-product curve is the simplest
automated market maker. Everything here — reserves, the fee-adjusted swap
formula, LP share accounting — maps directly to how real on-chain pools
work.
