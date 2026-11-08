import { PhotoInput } from "./PhotoInput";

export function Welcome({ onPhoto, busy }: {
	readonly onPhoto: (file: File) => void;
	readonly busy: boolean;
}) {
	return <div className="welcome">
		<p className="eyebrow">PHOTO → COPPER → NET</p>
		<h1>실제 사진에서<br />배선 검토를 시작하세요</h1>
		<p className="help">원본 픽셀을 유지하며 copper를 추출하고,<br />확정한 NET과 복원 후보를 같은 화면에서 검토합니다.</p>
		<PhotoInput onPhoto={onPhoto} disabled={busy} />
		<div className="welcome-workflow">
			<p><b>01 사진 입력</b><span>PNG · JPEG · 여러 layer</span></p>
			<p><b>02 Copper 분석</b><span>재질 분리 · native ROI</span></p>
			<p><b>03 검토 · 저장</b><span>NET 확인 · 교정 · 내보내기</span></p>
		</div>
		<p className="help">관측 copper와 복원 추가분을 분리합니다. 사진만으로 NET 이름이나 완전 복원을 보장하지 않습니다.</p>
	</div>;
}
