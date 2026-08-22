# GW EnergyPilot branding

GW EnergyPilot ships local Home Assistant brand assets in:

```text
custom_components/gw_energypilot/brand/
├── icon.png
└── logo.png
```

Home Assistant 2026.3 and newer supports local brand images for custom integrations through its Brands Proxy API. The supported local brand files are PNG files (`icon.png`, `dark_icon.png`, `logo.png`, `dark_logo.png` and optional `@2x` variants).

SVG is not a supported Home Assistant integration-brand format. For that reason the EnergyPilot SVG is stored separately for EnergyPilot-owned frontend surfaces:

```text
custom_components/gw_energypilot/frontend/gw-energy-pilot-logo.svg
```

The built-in EnergyPilot dashboard also keeps its important logo marks self-contained/inline so browser caching or a missing external image cannot remove the dashboard identity.

## HACS placeholder icon

As of Home Assistant/HACS releases in August 2026, HACS has an open frontend issue where custom integrations that correctly ship local brand images can still show **Icon not available** in HACS. Home Assistant itself uses the local Brands Proxy API, while HACS can still request the public brands/CDN source for that repository view.

This means a missing icon specifically inside HACS does not indicate that the EnergyPilot local brand files are missing or broken.

References:

- Home Assistant developer announcement: https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/
- HACS local-brand issue: https://github.com/hacs/integration/issues/5402
- Related HACS issue: https://github.com/hacs/integration/issues/5171
