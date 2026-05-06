# Moire — λ and k derivation (audit)

## λ

Goal: 95 % of asymptotic supply minted by year 16.

```
blocks_per_year = 365.25 × 86400 / 60 = 525,960          (60s blocks)
N_16            = 16 × 525,960         = 8,415,360       (calendar)
                  use exactly 8,409,600 = 16 × 365 × 1440 (no leap years; canon)

S(N) = (k·Ā / λ) · (1 − e^(−λN))
S(∞) = k·Ā / λ
S(N_16) / S(∞) = 1 − e^(−λ·N_16) = 0.95
                 e^(−λ·N_16) = 0.05
                 λ = -ln(0.05) / N_16
                 λ = 2.99573 / 8,409,600
                 λ ≈ 3.5622 × 10^-7  per block
```

Half-life: `ln(2) / λ ≈ 1,945,890 blocks ≈ 3.7 years`.

By year 16: `4.32 half-lives elapsed`, so `1 − 2^-4.32 ≈ 0.95`. ✓

## k

Target asymptotic cap = 21,000,000 MOI × 10^12 attomoire/MOI = 2.1 × 10^19 attomoire.

```
S(∞)   = k · Ā / λ                       (Ā := long-run mean activity)
k      = S(∞) · λ / Ā
       = 2.1 × 10^19 · 3.5622 × 10^-7 / 1
       = 7.48 × 10^12 attomoire/block
       = 7.48 MOI per block at n = 0 with Ā = 1
```

`Ā = 1` is the upper bound from constitution Article III; in practice `Ā < 1` until
the network saturates, so realized issuance is strictly below cap.

## Sanity check

At year 1 (`n = 525,960`): `R(n) ≈ 7.48 · exp(-0.187) ≈ 6.20 MOI/block`.
At year 4 (`n = 2,103,840`): `R(n) ≈ 7.48 · exp(-0.749) ≈ 3.54 MOI/block`.
At year 16 (`n = 8,409,600`): `R(n) ≈ 7.48 · exp(-2.996) ≈ 0.374 MOI/block`.

Cumulative supply at year 16 ≈ 21 M × 0.95 = 19.95 M MOI. ✓

## After transition

`R(n) = k · grad_H(ΔC) · exp(-λn)`. `grad_H` is bounded above by `θ · Ā` immediately
before transition (that's how the predicate fires); afterwards it monotonically
decays as `H(C)` approaches its irreducible Kolmogorov floor. The `exp(-λn)`
envelope is unchanged, so the asymptotic-cap bound from the PoA phase still
holds.

## Genesis pin

These numbers are pinned in `genesis/params.toml`. Modification requires a
`reduce(ΔC)` tx that itself reduces overall `H(C)`. Inflation-via-tuning is
self-defeating because the tuning patch is subject to the entropy reduction
floor (Article VI).
