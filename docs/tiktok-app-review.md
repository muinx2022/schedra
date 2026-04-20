# TikTok App Review

## Website URLs

- Website: `https://schedra.net/tiktok-review`
- Sign in: `https://schedra.net/login`
- Register: `https://schedra.net/register`
- Privacy policy: `https://schedra.net/chinh-sach-rieng-tu`
- Terms of service: `https://schedra.net/quy-dinh-su-dung`

## Products and scopes currently implemented

- Product: TikTok account connection for publishing inside an authenticated Schedra workspace
- Scope: `user.info.basic`
- Scope: `video.publish`

Schedra does not use TikTok for end-user login. TikTok is only used after the user signs in to Schedra and connects a TikTok creator account from Workspace Settings.

## Submission copy

Schedra is a social media publishing workspace. Inside an authenticated Schedra account, the user can connect a TikTok creator profile from Workspace Settings through TikTok OAuth. We use `user.info.basic` to identify and display the connected TikTok creator account inside the workspace after authorization. We use `video.publish` so the user can publish or schedule media posts from Schedra to the TikTok account they connected. In this version, the TikTok flow is available on the live website at `https://schedra.net/tiktok-review`, where reviewers can sign in, open the TikTok connection flow, return to Settings with the connected creator account visible, and then continue to the Posts screen to publish content to TikTok.

## Demo video checklist

1. Open `https://schedra.net/tiktok-review`.
2. Show that the domain matches the website URL submitted in TikTok Developer Portal.
3. Create a workspace or sign in with the review account.
4. From the review page, open the TikTok connection flow.
5. Complete TikTok OAuth and return to Schedra.
6. Show the connected TikTok creator account in Workspace Settings.
7. Open Posts.
8. Create or open a post with supported media.
9. Select the connected TikTok account.
10. Publish immediately or schedule the post.

## Reviewer notes

- The TikTok integration is used only inside the authenticated Schedra workspace.
- The user explicitly chooses when to connect the account and when to publish content.
- The app already exposes privacy policy and terms of service on the same verified domain.
