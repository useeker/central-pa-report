# Central PA Report — Automation Bot Setup Guide
**For:** Arpan Tiwari · Central PA Report · Partnered with Real Brokerage  
**Date drafted:** Wednesday, Nov 4, 2026  
**Status:** DRAFT ONLY — nothing configured, connected, or sent from this guide  
**Companion files:** social-media-package · directory-sponsor-pitch · crm-structure · mosaic call script · mosaic flyer

**Default story link for tonight’s Mosaic campaign**  
https://www.centralpareport.com/mosaic-tallest-tower-lancaster  

*Later: swap the URL per post (HACC, Mill Creek, Biz Love) or use a router link that maps keyword + post ID → correct story.*

---

## Exact auto-reply message (use everywhere)

```
Thanks for commenting REPORT — here’s the full Central PA Report breakdown:

https://www.centralpareport.com/mosaic-tallest-tower-lancaster

If you live nearby and want a free, no-obligation home value check as Mosaic gets underway, reply VALUE and I’ll have Arpan follow up.

— Arpan Tiwari
Central PA Report | Partnered with Real Brokerage
```

**SMS / character-conscious variant (≤320 chars target):**
```
Central PA Report — Mosaic tower story: https://www.centralpareport.com/mosaic-tallest-tower-lancaster
Free no-obligation value check? Reply VALUE. Reply STOP to opt out.
— Arpan Tiwari | Partnered with Real Brokerage
```

---

## (1) ManyChat setup — Instagram + Facebook “REPORT”

### What you need
- Facebook Page for Central PA Report (or Arpan’s business Page linked to IG)
- Instagram Professional account linked to that Page
- ManyChat account (Pro plan usually required for comment growth tools / IG)

