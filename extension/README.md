# CampusAI browser extension

A minimal Chrome extension: click the toolbar icon, get the live CampusAI chat UI in a popup. No new backend work — it's an `<iframe>` onto the same deployed frontend at [docuchat-psi.vercel.app](https://docuchat-psi.vercel.app).

## Install (unpacked, for local use)

This isn't published to the Chrome Web Store (that needs a developer account and review). To load it yourself:

1. Open `chrome://extensions`.
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and select this `extension/` folder.
4. Pin the CampusAI icon to your toolbar and click it.

## Notes

- `popup.html`'s iframe points at the production URL. If you redeploy the frontend elsewhere, update that URL (and in `manifest.json` if you add host permissions later).
- No `content_security_policy` override is set, so the extension page uses Chrome's default — which allows the remote iframe. If you later add script that talks to the extension APIs, keep that in mind.
