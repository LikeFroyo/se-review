# Untrusted model input — injection, instruction confusion, and poisoned retrieval

Audit every byte that reaches a model. The model cannot distinguish an instruction from data, so the *caller's* architecture is the only control.

## What to look for

- **Instruction and data in one channel:** User text, an uploaded document, a web page, an email body, or a tool result concatenated into the same prompt as the instructions, so content can assert a new instruction and the model cannot tell which is which.
- **Instruction placed after untrusted content:** The system instruction positioned before the untrusted block, where recency makes the later content dominate — the structural half of the same defect.
- **Retrieved content with no trust label:** Chunks from a shared corpus, another tenant's data, or a wiki page fed to the model with no provenance marker, so the model treats stored content as authoritative.
- **Retrieval poisoning surface:** A document store writable by the same population whose questions it answers, so an attacker plants the answer and the model retrieves their text as fact.
- **Tool output fed back unfiltered:** A tool or API response placed in the prompt raw, including its error text and any content it fetched, so a page that reflects attacker text reaches the model through the tool channel.
- **Trust boundary crossed by metadata:** Filenames, titles, URLs, or usernames from untrusted sources placed in the instruction region rather than the data region.
- **No output scoping:** The model granted a capability — a tool, a URL, a query scope — that the calling user would not have, so injected instructions can act beyond the requester's permissions.
