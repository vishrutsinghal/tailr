# PM-7 Adoption Validation Design

The Evaluation Harness owns one sealed adoption catalog and local study state
under `.tailtrail/evaluation/adoption/`. The catalog fixes cohorts, scenarios,
thresholds, safety boundaries, feedback signals, and decision reasons. Trial
input uses random study-local aliases and compact evidence references only.
Recording derives time-to-plan from timestamps and seals an immutable receipt;
it does not trust a caller-supplied duration.

The report revalidates every receipt and catalog identity before aggregation.
Fixture receipts remain visible but are excluded from metrics. Observed receipts
are grouped by cohort, with nearest-rank p75 values and explicit denominators.
Missing denominators fail the relevant gate, while zero interventions correctly
produce a zero false-intervention rate. Any malformed or tampered artifact makes
the report `invalid`; sufficient coverage with a missed threshold becomes
`thresholds-not-met`; only all passing gates become `qualified`.

Feedback signals are closed categorical values. A recommendation becomes
eligible only after three independent qualifying participants repeat it with
all safety observations intact. Approved proposals bind the exact report digest
and supporting trial IDs. Applied decisions additionally require separate
change and validation references. These artifacts establish evidence lineage;
they grant no implementation, release, acceptance, or safety-bypass authority.
