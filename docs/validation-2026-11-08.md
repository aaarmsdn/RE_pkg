# 검증 결과 — 2026-11-08

## 자동 검사

- Python: `uv run pytest -q` —176passed.
- 게시할 Git index만 새 임시 폴더에 복원: API/실물 재질/baseline 경로 관련18tests PASS. 로컬 프로젝트·사진·.omo 없이 검사.
- Python lint: `uv run ruff check pkg_re tests` —PASS.
- Frontend: `pnpm run check`, `pnpm test`, `pnpm run build` —46tests, typecheck/build PASS.
- [24개 PNG 재입력](../outputs/plane-benchmark/README.md):72개 stage/layer 측정, Clean18행. Clean 전배치 terminal/pair/면적 엄격검사 PASS. 관측 false copper도 gate에 포함.
- [실물 JPEG API](../outputs/real-photo-benchmark/metrics.json):업로드,4M ROI 제한, 색차 추출, 확인 NET 전파, CSV,ZIP 재열기 PASS. 최신 source35개 해시 일치.
- 별도 코드 리뷰: blocking issue0. Clean gate의 관측 false copper 누락을 수정하고 실패→통과 회귀시험 수행. 현재 보고서는 Clean18행 존재를 별도로 확인했다. 보고서 helper만 Clean 없는 임의 입력에 재사용할 때는 coverage 검사가 추가로 필요하다.

## 실제 브라우저

Chrome에서 primary 사진 입력 버튼으로5616×3744 JPEG를 업로드했다. ROI1800/1000/1200/1200, 색차14로 분석하고 PHOTO_PLANE_A 표식을 입력했다. 화면 범례·면적표와 실제 다운로드 CSV에815312px²/1island를 확인했다. 후보2개 선택→기각→pending100→98→Undo100도 확인했다. 새 DQ32 Diagonal 예제 생성과 양층 이미지 표시를 확인했다.

390px와1440px에서 가로 넘침 없이 표시했다. 창 크기 전환 중 발견한 음수 canvas scale 오류를 수정하고 실브라우저에서 재검증했다. 앱은 단일 dark palette이며 light/dark OS 선호 양쪽에서 같은 팔레트로 검사했다. 사용자 viewport와 media override는 원복했다. 원본 사진이 포함된 GUI 캡처는 로컬 증거로만 보관하며 이 공개 저장소에는 포함하지 않는다.

## 정확도 경계

Clean은 통과하지만 Damaged는 일부 단절이 남는다. Severe와 전역 Diagonal은 완전 자동 복원 실패다. False added0은 blur가 만든 관측 false copper0을 뜻하지 않는다. 실물에는 정답 netlist가 없어 정확도 수치를 주장하지 않는다. PHOTO_PLANE_A는 동작 검증용 사용자 표식이다.

[후속 복원 전략](superpowers/specs/2026-11-08-damage-recovery-strategy.md)에 전역 scratch 주기·방향 검출, 경쟁 연결 가설, 층간 근거, 사람 교정과 각 단계 통과 기준을 기록했다. `.mcm` 및 Siwave 해석 모델 생성은 후속 단계다.
