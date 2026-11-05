# Mosaic Tower — Homeowner Call Script (Free Value Check)
**For:** Arpan Tiwari · Central PA Report · Partnered with Real Brokerage  
**Area:** Homes near Mosaic / Willow Valley Communities · 17 W. Vine St., downtown Lancaster  
**Story:** Lancaster County’s tallest tower breaking ground  
**Live page:** https://www.centralpareport.com/mosaic-tallest-tower-lancaster  
**Date drafted:** Wednesday, Nov 4, 2026  
**Status:** DRAFT ONLY — nothing dialed or sent from this file

**Tone:** Warm, local, informational. Lead with the growth story. Never pushy. If they say no, thank them and end cleanly.

---

## Before you dial
- Know the street / block you’re calling (don’t guess the address out loud unless you’re sure).
- Have the story URL ready to text if they ask.
- Goal of the call: offer a **free value check** — not to list the house on this call.
- Compliance: identify yourself; respect Do Not Call; log every attempt in CRM.

---

## (1) Soft opener (live answer)

Hi [First Name] — this is Arpan Tiwari with Central PA Report. I’m Partnered with Real Brokerage, and I track growth around Lancaster.

I’m not calling with a hard pitch. I’m calling because I’m tracking growth right around Vine Street and Penn Square — and your street sits right in the middle of it.

Quick question: have you heard that Willow Valley Communities just broke ground on Mosaic, the new high-rise downtown?

*[Pause. Let them answer.]*

---

## (2) Value pitch (story facts → nearby homes)

Totally fair either way — here’s the short version.

On Wednesday they broke ground on **Mosaic** at **17 West Vine Street**, between Southern Market and the Lancaster Marriott. It’s set to be **Lancaster County’s tallest building** — **20 stories**, **146 luxury retirement units**, about **$214 million** to build. Roughly **80 of the 146 units are already reserved**, and Willow Valley has said residents are coming from **44 states**. First residents are expected around **2029**.

What that usually means for nearby homeowners isn’t overnight magic — it’s a longer signal: a big bet on downtown, construction activity now, and more full-time residents who eat, shop, and spend in the neighborhood later. Projects like that are one of the things people watch when they ask what homes around Penn Square / Vine Street are worth in this market.

I put a clean breakdown up on Central PA Report if you ever want the details: centralpareport.com — the Mosaic story is live there.

---

## (3) The close (free value check)

The only reason I’m calling is this: if you’d ever like a **free value check** on your home — just a clear, no-obligation look at where you sit in this market with that tower coming online — I’m happy to do that for you.

Would it be useful to know what your home looks like worth in this market, or is now not the right time?

### If YES
Great. I only need your address confirmation and a good email or text number to send a short summary. Prefer a quick 10-minute call later this week, or should I send something written first?

### If MAYBE / SEND INFO
Perfect — I’ll text/email the Mosaic story link and a one-line note on the free value check. No pressure. You can reply when you’re ready.

### If NO
Totally understand. Thanks for your time — and congrats on being in a pocket of Lancaster that’s getting real attention. Have a good [evening/day].

### If “Are you trying to list my house?”
Fair question. Right now I’m offering information and a free value check tied to the Mosaic news. If you ever want to talk selling, that’s your call — not a requirement for the check.

---

## (4) Voicemail version (~25–30 sec)

Hi [First Name], this is Arpan Tiwari with Central PA Report — Partnered with Real Brokerage. I’m tracking growth around downtown Lancaster, and your street is right in the middle of it.

Willow Valley just broke ground on Mosaic on Vine Street — Lancaster County’s tallest building: 20 stories, 146 luxury retirement units, about $214 million, with roughly 80 units already reserved by people from 44 states.

I’m offering nearby homeowners a free, no-obligation value check if you’d like to know what your home looks like worth in this market. No pressure either way. My number is [your callback number]. Again, Arpan Tiwari, Central PA Report. Thanks.

---

## Optional SMS follow-up (after VM or “send info”)

Arpan Tiwari here (Central PA Report / Real Brokerage). Mosaic just broke ground on Vine St. — 20 stories, ~$214M. Free value check if useful: reply YES or call me at [number]. Story: https://www.centralpareport.com/mosaic-tallest-tower-lancaster

---

## (5) CRM logging note format (per call)

Copy into `notes` + update `status` / `next_follow_up` on the lead.

```text
CALL LOG — Mosaic homeowner outreach
Date/time (ET): YYYY-MM-DD HH:MM
Lead ID: CPR-…
Address / street: 
Outcome: answered | voicemail | no answer | wrong number | DNC requested
Duration: 
Opener delivered: yes/no
Story facts shared: yes/partial/no
Value check offered: yes/no
Their response: interested | send info | not now | no | hostile | question (note)
What they said (quote/paraphrase): 
Objections: 
Info promised: story link / value check writeup / callback
Next follow-up date: YYYY-MM-DD
Next action: 
Assigned: Arpan Tiwari | Central PA Report Daily
```

### Quick status mapping
| Outcome | Status | Next follow-up |
|---------|--------|----------------|
| Interested in value check | `active` | Within 2 days (send or complete check) |
| Send info / maybe | `nurturing` | +7 days |
| Voicemail left | `contacted` | +3 days (one bump), then +7 |
| No answer (no VM) | `contacted` | +1 day retry, max 3 attempts / 7 days |
| Not now / no | `nurturing` or `closed` | +30 days soft, or close if firm no |
| DNC | `closed` + `do_not_contact: yes` | none |

### One-line CRM example
`2026-11-05 10:14 ET — Answered. Soft opener + Mosaic facts. Interested in free value check; preferred email summary. Sent story URL. next_follow_up=2026-11-07. status=active.`

---

## Do / Don’t
**Do:** Lead with Lancaster growth · use exact verified facts · offer free value check · log every call  
**Don’t:** Scare about “selling before it’s too late” · invent comps on the phone · pressure for a listing appointment · call past agreed quiet hours  

**Related files:** `crm-structure-2026-11-04.md` · `social-media-package-2026-11-04.md` · Mosaic live URL above
