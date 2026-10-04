# Unsafe parsing — untrusted bytes into interpreters and filesystem paths

Audit every point where request-derived data reaches a parser that constructs more than data, or a path the service can write.

## Deserialization and entity resolution

- **Object reconstruction from untrusted bytes:** `pickle.loads`, `yaml.load` without a safe loader, `marshal.loads`, `ObjectInputStream`, .NET `BinaryFormatter`, or PHP `unserialize` on any request-derived value, letting a crafted payload instantiate a gadget chain and run code as the service account.
- **External entity resolution:** An XML, SVG, or document parser left able to resolve DTDs, external entities, or XInclude, so a document reads local files or reaches internal endpoints on the server's behalf.
- **Expression or template evaluation:** `eval`, `exec`, a dynamic `Function` constructor, or a template compiled from a client-supplied string — code execution by a less exotic route.

## Path traversal and archive extraction

- **Unvalidated path join:** A filename or path segment from the request concatenated onto a base directory with no containment check after resolution, so `..` segments escape the intended root on read or write.
- **Archive extraction trusting entry names:** `ZipFile.extractall` or an equivalent writing members under their own `entry.name`, so an entry named `../../…` plants a file outside the destination.
- **Symlink-following write:** An upload or cache path where a symlink already present in the destination redirects the write to an attacker-chosen target.
