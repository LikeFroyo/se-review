# Phase 2 — Stack

Establish what the language is assembled with, find the current rules for each component, and check the project against them — including where components have to agree with each other.

Load `shared/identification.md` for step 1, `shared/source-resolution.md` for step 2, `shared/adherence.md` and `shared/report-format.md` for steps 3 and 4. Phase 1 must have passed its gate.

## Step 1 — Identify the components

Enumerate **every** category. An empty category is a reported result; an unenumerated one is a gap.

| Category | What it covers | Version resolved from |
|---|---|---|
| **Runtime & framework** | Execution environment, application framework, and the server/host it runs on | Lock data, framework pin, runtime image or engine declaration |
| **Libraries** | First-party and third-party code the project depends on directly | Lock data per package, not the manifest range |
| **Datastore** | Primary store, cache, search index, queue/broker, and the driver or client | Driver or client pin, connection configuration, migration tool pin |
| **Wire protocol** | The protocol spoken between components, including its version and any negotiated features | Client and server declarations, handshake or capability configuration |
| **Transport** | Carriage of that protocol: HTTP version, framing, serialization format, connection semantics | Client configuration, server configuration, negotiated defaults |
| **Authentication & authorization scheme** | The scheme, its parameters, and the library implementing it | Library pin plus the scheme's own configuration |
| **Infrastructure & platform** | Cloud, container, orchestrator, infrastructure-as-code, and managed services | Image and module pins, infrastructure definitions |
| **Build & packaging** | Build system, bundler, transpiler, compiler flags, packaging format | Build tool pin, resolved config |
| **Testing & verification** | Test framework, assertion library, mocking, coverage tooling | Lock data per tool |
| **Observability & configuration** | Logging, metrics, tracing, and the configuration mechanism itself | Library pins, and the configuration schema the project declares |

For each component, record the resolved version and its evidence. Where a category contains many components, audit the ones on a critical path in full and the rest by sample — and record which is which.

**Tooling is a component.** A formatter, linter, or transpiler pinned to a version that the ecosystem has moved past is a legitimate finding, and it is a common one.

## Step 2 — Research each component

Per `shared/source-resolution.md`, for each component: find the steward, get the specification or reference for the pinned version line, establish currency separately, extract the obligations with their own strength, and find the migration path if the pin is behind.

### Stack research agenda

Apply the Phase 1 agenda where it applies, and add these:

| # | Question | Typical rules it produces |
|---|---|---|
| 11 | What is the supported-version policy? | Which lines receive security fixes, what support ends and when |
| 12 | What is the required production configuration? | Settings the project must set, and settings whose absence has a defined consequence |
| 13 | What is the required deployment shape? | What the component assumes about its host, and what breaks when the assumption fails |
| 14 | What is the migration procedure? | Ordered steps, breaking changes, coexistence requirements, and what must not run during migration |
| 15 | What is deprecated in the current line? | What the next upgrade removes, so the cost is known in advance |
| 16 | What are the licensing and redistribution obligations? | Terms that constrain how the project may deploy what it has assembled |

Agenda item 12 is the highest-yield item in this phase. A component's required configuration being absent is a conformance finding, not a style note — and it is invisible to a reviewer who reads only the project's own code.

## Step 3 — Cross-component agreement

This is the check unique to the stack phase, and it is the reason the stack is assessed as a whole rather than component by component.

1. **Version correspondence.** For every client/peer pair, do the pinned versions actually correspond? A client and server on incompatible lines fail at runtime in ways neither component's own audit would predict.
2. **Feature negotiation.** Where a protocol negotiates features, does the project's configuration request only what the peer supports, and does it degrade correctly when the peer does not?
3. **Serialization agreement.** Do the two sides of a boundary agree on field names, types, nullability, encoding, and default values? A mismatch is a data-integrity defect that both single-component audits pass.
4. **Configuration dependency.** Does a component's required setting depend on another component's behaviour, and does the project set both consistently?
5. **Version skew inside one component.** Where the same component appears at two versions in one tree, state whether the coexistence is supported or is a latent conflict.

Each disagreement is a finding, graded by its consequence, and cited from **both** sides.

## Step 4 — Adhere, and profile each component

1. Evaluate each component's ruleset per `shared/adherence.md`. A component with no profile and no cited ruleset is reported as **unaudited** — never silently skipped.
2. Record the cross-component findings from step 3.
3. Record coverage: examined, not examined, sampled, unresolvable.
4. Route defects out as hand-off notes.
5. Write or update one profile per component at `profiles/<component>.md` per `profiles/README.md`.
   No index is kept over these profiles — see the note in `phase1-language.md` step 4.

Each component profile carries its own steward, sources, resolved version, currency position with dates, ruleset, and conformance state. Component profiles do not restate the language profile — they reference it.

## Sequencing note

Research components in dependency order: transport before the protocol it carries, protocol before the library that implements it, runtime before the framework that runs on it. A component's specification frequently defines what the layer above it may assume, and auditing the upper layer first produces rules the lower layer has already contradicted.
