# GW EnergyPilot branding

GW EnergyPilot v0.30 ships a complete local Home Assistant brand set in:

```text
custom_components/gw_energypilot/brand/
├── icon.png
├── icon@2x.png
├── dark_icon.png
├── dark_icon@2x.png
├── logo.png
└── dark_logo.png
```

Home Assistant 2026.3 and newer supports local brand images for custom integrations through its Brands Proxy API. The integration therefore deploys PNG files in `brand/` and keeps the scalable SVG masters outside that directory.

The icon assets use the existing GW EnergyPilot square mark. `icon.png` and `dark_icon.png` are 256×256; their `@2x` variants are 512×512. The landscape light/dark logos are 800×256.

SVG is not a supported Home Assistant integration-brand format. The scalable EnergyPilot masters are stored for EnergyPilot-owned frontend/documentation surfaces:

```text
custom_components/gw_energypilot/frontend/gw-energy-pilot-logo.svg
custom_components/gw_energypilot/frontend/gw-energy-pilot-wordmark.svg
custom_components/gw_energypilot/frontend/gw-energy-pilot-wordmark-dark.svg
```

The built-in EnergyPilot dashboard also keeps important identity marks self-contained/inline so browser caching or a missing external image cannot remove dashboard identity.

## Palette

```text
Deep navy      #061327
Navy           #0C2F56
Border blue    #15527D
Cyan           #20DCFF
Aqua           #19E1D5
Energy green   #22F59C
```

## HACS placeholder icon

As of Home Assistant/HACS releases in August 2026, HACS has an open frontend issue where custom integrations that correctly ship local brand images can still show **Icon not available** in HACS. Home Assistant itself uses the local Brands Proxy API, while HACS can still request the public brands/CDN source for that repository view.

This means a missing icon specifically inside HACS does not indicate that the EnergyPilot local brand files are missing or broken.

References:

- Home Assistant developer announcement: https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/
- HACS local-brand issue: https://github.com/hacs/integration/issues/5402
- Related HACS issue: https://github.com/hacs/integration/issues/5171
