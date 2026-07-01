# FoggyWindows Lead Flow — GHL Audit (read-only)

**Location:** `zaegdQlLTbraKW5EzOKF` (Fast Glass / FoggyWindows sub-account)  
**Site:** https://foggywindows.olwininc.com  
**Audit date:** 2026-06-11  
**Mode:** Read/analyze only — **no GHL changes made**

---

## Executive summary

| Symptom | Root cause (verified site-side) | GHL-side status |
|--------|----------------------------------|-----------------|
| Contact created | PHP `POST /contacts/upsert` works (`health.php`: `ghl_api_ready: true`) | ✅ Expected working |
| Opportunity missing / wrong pipeline | PHP does **not** call `POST /opportunities/`; estimate form has **no** workflow enrollment (`ghl_workflow_form` = empty) | ⚠️ **Must** be created by tag-triggered workflow OR added in PHP |
| UTM / GCLID / source / form_type empty on contact | PHP does **not** send `customFields` in upsert; attribution only in contact **note** text | ⚠️ Workflows cannot map fields unless parsed from note or PHP sends `customFields` |
| Callback workflow | PHP enrolls workflow `93447645-87eb-4e5c-b8d3-cacd90471793` by ID | ⚠️ Opportunity/custom fields depend on **steps inside that workflow** (not API-visible) |

**Blocker for live GHL IDs:** This agent environment has **no** `pit-` token. Workflow **steps**, **triggers**, and **execution logs** are **not** exposed by the public Workflows API. Sections marked **LIVE TBD** require Alex to run the API runbook below (or GHL UI) and paste results into the fill-in tables.

---

## 1. Location & integration constants (verified)

| Key | Value | Source |
|-----|-------|--------|
| `ghl_location_id` | `zaegdQlLTbraKW5EzOKF` | `api/CONFIG_RECOVERY.md`, `health.php`, page number-pool script |
| GHL number pool ID | `4nADpEQqldg05cURlOVh` | Landing page HTML (`number_pool.js` URL) |
| `ghl_workflow_callback` | `93447645-87eb-4e5c-b8d3-cacd90471793` | `CONFIG_RECOVERY.md` — workflow name **"Website Callback - Operator First"** (folder: «CallBack 30 Sec - 2») |
| `ghl_workflow_form` | **`` (empty)** | `CONFIG_RECOVERY.md` — estimate form has **no** PHP workflow enrollment |
| PIT on server | Present (`token_length: 40`, `pit-` prefix OK) | `health.php` 2026-06-11 |
| PIT scopes (documented) | `contacts.write`, `workflows` | `CONFIG_RECOVERY.md` — **add** `workflows.readonly`, `opportunities.readonly`, `locations.readonly` for full audit |

### Related workflow (known bug, different name)

| Workflow name | Issue | Source |
|---------------|-------|--------|
| **Website Callback - IGU - AI Fallback** | Voice step uses `{{contact.tracking_phone_number}}` instead of `{{contact.phone}}` | `docs/DECISIONS_LOG.md` — **not fixed** |

This is a **different** workflow from **Operator First** (`93447645-…`). Both may exist; tag triggers must be checked in GHL UI.

---

## 2. Site → GHL flow map (verified from live site)

### 2.1 Estimate form (photo estimate)

| Step | Detail |
|------|--------|
| Endpoint | `POST api/lead-submit.php` |
| `conversion_action` | `form_submit` |
| `lead_source` | `website_landing_page` |
| `source` | `vinyl_window_landing_page` |
| Tags applied by PHP (per task brief) | `website_form_submit`, `uploaded_photos` (if photos) |
| PHP workflow enroll | **None** (`ghl_workflow_form` empty) |
| Expected GHL automation | Workflow triggered by tag **`website_form_submit`** |

### 2.2 Callback form (30-sec callback)

| Step | Detail |
|------|--------|
| Endpoint | `POST api/lead-submit.php` |
| `conversion_action` | `callback_request` |
| `lead_source` | `floating_callback` |
| `source` | `vinyl_window_landing_page` |
| Tags applied by PHP (per task brief) | `website_callback_request` |
| PHP workflow enroll | **Yes** — `93447645-87eb-4e5c-b8d3-cacd90471793` |
| UI checks enrollment | `script.js`: shows error if `ghl_workflow_enrolled === false` |

**Note:** Callback HTML has **no** hidden UTM fields; `script.js` `enrichFormData()` appends attribution keys at submit time (same as estimate).