### Connect accounts
1. Go to [manychat.com](https://manychat.com) → Sign up / Log in.  
2. **Settings → Channels** (or onboarding wizard).  
3. Connect **Facebook Page** → approve Meta permissions (messages, comments as allowed).  
4. Connect **Instagram** → select the Professional IG linked to that Page.  
5. Confirm both show **Connected** (green).

### Auto-reply on keyword REPORT (DMs)
1. ManyChat → **Automation** → **New automation** (or **Flow**).  
2. Trigger: **Instagram** / **Facebook** → **User sends a message** → condition **contains** → `REPORT` (case-insensitive if available).  
3. Also add trigger variants: `Report`, `report` if the tool is case-sensitive.  
4. Action: **Send message** → paste the **Exact auto-reply message** above.  
5. Optional next step: **Wait for reply** → if user sends `VALUE`, tag `value_check_interest` and notify Arpan (email/Slack).  
6. **Publish** / set Live.

### Auto-reply when someone comments REPORT
1. ManyChat → **Instagram** → **Comment growth tools** / **Automation** → trigger **New comment on post/reel** (or “any media”).  
2. Condition: comment text **contains** `REPORT`.  
3. Action A: **Reply to comment** (public) — short: `Sent you the link — check your DMs` (optional; keep light).  
4. Action B: **Send Instagram DM** — paste the full auto-reply with Mosaic URL.  
5. Scope: start with **Specific posts** (tonight’s Mosaic reel) to avoid wrong links; later use per-post flows.  
6. Repeat equivalent for **Facebook** comments if ManyChat shows FB comment triggers for your plan.  
7. **Publish**.

### Test
- From a friend account: comment `REPORT` on the Mosaic reel → confirm DM received.  
- DM `REPORT` to the IG profile → confirm same reply.  
- Do **not** test on strangers until opt-in/compliance notes below are followed.

---

## (2) Zapier setup — text-in “REPORT” (Twilio or similar)

### What you need
- Zapier account  
- SMS provider with a number: **Twilio** is the common path (or Bandwidth / MessageBird if you already use one)  
- AUS / 10DLC registration if sending SMS in the US (Twilio will prompt — required for reliable delivery)

### High-level Zap
**Trigger:** New SMS received (Twilio) where Body contains `REPORT`  
**Actions:** (1) Send SMS reply with story + VALUE offer + STOP language → (2) Create/update CRM lead

### Step-by-step (Twilio + Zapier)
1. Create/log in to [Twilio](https://www.twilio.com) → buy a local PA or toll-free number.  
2. Complete **US A2P 10DLC** brand + campaign registration (marketing/customer care as appropriate).  
3. Zapier → **Create Zap**.  
4. **Trigger:** Twilio → **New SMS** → connect Twilio Account SID + Auth Token → choose the number.  
5. **Filter** (Zapier Filter): Body (Text) **(Text) Contains** `REPORT` (case-insensitive filter if available).  
6. **Action:** Twilio → **Send SMS**  
   - To: trigger From number  
   - Body: **SMS variant** above (include `Reply STOP to opt out`)  
7. **Action:** CRM create lead (see section 3).  
8. **Optional:** If Body contains `VALUE` (separate Zap or Paths): notify Arpan by email/SMS; set interest_type = buying/unknown + tag value check.  
9. Turn Zap **On**. Test with your phone only first.

### If not using Twilio
Use any Zapier-supported SMS app with inbound webhooks the same way: inbound message containing REPORT → outbound reply → CRM row.

---

## (3) CRM integration — every REPORT → new lead

Match fields from `crm-structure-2026-11-04.md`.

| CRM field | Value on REPORT capture |
|-----------|-------------------------|
| `name` | Platform display name / “SMS +1…” if unknown |
| `source` | `REPORT comment` or `REPORT DM` or `REPORT text` |
| `source_detail` | Platform + post ID/URL + timestamp |
| `story_url` | https://www.centralpareport.com/mosaic-tallest-tower-lancaster *(or active story)* |
| `status` | **`new`** |
| `interest_type` | `unknown` (upgrade to buying when they reply VALUE) |
| `county_of_interest` | Lancaster (default for Mosaic); else unknown |
| `next_follow_up` | Created date + 1 day (24-hour first-touch rule) |
| `assigned_bot` | Central PA Report Daily |
| `assigned_human` | Arpan Tiwari |
| `do_not_contact` | `no` (set `yes` if STOP / unsubscribe) |

### Wire options (pick one)
**A. Google Sheet (fastest start)**  
- Zapier action: Google Sheets → Create Spreadsheet Row → map columns from `crm-leads-template-10.csv`.  
- ManyChat: native Google Sheets / Zapier step on same flows.

**B. HubSpot**  
- Zapier or ManyChat HubSpot action → Create Contact + deal/lead note.  
- Property `lead_source` = REPORT comment/DM/text; `hs_lead_status` ≈ NEW.

**C. ManyChat Custom Fields + tag `report_lead`**  
- Nightly export or Zapier “New tagged user” → Sheet/HubSpot.

### Paths to log
| Channel | When to create lead |
|---------|---------------------|
| IG/FB comment REPORT | When keyword automation fires (even if DM fails, log attempt) |
| IG/FB DM REPORT | On inbound keyword |
| SMS REPORT | On Twilio inbound after filter |

Always store: **source, date/time (ET), status = new**.

---

## (4) Order of operations for Arpan (click path)

Do this in order — don’t buy SMS traffic before Meta channels work.

1. **Confirm Meta assets**  
   - IG Professional + Facebook Page linked  
   - Logins: Facebook password, IG password, business.facebook.com access  

2. **Create ManyChat**  
   - Sign up → connect FB Page → connect IG → verify Live  

3. **Build REPORT DM flow**  
   - Trigger contains REPORT → send exact auto-reply → Publish → test with friend account  

4. **Build REPORT comment → DM flow**  
   - Attach to Mosaic reel first → test comment → confirm DM + optional public reply  

5. **Stand up CRM sink**  
   - Copy `crm-leads-template-10.csv` to Google Sheets **or** confirm HubSpot properties  
   - Connect Zapier/ManyChat → create row/contact with status `new`  

6. **Attach CRM action to ManyChat flows**  
   - Every REPORT success path creates a lead  

7. **SMS (optional week 2)**  
   - Twilio number + 10DLC → Zapier inbound REPORT → SMS reply → same CRM sheet/HubSpot  
   - Print number on flyer / bio only after opt-in language is ready  

8. **Go live checklist**  
   - [ ] Friend test IG comment  
   - [ ] Friend test IG DM  
   - [ ] Friend test SMS (if live)  
   - [ ] New row appears in CRM with status `new`  
   - [ ] STOP / unsubscribe path works for SMS  
   - [ ] Mosaic URL correct in reply  

9. **Hand off to routine**  
   - Central PA Report Daily weekday run stays content; ManyChat/Zapier own the REPORT inbox  
   - Arpan reviews `new` leads within 24 hours per CRM cadence  

---

## (5) Compliance note — opt-in only, no unsolicited texts

- **REPORT is the opt-in.** Only auto-reply to people who commented, DMed, or texted REPORT (or joined an explicit signup).  
- **Do not** blast SMS/IG DMs to purchased lists, scraped numbers, or “everyone near Vine Street.”  
- **SMS:** Include identification + **Reply STOP to opt out** on outbound texts; honor STOP immediately (`do_not_contact = yes`).  
- **Meta:** Follow Instagram/Facebook messaging policies; don’t spam replies on unrelated posts.  
- **Real estate:** Free value check is an offer of information — not a guarantee of value; no pressure language in automations.  
- **TCPA / state rules:** When in doubt, get counsel before advertising a text-in number widely.  
- This guide configures tools **when Arpan clicks through** — Grok Bot has not connected ManyChat, Zapier, or Twilio from this draft.

---

## Quick reference — credentials you’ll log into
| Service | Purpose |
|---------|---------|
| Facebook / Meta Business | Page + IG permissions |
| Instagram | Professional account |
| ManyChat | REPORT comment/DM bots |
| Zapier | SMS + CRM glue |
| Twilio (or SMS vendor) | Text-in number |
| Google Sheets or HubSpot | Lead log |

---

## Related project files
- `social-media-package-2026-11-04.md`  
- `directory-sponsor-pitch-2026-11-04.md`  
- `crm-structure-2026-11-04.md` / `crm-leads-template-10.csv`  
- `mosaic-homeowner-call-script-2026-11-04.md`  
- `mosaic-homeowner-flyer-2026-11-04.md`  
- Live Mosaic URL: https://www.centralpareport.com/mosaic-tallest-tower-lancaster
