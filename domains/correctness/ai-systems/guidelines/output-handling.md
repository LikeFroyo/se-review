# Output handling — model output is untrusted data, never a decision

Audit every point where a model's text becomes something that acts. The output is a suggestion produced by a non-deterministic component; treating it as an instruction is the defect.

## What to look for

- **Output executed or evaluated:** Model text passed to `eval`, `exec`, a template compiler, a shell, a query language, or a deserializer, so a crafted completion becomes code execution.
- **Output interpolated into a query or path:** Completion text concatenated into SQL, a command line, a file path, or a URL without parameterisation or a fixed allowlist, so the model becomes the injection vector the input never was.
- **Output used as an authorization decision:** A model-returned role, permission, price, account id, or approval treated as authoritative, where the model was only asked to *suggest* it and a deterministic check was expected to confirm it.
- **Structure assumed from prose:** Parsing a required field out of free text with a regex or a split, so a model that rephrases, adds a preamble, or omits the field produces a wrong or empty value with no error.
- **Unvalidated tool arguments:** Arguments the model produced for a tool passed straight through, so an out-of-range, cross-tenant, or malformed value reaches the tool.
- **Model output persisted or logged raw:** A completion written to a record, a ticket, or a log verbatim, where it is later rendered or executed by a system that treats stored text as trusted.
- **Model output used to build a URL or a redirect target:** A completion supplied as a link destination with no scheme or host allowlist, so a plausible-looking answer becomes an open redirect or an SSRF hop.
