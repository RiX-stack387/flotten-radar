# Language Detection Router

A platform-agnostic, configurable language detection system with injectable detectors and timeout-based fallback.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LanguageDetectionRouter                             │
│                            (Singleton)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │  Detector 1 │   │  Detector 2 │   │  Detector 3 │   │  Detector N │      │
│  │  Priority:1 │   │  Priority:2 │   │  Priority:3 │   │  Priority:N │      │
│  │  Timeout:50 │   │  Timeout:150│   │  Timeout:500│   │  Timeout:X  │      │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘      │
│        ↓                  ↓                  ↓                  ↓           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Fallback Chain (on timeout only)                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detection Flow

```
                              detect(text)
                                   │
                                   ▼
                        ┌──────────────────┐
                        │  Normalize Text  │
                        │  (strip emojis,  │
                        │   URLs, etc.)    │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Text Length?    │
                        └────────┬─────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
     ┌────────────────┐                   ┌────────────────┐
     │  SHORT (≤50)   │                   │   LONG (>50)   │
     └───────┬────────┘                   └───────┬────────┘
             │                                    │
             ▼                                    │
     ┌────────────────┐                           │
     │   Dictionary   │                           │
     │    Lookup      │                           │
     └───────┬────────┘                           │
             │                                    │
     ┌───────┴───────┐                            │
     │               │                            │
  Match?          No Match                        │
     │               │                            │
     ▼               └────────────┬───────────────┘
  Return                          │
  Result                          ▼
                         ┌────────────────┐
                         │  Run Detectors │
                         │  (with timeout │
                         │   fallback)    │
                         └───────┬────────┘
                                 │
                                 ▼
                         ┌────────────────┐
                         │ Process Result │
                         │ (filter, etc.) │
                         └───────┬────────┘
                                 │
                                 ▼
                         ┌────────────────┐
                         │ Return Result  │
                         │ or Fallback    │
                         └────────────────┘
```

## Fallback Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Detector Execution Flow                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Detector 1 (Priority 1)                                           │
│        │                                                            │
│        ├── Success ──────────────────────────► Return Result        │
│        │                                                            │
│        ├── Empty Result ─────┐                                      │
│        │                     │                                      │
│        ├── Error ────────────┼───► Try Next Detector                │
│        │                     │                                      │
│        └── TIMEOUT ──────────┘                                      │
│                                                                     │
│   Detector 2 (Priority 2)                                           │
│        │                                                            │
│        └── ... (same logic)                                         │
│                                                                     │
│   If all fail ─────────────────────────────► Return null/fallback   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```typescript
import { LanguageDetectionRouter } from "./LanguageDetectionRouter";
import { ChromeLanguageDetector } from "./detectors/ChromeLanguageDetector";
import { FastTextLanguageDetector } from "./detectors/FastTextLanguageDetector";

// 1. Get router instance
const router = LanguageDetectionRouter.getInstance();

// 2. Configure (optional)
router.configure({
	maxDetectorAttempts: 2, // Max detectors to try
	shortTextThreshold: 50, // Characters threshold
	preferredLanguagesProvider, // Your languages provider
});

// 3. Register detectors (lower priority = tried first)
router.registerDetector(new ChromeLanguageDetector(), {
	priority: 1,
	timeoutMs: 50,
});

router.registerDetector(new FastTextLanguageDetector(), {
	priority: 2,
	timeoutMs: 150,
});

// 4. Initialize (checks support, calls init())
await router.initialize();

// 5. Detect language
const result = await router.detect("Hello world");
// → { language: "en", confidence: 0.95 }
```

## Configuration Options

| Option                       | Type                        | Default     | Description                               |
| ---------------------------- | --------------------------- | ----------- | ----------------------------------------- |
| `normalizeText`              | `boolean`                   | `true`      | Strip emojis, URLs, etc. before detection |
| `maxTextLength`              | `number`                    | `10000`     | Truncate text longer than this            |
| `defaultTimeoutMs`           | `number`                    | `500`       | Default timeout per detector              |
| `shortTextThreshold`         | `number`                    | `50`        | Chars threshold for short text strategy   |
| `maxDetectorAttempts`        | `number`                    | `Infinity`  | Max detectors to try per call             |
| `preferredLanguagesProvider` | `PreferredLanguagesBuilder` | `undefined` | Provider for user's preferred languages   |

## Implementing a Detector

