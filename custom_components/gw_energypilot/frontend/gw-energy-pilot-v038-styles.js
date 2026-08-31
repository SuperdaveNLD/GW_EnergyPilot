export function ensureV038Styles(root) {
  if (root.querySelector("#ep-v038-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v038-style";
  style.textContent = `
    .ep-v038-strategy {
      margin-top:15px; padding-top:14px;
      border-top:1px solid rgba(81,168,211,.10);
    }
    .ep-v038-kicker { color:#62e5f7; font-size:10px; font-weight:900; letter-spacing:.15em; }
    .ep-v038-title { margin-top:3px; color:#e8f7fc; font-size:17px; font-weight:860; }
    .ep-v038-description { max-width:820px; margin-top:5px; color:#7696aa; font-size:11px; line-height:1.5; }
    .ep-v038-profile-grid {
      display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin-top:12px;
    }
    .ep-v038-profile {
      appearance:none; position:relative; box-sizing:border-box; width:100%; min-width:0; min-height:86px;
      padding:11px 10px; border:1px solid rgba(75,164,209,.16); border-radius:11px;
      color:#a7c3d1; background:rgba(5,27,47,.52); cursor:pointer; text-align:left;
      touch-action:pan-y; -webkit-tap-highlight-color:transparent;
      transition:border-color .12s linear,background-color .12s linear,box-shadow .12s linear,transform .12s linear;
    }
    .ep-v038-profile:hover:not(:disabled),
    .ep-v038-profile:focus-visible {
      border-color:rgba(55,213,231,.42); background:rgba(7,43,66,.72);
    }
    .ep-v038-profile:active:not(:disabled) { transform:translateY(1px); }
    .ep-v038-profile[aria-pressed="true"] {
      border-color:rgba(41,226,181,.62);
      background:linear-gradient(145deg,rgba(10,82,91,.68),rgba(8,67,52,.60));
      box-shadow:inset 0 0 18px rgba(37,220,174,.08),0 0 0 1px rgba(41,226,181,.08);
    }
    .ep-v038-profile:disabled { opacity:.56; cursor:wait; }
    .ep-v038-profile strong {
      display:block; padding-right:35px; color:#e7f7fc; font-size:12px; font-weight:850;
      line-height:1.25; overflow-wrap:anywhere; hyphens:auto;
    }
    .ep-v038-profile small {
      display:block; margin-top:6px; color:#789aab; font-size:9px; line-height:1.45;
      overflow-wrap:anywhere; hyphens:auto;
    }
    .ep-v038-profile[aria-pressed="true"] small { color:#91b8b6; }
    .ep-v038-profile-range { display:block; margin-top:7px; color:#9ab6c5; font-size:9px; font-weight:800; }
    .ep-v038-badge {
      position:absolute; top:8px; right:8px; color:#70e8c2; font-size:8px; font-weight:900; letter-spacing:.08em;
    }
    .ep-v038-message { margin-top:9px; min-height:16px; color:#6f91a4; font-size:10px; }
    .ep-v038-message.ok { color:#72dbb3; }
    .ep-v038-message.error { color:#ef9f98; }
    .ep-v038-custom {
      margin-top:11px; padding:11px; border:1px solid rgba(67,188,215,.12); border-radius:11px;
      background:rgba(5,24,42,.38);
    }
    .ep-v038-custom-head { color:#d8edf5; font-size:13px; font-weight:820; }
    .ep-v038-custom-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:9px; }
    .ep-v038-soc { padding:9px 10px; border:1px solid rgba(76,157,202,.10); border-radius:9px; background:rgba(7,29,50,.43); }
    .ep-v038-soc-label { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:6px; color:#9bb5c5; font-size:10px; }
    .ep-v038-soc-label strong { color:#e5f4fa; font-size:12px; }
    .ep-v038-soc input { width:100%; accent-color:#25ddb6; touch-action:pan-y; }
    .ep-v038-custom-values { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:7px; margin-top:9px; }
    .ep-v038-custom-value { display:block; padding:8px; border:1px solid rgba(76,157,202,.10); border-radius:8px; background:rgba(7,29,50,.32); min-width:0; }
    .ep-v038-custom-value span { display:block; color:#7899aa; font-size:9px; }
    .ep-v038-custom-value input {
      box-sizing:border-box; width:100%; min-width:0; min-height:34px; margin-top:5px; padding:6px 8px;
      border:1px solid rgba(80,178,215,.22); border-radius:7px; outline:none;
      color:#d9edf5; background:rgba(3,20,36,.72); font:750 11px ui-monospace,SFMono-Regular,Menlo,monospace;
    }
    .ep-v038-custom-value input:focus { border-color:rgba(43,221,185,.62); box-shadow:0 0 0 2px rgba(43,221,185,.10); }
    .ep-v038-custom-value input:disabled { opacity:.55; }
    .ep-v038-custom-actions { display:flex; justify-content:flex-end; margin-top:9px; }
    .ep-v038-custom-save {
      min-height:36px; padding:7px 12px; border:1px solid rgba(42,224,183,.42); border-radius:8px;
      color:#defcf2; background:rgba(10,88,72,.58); cursor:pointer; font-size:10px; font-weight:850;
    }
    .ep-v038-custom-save:disabled { opacity:.5; cursor:wait; }
    .ep-v038-custom-note { margin-top:9px; color:#6f8ea1; font-size:9px; line-height:1.5; }
    .ep-v038-managed {
      margin-top:11px; padding:11px; border:1px solid rgba(67,188,215,.12); border-radius:11px;
      background:rgba(5,24,42,.38);
    }
    .ep-v038-managed-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:7px; margin-top:9px; }
    .ep-v038-managed-grid span { padding:8px; border:1px solid rgba(76,157,202,.10); border-radius:8px; color:#7899aa; font-size:9px; }
    .ep-v038-managed-grid strong { display:block; margin-top:3px; color:#d9edf5; font-size:11px; }
    .ep-v038-diagnostic-note { margin-top:10px; color:#66869a; font-size:10px; }

    /* v0.38 owns physical particle direction. The old inbound/outbound and
       semantic classes may remain for compatibility, but neither may reverse
       the authoritative keyframe selected below. */
    .ep-flow-link[data-ep-v038-motion] .ep-v011-particles span {
      animation-direction:normal !important;
    }
    .ep-flow-link[data-ep-v038-motion="right"] .ep-v011-particles span {
      animation-name:epV038HRight !important;
    }
    .ep-flow-link[data-ep-v038-motion="left"] .ep-v011-particles span {
      animation-name:epV038HLeft !important;
    }
    .ep-flow-link[data-ep-v038-motion="down"] .ep-v011-particles span {
      animation-name:epV038VDown !important;
    }
    .ep-flow-link[data-ep-v038-motion="up"] .ep-v011-particles span {
      animation-name:epV038VUp !important;
    }
    .ep-flow-link[data-ep-v038-motion="idle"] .ep-v011-particles span {
      animation-name:none !important; opacity:.22 !important;
    }
    @keyframes epV038HRight {
      from { translate:-9px 0; }
      to { translate:var(--ep-track-distance,80px) 0; }
    }
    @keyframes epV038HLeft {
      from { translate:var(--ep-track-distance,80px) 0; }
      to { translate:-9px 0; }
    }
    @keyframes epV038VDown {
      from { translate:0 -9px; }
      to { translate:0 var(--ep-track-distance,80px); }
    }
    @keyframes epV038VUp {
      from { translate:0 var(--ep-track-distance,80px); }
      to { translate:0 -9px; }
    }

    @media (max-width:1000px) {
      .ep-v038-profile-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
      .ep-v038-custom-values,.ep-v038-managed-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
    }
    @media (max-width:650px) {
      .ep-v038-profile-grid { grid-template-columns:1fr 1fr; }
      .ep-v038-custom-grid,.ep-v038-custom-values,.ep-v038-managed-grid { grid-template-columns:1fr; }
    }
    @media (max-width:430px) { .ep-v038-profile-grid { grid-template-columns:1fr; } }
  `;
  root.appendChild(style);
}
