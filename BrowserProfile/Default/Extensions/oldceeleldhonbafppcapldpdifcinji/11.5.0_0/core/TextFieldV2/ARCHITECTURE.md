# TextFieldV2 Architecture

TextFieldV2 is a small, self-contained module that solves one hard problem: **keeping grammar underlines (and other markers) in the right place while the user is typing.**

---

## The Problem

Imagine you're typing in a text editor. The grammar checker finds an error at positions 10–15 ("teh quick"). While the server was thinking, you added a sentence at the beginning. Now position 10–15 points to different text entirely. The underline is in the wrong place.

TextFieldV2 tracks every edit as a structured operation, then slides all the markers forward or backward so they stay under the correct words.

---

## How It Works (30-Second Version)

```
User types → TextField records edit as an operation → All markers are adjusted → Done
```

1. Every time the text changes, `TextField` computes a diff (what was inserted, deleted, or replaced).
2. That diff is stored in a history log (up to 500 entries).
3. Every existing marker (span) is run through a **behavior** that decides:
    - Should this marker survive the edit? (e.g., if the user edited inside the error, drop it)
    - If yes, where should its start/end positions move to?

---

## File Map

```
TextFieldV2/
├── index.ts                  ← Public barrel (re-exports everything)
├── types.ts                  ← Core data types and interfaces
├── TextField.ts              ← Main class: text + version + spans + history
├── utils/
│   └── ot.ts                 ← Diff algorithm and index math
└── behaviors/
    ├── DefaultSpanBehavior.ts ← Base class for all span behaviors
    └── index.ts              ← Concrete behaviors (Grammar, Recommendation, Sentence)
```

Total: ~600 lines. No DOM, no RxJS, no browser APIs. Pure data logic.

---

## Core Concepts

### Operations (OT)

Every text change is represented as exactly **one** operation:

| Type        | Meaning                            | Example                      |
| ----------- | ---------------------------------- | ---------------------------- |
| `insert`    | New text added at a position       | Typing "hello" at position 5 |
| `delete`    | Text removed between two positions | Deleting characters 3–7      |
| `replace`   | Text swapped for different text    | Replacing "teh" with "the"   |
| `no-change` | Text is identical                  | Setting the same text again  |

Each operation carries a **version number** — a simple counter that goes up by 1 on every real change.

### Spans

A **span** is a marker on the text — think of it as a highlighted range. Each span has:

- `start` / `end` — character positions in the text
- `type` — what kind of marker (`"suggestion"` for grammar errors, `"sentence"` for sentence boundaries)
- `otVer` — which version of the text these positions are valid for
- `id` — optional unique identifier
- `contextWindow` — optional wider range used by recommendation-type spans

### Behaviors

A **behavior** is a strategy that answers two questions for a span when an edit happens:

1. **Should this span survive?** (`shouldKeep`)
2. **Where should its positions move?** (`transform`)

```
┌─────────────────────────────────────────────────────┐
│               SpanBehavior (interface)               │
│                                                     │
│   shouldKeep(span, operation) → true / false        │
│   transform(span, operation)  → new span / null     │
└─────────────────────────────────────────────────────┘
```

---

## Architecture Diagram

```
                    ┌──────────────────────────────────────────────┐
                    │              TextField                        │
                    │                                              │
                    │  State:                                      │
                    │    • currentText     (the actual string)     │
                    │    • currentVersion  (monotonic counter)     │
                    │    • history[]       (past operations)       │
                    │    • spans[]         (active markers)        │
                    │    • behaviorMap     (strategy per type)     │
                    │                                              │
   setText(new) ───►│  1. Diff old vs new → OTOperation           │
                    │  2. Version++                                │
                    │  3. Push operation to history                │
                    │  4. For each span:                           │
                    │       behavior.transform(span, op)           │
                    │       → keep (with new positions)            │
                    │       → or drop (edit touched the span)      │
                    │  5. Return { operation, removedSpanIds }     │
                    │                                              │
   setSpans([]) ───►│  1. For each incoming span:                  │
                    │       Replay history from span.otVer         │
                    │       → bring span positions up to date      │
                    │  2. Merge with existing spans                │
                    │       → by ID (upsert)                       │
                    │       → by type (replace id-less spans)      │
                    │                                              │
                    └──────────────────────────────────────────────┘
                              │
                              │ delegates to
                              ▼
                    ┌──────────────────────────────────────┐
                    │     DefaultSpanBehavior (abstract)    │
                    │                                      │
                    │  transform(span, op):                │
                    │    if !shouldKeep → return null       │
                    │    else → shift start/end positions   │
                    │           using transformIndex()      │
                    └────────────┬─────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
     ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
     │ GrammarBehavior│ │ Recommendation │ │ SentenceBehavior│
     │                │ │   Behavior     │ │                │
     │ Drop if edit   │ │ Drop if edit   │ │ Drop if edit   │
     │ touches the    │ │ is inside the  │ │ is strictly    │
     │ error range    │ │ context window │ │ inside sentence│
     │ (± 1 char)     │ │ around span    │ │ boundaries     │
     └────────────────┘ └────────────────┘ └────────────────┘
```

---

## The Diff Algorithm (`calculateOT`)

Given old text and new text, produce a single operation describing the change.

**Algorithm:** Find the longest common prefix and suffix, then classify what happened in the middle.

```
Old: "The quik brown fox"
New: "The quick brown fox"

Common prefix: "The qui"  (7 chars)
Common suffix: " brown fox"  (10 chars)

Middle of old: "k"   (positions 7–8)
Middle of new: "ck"  (positions 7–9)

Result: replace(start=7, end=8, text="ck")
```

