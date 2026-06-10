# Campaign Assets (Local Working Storage)

Per-campaign working files used during campaign creation skills. Local-only; this folder is gitignored except this README.

## Structure

```
campaign_assets/
└── <campaign_slug>/                     e.g. qt-pmax-brand-batch-2
    ├── PROPOSAL.md                      <- human-readable working proposal (REQUIRED)
    └── <brand_or_asset_group_slug>/     e.g. southwire
        ├── sourced/                     Claude pulls from Shopify, manufacturer, sellers, web
        │   └── rejected/                Sourced candidates rejected during QA
        ├── generated/                   Adam adds ChatGPT-generated images here
        │   └── rejected/                Generated candidates rejected during QA
        └── manifest.md                  Tracks every image's source, type, status, upload result
```

## `PROPOSAL.md` -- the working artifact

Required for every campaign creation task per `CAMPAIGN_CREATION_BEST_PRACTICES.md` § Required: PROPOSAL.md. It captures:

- Status, customer ID, skill, dates, and (after commit) `proposal_id` + `campaign_resource_name`
- One section per workflow step
- Inline `🛑 Checkpoint N` markers showing approval state
- Outstanding items / blockers
- Revision log

Adam reads PROPOSAL.md at every pause checkpoint. It is the single document that captures the entire task end-to-end.

## Lifecycle

1. Skill creates `<campaign_slug>/` and writes `PROPOSAL.md` early (after the initial data pull).
2. Skill creates per-brand (or per-asset-group) subfolders during Step 6 (image preparation).
3. Claude sources existing images into `sourced/`, populating each `manifest.md`.
4. Claude reviews candidates and moves parts, accessories, weak generated outputs, or off-brand images into the relevant `rejected/` folder, preserving manifest rows with rejection reasons.
5. Adam adds ChatGPT-generated supplement images into `generated/`.
6. Skill calls `upload_google_ads_image_asset` for approved images and records `resource_name` in the manifest.
7. PROPOSAL.md updates through each revision and after each checkpoint confirmation.
8. At commit, the returned `proposal_id` and resource names are appended to PROPOSAL.md; status flips to `committed`.
9. Folder stays as the local audit narrative paired with the `audit.db` row.

## Gitignore behavior

- The folder itself is committed (this README only).
- Per-campaign subfolders are gitignored (binary images, working notes).
- `PROPOSAL.md` files inside campaign folders are also gitignored by default. If a specific proposal should be tracked, copy it out explicitly or adjust `.gitignore` for that file.

See `PMAX_IMAGE_BEST_PRACTICES.md` for the image manifest schema and the direct-image-link rule for any generation prompt.
