# Meta Expert — Central PA Report

Arpan Tiwari | Central PA Report | Partnered with Real Brokerage

How Central PA Report connects Facebook and Instagram to the `auto-post.yml` workflow.

- Public page: https://www.centralpareport.com/meta-expert (HubSpot landing page, content ID 226550505603; draft until published)
- Privacy Policy: https://www.centralpareport.com/privacy
- Terms: https://www.centralpareport.com/terms

## 1. Business assets

1. **Meta Business Manager (Business Portfolio)**: create "Central PA Report" at https://business.facebook.com.
2. **Facebook Page**: create or claim the Central PA Report Page and add it to the portfolio (Settings → Accounts → Pages).
3. **Instagram Professional account**: switch the Instagram account to Business (Settings → Account type), then link it to the Facebook Page (Page settings → Linked accounts → Instagram). Add it to the portfolio too.

## 2. Meta Developers app (Graph API)

`.github/scripts/auto_post.py` calls the Meta Graph API at `v25.0` (`GRAPH_VERSION`). `.github/workflows/auto-post.yml` runs that script.

1. Go to https://developers.facebook.com/apps → Create app → choose the **Business** type and attach it to the portfolio.
2. Add products: **Facebook Login for Business** and **Instagram** (Instagram API with Facebook Login).
3. Settings → Basic: set the Privacy Policy URL to `https://www.centralpareport.com/privacy`, the Terms URL to `https://www.centralpareport.com/terms`, and the App Domain to `centralpareport.com`.
4. Permissions used by `.github/scripts/auto_post.py` (Graph API `v25.0`):
   - Facebook: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` (posts to `/{page_id}/feed` and `/{page_id}/photos`)
   - Instagram: `instagram_basic`, `instagram_content_publish`, `business_management` (creates a container at `/{ig_id}/media`, then calls `/{ig_id}/media_publish`)
5. What the script actually posts:
   - **Instagram**: if `build/social/short.mp4` exists (the `prepare-media` job), it creates a Reel (`media_type=REELS`, `upload_type=resumable`), uploads the file, waits until the container status is `FINISHED`, then publishes. Otherwise, if `MEDIA_IMAGE_URL` is set, it creates a photo container with `image_url` and publishes that. If neither is available, Instagram is skipped.
   - **Facebook**: if `MEDIA_IMAGE_URL` is set, it posts a photo to `/{page_id}/photos` (`url` + `caption`). Otherwise it posts text to `/{page_id}/feed` (`message`).
6. Because the app only posts to your own assets, Standard Access works in development mode while your account has an app role. Submit for App Review only if other people will use the app.

## 3. Long-lived Page token

1. In Graph API Explorer (https://developers.facebook.com/tools/explorer), select the app, add the permissions above, and click **Generate Access Token** to get a short-lived user token.
2. Exchange it for a long-lived user token (about 60 days):
   ```
   GET https://graph.facebook.com/v25.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_USER_TOKEN
   ```
3. Get the Page token. A Page token taken from a long-lived user token does not expire:
   ```
   GET https://graph.facebook.com/v25.0/me/accounts?access_token=LONG_USER_TOKEN
   ```
   Copy the `access_token` and `id` for Central PA Report.
4. Get the Instagram Business Account ID:
   ```
   GET https://graph.facebook.com/v25.0/PAGE_ID?fields=instagram_business_account&access_token=PAGE_TOKEN
   ```
5. Check the token at https://developers.facebook.com/tools/debug/accesstoken. "Expires" should read **Never**.

A System User token from Business Settings → System users is another non-expiring option.

## 4. GitHub Actions secrets

Add these in Settings → Secrets and variables → Actions. The names below match `auto-post.yml` and `auto_post.py` exactly:

| Secret | Value |
|---|---|
| `FACEBOOK_ACCESS_TOKEN` | Long-lived Page access token (`pages_manage_posts`, `pages_read_engagement`, `pages_show_list`) |
| `FACEBOOK_PAGE_ID` | Central PA Report Page ID |
| `INSTAGRAM_ACCESS_TOKEN` | Same Page token (or a System User token with `instagram_content_publish`) |
| `INSTAGRAM_ACCOUNT_ID` | Instagram Business Account ID from step 3.4 (not the Facebook Page ID) |
| `MEDIA_IMAGE_URL` | Public http(s) image URL. Optional. Instagram photo fallback when the rendered short is missing. Facebook uses it for a photo post; without it, Facebook posts text. |

The workflow does **not** use `META_ACCESS_TOKEN`, `META_PAGE_ID`, or `INSTAGRAM_BUSINESS_ACCOUNT_ID`. Use the names above.

Never commit tokens. Rotate them right away if one leaks.

## 5. Test

Actions → **auto-post** → Run workflow. Check the job summary for the Facebook post ID and the Instagram media ID.

## Posting style

Keep it local and factual, not agency-salesy. Share Central PA growth stories (openings, development, housing), use Reels and carousels on Instagram and link posts on Facebook, and end with a CTA such as **Comment REPORT** for the next story or **subscribe** at centralpareport.com.
