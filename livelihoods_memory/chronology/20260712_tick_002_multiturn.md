# Tick 002 multiturn — first livelihoods dialogue pass

## Why

Seed saturation does not test whether typed holes can be clarified and bound without rewriting
the expression tree. Five sector cases exercised facility, place, indicator, and behavior-proxy
holes with model binding and deterministic substitution side by side.

## Result

The pass scored 0.886. One failure was a mismatched scripted slot name, not architecture. The
other was real under-holing: `job market` became a concrete `job` entity, leaving no slot for the
user's requested youth-unemployment measure. I retained the unary trend tree shape but changed
its exemplar to `COMPARE(AGGREGATE(SELECT(?indicator, ?place)))`. Dialogue and the full seed bank
must both rerun to detect in-context rotation.
