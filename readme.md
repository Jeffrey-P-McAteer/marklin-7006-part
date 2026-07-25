
# Marklin 7006 Part design files

Learning project for me to use [cadquery](https://github.com/cadquery/cadquery) to
design a part with slightly more complex geometries than most interactive editors let you design.

Overkill for part in question, but also a CAD skill I've always wanted to have in my pocket - with this
you could easily design parametric parts where a design measurement is not known until later.

# Building .stl files

```bash
uv run part-design.py
```

Which generates the file `build/marklin-7006-part.stl`

A live preview may be seen by running:

```bash
uv run preview.py build/marklin-7006-part.stl
```

Which will re-render the part every time the given file changes.

