import { useEffect, useRef } from "react";
import type { Candidate, Layer, Mutate } from "./api";
import { candidateTitle } from "./reviewGeometry";
import { ReviewThumbnail } from "./ReviewThumbnail";
import type { SelectionChange } from "./bulkSelection";
const recommendationTitle = { accept: "승인 권고", reject: "기각 권고", review: "검토 필요" } as const;
export function Review({
	layer,
	mutate,
	selected,
	onSelect,
	revision,
	selectedIds,
	onSelection,
}: {
	readonly layer: Layer;
	readonly mutate: Mutate;
	readonly selected: Candidate | undefined;
	readonly onSelect: (id: string) => void;
	readonly revision: number;
	readonly selectedIds: readonly string[];
	readonly onSelection: (change: SelectionChange) => void;
}) {
	const list = useRef<HTMLDivElement>(null);
	const ordered = layer.candidates
		.map((candidate, index) => ({ candidate, index }))
		.sort((a, b) => Number(b.candidate.status === "pending") - Number(a.candidate.status === "pending"));
	useEffect(() => {
		const card = list.current?.querySelector('[aria-current="true"]');
		card?.scrollIntoView({ block: "nearest", inline: "nearest" });
	}, [selected?.id]);
	return (
		<section>
			<h2>
				Repair review{" "}
				<span className="badge">
					{layer.candidates.filter((c) => c.status === "pending").length}{" "}
					pending
				</span>
			</h2>
			<p className="help">
				체크박스는 일괄 선택, 제목·사진은 위치 확대. 이미지에서 후보 선택 도구로 여러 후보를 묶을 수 있습니다.
			</p>
			<div className="candidate-list" ref={list}>
				{layer.candidates.length === 0 && (
					<p className="empty-small">
						{layer.analyzed
							? "이 설정에서 생성된 후보 없음."
							: "Copper 추출 · NET 전파 후 후보 표시."}
					</p>
				)}
				{ordered.map(({ candidate, index }) => (
					<article
						className={`candidate ${candidate.status} ${selected?.id === candidate.id ? "review-selected" : ""} ${selectedIds.includes(candidate.id) ? "bulk-selected" : ""} ${candidate.kind === "short_split" ? "split-candidate" : ""}`}
						key={candidate.id}
						aria-current={selected?.id === candidate.id ? "true" : undefined}
					>
						<label className="candidate-check">
							<input type="checkbox" checked={selectedIds.includes(candidate.id)} disabled={candidate.status !== "pending"} onChange={() => onSelection({ ids: [candidate.id], mode: "toggle" })} />
							후보 {index + 1} 일괄 선택
						</label>
						<button
							className="candidate-title"
							aria-pressed={selected?.id === candidate.id}
							onClick={() => onSelect(candidate.id)}
						>
							<span className="candidate-number">{index + 1}</span>
							{candidateTitle[candidate.kind]}
							<span className="locate-label">사진에서 확대 →</span>
						</button>
						<button
							className="thumbnail-button"
							aria-label={`후보 ${index + 1} 위치 확대`}
							onClick={() => onSelect(candidate.id)}
						>
							<ReviewThumbnail layer={layer} candidate={candidate} />
						</button>
						<div className="mono">
							{candidate.kind === "short_split" ? "제거" : "추가"} {candidate.pixels.toLocaleString()} px² · {candidate.status}
						</div>
						{candidate.decision_source && <small>{candidate.decision_source === "automatic" ? "자동 처리" : "수동 처리"} · Undo 가능</small>}
						<p className={`recommendation ${candidate.recommendation}`}>
							<strong>{recommendationTitle[candidate.recommendation]}</strong>{" · "}
							{candidate.recommendation_reason || "NET 근거 갱신 후 확인"}
						</p>
						{candidate.hint_nets.length > 0 && <small>NET 근거: {candidate.hint_nets.join(" · ")}</small>}
						<small>
							원본 x {candidate.bbox[0]}, y {candidate.bbox[1]} ·{" "}
							{candidate.bbox[2]} × {candidate.bbox[3]} px
						</small>
						<details className="candidate-reason">
							<summary>판정 근거</summary>
							<p>{candidate.reason}</p>
						</details>
						<div className="actions">
							<button
								className="primary"
								disabled={candidate.status !== "pending"}
								onClick={() =>
									void mutate("candidates/batch", {
										ids: [candidate.id],
										decision: "accepted",
										expected_revision: revision,
									})
								}
							>
								#{index + 1} 승인
							</button>
							<button
								disabled={candidate.status !== "pending"}
								onClick={() =>
									void mutate("candidates/batch", {
										ids: [candidate.id],
										decision: "rejected",
										expected_revision: revision,
									})
								}
							>
								기각
							</button>
						</div>
					</article>
				))}
			</div>
		</section>
	);
}
