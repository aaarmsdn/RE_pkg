# 2차원 문자열 ballmap NPY 예제

`ballmap-8x4.npy`: 기존 합성 BGA의8열×4행 배열, shape `(4, 8)`, Unicode160자 슬롯. DQ0–15 각1개, VSS8개, VDD4개, VDDQ4개. 실제 DRAM 규격 파일이 아니다.

```python
import numpy as np

ballmap = np.load("ballmap-8x4.npy", allow_pickle=False)
print(ballmap.shape)       # (4, 8)
print(ballmap[0, 0])       # DQ8
np.save("my-ballmap.npy", ballmap, allow_pickle=False)
```

새로 만들 때는 다음처럼 저장한다. 기존 고정 폭 배열에 긴 이름을 대입하면 잘릴 수 있으므로160자 제한을 먼저 확인한다.

```python
rows = [["VSS", "DQ0", "DQ1", "VDDQ"],
        ["", "?", "NC", "VDD"]]
assert all(len(name) <= 160 for row in rows for name in row)
ballmap = np.asarray(rows, dtype="<U160")
np.save("ballmap.npy", ballmap, allow_pickle=False)
```

- 빈 문자열 `""`: 설계상 ball 없음. 금속을 보충하지 않음.
- `"?"`: ball 있음, NET 미확정. 이름 전파 근거로 사용하지 않음.
- `"NC"`: ball 있음, 전기 NET 없음. 다른 NC와 같은 NET으로 묶지 않음.
- 사진에서 금속이 없어져도 원래 NET 이름 유지. 예: 사라진 VSS ball도 배열에는 `"VSS"`.
- row는 아래, col은 오른쪽인 논리 배열. 사진 회전·mirror는 별도 정렬.

`ballmap-8x4.meta.json`은 선택적인 metadata 규격 예시다. 5mm pitch는 이 합성 예제 값이다. 실제 사진에는 실제 pitch와 land 크기를 입력해야 한다. NPY 하나만 공급하면 GUI에서 나머지 값을 지정하는 방식으로 설계했다.

현재 앱은 CSV만 지원하며 **NPY importer는 구현 전**이다. [복원·입력 설계](../../superpowers/specs/2026-11-08-diagonal-severe-npy-design.md)에 후속 변경과 검증 기준을 기록했다.
