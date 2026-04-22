# Inspection Clip Example

Source PDF:

```text
meviy_quotation_examples/pdfs/009_12213_*.pdf
```

Observed drawing attributes:

- Material: `SUS304-2B`
- Thickness: `t=0.5`
- Process note: `laser cutting`
- Features: `2 x φ4` holes, bend, hem bend
- Category: sheet metal part

Suggested process chain:

1. Laser cutting
2. Bending
3. Hem bending
4. Dimensional inspection

The 3D sample in `src/cadquery/hem_clip_stages.py` is a visual approximation of these stages.
