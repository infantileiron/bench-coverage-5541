/** @typedef {{id: number, code: string, title: string, bank: string, stable: boolean}} Segment */
/** @typedef {{id: number, segment_code: string, campaign: string, round_code: 'A'|'B', asset_code: string, state: string}} Capture */
/** @typedef {{id: number, title: string, status: string, note: string, parameters: object, result?: object}} Analysis */
/** @typedef {{id: number, title: string, campaign: string, status: 'draft'|'estimated'|'inconclusive', seed: number, confidence: number, locked_snapshot: object, strata: object[], result?: object, note: string}} SamplingPlan */
/** @typedef {{id: number, plan_id: number, segment_code: string, state: 'pending'|'counted'|'blocked'|'suspended', total_found: number|null, asset_codes: string[], missing_locked: string[], reason: string, reporter: string}} RecountReturn */
