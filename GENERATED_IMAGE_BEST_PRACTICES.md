# Generated Image Best Practices

This file captures lessons from generating PMax supplement images inside Codex. It is specifically about AI-generated raster assets, not sourced Shopify or manufacturer images.

## Current finding: URL text is not enough

On 2026-05-22, we tested a Southwire lifestyle prompt using direct Shopify CDN URLs in the prompt text. The generated subject did not match the referenced Southwire 6506TLSX X-Treme Box closely enough for ad use.

The likely failure mode: the generation tool treated the URL and product description as text context instead of strongly using the reference image pixels. Direct image URLs are still useful for audit and for tools that can dereference them, but they are not sufficient proof that a generated image will preserve exact product geometry, proportions, outlets, labels, or color blocking.

Hard rule: do not run product-faithful image generation from URL text alone. The actual source image pixels must be passed, attached, or made visible to the generation context, and the prompt must explicitly instruct the model to preserve the visible source product.

## Preferred workflow for product-faithful ad images

1. Start from the local sourced product image whenever product fidelity matters.
2. Make the reference image visible to the generation context before prompting. In Codex, use `view_image` on the local source file immediately before `image_gen`.
3. Visually review the full sourced image pool before writing generation prompts.
4. Identify a 2-3 product composition when the source pool supports it. Prefer products that:
   - have strong silhouettes and readable shapes at thumbnail size;
   - are actively used together on the same job;
   - create a believable foreground / midground / background arrangement;
   - represent the asset group's commercial center of gravity better than small accessories.
5. Pass or reveal the selected source images directly to the image-generation context, not just as URL text. In Codex, use `view_image` on each selected local source immediately before the `image_gen` call. In API or CLI workflows, attach the actual image files as image inputs where supported.
6. Ask for a product-faithful scene composition, not a fully invented scene.
7. Preserve the exact product geometry first; let the scene, lighting, and background be creative.
8. Keep the prompt narrower than a normal lifestyle prompt. Do not ask for too many changes at once.
9. Visually inspect every generated output before accepting it. Open the generated image next to the exact source image(s) and check for hallucinations, product misrepresentation, strange use, unsafe handling, impossible physics, incorrect trade context, wrong colorway, wrong geometry, extra attachments, fake text, and missing major parts.
10. If the image fails visual QA, move it to `generated/rejected/`, record the specific reason in `manifest.md`, and regenerate with a narrower prompt that directly addresses the failure. Example: "preserve the rectangular outlet layout exactly" or "do not add extra wheels, controls, gauges, or cables."
11. If one regenerate still drifts, stop using pure generation for that asset and switch to compositing so the real product pixels remain intact.
12. Save failed attempts with a versioned filename only if they are useful for comparison; otherwise replace the candidate before upload.

## Multi-product composition requirement

Once source images are determined, do a visual selection pass before generating:

1. Open the sourced products and assess compositional potential.
2. Choose 2-3 products that either naturally work together or create a strong advertising composition.
3. Write the prompt around how those specific products interact in the scene.
4. Pass or reveal those source images directly to the generation tool call.
5. Record the selected local source files in the manifest row for the generated image.

Example: for iTOOLco wire-pulling creative, a Cannon 6K puller, reel jacks with a loaded cable reel, and the manufacturer jobsite pull image form a natural same-job composition. The Cannon puller is the hero, the reel jacks/cable reel explain supply side, and the jobsite image anchors the environment.

## Prompt pattern for Codex built-in image generation

Use this when the source image has been loaded into context:

```text
Use the visible reference image as the product identity source. Preserve the exact product silhouette, proportions, color blocking, outlet layout, legs/stand, and major physical details. Create a realistic advertising image by placing that same product into [environment]. Do not redesign the product. Do not invent a different box/tool. No text overlay, no watermark, no promotional badge.
```

Do not use this pattern unless the source image is actually visible or attached in the generation context. If only a direct URL is available, download or save the source image into the campaign `sourced/` folder first, then reveal or attach that local file before generation.

## When to use compositing instead of generation

If the generated product still drifts after one retry, switch to a compositing workflow:

1. Use the real sourced product image as the product layer.
2. Remove the white background or create a clean cutout.
3. Generate or source a jobsite background separately.
4. Composite the real product into the scene with matched shadows, perspective, and color.

This is more reliable for exact-SKU ad creative because the product pixels remain real.

## Manifest notes

For generated assets, keep both:

- The original source URL from Shopify or manufacturer.
- The local reference file path used during generation.

Example manifest source field:

```text
generated from local reference sourced/shopify-studio-hero-1.jpg; original URL: https://cdn.shopify.com/...
```

## Reject folder workflow

Generated images that fail QA should be moved to `generated/rejected/`, not deleted. Keep the manifest row, update the path to `generated/rejected/<filename>`, and write a short reason such as:

- product drifted from the reference
- wrong colorway or geometry
- hallucinated product features or extra attachments
- product used in a strange, unsafe, or category-misrepresenting way
- text overlay, watermark, or logo-like marking appeared
- background or crop weakens the ad at thumbnail size

Only images left in the active `generated/` folder are eligible for upload.
