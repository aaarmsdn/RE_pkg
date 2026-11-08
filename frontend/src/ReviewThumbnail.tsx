import { useId, useState } from "react";
import type { Candidate, Layer } from "./api";
import { contextCrop } from "./reviewGeometry";
export function ReviewThumbnail({
	layer,
	candidate,
}: {
	readonly layer: Layer;
	readonly candidate: Candidate;
}) {
	const clip = useId();
	const [failed, setFailed] = useState(false);
	const crop = contextCrop(candidate.bbox, layer);
	const [x, y, w, h] = candidate.bbox;
	const revision = (url: string) =>
		`${url}${url.includes("?") ? "&" : "?"}revision=${layer.revision}`;
	if (failed) return <p className="error-text">원본 / 후보 이미지 로드 실패</p>;
	return (
		<div className="review-thumbnails">
			{[false, true].map((proposal) => (
				<figure key={String(proposal)}>
					<svg
						viewBox={crop.join(" ")}
						role="img"
						aria-label={
							proposal
								? "원본 위 선택 후보 mask와 주변 copper"
								: "후보 위치의 실제 원본과 주변 copper"
						}
						preserveAspectRatio="xMidYMid meet"
					>
						<defs>
							<clipPath id={`${clip}-${proposal}`}>
								<rect x={x} y={y} width={w} height={h} />
							</clipPath>
						</defs>
						<image
							href={revision(layer.image_url)}
							width={layer.width}
							height={layer.height}
							onError={() => setFailed(true)}
						/>
						{proposal && candidate.status === "pending" && (
							<image
								href={revision(layer.candidate_url)}
								width={layer.width}
								height={layer.height}
								clipPath={`url(#${clip}-${proposal})`}
								onError={() => setFailed(true)}
							/>
						)}
						<rect
							x={x}
							y={y}
							width={w}
							height={h}
							fill="none"
							stroke={candidate.kind === "short_split" ? "#f39991" : "#efc271"}
							strokeWidth="1.5"
							vectorEffect="non-scaling-stroke"
						/>
					</svg>
					<figcaption>
						{proposal
							? candidate.status === "pending"
								? candidate.kind === "short_split" ? "제거 제안 · 미승인" : "추가 제안 · 미승인"
								: "처리됨 · 후보 mask 제외"
							: "원본 · 변경 없음"}
					</figcaption>
				</figure>
			))}
		</div>
	);
}
