# @amcp/sdk

TypeScript SDK for AMCP. Thin by law: it speaks the protocol fluently and gets out of the way.

```bash
npm install   # devDeps only — runtime dependencies: zero
npm run build # tsc → dist/
npm test      # vitest: all fixtures vs live reference + SDK behavior + drift tripwire
npm run check # tsc --noEmit
```

```ts
import { TaskClient, SessionClient, IdentityClient, DisputeClient } from "@amcp/sdk";

const tasks = new TaskClient({ baseUrl: "https://agent.example" });
const { receipt } = await tasks.run("score_lead", { lead: {...} },
  { idempotencyKey: crypto.randomUUID(), trial: true });

const id = new IdentityClient({ baseUrl: "https://agent.example" });
await id.verifyReceiptViaDirectory(receipt); // offline, advertised key
```

## Constraints (enforced, not aspirational)

- **Zero runtime dependencies** — `dependencies: {}`.
- **Node 20+ and Workers** — no `node:*` imports in `src/`; WebCrypto for Ed25519.
- **Types mirror `schemas/`** — `test/schema-drift.test.ts` fails CI on drift.
- **Wire proven by fixtures** — `test/fixtures.test.ts` replays every fixture against the reference.
