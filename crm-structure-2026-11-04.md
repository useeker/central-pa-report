# Central PA Report — CRM Structure
**Date:** Wednesday, Nov 4, 2026  
**Status:** DRAFT ONLY — structure + templates; nothing sent to leads  
**Location:** `/workspace/central-pa-report/` (alongside social package + directory sponsor pitch)

---

## 1) Lead fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `lead_id` | text | yes | e.g. `CPR-2026-11-04-001` |
| `name` | text | yes | Full name if known; else handle (`@ig_user`, TikTok name) |
| `email` | email | no | Prefer when they reply to REPORT DM / form |
| `phone` | phone | no | Store digits + US format; never post publicly |
| `instagram` / `tiktok` / `facebook` | text | no | Handle or profile URL |
| `source` | enum | yes | `REPORT comment` · `directory inquiry` · `referral` · `website` · `event` · `other` |
| `source_detail` | text | no | Platform + post (e.g. “IG Reel · Mosaic tower · Nov 4”) |
| `interest_type` | enum | yes | `buying` · `selling` · `investing` · `renting` · `business sponsorship` · `partnership` · `newsletter only` · `unknown` |
| `county_of_interest` | enum/multi | no | `Cumberland` · `Dauphin` · `York` · `Lancaster` · `Lebanon` · `multi` · `unknown` |
| `municipality` | text | no | e.g. Harrisburg, East Lampeter Twp. |
| `story_touched` | text | no | Which Central PA Report story sparked contact |
| `story_url` | url | no | Live HubSpot URL sent after REPORT |
| `notes` | long text | no | Freeform; date-stamp updates |
| `status` | enum | yes | `new` · `contacted` · `nurturing` · `active` · `closed` |
| `status_reason` | text | no | e.g. closed-won listing · closed-lost timing · sponsorship signed |
| `next_follow_up` | date | yes if not closed | America/New_York calendar date |
| `assigned_bot` | text | yes | Default: `Central PA Report Daily` (this bot) |
| `assigned_human` | text | yes | `Arpan Tiwari` |
| `created_at` | datetime | yes | When first logged |
| `updated_at` | datetime | yes | Last edit |
| `consent_newsletter` | yes/no | no | Opt-in for weekly newsletter |
| `do_not_contact` | yes/no | yes | Default `no` |

**Interest type guidance**
- Real estate path: buying / selling / investing / renting → Arpan / Real Brokerage nurture  
- Growth media path: business sponsorship / partnership → Best of Central PA directory pitch  
- `newsletter only` → light touch; still log REPORT source  

---

## 2) Status pipeline

| Stage | Definition | Exit criteria |
|-------|------------|---------------|
| **new** | Lead captured; no human/bot outreach yet beyond auto REPORT link if applicable | First personalized reply or call attempt logged → `contacted` |
| **contacted** | At least one outbound touch (DM, email, call, or text) with the lead | They engage (reply, click, book) → `nurturing` or `active`; no reply after cadence → stay contacted until day-7 nurture or close |
| **nurturing** | Warm but not transaction-ready; on weekly value touches (stories, market notes) | Clear buying/selling/sponsor intent + next step booked → `active`; asks to stop → `closed` + `do_not_contact` |
| **active** | Working deal or sponsor conversation (showing, listing consult, directory tier discussion) | Deal/sponsor closed-won or lost → `closed` |
| **closed** | Terminal. Won, lost, or opted out | Reopen only if they re-engage → new lead_id or reset to `nurturing` with note |

**Pipeline diagram (text)**  
`new` → `contacted` → `nurturing` ⇄ `active` → `closed`

---

## 3) Sample lead entry — “REPORT” commenter

```yaml
lead_id: CPR-2026-11-04-001
name: Jordan M. (IG @jordan.m.pa)
email: null
phone: null
instagram: "@jordan.m.pa"
tiktok: null
facebook: null
source: REPORT comment
source_detail: "Instagram Reel · Lancaster County's Tallest Tower Breaks Ground · posted Wed Nov 4, 2026 ~8:45 PM ET"
interest_type: unknown
county_of_interest: Lancaster
municipality: Lancaster city / downtown area (inferred from story)
story_touched: "Lancaster County's Tallest Tower Breaks Ground (Mosaic / Willow Valley)"
story_url: https://www.centralpareport.com/mosaic-tallest-tower-lancaster
notes: |
  2026-11-04 21:02 ET — Commented REPORT on IG Reel. Sent live article link via DM.
  Asked if they want weekly newsletter; awaiting reply.
  Watch for buying/investing signal near downtown Lancaster.
status: contacted
status_reason: null
next_follow_up: 2026-11-11
assigned_bot: Central PA Report Daily
assigned_human: Arpan Tiwari
created_at: 2026-11-04T21:02:00-05:00
updated_at: 2026-11-04T21:05:00-05:00
consent_newsletter: unknown
do_not_contact: no
```

