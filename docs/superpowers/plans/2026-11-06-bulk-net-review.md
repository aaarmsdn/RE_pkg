# Bulk spatial review and NET-constrained automation

**Goal:** Select repair candidates directly on the image, approve/reject selections in one undoable transaction, and use confirmed physical net hints to automate unambiguous decisions.

**Architecture:** Existing local graph remains authority for confirmed identities. Candidate recommendations derive from current accepted masks, explicit seeds and actual via contacts. Original pixels remain immutable. Automatic edits preserve inferred/erased provenance and undo. Synthetic truth is excluded from all inference.

**Spec:** Current user request plus approved reconstruction design. User authorizes batch actions and hint-driven automation; this extends existing review rather than replacing it.

## Decisions

- Rectangle selection mode + Shift add/toggle; pending candidates only. Selection resets on layer/project/regeneration and clears decided items. Focus/zoom separate from checkbox selection.
- Manual batch endpoint `candidates/batch`: ids, accepted/rejected, expected_revision. Validate all pending IDs and current revision; all-or-none transaction, one undo. Reject combinations creating/expanding conflicts, preserving masks on failure.
- NET recommendations: accept/reject/review plus rationale and contributing net names. Different assigned nets must not be bridged. Existing conflict or unnamed ambiguous region cannot imply safe material geometry.
- Auto endpoint `candidates/auto`: optional selected IDs, expected_revision; process deterministic sequence and recompute hints after geometry changes. Auto rejects proven cross-net bridges, accepts only geometrically supported conservative repairs; unknown/round holes and ambiguous cuts stay pending. Summary reports actual accepted/rejected/review counts.
- Opt-in analysis checkbox runs auto after extraction. One-shot auto button works on selected/all pending candidates. All automated status is labelled and reversible.
- Weak observed bridges in a conflicting component may produce `short_split` erase proposals, never force a full plane partition simply by nearest seed. Preserve terminals/protected edits; only present a split if graph conflicts decrease and confirmed contacts remain. Manual review required for cuts.
- Current candidate cap remains100 and is disclosed. Runtime classification should use one graph plus local neighborhoods, not100 full graph rebuilds for a preview.

## Ownership and verification

- Root: model/API contracts, routes, atomic batch decisions and undo tests, integration and actual browser QA.
- NET engine worker: recommendation/auto and bounded short-split proposal modules + meaningful topology tests; root wires callers.
- Frontend worker: spatial multiselect, selection toolbar, recommendation display and auto controls; interaction geometry tests.
- Independent reviewer: final scoped code/test review.

Test unknown IDs/duplicate IDs/stale revisions; batch interacting repairs causing short; rollback and one-step undo; cross-layer hint identity; same-net scratch vs intentional antipad; marker/protected pixel preservation; clean BGA no inferred corruption, damage counts honestly reported. Browser exercise rectangle selection, Shift toggle, batch reject/undo, guarded batch approve and auto summary.