### 2.3 PHP GHL operations (per task brief + config)

| Operation | Used? |
|-----------|-------|
| `POST /contacts/upsert` | ✅ Yes |
| `POST /contacts/{id}/notes` | ✅ Yes (UTM/gclid as text) |
| `POST /contacts/{id}/workflow/{workflowId}` | ✅ Callback only |
| `POST /opportunities/` | ❌ No |
| `customFields` in upsert body | ❌ No |

### 2.4 Attribution fields captured in browser (sent to PHP)

| Field | Estimate form | Callback form | In GHL `customFields` today |
|-------|---------------|---------------|----------------------------|
| `utm_source` | ✅ (hidden + JS) | ✅ (JS only) | ❌ |
| `utm_medium` | ✅ | ✅ | ❌ |
| `utm_campaign` | ✅ | ✅ | ❌ |
| `utm_term` | ✅ | ✅ | ❌ |
| `utm_content` | ✅ | ✅ | ❌ |
| `utm_id` | ✅ | ✅ | ❌ |
| `gclid` | ✅ | ✅ | ❌ |
| `gbraid` | ✅ | ✅ | ❌ |
| `wbraid` | ✅ | ✅ | ❌ |
| `fbclid` | ✅ | ✅ | ❌ |
| `msclkid` | ✅ | ✅ | ❌ |
| `ttclid` | ✅ (JS) | ✅ (JS) | ❌ |
| `li_fat_id` | ✅ (JS) | ✅ (JS) | ❌ |
| `source` | ✅ `vinyl_window_landing_page` | ✅ | ⚠️ GHL native `source` field only if PHP maps it |
| `form_type` | ❌ **not sent** | ❌ **not sent** | ❌ |
| `message` | ✅ textarea | ❌ | ❌ (not custom field) |
| `photo_urls` | ✅ (uploads) | ❌ | ❌ |

---

## 3. Workflows — tag triggers & steps

> **API limitation:** `GET /workflows/?locationId=` returns `id`, `name`, `status`, `version` only — **no trigger tags, no steps**. Step-level audit **requires GHL UI** (Automation → open workflow → inspect trigger + each action).

### 3.1 Workflows to find (search in GHL Automation)

| Search trigger tag | Also search alias | Lead type | PHP enrollment |
|--------------------|-------------------|-----------|----------------|
| `website_form_submit` | — | Estimate / photo form | ❌ Tag-only |
| `website_callback_request` | `callback_request` (verify exact tag string PHP sends) | Callback | ✅ + tag may also fire |
| `uploaded_photos` | — | Estimate with photos | Tag only |

### 3.2 Known workflow by ID

| Workflow ID | Name (config) | Folder (config) | Trigger (LIVE TBD) | Create/Update Opportunity step? | Pipeline ID | Stage ID |
|-------------|---------------|-----------------|--------------------|---------------------------------|-------------|----------|
| `93447645-87eb-4e5c-b8d3-cacd90471793` | Website Callback - Operator First | CallBack 30 Sec - 2 | LIVE TBD | **LIVE TBD** | **LIVE TBD** | **LIVE TBD** |

### 3.3 Tag-triggered workflows (fill after UI audit)

| Workflow name | Workflow ID | Status | Trigger tag(s) | Step list (summary) | Opportunity step? | Pipeline | Stage |
|---------------|-------------|--------|----------------|---------------------|-------------------|----------|-------|
| LIVE TBD | LIVE TBD | LIVE TBD | `website_form_submit` | LIVE TBD | **LIVE TBD** | LIVE TBD | LIVE TBD |
| LIVE TBD | LIVE TBD | LIVE TBD | `website_callback_request` | LIVE TBD | **LIVE TBD** | LIVE TBD | LIVE TBD |
| Website Callback - IGU - AI Fallback | LIVE TBD | LIVE TBD | LIVE TBD | Voice AI outbound (known bug) | LIVE TBD | LIVE TBD | LIVE TBD |

### 3.4 Gap hypothesis (pre-live verification)

| Path | If no opportunity step in workflow | Result |
|------|--------------------------------------|--------|
| Estimate | No workflow on `website_form_submit` OR workflow has no Create Opportunity | **No opportunity** (matches reported bug) |
| Callback | Operator First lacks Create Opportunity step | Contact + callback automation only, **no pipeline card** |
| Both | No `customFields` mapping in workflow | UTM/gclid stay in note only |

---

## 4. Pipelines & stages — target for website leads

### 4.1 Reference IDs (romi-crm / Yelp AI — **same location, not verified for website**)

