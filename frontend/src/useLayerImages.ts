import { useEffect, useState } from "react";
import type { Layer } from "./api";
import { netImageUrl } from "./reviewGeometry";
export function useLayerImages(layer: Layer, selectedNet: string | null) {
	const urls = [
		layer.image_url,
		layer.overlay_url,
		layer.candidate_url,
		layer.protect_url,
		netImageUrl(layer.net_overlay_url, selectedNet),
	].map(
		(url) => `${url}${url.includes("?") ? "&" : "?"}revision=${layer.revision}`,
	);
	const requestKey = JSON.stringify(urls);
	const [loaded, setLoaded] = useState<{
		key: string;
		images: HTMLImageElement[];
		error: string;
	}>({ key: "", images: [], error: "" });
	useEffect(() => {
		let active = true;
		Promise.all(
			urls.map(
				(url) =>
					new Promise<HTMLImageElement>((resolve, reject) => {
						const image = new Image();
						image.onload = () => resolve(image);
						image.onerror = () => reject(new Error(`이미지 로드 실패: ${url}`));
						image.src = url;
					}),
			),
		)
			.then((images) => {
				if (active) setLoaded({ key: requestKey, images, error: "" });
			})
			.catch((error: unknown) => {
				if (active)
					setLoaded({
						key: requestKey,
						images: [],
						error: error instanceof Error ? error.message : "이미지 로드 실패",
					});
			});
		return () => {
			active = false;
		};
	}, [requestKey]);
	return {
		images: loaded.key === requestKey ? loaded.images : [],
		loadError: loaded.key === requestKey ? loaded.error : "",
		loading: loaded.key !== requestKey,
	};
}
