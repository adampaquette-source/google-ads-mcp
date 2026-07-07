# PMax Image Asset Best Practices

Use this document when sourcing, generating, or uploading image assets for any Performance Max asset group. The goal is to feed Google's PMax algorithm a diverse, high-quality, brand-relevant creative pool that maximizes ad strength, CTR, and conversion rate.

This is an evergreen reference. The brand-specific execution lives in `PMAX_BRAND_BREAKOUT_SKILL.md` (or whichever campaign creation skill is being run -- see the registry in `CAMPAIGN_CREATION_BEST_PRACTICES.md`).

---

## Why image quality and quantity both matter

- PMax asset groups with **Excellent ad strength see 18-25% more conversions** than groups at Good. Image diversity is a major input.
- **Lifestyle images outperform product-only shots by ~28% on YouTube placements** (Google internal data).
- **Lifestyle imagery can lift CTR by up to 30%** in some industries vs studio-only.
- **Quality beats quantity** -- 5 excellent images outperform 20 mediocre ones -- but Google's algorithm also needs **variety** to find winners. The target is 10 images per asset group covering distinct visual approaches.

---

## Target count: 10 images per asset group

Aim for **10 approved images per asset group**, max 20 (Google's hard limit per slot type). Each asset group should include **at least 3 supplemental generated images** after real-source image sourcing is complete. The mix should look like:

| Type | Purpose | Funnel stage | Approximate share | Count target |
|---|---|---|---|---|
| **Studio product on white / light** | Show product clearly, build trust | Consideration | 30% | ~3 |
| **Lifestyle / in-space (no interaction)** | Product staged in a real trade environment, not being operated | Awareness, consideration | 40% | ~4 |
| **Close-up detail** | Build quality, feature callouts | Consideration | 15% | ~2 |
| **Contextual scene** | Wider environment that signals the buyer's world | Awareness | 15% | ~1-2 |

**First-slot rule**: a strong studio hero in the first position lifts CTR. Place the cleanest, most product-forward image first.

---

## Required formats per asset group

| Aspect ratio | Min size | Recommended size | Use case |
|---|---|---|---|
| Landscape (1.91:1) | 600 x 314 | 1200 x 628 | Display, Discovery, Gmail |
| Square (1:1) | 300 x 300 | 1200 x 1200 | Discovery, Search, Maps |
| Portrait (4:5) | 480 x 600 | 960 x 1200 | Mobile feed, Discovery |

Optional but high-impact:
- **9:16 vertical video** (1080 x 1920): achieves ~40% lower CPMs than horizontal formats in 2026.

---

## Sourcing priority (do this BEFORE generating any images)

Sourcing existing high-quality images is faster, cheaper, and usually better than generation. Generation is the **supplement**, not the primary source. Work through these in order until you have enough real-source images to support a 10-image final set, then add at least 3 generated supplemental images:

### 1. Existing account assets
Run `list_google_ads_image_assets(customer_id)`. Filter to brand-named images. These have already been used, are in the account, and have known dimensions.

### 2. Shopify MCP (the store's own catalog)
Use the Shopify MCP server:
- `get-collection` -- find the brand collection, list products in it
- `get-product` -- pull each product's image URLs (CDN-hosted, direct, high-resolution)

Product images from the store's own Shopify catalog are ideal: they match the store's actual inventory, they're already on a clean background, and the URLs are direct CDN links suitable for `upload_google_ads_image_asset`.

### 3. Manufacturer media library
Visit the brand's official website. Look for:
- Press / media kit pages
- Product detail pages (right-click → "view image" to get the direct CDN URL, not the PDP link)
- "For dealers" or partner asset libraries
- Brand colorways and lifestyle photography sections

Many manufacturers (Milwaukee, DeWalt, Makita, Bosch, Klein, etc.) publish high-resolution product photography for retailers. Use it.

For hero equipment, manufacturer websites are explicitly approved as a preferred source when the store catalog images are thin, accessory-heavy, or not visually representative. Prioritize official manufacturer product hero images and jobsite/lifestyle images over low-quality store shots of parts, adapters, add-ons, or consumables. Save them as `manufacturer-hero-<product>.ext` or `manufacturer-lifestyle-<product>.ext`, and record the official source URL in `manifest.md`.

### 4. Other authorized sellers of the brand
Search for the brand on other major industrial / pro tool retailers (Acme Tools, Tool Nut, CPO Outlets, Toolbarn, etc.). Their product detail pages often have higher-resolution images than the manufacturer site. Same rule: pull the **direct image URL**, not the PDP URL.

### 5. General web search (image search)
For lifestyle / contextual shots that no retailer publishes, use Google Images with:
- `<brand> <product>` filtered to large size, no license restriction
- `<brand> jobsite` for in-use shots
- Reverse image search to find higher-res versions of any candidate

### 6. ChatGPT / image generation (supplement only)
Once you have exhausted real sources, generate the supplemental images needed to reach the 10-image final set. **Every asset group must include at least 3 generated supplemental images**, even when sourced studio coverage is already strong. Generated images must always be anchored to real product images -- see "Image generation prompt rules" below. For Codex built-in image generation, the local sourced image must be loaded into the visible context with `view_image` immediately before prompting. A direct URL pasted into prompt text is audit metadata only and must not be treated as product reference input.

Use Variations of these directions to generate at least three images, up to as many needed to hit the 10 image quota:

1. **Studio/detail supplement** -- product-forward, clean, source-faithful, useful as a square or landscape crop
2. **Lifestyle / in-use supplement** -- almost always needed since manufacturer catalogs rarely have varied lifestyle shots
3. **Hero product cinematic** (MANDATED) -- one specific named hero product in dramatic lighting + realistic trade environment
4. **Hero product cinematic** visually inspect the sourced product pool and identify whether a 2-3 product composition would produce a better ad than a single-product scene. Prefer products that are actively used together on the same job or that create a strong foreground / midground / background composition. 

---

## Per-campaign asset folder convention

Working images for each campaign live in:

```
campaign_assets/
└── <campaign_slug>/
    └── <brand_or_asset_group_slug>/
        ├── sourced/         <- images Claude pulls from Shopify / manufacturer / sellers / web
        │   └── rejected/    <- sourced images reviewed out of the active set
        ├── generated/       <- images Adam generates via ChatGPT and saves here
        │   └── rejected/    <- generated images reviewed out of the active set
        └── manifest.md      <- per-asset-group manifest listing every image's source, type, status
```

- `<campaign_slug>` is a kebab-case version of the campaign name (e.g. `qt-pmax-brand-batch-2`).
- `<brand_or_asset_group_slug>` is lowercase brand or asset group name (e.g. `southwire`).
- `sourced/` is filled by Claude during sourcing (steps 1-5 above). Each file is saved with a meaningful name: `<source>-<type>-<n>.<ext>` (e.g. `shopify-studio-1.jpg`, `manufacturer-lifestyle-2.jpg`).
- `generated/` is filled by Adam after running the ChatGPT prompts. Naming: `chatgpt-<prompt-label>-<n>.png` (e.g. `chatgpt-studio-hero-1.png`).
- Each of `sourced/` and `generated/` has a `rejected/` subfolder. Move reviewed-out files there instead of deleting them, and keep the manifest row with the `rejected/` path plus a short reason.
- `manifest.md` is a simple table maintained as the folder fills:

  ```
  | File | Source URL | Type | Aspect | Status |
  |---|---|---|---|---|
  | sourced/shopify-studio-1.jpg | https://cdn.shopify.com/... | studio | 1:1 | ready |
  | generated/chatgpt-hero-1.png | (gen) | hero cinematic | 1.91:1 | uploaded -> resource_name |
  ```

The `campaign_assets/` directory is gitignored (binary files, local working storage). Images are uploaded to Google Ads from these local paths via `upload_google_ads_image_asset` once approved.

## Active-set review and rejection rules

After sourcing and generation, review every candidate before upload. The active set should represent the brand's core products and buyer-recognizable use cases, not just anything technically sold under the brand.

Generated candidates have an extra mandatory QA gate before they can remain in the active `generated/` folder:

1. Open the generated image and the exact local source image(s) used to create it.
2. Compare the generated product against the source for silhouette, proportions, color blocking, major parts, handles, legs, wheels, ports/outlets, blades, jaws, battery shape, and any visible markings.
3. Check whether the product is being used in a believable, trade-accurate way. Reject strange use cases, unsafe handling, impossible physics, nonsensical jobsite context, or scenes where the product's purpose is misrepresented.
4. Inspect for hallucinations: invented attachments, extra controls, wrong number of parts, impossible geometry, brand-like fake text, unrelated products, or a product that only vaguely resembles the source.
5. If any issue is flagged, move the candidate to `generated/rejected/`, record the reason in `manifest.md`, and regenerate with a narrower prompt that names the failed detail to preserve or avoid. If one retry still drifts, stop generating and switch to the compositing workflow in `GENERATED_IMAGE_BEST_PRACTICES.md`.

Move a candidate to the relevant `rejected/` folder when it is:

- a replacement part, consumable, small fitting, socket, bit, adapter, or module
- a battery, charger, attachment, accessory, add-on, or narrow support item that would steer the asset group away from the brand's core product line
- too visually ambiguous to communicate the brand or product category at thumbnail size
- low quality enough to weaken the asset group when better candidates exist
- generated with product drift, inaccurate colors, incorrect geometry, text overlays, watermarks, or brand-like markings inside the image
- generated with a product being used in a strange, unsafe, physically impossible, or category-misrepresenting way

Do not upload rejected images. Keep them in `rejected/` for audit and iteration history, with the manifest status explaining why they were excluded.

---

## Image generation prompt rules

**Every generation prompt MUST use the actual source image as reference input.** ChatGPT image generation produces generic, low-quality, brand-inconsistent output when given only text descriptions or product URLs. Direct image links are still required for audit and reproducibility, but they are not sufficient. The source image pixels must be passed, attached, or made visible to the generation context before the prompt is run.

See `GENERATED_IMAGE_BEST_PRACTICES.md` for Codex-specific lessons and retry workflow.

**No-interaction rule (default case).** Do NOT generate or composite the product physically interacting with other objects (cord being plugged in, hand pulling a trigger, saw cutting a beam, tool driving a rod, pump moving water). Physical interaction is the main failure mode of this kind of generation: the model renders the contact/connection point implausibly (e.g. a cord plugged into the power switch instead of an outlet). The default is a hero shot of the product (or a 2-3 product composition) staged in a relevant space, not being used. The product being **held** is a tolerable secondary case, since there is no complex functional contact point to get wrong. Environment, lighting, and camera angle create the lifestyle feel; the product simply sits in the scene.

Rules:

1. **Hard stop before generating:** if the selected local source image has not been passed, attached, or revealed to the generation context, do not generate. In Codex, call `view_image` on each selected local source file immediately before `image_gen`.
2. **Prompt must explicitly bind to the visible source image.** Use language like: "Use the visible source image as the product identity source. Preserve this exact product's silhouette, proportions, color blocking, major parts, and physical details. Do not redesign the product or invent a different tool."
3. **Always record a direct image link** (the actual `.jpg` / `.png` / `.webp` URL), not a PDP / HTML page link. This URL is for audit and reproducibility. Do not assume that a URL in prompt text alone will be used as a faithful visual reference.
4. **For multi-product compositions**, pass or reveal every selected source image and record a separate direct image link **per product** in the manifest (e.g. "drill: <link1>, impact: <link2>, battery: <link3>"). Each reference should be the cleanest available image, usually a manufacturer studio shot.
5. **How to get a direct image URL**:
   - Shopify MCP `get-product` returns image URLs in its response -- use those directly.
   - Manufacturer / seller PDPs: right-click the product image → "Copy image address". Avoid lazy-loaded placeholder URLs (look for the high-res variant).
   - Test the URL in a browser -- it must load the image directly, not a page wrapping the image.
6. **For lifestyle / contextual shots**: still pass or reveal the source product image. The background may be invented, but the product must be copied from the source identity, not imagined from text.
7. **For multi-product compositions**: visually select the 2-3 products first, then provide all selected source images as actual image inputs where supported. In Codex, reveal each selected local file with `view_image` immediately before generation.
8. **Save the chosen reference URLs and local source file paths in the `manifest.md` row** for the generated image so future audits can reproduce.

### Updated 3-prompt structure (minimum generated set)

**Prompt 1 -- Studio/detail supplement**
- Composition: clean studio, light background, single signature product or product family
- **Reference input:** visible or attached source image of the actual product (mandatory); record the direct CDN URL in the manifest
- Prompt must say: preserve the exact visible product, do not redesign it, do not invent a different tool
- Lighting: soft directional, premium catalog look
- Format: square 1200x1200 primary, landscape 1200x628 crop variant

**Prompt 2 -- Lifestyle / in-space supplement (no interaction -- see the No-interaction rule above)**
- Composition: the product staged in the trade environment the buyer recognizes, sitting in the scene -- NOT being operated or connected to anything. Held-in-hand is the only tolerable interaction.
- **Reference input:** visible or attached source image of the actual product (mandatory); record the direct CDN URL in the manifest
- Prompt must say: preserve the exact visible product, only change environment, lighting, and camera angle; the product is placed in the space, not being used
- Real-world lighting with mood (jobsite floodlight, golden hour, workshop overhead, etc.)
- Format: landscape 1200x628 primary

**Prompt 3 -- Hero product cinematic** (MANDATED for every brand-specific asset group)
- Composition: specific named hero product (identified via Shopify MCP `get-product` or web search), realistic trade environment, dramatic lighting (rim / side / low-key)
- **Reference input:** visible or attached source image of the actual hero product (mandatory); record the direct CDN URL in the manifest
- Prompt must say: this same product is the hero; preserve exact silhouette, proportions, color blocking, and major physical details
- Shallow depth of field, atmosphere
- Format: square or landscape per asset group need

---

## What makes a high-performing PMax image

1. **Relevance to the asset group's products**. The image must visually represent what the asset group serves. Brand color cues, recognizable product silhouettes, environment matching the brand's customer.
2. **Single clear subject**. Don't crowd the frame.
3. **Contrast and color separation**. Reads at thumbnail size. White/light grey for studio. Avoid busy backgrounds.
4. **Real-world environment for lifestyle**. Match the actual trade (electricians on panels, plumbers under sinks). No generic stock.
5. **Dramatic lighting on hero shots**. Side / rim / low-key with shallow depth of field.
6. **No text overlay**. PMax adds headlines. Text in images causes ad strength penalties.
7. **No logos in the image frame**. The brand logo lives at campaign level.
8. **Safe area**. Keep key elements away from edges (Google crops aggressively).

---

## How to maximize relevance to the asset group's products

1. **For brand-specific asset groups**: at least one image must depict a brand-signature product (hero product rule, see Prompt 3).
2. **For category asset groups**: pick the category's center of gravity (e.g. for "Cordless Power Tools", a brushless drill, not a niche accessory).
3. **For trade-focused asset groups**: the lifestyle / contextual image must show the actual trade environment.
4. **Match the brand's existing brand guidelines**: signature colorway (Milwaukee red, DeWalt yellow, Makita teal/black) should land naturally in framing and product selection.

---

## Hero product rule (mandatory)

At least one image per asset group set must be a hero photo of one specific named product that best represents the asset group. Generated from a prompt that:

1. References the actual product by name (e.g. "Southwire MHB4000 Maxis Hydraulic Conduit Bender", not "a Southwire conduit bender").
2. Uses the actual source image as visible or attached reference input, and records a **direct image link** for that product in the manifest. PDP links do not work for audit or reproduction.
3. Specifies dramatic lighting (rim / side / low-key, shallow depth of field).
4. Specifies a realistic background environment relevant to that trade or the tool's typical use (jobsite, fab shop, electrical panel, etc.). Not white seamless.

This image becomes the asset group's anchor. Other images in the mix provide variety around it.

---

## Anti-patterns -- avoid these

- Text overlay inside the image ("Save 20%", "Free Shipping", "Buy Now")
- Multiple disconnected products in a single composition
- Stock photography unrelated to the brand's actual products
- Heavily filtered / oversaturated images
- Logos inside images (logo lives at campaign level)
- 9:16 portrait crops that lose product detail
- Faces dominating the frame and pulling attention from product
- Generic "professional" stock not signaling the actual trade
- **Generation prompts that only include product URLs or text descriptions** -- generic output, brand drift, fantasy products, wasted iterations
- **Generation prompts that do not explicitly command source-product preservation** -- the model may redesign the product even when an image is present
- **Depicting the product physically interacting with other objects** (plugged in, operated, cutting, driving, pumping) -- the rendered contact/connection point is the main defect in generated images. Default to product-in-space; held-in-hand is the only tolerable interaction. See the No-interaction rule.
- **Garbled or invented product logos / lettering** -- even the product's OWN wordmark rendered illegibly (e.g. an on-blade "makita" that comes out "makitn") is an automatic reject. Fine text on blade faces and small spec labels garbles at any quality tier. Mitigate by framing branded faces edge-on or out of frame, leaning on large body logos (which render cleanly), instructing the model to leave a surface plain rather than write distorted text, and using the high tier when a legible logo matters; composite if it persists.

---

## Sources

- [Performance Max Creative Strategy: How to Feed the Algorithm What It Actually Needs (GROAS)](https://www.groas.com/post/performance-max-creative-strategy-how-to-feed-the-algorithm-what-it-actually-needs)
- [Performance Max Creative Specs: Sizes, Formats, and Best Practices 2026 (Hawky)](https://hawky.ai/blog/performance-max-creative-specs-guide)
- [Performance Max Campaigns: The Ultimate Ecommerce Guide 2026 (Store Growers)](https://www.storegrowers.com/performance-max-campaigns/)
- [Google Ads Performance Max 2026 Campaign Guide (Digital Applied)](https://www.digitalapplied.com/blog/google-ads-performance-max-2026-campaign-guide)
- [Testing Product Images vs Lifestyle Shots A/B Tactics (Staphaus)](https://www.staphaus.com/insights/testing-product-images-vs-lifestyle-shots-a-b-tactics-for-furniture-creatives)
- [AI Lifestyle Images vs Studio Photos What Converts Better (Toolient)](https://www.toolient.com/2026/03/ai-lifestyle-images-vs-studio-photos-conversion.html)
- [Optimizing Performance Max for Online Shops 2026 (XICTRON)](https://www.xictron.com/en/blog/google-performance-max-online-shops-2026/)
- [Pmax Best Practices 2026 (Channable)](https://www.channable.com/blog/performance-max-campaigns-best-practices)