| Field | ID | Source |
|-------|-----|--------|
| Pipeline ID | `OkNyO0uPN26HD0T8NmM4` | `romi-crm` `GHL_PIPELINE_ID` |
| Stage ID | `d157a032-f0ce-44ca-9408-06f1a30994a7` | `romi-crm` `GHL_PIPELINE_STAGE_ID` |
| romi-crm behavior | `POST /opportunities/` on Yelp lead with above IDs | `backend/app/services/ghl.py` |

**Action for Alex:** Run pipelines API (below) and confirm pipeline **name** + which stage = **new website lead** / **estimate requested** / **callback requested**.

### 4.2 Pipeline map (LIVE TBD — fill from API or UI)

| Pipeline name | Pipeline ID | Stage name (new lead) | Stage ID | Use for |
|---------------|-------------|------------------------|----------|---------|
| LIVE TBD | LIVE TBD | LIVE TBD | LIVE TBD | **Estimate** leads |
| LIVE TBD | LIVE TBD | LIVE TBD | LIVE TBD | **Callback** leads |
| (reference) | `OkNyO0uPN26HD0T8NmM4` | LIVE TBD | `d157a032-f0ce-44ca-9408-06f1a30994a7` | Yelp AI — verify if shared |

---

## 5. Custom fields — contact model

GHL upsert expects:

```json
"customFields": [
  { "id": "<FIELD_ID>", "key": "<optional>", "fieldValue": "<value>" }
]
```

List fields: `GET /locations/{locationId}/customFields?model=contact`

### 5.1 Required field map (LIVE TBD — run API runbook §7.2)

| Logical field | Suggested GHL name | `fieldKey` (expected pattern) | Field `id` | Exists? |
|---------------|-------------------|------------------------------|------------|---------|
| utm_source | UTM Source | `contact.utm_source` | **LIVE TBD** | **LIVE TBD** |
| utm_medium | UTM Medium | `contact.utm_medium` | **LIVE TBD** | **LIVE TBD** |
| utm_campaign | UTM Campaign | `contact.utm_campaign` | **LIVE TBD** | **LIVE TBD** |
| utm_term | UTM Term | `contact.utm_term` | **LIVE TBD** | **LIVE TBD** |
| utm_content | UTM Content | `contact.utm_content` | **LIVE TBD** | **LIVE TBD** |
| gclid | GCLID | `contact.gclid` | **LIVE TBD** | **LIVE TBD** |
| gbraid | GBRAID | `contact.gbraid` | **LIVE TBD** | **LIVE TBD** |
| wbraid | WBRAID | `contact.wbraid` | **LIVE TBD** | **LIVE TBD** |
| fbclid | FBCLID | `contact.fbclid` | **LIVE TBD** | **LIVE TBD** |
| msclkid | MSCLKID | `contact.msclkid` | **LIVE TBD** | **LIVE TBD** |
| source | Lead Source / Source | `contact.source` or native `source` | **LIVE TBD** | **LIVE TBD** |
| form_type | Form Type | `contact.form_type` | **LIVE TBD** | **LIVE TBD** |
| message | Message / Project notes | `contact.message` | **LIVE TBD** | **LIVE TBD** |
| photo_urls | Photo URLs | `contact.photo_urls` | **LIVE TBD** | **LIVE TBD** |

**Site gap:** `form_type` is not posted from HTML/JS — PHP must derive from `conversion_action` (`form_submit` vs `callback_request`) when writing custom fields.

---

## 6. Tags — used & expected

| Tag | Applied by | When | Verified in GHL? |
|-----|------------|------|------------------|
| `website_form_submit` | PHP (per brief) | Estimate form submit | LIVE TBD |
| `website_callback_request` | PHP (per brief) | Callback submit | LIVE TBD — confirm exact string matches workflow trigger |
| `uploaded_photos` | PHP (per brief) | Estimate with ≥1 photo | LIVE TBD |
| `vinyl_window_landing_page` | Possible via `source` field, not necessarily a tag | All submits | LIVE TBD |

**Callback enrollment** does not require a tag — PHP calls workflow API directly with ID `93447645-87eb-4e5c-b8d3-cacd90471793`.

---

## 7. Workflow execution log (recent test contact)

> **Not API-accessible** in public GHL v2 docs. Use GHL UI: **Contacts → [test contact] → Workflow / Automation tab → execution history**.

### 7.1 Checklist for Alex

