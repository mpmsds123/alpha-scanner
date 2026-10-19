# Design evolution

The scanner changed when evidence contradicted an assumption. This is the core research record, not implementation churn.

| Initial belief or proposal | Evidence | Design response |
|---|---|---|
| Every dataset could be evaluated with a 10-year noise band | One live dataset had only about two years of usable history | Add a minimum-history gate before allocating more budget; do not report the 10-year FDR for that dataset |
| Operator-level sequential pruning would save budget | Replay across nine worth-mining datasets pruned nothing: 7,270 simulations and 243 hits both before and after | Remove operator pruning; use field-first ordering without deletion |
| Field hits should predict more hits | Post-hit cells produced materially higher hit rates in historical data | Prioritize remaining templates from hit fields |
| False positives from noise would be the main post-threshold constraint | In one rich dataset, 30 of 34 platform checks failed production correlation | Treat novelty/correlation as the binding constraint, separate from noise FDR |
| One family leader could represent the family's correlation verdict | Lower-ranked family members sometimes passed after leaders failed | Do not infer a whole family's correlation result from one representative |
| Field-first ordering would visibly front-load hits | Two early datasets produced mixed first-half vs second-half counts | Keep the mechanism, but label the timing benefit inconclusive |

The current design therefore makes narrow claims: it detects low-yield datasets quickly, directs search toward empirically productive fields, preserves resumability, and exposes where selection and novelty remain unresolved.

