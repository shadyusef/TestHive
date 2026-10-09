# Screen map cache
One file per module: `mobile/screens/<module>.md`.
The mobile engineer inspects each screen ONCE, records its stable element ids here, and reuses them in later flows.
Re-inspect a screen only when a step on it fails.

Format (one block per screen):
```
## <ScreenName>
- id: <element id> | label: <text> | note: <optional>
```
