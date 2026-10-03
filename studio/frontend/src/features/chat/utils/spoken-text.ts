// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

import { fromMarkdown } from "mdast-util-from-markdown";
import { gfmFromMarkdown } from "mdast-util-gfm";
import { gfm } from "micromark-extension-gfm";

type MarkdownNode = {
  type: string;
  value?: string;
  alt?: string | null;
  children?: MarkdownNode[];
};

// Containers whose children are blocks: a line break between them gives the voice a pause.
const BLOCK_CONTAINERS = new Set([
  "root",
  "blockquote",
  "list",
  "listItem",
  "table",
]);

function read(node: MarkdownNode): string {
  switch (node.type) {
    case "text":
    case "inlineCode":
    case "code":
      return node.value ?? "";
    // Renderer-only: a voice has nothing to say for raw HTML or a rule.
    case "html":
    case "thematicBreak":
      return "";
    case "image":
    case "imageReference":
      return node.alt ?? "";
    case "break":
      return "\n";
    case "tableRow":
      return (node.children ?? []).map(read).join(", ");
    default:
      return (node.children ?? [])
        .map(read)
        .join(BLOCK_CONTAINERS.has(node.type) ? "\n" : "");
  }
}

/** The words of a markdown reply without its markup, for a voice to read (#12547). A system
 *  voice reads the source as written, so bold came out as "asterisk asterisk" and a link as its
 *  URL. Parsed with the same CommonMark + GFM rules the chat renders with, so what is read is
 *  what is shown: emphasis and headings lose their marks, links read their text, images their
 *  alt, code reads as written, table cells are separated by commas. */
export function markdownToSpeech(markdown: string): string {
  const tree = fromMarkdown(markdown, {
    extensions: [gfm()],
    mdastExtensions: [gfmFromMarkdown()],
  });
  return read(tree)
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{2,}/g, "\n")
    .trim();
}
