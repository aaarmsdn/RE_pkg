import type { Layer, Mutate } from "./api";
import type { SelectionChange } from "./bulkSelection";

export function CandidateActions({ layer, revision, selectedIds, onSelection, mutate }: {
	readonly layer: Layer;
	readonly revision: number;
	readonly selectedIds: readonly string[];
	readonly onSelection: (change: SelectionChange) => void;
	readonly mutate: Mutate;
}) {
	const pending = layer.candidates.filter((candidate) => candidate.status === "pending");
	const count = selectedIds.length;
	const summary = layer.review_summary;
	return (
		<div className="candidate-actions" aria-label="후보 일괄 처리">
			<div className="selection-heading">
				<strong aria-live="polite">선택 {count}개 <span className="help">/ 미처리 {pending.length}개</span></strong>
				<div className="actions">
					<button disabled={!pending.length} onClick={() => onSelection({ ids: pending.map((candidate) => candidate.id), mode: "replace" })}>미처리 전체 선택</button>
					<button disabled={!count} onClick={() => onSelection({ ids: [], mode: "replace" })}>선택 해제</button>
				</div>
			</div>
			<div className="actions">
				<button className="primary" disabled={!count} onClick={() => void mutate("candidates/batch", { ids: selectedIds, decision: "accepted", expected_revision: revision })}>선택 {count}개 승인</button>
				<button disabled={!count} onClick={() => void mutate("candidates/batch", { ids: selectedIds, decision: "rejected", expected_revision: revision })}>선택 {count}개 기각</button>
				<button disabled={!pending.length} onClick={() => void mutate("candidates/auto", { ids: count ? selectedIds : null, expected_revision: revision })}>{count ? `선택 ${count}개` : "미처리 전체"} NET 자동 처리</button>
				<button disabled={!layer.analyzed} onClick={() => void mutate("candidates/evaluate", { expected_revision: revision })}>NET 근거 갱신</button>
			</div>
			<p className="help">후보 선택 도구: 사각형 드래그 · Shift+드래그 추가 · 핀 클릭 토글. 다른 NET 단락 후보는 기각; 불확실한 후보는 검토 유지. 자동 처리 Undo 가능.</p>
			{summary && <p className="review-summary" role="status">최근 {summary.source === "automatic" ? "자동" : "수동"} 처리: 승인 {summary.accepted} · 기각 {summary.rejected} · 검토 유지 {summary.review}</p>}
		</div>
	);
}
