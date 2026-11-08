import { useId, useState } from "react";

export function PhotoInput({ onPhoto, compact = false, disabled = false }: {
	readonly onPhoto: (file: File) => void;
	readonly compact?: boolean;
	readonly disabled?: boolean;
}) {
	const id = useId();
	const [dragging, setDragging] = useState(false);
	return <div className={`photo-input ${compact ? "compact" : ""} ${dragging ? "dragging" : ""}`}
		onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }}
		onDragLeave={() => setDragging(false)}
		onDrop={(event) => {
			event.preventDefault(); setDragging(false);
			const file = event.dataTransfer.files[0];
			if (file && !disabled) onPhoto(file);
		}}>
		<label htmlFor={id}>{compact ? "새 사진으로 시작" : "PNG / JPEG 사진 열기"}</label>
		<input id={id} type="file" accept="image/png,image/jpeg" disabled={disabled} onChange={(event) => {
			const file = event.target.files?.[0];
			if (file) onPhoto(file);
			event.target.value = "";
		}} />
		{!compact && <p className="help">파일을 선택하거나 여기에 놓으세요 · 원본 ≤ 30M px<br />새 프로젝트로 저장됩니다. 기존 작업은 유지됩니다.</p>}
	</div>;
}