```typescript
import { ILanguageDetector, DetectedLanguages } from "./types";

class MyCustomDetector implements ILanguageDetector {
	readonly id = "my-custom-detector";
	readonly name = "My Custom Detector";

	async isSupported(preferredLanguages?: string[]): Promise<boolean> {
		// Check if detector can run in this environment
		return typeof MyAPI !== "undefined";
	}

	async init(): Promise<void> {
		// Load models, warm up caches, etc.
	}

	async detect(text: string): Promise<DetectedLanguages> {
		// Return array of { language, confidence }
		// Return empty array [] on failure (never null)
		return [{ language: "en", confidence: 0.95 }];
	}

	dispose(): void {
		// Cleanup resources
	}
}
```

## Detection Options

```typescript
const result = await router.detect(text, {
	preferredLanguages: ["en", "de"], // Override preferred languages
	forcePreferredLanguages: true, // Restrict results to preferred only
	shouldReturnFallback: true, // Return { language: 'en', confidence: 0 } instead of null
	maxDetectorAttempts: 1, // Override max attempts for this call
});
```

## Built-in Filtering

The router automatically filters:

| Filter                       | Description                                     |
| ---------------------------- | ----------------------------------------------- |
| **Blacklisted Languages**    | `haw`, `hmn`, `co`, `fy`, `gd`, `cbk`, `und`    |
| **Latn Variants**            | Languages ending with `-Latn` (e.g., `sr-Latn`) |
| **Galician False Positives** | `gl` filtered when `pt`/`es`/`ca` is preferred  |

## API Reference

### Router Methods

| Method                                | Description                        |
| ------------------------------------- | ---------------------------------- |
| `getInstance()`                       | Get singleton instance             |
| `configure(config)`                   | Update configuration               |
| `registerDetector(detector, options)` | Add detector with priority/timeout |
| `unregisterDetector(id)`              | Remove detector                    |
| `toggleDetector(id, enabled)`         | Enable/disable detector            |
| `setDetectorTimeout(id, ms)`          | Update detector timeout            |
| `getActiveDetectors()`                | Get enabled detectors              |
| `initialize()`                        | Initialize all detectors           |
| `detect(text, options?)`              | Detect language                    |
| `getDialectForLanguage(code)`         | Get dialect for language           |
| `dispose()`                           | Cleanup all detectors              |

## Callbacks

```typescript
router.configure({
	onDetectionComplete: (result) => {
		analytics.track("detection_complete", result);
	},
	onDetectionError: (error, detectorId) => {
		logger.error(`Detector ${detectorId} failed`, error);
	},
	onDetectorTimeout: (detectorId, timeoutMs) => {
		metrics.increment("detector_timeout", { detectorId });
	},
});
```

## Text Processing Pipeline

```
Raw Text
    │
    ▼
┌─────────────────┐
│ Strip Emojis    │
│ Strip URLs      │
│ Strip Emails    │
│ Strip Mentions  │
│ Strip Hashtags  │
│ Normalize WS    │
│ Truncate        │
└────────┬────────┘
         │
         ▼
  Normalized Text
```

## Short vs Long Text Strategy

```
┌────────────────────────────────────────────────────────────────┐
│                    Detection Strategy                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  SHORT TEXT (≤50 chars)                                        │
│  ├── 1. Dictionary lookup (common phrases)                     │
│  ├── 2. Detectors (restricted to preferred languages)          │
│  └── 3. Filter results to preferred languages only             │
│                                                                │
│  LONG TEXT (>50 chars)                                         │
│  ├── 1. Detectors (full language set)                          │
│  └── 2. High confidence early return optimization              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Preferred Languages Provider

The `PreferredLanguagesBuilder` collects user's preferred languages from multiple sources and provides them to the router for better detection accuracy.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│               PreferredLanguagesBuilder                         │
│                    (Singleton)                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Language Sources (Priority Order)                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                         │   │
│   │  1. GeoIP API ──────► ["de", "en"]  (from user's IP)    │   │
│   │         │                                               │   │
│   │         ▼                                               │   │
│   │  2. Navigator ──────► ["de-DE", "en-US", "fr"]          │   │
│   │         │              (browser settings)               │   │
│   │         ▼                                               │   │
│   │  3. Fallback ───────► ["en"]  (always included)         │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│              ┌───────────────────────┐                          │
│              │  Dedupe & Normalize   │                          │
│              │  ["de", "en", "fr"]   │                          │
│              └───────────────────────┘                          │
│                          │                                      │
│                          ▼                                      │
│              ┌───────────────────────┐                          │
│              │   Storage (persist)   │                          │
│              └───────────────────────┘                          │
│                                                                 │
│   Dialect Extraction (automatic)                                │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  "en-GB" ──► { en: "gb" }                               │   │
│   │  "de-AT" ──► { de: "at" }                               │   │
│   │  "pt-BR" ──► { pt: "br" }                               │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Setup

```typescript
import { PreferredLanguagesBuilder } from "./preferredLanguagesBuilder";

