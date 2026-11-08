# BGA PNG 재입력 시험

정답 mask는 평가에만 사용. 인식 입력은 저장 후 다시 읽은 PNG.
NET 이름은 별도 제공한 L1 ballmap에서만 시작하며 L2 pad/via에는 이름을 주입하지 않음.
원본 PNG만으로는 임의의 DQ/VSS 이름을 알아낼 수 없으므로 png_only는 전부 미할당이 정상.

Plane 비율은 pristine plane-only 면적. 아래 recall/IoU는 손상 전 전체 copper 기준.

|입력|단계|층|Copper precision|Copper recall|IoU|충돌 px|미할당 px|정확한 terminal|
|---|---|---|---:|---:|---:|---:|---:|---:|
|clean|png_only|L1|100.0000%|100.0000%|100.0000%|0|2,481,646|0/32|
|clean|png_only|L2|100.0000%|100.0000%|100.0000%|0|2,314,134|0/36|
|clean|supplied_ballmap_and_vias|L1|100.0000%|100.0000%|100.0000%|0|0|32/32|
|clean|supplied_ballmap_and_vias|L2|100.0000%|100.0000%|100.0000%|0|0|36/36|
|clean|explicit_land_restore|L1|100.0000%|100.0000%|100.0000%|0|0|32/32|
|clean|explicit_land_restore|L2|100.0000%|100.0000%|100.0000%|0|0|36/36|
|damaged|png_only|L1|99.9806%|99.7251%|99.7058%|0|2,475,304|0/32|
|damaged|png_only|L2|99.9879%|99.9407%|99.9287%|0|2,313,041|0/36|
|damaged|supplied_ballmap_and_vias|L1|99.9806%|99.7251%|99.7058%|0|3,079|28/32|
|damaged|supplied_ballmap_and_vias|L2|99.9879%|99.9407%|99.9287%|0|11,798|33/36|
|damaged|explicit_land_restore|L1|99.9807%|99.9458%|99.9265%|0|0|32/32|
|damaged|explicit_land_restore|L2|99.9879%|99.9407%|99.9287%|0|2,348|35/36|
|severe|png_only|L1|99.3776%|99.6693%|99.0511%|0|2,488,930|0/32|
|severe|png_only|L2|98.3206%|99.8608%|98.1860%|0|2,350,384|0/36|
|severe|supplied_ballmap_and_vias|L1|99.3776%|99.6693%|99.0511%|2,468,561|914|8/32|
|severe|supplied_ballmap_and_vias|L2|98.3206%|99.8608%|98.1860%|2,312,665|2,353|7/36|
|severe|explicit_land_restore|L1|99.3790%|99.8909%|99.2712%|2,474,888|5|8/32|
|severe|explicit_land_restore|L2|98.3206%|99.8608%|98.1860%|2,312,665|2,353|7/36|

복원 후보는 자동 승인하지 않음. 명시적 land 보충은 known populated ball disk만 추가하며 숨겨진 escape trace를 만들지 않음. Severe의 흐려진 gap은 단일 PNG에서 정보가 소실될 수 있어 단락·미할당을 실패로 기록하고 사람 교정 대상으로 남김.

실물 PCB 정답 netlist나 Cadence/Siwave 검증을 대신하는 시험이 아님.

## 복원 후보의 오탐

|입력|층|후보 수|제안 추가 px|정답상 빠진 copper px|
|---|---|---:|---:|---:|
|clean|L1|100|10704|0|
|clean|L2|100|6644|0|
|damaged|L1|100|10818|194|
|damaged|L2|100|6716|144|
|severe|L1|100|6796|624|
|severe|L2|100|1614|824|

두 마지막 열의 차이는 의도적 gap/void에 대한 오탐입니다. 후보 100개는 생성 상한이며 전체 후보 수가 아닙니다. Clean에도 후보가 생기므로 일괄 승인은 부적절합니다.

Ballmap 재입력: ballmap.csv, Origin(336,528)px, pitch160px=5mm, land radius24px. 좌표는 합성 샘플용이며 실제 PCB에 적용하면 안 됩니다.
