import "./gw-energy-pilot-v008.js?v=0.47-custom-battery1";

const VERSION = "0.09";
const PANEL_NAME = "gw-energypilot-panel";

/*
 * Keep the dashboard header branding self-contained in the active frontend
 * module. Older frontend layers also provide branding, but v0.09 must not
 * depend on a previous render hook finding/replacing an <img> element.
 */
const V009_LOGO_MARK = `
<svg viewBox="0 0 100 100" role="img" aria-label="GW EnergyPilot" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="epV009HeaderBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0c2f56"/>
      <stop offset="1" stop-color="#061327"/>
    </linearGradient>
    <linearGradient id="epV009HeaderGlow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#20dcff"/>
      <stop offset="0.52" stop-color="#19e1d5"/>
      <stop offset="1" stop-color="#22f59c"/>
    </linearGradient>
    <filter id="epV009HeaderShadow" x="-45%" y="-45%" width="190%" height="190%">
      <feGaussianBlur stdDeviation="2.6" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect x="2" y="2" width="96" height="96" rx="24" fill="url(#epV009HeaderBg)" stroke="#15527d" stroke-width="2"/>
  <circle cx="50" cy="50" r="31" fill="none" stroke="#18dfff" stroke-width="5" opacity=".92" filter="url(#epV009HeaderShadow)"/>
  <path d="M58 20 41 47h13l-8 19 23-29H56l8-17Z" fill="#22f59c" filter="url(#epV009HeaderShadow)"/>
  <text x="50" y="68" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="26" font-weight="900" letter-spacing="-2" fill="url(#epV009HeaderGlow)" filter="url(#epV009HeaderShadow)">GW</text>
</svg>`;

function ensureV009BrandLogo(root) {
  const brand = root.querySelector(".brand");
  if (!brand) return;

  let mark = brand.querySelector(".ep-brand-mark");
  const image = brand.querySelector("img");

  if (!mark) {
    mark = document.createElement("div");
    mark.className = "ep-brand-mark ep-v009-brand-mark";
    mark.innerHTML = V009_LOGO_MARK;

    if (image) {
      image.replaceWith(mark);
    } else {
      brand.prepend(mark);
    }
  } else {
    /* Refresh the mark as well, so cached/older header markup cannot win. */
    mark.classList.add("ep-v009-brand-mark");
    mark.innerHTML = V009_LOGO_MARK;
    if (image) image.remove();
  }
}

function ensureV009BrandStyles(root) {
  if (root.querySelector("#ep-v009-brand-style")) return;

  const style = document.createElement("style");
  style.id = "ep-v009-brand-style";
  style.textContent = `
    .ep-v009-brand-mark {
      width: 62px !important;
      height: 62px !important;
      min-width: 62px;
      flex: 0 0 62px !important;
      display: grid !important;
      place-items: center;
      border-radius: 17px;
      overflow: visible !important;
      opacity: 1 !important;
      visibility: visible !important;
      filter: drop-shadow(0 0 18px rgba(25,217,255,.22));
    }
    .ep-v009-brand-mark svg {
      display: block !important;
      width: 100% !important;
      height: 100% !important;
      opacity: 1 !important;
      visibility: visible !important;
    }
    @media (max-width: 720px) {
      .ep-v009-brand-mark {
        width: 48px !important;
        height: 48px !important;
        min-width: 48px;
        flex-basis: 48px !important;
        border-radius: 13px;
      }
    }
  `;
  root.appendChild(style);
}

await customElements.whenDefined(PANEL_NAME);

const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV009Render() {
  previousRender.call(this);

  const root = this.shadowRoot;
  if (!root) return;

  ensureV009BrandLogo(root);
  ensureV009BrandStyles(root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
  }
};