The `transformIndex` function then answers: "If a character was at position X before this operation, where is it now?"

- **Insert before X** → X shifts right by the inserted length
- **Delete before X** → X shifts left by the deleted length
- **Edit straddles X** → X collapses to the edit start (position is inside the changed region)

---

## Behavior Rules — When Is a Span Dropped?

Each behavior defines different sensitivity to edits. Here's when each one drops a span:

### GrammarBehavior

Drops the span if the edit **touches or is adjacent to** the error range.

```
   span.start-1          span.end+1
        ▼                    ▼
  ──────[======ERROR======]──────
        ◄── "danger zone" ──►

  If any part of the edit falls in the danger zone → drop the span.
```

**Why:** If you type right next to a grammar error, the error likely changed. Better to re-check than show a stale underline.

### RecommendationBehavior

Drops the span if the edit falls inside the **context window** (or the span range if no context window exists).

```
   ctx.start              ctx.end
      ▼                      ▼
  ────[====CONTEXT WINDOW====]────
           [==SPAN==]
      ◄── "danger zone" ────►

  Edit inside context window → drop.
```

**Why:** Recommendations depend on surrounding context. Changing nearby words may invalidate the suggestion.

### SentenceBehavior

Drops the span if the edit is **strictly inside** the sentence boundaries (for inserts) or overlaps them (for deletes/replaces).

```
   span.start              span.end
       ▼                      ▼
  ─────[======SENTENCE======]─────

  Insert strictly between start and end → drop.
  Delete/replace overlapping the boundary → drop.
  Insert at the boundary edge → keep (allows appending to sentences).
```

**Why:** Inserting text inside a sentence changes its structure, so sentence boundaries need to be recalculated.

---

## The History Replay Mechanism

When the server returns grammar errors, those errors are tagged with the version of the text that was checked. But the user may have kept typing since then. The history replay brings those errors up to date.

```
Timeline:
  v0: "Hello wrold"          ← server checks this
  v1: "Hello wrold!"         ← user added "!"
  v2: "Hey, Hello wrold!"    ← user added "Hey, "
  v3: server returns error at positions 6–11 (otVer=0)

Replay:
  Apply v1 (insert "!" at end)  → error stays at 6–11 ✓
  Apply v2 (insert "Hey, " at 0) → error shifts to 11–16 ✓

Result: error underline appears at the correct position in v3 text.
```

If at any point a replay operation would invalidate the span (e.g., the user edited inside the error), the span is dropped entirely — the server will re-check and send a fresh result.

The history buffer holds up to **500 operations**. If a span is so old that its version predates the oldest stored operation, it cannot be replayed and is rejected with an error.

---

## Span Merging (setSpans)

When new spans arrive, they are merged with existing ones:

```
                        Incoming spans
                              │
                    ┌─────────┴──────────┐
                    │                    │
               Has ID?              No ID?
                    │                    │
              Upsert into         Replace all existing
              span map by ID      id-less spans of
              (add or update)     the same type
                    │                    │
                    └─────────┬──────────┘
                              │
                         Final span list
```

This allows the server to update specific errors by ID while also replacing bulk data like sentence boundaries.

---

## Integration with the Rest of the System

TextFieldV2 does not run alone. It sits inside a pipeline:

```
  ┌──────────┐      ┌──────────────────┐      ┌─────────────┐
  │  Editor  │ ───► │ TextFieldCheck   │ ───► │  TextField   │
  │  (DOM)   │      │   Pipeline       │      │  (TextFieldV2)│
  └──────────┘      │                  │      └─────────────┘
                    │  • Batches edits │           │
                    │  • Syncs with    │◄──────────┘
                    │    server        │   returns OT ops
                    │  • Manages check │   and span changes
                    │    scheduling    │
                    └──────────────────┘
```

- **`syncAwareCheckPipeline.ts`** creates a `TextField` with `GrammarBehavior` and `SentenceBehavior`.
- On each text change, it calls `setText` and collects the OT operation for the server.
- When the server responds with errors, it calls `setSpans` to merge them in.
- A `postTransformHook` adjusts related metadata (like phrase diff offsets) when spans shift.

---

## Key Design Decisions

| Decision                       | Rationale                                                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Single operation per edit      | Simplifies diff, history, and replay. Compound edits (e.g., find-and-replace) become one `replace`.              |
| Strategy pattern for behaviors | Different span types have different invalidation rules. New types can be added without changing `TextField`.     |
| History cap at 500             | Prevents unbounded memory growth in long editing sessions.                                                       |
| Lightweight history entries    | Stored operations strip the actual text content (keep only length) since replay only needs index math, not text. |
| No DOM or events               | Pure data logic that can run in any JS context (content script, service worker, tests).                          |
| Version as a monotonic counter | Simple, deterministic ordering. No need for vector clocks since there's only one writer.                         |

---

## Glossary

| Term               | Meaning                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **OT**             | Operational Transformation — a technique for keeping data consistent across concurrent edits. Here used in a simplified single-writer form. |
| **Span**           | A marked range in the text (e.g., a grammar error underline from position 5 to 10).                                                         |
| **Behavior**       | A pluggable strategy that decides how a span type reacts to text edits.                                                                     |
| **Version**        | A counter that increments with each text change. Used to track which version of the text a span's positions are valid for.                  |
| **History**        | A rolling log of past operations used to replay span positions forward in time.                                                             |
| **Context window** | An optional wider range around a span, used by recommendations to decide if nearby edits should invalidate the suggestion.                  |
| **Transform**      | The process of adjusting a span's positions to account for a text edit.                                                                     |
| **Replay**         | Applying multiple historical operations to a span to bring it from an older version to the current version.                                 |
