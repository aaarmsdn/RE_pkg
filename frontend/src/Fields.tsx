import type { ReactNode } from "react";
export function Field({
	label,
	children,
}: {
	readonly label: string;
	readonly children: ReactNode;
}) {
	return (
		<label className="field">
			<span>{label}</span>
			{children}
		</label>
	);
}
export function NumberField({
	label,
	value,
	onChange,
	min,
	max,
	step = "any",
}: {
	readonly label: string;
	readonly value: number;
	readonly onChange: (value: number) => void;
	readonly min?: number;
	readonly max?: number;
	readonly step?: number | "any";
}) {
	return (
		<Field label={label}>
			<input
				type="number"
				value={value}
				min={min}
				max={max}
				step={step}
				onChange={(e) => onChange(Number(e.target.value))}
			/>
		</Field>
	);
}
