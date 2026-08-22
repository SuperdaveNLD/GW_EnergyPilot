import "./gw-energy-pilot.js?v=0.05";

const VERSION = "0.06";
const PANEL_NAME = "gw-energypilot-panel";

const LOGO_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="GW EnergyPilot">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0a274a"/>
      <stop offset="1" stop-color="#06152d"/>
    </linearGradient>
    <linearGradient id="energy" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#20dcff"/>
      <stop offset="0.52" stop-color="#16e5d0"/>
      <stop offset="1" stop-color="#20f49d"/>
    </linearGradient>
    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect x="3" y="3" width="122" height="122" rx="29" fill="url(#bg)" stroke="#16466e" stroke-width="3"/>
  <path d="M66 27H48C31 27 20 38 20 55s11 28 28 28h18V61H49v11h6v1H48c-10 0-16-7-16-18s6-18 16-18h18V27Z" fill="url(#energy)" filter="url(#glow)"/>
  <path d="M64 47 76 91l12-28 10 28 13-45h-12l-5 24-7-21H78l-7 21-5-23H64Z" fill="url(#energy)" filter="url(#glow)"/>
  <path d="M69 31 58 54h12l-7 20 23-30H74l9-13H69Z" fill="#d8fff4" opacity=".95"/>
</svg>`;

const LOGO_DATA_URI = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(LOGO_SVG)}`;

await customElements.whenDefined(PANEL_NAME);

const PanelClass = customElements.get(PANEL_NAME);
const originalRender = PanelClass.prototype._render;

PanelClass.prototype._render = function patchedRender() {
  originalRender.call(this);

  const root = this.shadowRoot;
  if (!root) {
    return;
  }

  const logo = root.querySelector(".brand img");
  if (logo) {
    logo.src = LOGO_DATA_URI;
    logo.alt = "GW EnergyPilot";
    logo.style.background = "transparent";
    logo.style.objectFit = "contain";
    logo.style.filter = "drop-shadow(0 0 15px rgba(25, 217, 255, .24))";
  }

  const versionBadge = root.querySelector(".version");
  if (versionBadge) {
    versionBadge.textContent = `v${VERSION}`;
  }

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
  }
};
