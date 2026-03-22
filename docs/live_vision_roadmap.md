# Live Vision Roadmap (Future)

## Goal

Remove the manual `spacebar` inference trigger and make board-state detection run continuously and reliably during live play.

## What Is Needed

1. Continuous inference loop
- Run board inference automatically every frame or every `N` frames.

2. Batched square inference
- Predict all 64 squares in a single model call instead of 64 separate calls.

3. Board-state stabilization (temporal smoothing)
- Require the same inferred board state across multiple consecutive frames before accepting it.

4. Move detection state machine
- Track states such as:
  - stable board
  - board changing / piece in motion
  - board stabilized after move
  - move confirmed

5. Occlusion handling
- Ignore transient frames when a human hand or robot arm blocks the board.

6. Confidence-based filtering
- Use prediction confidence to reject low-confidence square classifications.

7. Post-move confirmation
- Only commit a move after the board has settled and the inferred state is stable.

## Suggested v1 Live Strategy

1. Infer every 2-3 frames
2. Batch all 64 square predictions
3. Require stable board state for a short window (for example 300-700 ms)
4. Detect moves only on unstable -> stable transitions
5. Validate final move with `python-chess`

## Why This Matters

Even with a strong per-square model, live move detection can fail due to:

- hand/arm occlusion
- glare/reflections
- pieces moving mid-frame
- transient misclassifications

The main improvement needed is runtime state stabilization, not just a better model.

