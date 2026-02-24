# Mask PNG Builder

Open `index.html` in a browser.

## What it does
- Upload a normal image.
- Paint the mask area.
- Download an alpha-mask PNG (`input-alpha-mask.png`), ready for `LoadImage` mask output.
- Also exports an inverted-alpha variant if mask direction is opposite.

## Usage with this worker
In your RunPod request:
- Set `input.image_name` to the downloaded filename (for example `input-alpha-mask.png`).
- Add the file in `input.images` with the same `name` and base64 content.

Example shape:

```json
{
  "input": {
    "workflow": { "...": "..." },
    "image_name": "input-alpha-mask.png",
    "images": [
      {
        "name": "input-alpha-mask.png",
        "image": "data:image/png;base64,..."
      }
    ]
  }
}
```
