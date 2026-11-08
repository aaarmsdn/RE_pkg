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

앱에서 사진을 열고 왼쪽 **Ballmap · pitch 입력** 패널에서 `.npy`를 선택한다. NET 색상과 row/col 배치를 확인하고 **Ball pitch · mm**를 입력한다. 사진 위 원점은 `[0,0]` ball의 중심이고, **Ball pitch · px**는 이웃 ball 중심 간 pixel 거리다. 이 두 pitch의 비율로 mm/pixel scale을 설정한다. 적용 전에는 미리보기만 바뀌며, **Ballmap · pitch 적용** 후에는 map과 pitch가 프로젝트에 저장된다. ZIP 내보내기와 다시 열기에서도 유지된다.

사진 배치는 현재 축에 평행한 정사각 pitch를 사용한다. 행은 아래, 열은 오른쪽이다. 적용하면 기존 affine calibration을 해제하고 pitch 기반 scale로 재설정하므로 사진의 방향과 원점을 먼저 확인한다. 자동 회전·mirror 정렬 및 3점 정렬은 후속 범위다. Land 복원은 별도 선택이며, 복원 금속은 관측값과 구분해 inferred로 저장한다.

지원 범위: NPY 1/2/3, 고정 폭 Unicode `U1..U160`, 최대 5000칸, 파일 4 MiB, header 10 KiB. Object/pickle·숫자·byte 문자열 배열은 거부한다. 양쪽 공백은 제거하며 NET 이름의 대소문자는 보존한다. `.meta.json`은 참고 자료이며 자동으로 읽지 않는다. 기존 CSV 입력도 고급 입력에서 사용할 수 있다.

[복원·입력 설계](../../superpowers/specs/2026-11-08-diagonal-severe-npy-design.md)의 사선·Severe 복원 엔진은 별도 후속 작업이다.
