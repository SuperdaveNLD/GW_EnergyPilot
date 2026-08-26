import "./gw-energy-pilot-v036-customer-controller.js?v=0.36.2-scroll-stability1";

const VERSION = "0.36.2";
const PANEL_NAME = "gw-energypilot-panel";
const MOBILE_SCROLL_BREAKPOINT_PX = 720;

function composedParent(node) {
  if (node?.parentElement) return node.parentElement;
  const root = node?.getRootNode?.();
  const host = root?.host;
  return host instanceof Element ? host : null;
}

function shouldPreserveScroll(panel) {
  return Boolean(
    panel?.narrow === true ||
    panel?._narrow === true ||
    globalThis.matchMedia?.(`(max-width: ${MOBILE_SCROLL_BREAKPOINT_PX}px)`)?.matches === true
  );
}

function scrollSnapshot(element) {
  if (!(element instanceof Element)) return null;
  const scrollTop = Number(element.scrollTop || 0);
  const scrollLeft = Number(element.scrollLeft || 0);
  const scrollRange = Number(element.scrollHeight || 0) - Number(element.clientHeight || 0);
  if (scrollRange <= 1 && scrollTop <= 0) return null;

  const overflowY = globalThis.getComputedStyle?.(element)?.overflowY || "";
  if (scrollTop <= 0 && !/(auto|scroll|overlay)/.test(overflowY)) return null;
  return { element, scrollTop, scrollLeft };
}

function captureScrollPositions(panel) {
  const snapshots = [];
  const seen = new Set();
  let node = panel;

  while (node) {
    const snapshot = scrollSnapshot(node);
    if (snapshot && !seen.has(snapshot.element)) {
      snapshots.push(snapshot);
      seen.add(snapshot.element);
    }
    node = composedParent(node);
  }

  const documentScroller = globalThis.document?.scrollingElement;
  const documentSnapshot = scrollSnapshot(documentScroller);
  if (documentSnapshot && !seen.has(documentSnapshot.element)) {
    snapshots.push(documentSnapshot);
  }
  return snapshots;
}

function restoreScrollPositions(snapshots) {
  for (const snapshot of snapshots) {
    const element = snapshot.element;
    if (!element?.isConnected) continue;
    const maxTop = Math.max(0, Number(element.scrollHeight || 0) - Number(element.clientHeight || 0));
    const maxLeft = Math.max(0, Number(element.scrollWidth || 0) - Number(element.clientWidth || 0));
    element.scrollTop = Math.min(snapshot.scrollTop, maxTop);
    element.scrollLeft = Math.min(snapshot.scrollLeft, maxLeft);
  }
}

function stabilizeScrollAfterRender(snapshots) {
  if (!snapshots.length) return;

  // The legacy dashboard still rebuilds its Shadow DOM for relevant HA state
  // updates. Restore the HA scroll container immediately, then once more after
  // layout/ResizeObserver work has settled so a telemetry refresh cannot move
  // a phone viewport to a new browser scroll anchor.
  restoreScrollPositions(snapshots);
  globalThis.requestAnimationFrame?.(() => {
    restoreScrollPositions(snapshots);
    globalThis.requestAnimationFrame?.(() => restoreScrollPositions(snapshots));
  });
}

function updateVersion(root) {
  const versionBadge = root?.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root?.querySelectorAll("footer span") || [];
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV0362ScrollStabilityInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV0362ScrollStableRender() {
    const preserveScroll = shouldPreserveScroll(this);
    const snapshots = preserveScroll ? captureScrollPositions(this) : [];

    if (preserveScroll) this.style.setProperty("overflow-anchor", "none");
    else this.style.removeProperty("overflow-anchor");

    previousRender.call(this);
    updateVersion(this.shadowRoot);
    stabilizeScrollAfterRender(snapshots);
  };
  PanelClass.prototype.__epV0362ScrollStabilityInstalled = true;
}
