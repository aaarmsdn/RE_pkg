import { useEffect, useState } from "react";
import type { Layer } from "./api";
import { bulkSelectionScope, changeSelection, resolveBulkSelection } from "./bulkSelection";
import type { BulkSelection, SelectionChange } from "./bulkSelection";

export function useCandidateSelection(projectId: string | undefined, layer: Layer | undefined, epoch: number) {
	const candidates = layer?.candidates ?? [];
	const scope = bulkSelectionScope(projectId, layer, epoch);
	const [selection, setSelection] = useState<BulkSelection>({ scope, ids: [] });
	const selectedIds = resolveBulkSelection(selection, scope, candidates);
	useEffect(() => {
		setSelection((current) => {
			const ids = resolveBulkSelection(current, scope, candidates);
			return current.scope === scope && ids.length === current.ids.length ? current : { scope, ids };
		});
	}, [scope, layer?.candidates]);
	const selectCandidates = (change: SelectionChange) => setSelection((current) => ({
		scope,
		ids: changeSelection(resolveBulkSelection(current, scope, candidates), change),
	}));
	return { selectedIds, selectCandidates };
}