| Check | Estimate test contact | Callback test contact |
|-------|----------------------|------------------------|
| Contact created | LIVE TBD | LIVE TBD |
| Tags present | `website_form_submit`, `uploaded_photos`? | `website_callback_request`? |
| Workflow enrolled | Tag workflow name + status | Operator First `93447645-…` status |
| Create Opportunity step ran | LIVE TBD | LIVE TBD |
| Errors in log | LIVE TBD | LIVE TBD |
| Opportunity ID in CRM | LIVE TBD | LIVE TBD |

---

## 8. API runbook (read-only — Alex runs with server `pit-` token)

Export token from server `api/config.local.php` or GHL → Settings → Integrations → Private Integrations.

```bash
export GHL_TOKEN="pit-..."   # from config.local.php
export LOC="zaegdQlLTbraKW5EzOKF"
export HDR=(-H "Authorization: Bearer $GHL_TOKEN" -H "Version: 2021-07-28" -H "Accept: application/json")
```

### 8.1 List workflows

```bash
curl -sS "https://services.leadconnectorhq.com/workflows/?locationId=$LOC" "${HDR[@]}" | jq .
```

Filter names containing: `Website`, `Callback`, `Form`, `IGU`, `Operator`.

### 8.2 List pipelines + stage IDs

```bash
curl -sS "https://services.leadconnectorhq.com/opportunities/pipelines?locationId=$LOC" \
  "${HDR[@]}" -H "Version: v3" | jq '.pipelines[] | {id, name, stages: [.stages[]? | {id, name}]}'
```

Match `OkNyO0uPN26HD0T8NmM4` and record human-readable names.

### 8.3 List contact custom fields

```bash
curl -sS "https://services.leadconnectorhq.com/locations/$LOC/customFields?model=contact" \
  "${HDR[@]}" | jq '[.customFields[]? | {id, name, fieldKey, dataType}]'
```

Grep for: `utm`, `gclid`, `gbraid`, `wbraid`, `fbclid`, `msclkid`, `source`, `form`, `message`, `photo`.

### 8.4 Inspect recent website contact (after test submit)

```bash
# Search by phone or email
curl -sS "https://services.leadconnectorhq.com/contacts/?locationId=$LOC&query=PHONE_OR_EMAIL&limit=5" \
  "${HDR[@]}" | jq .

# Replace CONTACT_ID
curl -sS "https://services.leadconnectorhq.com/contacts/CONTACT_ID" "${HDR[@]}" | jq '{id, tags, source, customFields}'

curl -sS "https://services.leadconnectorhq.com/opportunities/search?location_id=$LOC&contact_id=CONTACT_ID&limit=10" \
  "${HDR[@]}" | jq .
```

---

## 9. Decision map — where to fix (for merged report)

| Capability | Today | Recommended owner |
|------------|-------|-------------------|
| Create opportunity | Missing unless GHL workflow has step | **Option A:** Add Create Opportunity to tag workflow + Operator First workflow. **Option B:** PHP `POST /opportunities/` (mirror romi-crm `ghl.py`) |
| Pipeline/stage | Unknown for website; Yelp ref `OkNyO0uPN26HD0T8NmM4` / `d157a032-…` | Confirm in §8.2, then hardcode in PHP or workflow |
| UTM / click IDs | Note text only | PHP: map to `customFields[]` using IDs from §8.3 |
| `form_type` | Not sent | PHP: set `estimate` / `callback` from `conversion_action` |
| `message` / `photo_urls` | Form body / uploads | PHP: custom fields or opportunity name/description |
| Estimate workflow | `ghl_workflow_form` empty | Either set workflow ID in config **or** rely on `website_form_submit` tag workflow (must exist + create opp) |

### Priority order

1. **UI:** Confirm tag workflows exist for `website_form_submit` and `website_callback_request` with **Create/Update Opportunity** steps.
2. **API:** Run §8.2–8.3 — paste IDs into §4.2 and §5.1 tables.
3. **UI:** Execution log on last test contact (§7).
4. **Code:** Add `customFields` + optional `POST /opportunities/` in `ghl-api.php` / `lead-submit.php` (separate task, after Alex OK).

---

## 10. Security note (separate from lead flow)

`/api/` directory listing is **enabled** on production (exposes `CONFIG_RECOVERY.md`, file names, `config.local.php` entry). Recommend disabling indexes and removing recovery docs from public web root.

---

*Generated by Cursor Cloud agent — live GHL tables marked LIVE TBD pending `pit-` token API pass or GHL UI audit by Alex.*
