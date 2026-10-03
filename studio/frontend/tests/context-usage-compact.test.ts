// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

// When the chat header is squeezed, the context bar shrinks to a ring.

import assert from "node:assert/strict";
import test from "node:test";

import { deriveContextUsageBar } from "../src/features/chat/lib/context-usage-bar-state.ts";

import { readSrc } from "./helpers/kit.ts";

test("the compact face is the ring, unless there is no window to fill", () => {
  // a known window: the ring alone, with no percent label
  assert.equal(deriveContextUsageBar({ used: 16384, total: 32768 })?.compactFace, null);
  // nothing counted yet: the empty ring
  assert.equal(deriveContextUsageBar({ used: null, total: 32768 })?.compactFace, null);
  // no window: the token count stands in for the ring
  assert.equal(deriveContextUsageBar({ used: 4096, total: null })?.compactFace, "4.1k");
});

test("the bar hands every input to the state, batching flags included", () => {
  const bar = readSrc("features/chat/components/context-usage-bar.tsx");
  assert.match(bar, /\(\{ className, \.\.\.input \}\) => \{\s*const state = deriveContextUsageBar\(input\);/);
});

test("the header shrinks the context bar before the model name", () => {
  const page = readSrc("features/chat/chat-page.tsx");
  assert.match(page, /"pointer-events-auto flex min-w-0 items-center gap-1"/);
  assert.match(page, /ml-auto flex min-w-min max-w-max grow basis-0 items-center gap-1 \*:shrink-0/);
});

test("the context meter stays up for a chat started on a project's landing (#12533)", () => {
  // Such a chat runs in place with the URL still on the project, so a gate on the single view
  // alone hid the meter until the chat was reopened by its thread id.
  const page = readSrc("features/chat/chat-page.tsx");
  assert.match(
    page,
    /const chatOpen =\s*view\.mode === "single" \|\|\s*\(view\.mode === "project" && activeThreadId !== null\);/,
  );
  assert.match(
    page,
    /\{showContextWindowUsage &&\s*chatOpen &&\s*\(contextUsage \|\| contextWindowKnown\) \? \(\s*<ContextUsageBar/,
  );
});