**CSV one-liner (same lead)**  
```csv
lead_id,name,email,phone,instagram,source,source_detail,interest_type,county_of_interest,story_touched,story_url,notes,status,next_follow_up,assigned_bot,assigned_human,created_at,do_not_contact
CPR-2026-11-04-001,"Jordan M. (IG @jordan.m.pa)",,,@jordan.m.pa,REPORT comment,"IG Reel · Mosaic tower · Nov 4",unknown,Lancaster,"Mosaic tallest tower",https://www.centralpareport.com/mosaic-tallest-tower-lancaster,"Sent article link via DM",contacted,2026-11-11,Central PA Report Daily,Arpan Tiwari,2026-11-04T21:02:00-05:00,no
```

---

## 4) Weekly follow-up cadence rule

| Stage / situation | Cadence rule (America/New_York) |
|-------------------|----------------------------------|
| **New lead** | First contact within **24 hours** (goal: same evening if REPORT before 9 PM). Send story link + soft ask (newsletter / how we can help). Set `next_follow_up` = created + 7 days. |
| **Contacted — no reply** | Touch 2 on **day 3** (short bump). Touch 3 on **day 7**. If still silent → move to `nurturing` with monthly story drip OR `closed` if clearly spam/irrelevant. |
| **Nurturing** | Value touch every **7 days** (new Central PA Report story, market note, or directory tip). No hard pitch more than once per 14 days. |
| **Active** | Follow the deal: next step date on calendar; bot reminds Arpan **1 day before** `next_follow_up`. |
| **Business sponsorship** | After directory pitch email: bump on **day 5–7** (use pitch follow-up line). Then every **14 days** max unless they reply. |
| **Closed / do_not_contact** | **No outreach.** Archive. |
| **Weekly review** | Every **Monday 8:00 AM ET** — bot or Arpan scans all leads where `next_follow_up` ≤ today and status ≠ closed. |

**Hard rules**
- Never message a lead marked `do_not_contact`.  
- REPORT replies always include the correct live story URL.  
- Real estate advice stays with Arpan / Real Brokerage compliance.  
- Drafts only until Arpan approves send.

---

## 5) Starter template — first 10 lead rows

Copy into Sheets/HubSpot/CSV. Replace placeholders.

```csv
lead_id,name,email,phone,instagram,tiktok,facebook,source,source_detail,interest_type,county_of_interest,municipality,story_touched,story_url,notes,status,status_reason,next_follow_up,assigned_bot,assigned_human,created_at,updated_at,consent_newsletter,do_not_contact
CPR-2026-11-04-001,[Name],,,,@handle,,,REPORT comment,"[Platform · post title · date]",unknown,Lancaster,,"Mosaic tallest tower",https://www.centralpareport.com/mosaic-tallest-tower-lancaster,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-002,[Name],,,,@handle,,,REPORT comment,"[Platform · HACC tuition · date]",unknown,Dauphin,,"HACC tuition cut",https://www.centralpareport.com/hacc-cuts-tuition-fall-2027,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-003,[Name],,,,@handle,,,REPORT comment,"[Platform · Mill Creek / 7 Brew · date]",unknown,Lancaster,East Lampeter,"Mill Creek Commons 7 Brew",https://www.centralpareport.com/mill-creek-commons-route-30-7-brew-gishs,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-004,[Name],,,,@handle,,,REPORT comment,"[Platform · Biz Love · date]",unknown,Dauphin,Harrisburg,"Harrisburg Biz Love",https://www.centralpareport.com/harrisburg-biz-love-november-small-businesses,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-005,[Business contact],contact@example.com,,,,,directory inquiry,"Best of Central PA pitch · Gish's",business sponsorship,Lancaster,East Lampeter,"Mill Creek Commons",https://www.centralpareport.com/mill-creek-commons-route-30-7-brew-gishs,"Directory sponsor prospect",new,,2026-11-11,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-006,[Business contact],contact@example.com,,,,,directory inquiry,"Best of Central PA pitch · Amma Jo",business sponsorship,Dauphin,Harrisburg,"Biz Love",https://www.centralpareport.com/harrisburg-biz-love-november-small-businesses,"Directory sponsor prospect",new,,2026-11-11,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-007,[Name],email@example.com,,,,,,website,"centralpareport.com contact form",buying,Cumberland,,"",,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-008,[Name],,,,,,referral,"Referred by [Name]",selling,York,,"",,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-009,[Name],,,,,,,event,"[Event name · date]",investing,Lebanon,,"",,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
CPR-2026-11-04-010,[Name],,,,,,,other,"[Detail]",partnership,multi,,"",,"",new,,2026-11-05,Central PA Report Daily,Arpan Tiwari,2026-11-04,,,,no
```

Also saved as standalone CSV for import:

**File:** `crm-leads-template-10.csv` (same folder)

---

## Related project files
- `social-media-package-2026-11-04.md`
- `directory-sponsor-pitch-2026-11-04.md`
- `2026-11-04-ondemand.md` / HubSpot live story URLs

**Next optional step (when Arpan asks):** Load this schema into HubSpot CRM properties or a Google Sheet; wire REPORT comment logging as a routine.
