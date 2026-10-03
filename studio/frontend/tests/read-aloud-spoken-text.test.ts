// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

// #12547: a system voice read the markdown source, so "**bold**" came out as "asterisk
// asterisk bold asterisk asterisk". Read aloud speaks the words the chat shows.

import assert from "node:assert/strict";
import test from "node:test";

import { markdownToSpeech } from "../src/features/chat/utils/spoken-text.ts";

test("emphasis, strikethrough and headings lose their marks", () => {
  assert.equal(
    markdownToSpeech("# Plan\n\nUse **bold**, _italic_ and ~~gone~~ words."),
    "Plan\nUse bold, italic and gone words.",
  );
});

test("lists and quotes read their items one per line", () => {
  assert.equal(
    markdownToSpeech("- one\n- two\n\n1. three\n\n> quoted\n\n---\n\nafter"),
    "one\ntwo\nthree\nquoted\nafter",
  );
});

test("links read their text, images their alt text", () => {
  assert.equal(
    markdownToSpeech(
      "See [the docs](https://docs.unsloth.ai) and ![a diagram](x.png).",
    ),
    "See the docs and a diagram.",
  );
});

test("code reads as written, raw HTML is silent", () => {
  assert.equal(
    markdownToSpeech(
      "Run `pip install unsloth`.<br>\n\n```sh\nunsloth studio\n```",
    ),
    "Run pip install unsloth.\nunsloth studio",
  );
});

test("table cells are separated so the voice pauses between them", () => {
  assert.equal(
    markdownToSpeech("| Model | Size |\n| --- | --- |\n| Qwen3 | 8B |"),
    "Model, Size\nQwen3, 8B",
  );
});

test("plain prose is untouched, including intraword underscores and literal symbols", () => {
  const prose = "Set max_seq_length to 2048; the loss fell 3 * 2 = 6 points.";
  assert.equal(markdownToSpeech(prose), prose);
});