// 1. Get instance and enable
const provider = PreferredLanguagesBuilder.getInstance();
provider.setEnabled(true);

// 2. Configure storage and HTTP client
provider.configure({
	preferredStorage: {
		languages: {
			get: () => chrome.storage.local.get("preferredLanguages"),
			set: (langs) => chrome.storage.local.set({ preferredLanguages: langs }),
		},
		dialects: {
			get: () => chrome.storage.local.get("preferredDialects"),
			set: (dialects) => chrome.storage.local.set({ preferredDialects: dialects }),
		},
	},
	httpGet: apiService.api.get, // For GeoIP API calls
	fallbackLanguage: "en",
});

// 3. Initialize on first install (fetches GeoIP + navigator languages)
await provider.setInitialPreferredLanguages();

// 4. Connect to router
router.configure({ preferredLanguagesProvider: provider });
```

### Provider Methods

| Method                                     | Description                                         |
| ------------------------------------------ | --------------------------------------------------- |
| `setEnabled(boolean)`                      | Enable/disable (disabled = no-op, returns defaults) |
| `configure(config)`                        | Set storage and HTTP client                         |
| `setInitialPreferredLanguages()`           | Fetch and persist languages from all sources        |
| `getPreferredLanguages()`                  | Get current preferred languages                     |
| `addPreferredLanguage(code)`               | Add a language (e.g., from UI selection)            |
| `removePreferredLanguage(code)`            | Remove a language                                   |
| `getUserPreferredDialectForLanguage(code)` | Get dialect for language (e.g., "en" → "us")        |

### Default Dialects

When no specific dialect is detected, these defaults are used:

| Language | Default Dialect |
| -------- | --------------- |
| `en`     | `us`            |
| `de`     | `de`            |
| `fr`     | `fr`            |
| `es`     | `es`            |
| `pt`     | `br`            |

### Per-Call Override

You can bypass the provider and pass languages directly:

```typescript
// Use provider's languages (default)
const result1 = await router.detect("Bonjour");

// Override with custom languages for this call only
const result2 = await router.detect("Bonjour", {
	preferredLanguages: ["fr", "en"], // Ignores provider
});

// Force results to only match preferred languages
const result3 = await router.detect("Bonjour", {
	preferredLanguages: ["fr", "en"],
	forcePreferredLanguages: true,
});
```

### Feature Flag Control

The provider has a built-in kill switch for A/B testing:

```typescript
// Controlled via experiment flag
const { isEnabled } = await getExperimentFlags();

provider.setEnabled(isEnabled);

// When disabled:
// - getPreferredLanguages() → ["en"] (fallback only)
// - setInitialPreferredLanguages() → no-op
// - addPreferredLanguage() → no-op
// - getUserPreferredDialectForLanguage() → default dialect
```

### Integration Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                    Full Integration Flow                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Extension Install                                                 │
│       │                                                            │
│       ▼                                                            │
│  ┌─────────────────────┐                                           │
│  │ Check Experiment    │                                           │
│  │ isEnabled?          │                                           │
│  └──────────┬──────────┘                                           │
│             │                                                      │
│      ┌──────┴──────┐                                               │
│      │             │                                               │
│   Enabled       Disabled                                           │
│      │             │                                               │
│      ▼             ▼                                               │
│  Configure      Skip                                               │
│  Provider       (uses defaults)                                    │
│      │                                                             │
│      ▼                                                             │
│  setInitialPreferredLanguages()                                    │
│      │                                                             │
│      ├── Fetch GeoIP languages                                     │
│      ├── Get navigator.languages                                   │
│      ├── Extract dialects (en-GB → gb)                             │
│      └── Persist to storage                                        │
│                                                                    │
│  On Detection                                                      │
│       │                                                            │
│       ▼                                                            │
│  router.detect(text)                                               │
│       │                                                            │
│       ├── options.preferredLanguages provided?                     │
│       │      │                                                     │
│       │   Yes ──► Use provided languages                           │
│       │      │                                                     │
│       │   No ───► Call provider.getPreferredLanguages()            │
│       │                                                            │
│       ▼                                                            │
│  Use languages for detection filtering                             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```
