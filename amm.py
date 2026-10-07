"""Constant-product AMM (x*y=k) simulator, Uniswap v2 style, in pure Python.

Implements the exact v2 swap math:
    amount_out = amount_in * 997 * reserve_out / (reserve_in * 1000 + amount_in * 997)
plus price quoting, price impact, and add/remove-liquidity with LP shares.
Zero dependencies.
"""

FEE_NUMERATOR = 997      # 0.3% fee (1000 - 997)
FEE_DENOMINATOR = 1000


class InsufficientLiquidity(Exception):
    pass


class Pool:
    """A single constant-product liquidity pool for tokens A and B."""

    def __init__(self, reserve_a: float = 0.0, reserve_b: float = 0.0):
        self.reserve_a = float(reserve_a)
        self.reserve_b = float(reserve_b)
        self.total_lp = 0.0  # outstanding LP share tokens

    # -- pricing -----------------------------------------------------------
    def spot_price(self) -> float:
        """Marginal price of A in terms of B (B per A)."""
        if self.reserve_a <= 0:
            raise InsufficientLiquidity("empty pool")
        return self.reserve_b / self.reserve_a

    def quote(self, amount_in: float, token_in: str = "A") -> float:
        """Amount out for a trade, WITHOUT applying the fee (v2 getAmountOut core)."""
        amount_in = float(amount_in)
        if amount_in <= 0:
            return 0.0
        if token_in == "A":
            r_in, r_out = self.reserve_a, self.reserve_b
        else:
            r_in, r_out = self.reserve_b, self.reserve_a
        if r_in <= 0 or r_out <= 0:
            raise InsufficientLiquidity("empty pool")
        return amount_in * r_out / (r_in + amount_in)

    def get_amount_out(self, amount_in: float, token_in: str = "A") -> float:
        """Amount out WITH the 0.3% fee — the exact Uniswap v2 formula."""
        amount_in = float(amount_in)
        if amount_in <= 0:
            return 0.0
        if token_in == "A":
            r_in, r_out = self.reserve_a, self.reserve_b
        else:
            r_in, r_out = self.reserve_b, self.reserve_a
        if r_in <= 0 or r_out <= 0:
            raise InsufficientLiquidity("empty pool")
        amount_in_with_fee = amount_in * FEE_NUMERATOR
        numerator = amount_in_with_fee * r_out
        denominator = r_in * FEE_DENOMINATOR + amount_in_with_fee
        return numerator / denominator

    def price_impact(self, amount_in: float, token_in: str = "A") -> float:
        """Relative price impact of a trade (0.0 = 0%, 1.0 = 100%).

        Compares the trade's execution price against the pool's marginal
        spot price — i.e. how much value the trade loses to slippage + fee
        relative to an infinitesimal trade.
        """
        amount_in = float(amount_in)
        if amount_in <= 0:
            return 0.0
        if token_in == "A":
            ideal = amount_in * self.spot_price()  # B per A
        else:
            ideal = amount_in / self.spot_price()
        if ideal <= 0:
            return 0.0
        got = self.get_amount_out(amount_in, token_in)
        return max(0.0, 1.0 - got / ideal)

    # -- trading -----------------------------------------------------------
    def swap(self, amount_in: float, token_in: str = "A") -> float:
        """Execute a swap, update reserves, return amount out."""
        amount_out = self.get_amount_out(amount_in, token_in)
        if token_in == "A":
            self.reserve_a += amount_in
            self.reserve_b -= amount_out
        else:
            self.reserve_b += amount_in
            self.reserve_a -= amount_out
        return amount_out

    # -- liquidity ----------------------------------------------------------
    def add_liquidity(self, amount_a: float, amount_b: float) -> float:
        """Deposit both tokens, mint LP shares proportional to the deposit."""
        amount_a, amount_b = float(amount_a), float(amount_b)
        if self.total_lp == 0:  # first deposit: geometric mean
            if amount_a <= 0 or amount_b <= 0:
                raise InsufficientLiquidity("initial deposit must be > 0")
            minted = (amount_a * amount_b) ** 0.5
        else:
            if self.reserve_a <= 0 or self.reserve_b <= 0:
                raise InsufficientLiquidity("empty pool")
            # v2 requires the deposit to match the current price ratio
            minted = min(
                amount_a * self.total_lp / self.reserve_a,
                amount_b * self.total_lp / self.reserve_b,
            )
        self.reserve_a += amount_a
        self.reserve_b += amount_b
        self.total_lp += minted
        return minted

    def remove_liquidity(self, lp_burned: float):
        """Burn LP shares, withdraw the proportional share of both tokens."""
        lp_burned = float(lp_burned)
        if lp_burned <= 0 or lp_burned > self.total_lp:
            raise ValueError("invalid LP amount")
        share = lp_burned / self.total_lp
        out_a = self.reserve_a * share
        out_b = self.reserve_b * share
        self.reserve_a -= out_a
        self.reserve_b -= out_b
        self.total_lp -= lp_burned
        return out_a, out_b

    @property
    def k(self) -> float:
        return self.reserve_a * self.reserve_b

    def __repr__(self):
        return (
            f"Pool(A={self.reserve_a:.4f}, B={self.reserve_b:.4f}, "
            f"k={self.k:.2f}, LP={self.total_lp:.4f})"
        )


def demo():
    pool = Pool()
    lp = pool.add_liquidity(1_000.0, 200_000.0)  # LP seeds the pool
    print(f"seeded: {pool}  (LP shares minted: {lp:.4f})")
    print(f"spot price: 1 A = {pool.spot_price():.2f} B\n")

    for size in (1.0, 10.0, 100.0):
        out = pool.get_amount_out(size, "A")
        print(
            f"swap {size:>6.1f} A -> {out:>10.2f} B   "
            f"impact: {pool.price_impact(size, 'A') * 100:5.2f}%"
        )
    print()

    got = pool.swap(10.0, "A")
    print(f"executed: swapped 10 A, received {got:.2f} B")
    print(f"after: {pool}")
    print(f"spot price now: 1 A = {pool.spot_price():.2f} B  (fee stays in the pool)")

    out_a, out_b = pool.remove_liquidity(lp / 2)
    print(f"\nburned half the LP -> withdrew {out_a:.2f} A and {out_b:.2f} B")
    print(f"final: {pool}")


if __name__ == "__main__":
    demo()
