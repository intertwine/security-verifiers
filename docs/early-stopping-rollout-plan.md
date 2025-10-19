# Early Failure Detection Rollout Plan

**Status**: ✅ Phases 1, 2, 4, 5 Complete
**Created**: 2025-10-18
**Completed**: 2025-10-18
**Priority**: Medium
**Actual Effort**: ~2.5 hours (as estimated)

## Overview

Extend the early failure detection system (currently implemented in E1/eval_network_logs.py) to all remaining evaluation scripts and environments. This will prevent costly evaluation runs with misconfigured models or API issues across the entire evaluation suite.

## 🎯 Implementation Summary

**Completed Phases:** 1, 2, 4, 5
**Status:** ✅ Production-ready for E1 and E2
**Time Investment:** 2.5 hours (matched original estimate)

### What Was Delivered

1. **E2 Multi-Turn Evaluation** ([scripts/eval_config_verification.py](../scripts/eval_config_verification.py))
   - Full early stopping integration with async evaluation loop
   - Proper error handling for `EarlyStopError` exceptions
   - Tested and verified with invalid models

2. **E2 Single-Turn Evaluation** ([scripts/eval_config_verification_singleturn.py](../scripts/eval_config_verification_singleturn.py))
   - Nested try-except pattern for proper exception propagation
   - Consistent interface with E1 and E2 multi-turn
   - Tested and verified with invalid models

3. **Makefile Integration**
   - `MAX_CONSECUTIVE_ERRORS` variable (default: 3)
   - Updated `eval-e1` and `eval-e2` targets
   - Help text documentation
   - Tested via `make eval-e2 MODELS="..." MAX_CONSECUTIVE_ERRORS=N`

4. **Comprehensive Documentation**
   - [AGENTS.md](../AGENTS.md) - Updated with examples and environment variables
   - [CLAUDE.md](../CLAUDE.md) - Updated with examples and environment variables
   - [WARP.md](../WARP.md) - Updated with examples and environment variables
   - [E2 README](../environments/sv-env-config-verification/README.md) - New "Early Failure Detection" section
   - [Makefile](../Makefile) - Updated help text

### Key Features

- **Smart Defaults**: Stops after 3 consecutive errors by default
- **Fully Configurable**: `--max-consecutive-errors N` or `MAX_CONSECUTIVE_ERRORS=N`
- **Disableable**: Set to `0` to process all examples
- **Consistent**: Same interface across E1 and E2 (multi-turn & single-turn)
- **Battle-Tested**: Verified with invalid models and edge cases

## Current State

### ✅ Completed
- [x] Core ErrorTracker utility ([scripts/eval_utils.py](../scripts/eval_utils.py))
- [x] Comprehensive test suite ([scripts/eval_utils_test.py](../scripts/eval_utils_test.py))
- [x] Full integration in E1 ([scripts/eval_network_logs.py](../scripts/eval_network_logs.py))
- [x] E2 multi-turn evaluation ([scripts/eval_config_verification.py](../scripts/eval_config_verification.py))
- [x] E2 single-turn evaluation ([scripts/eval_config_verification_singleturn.py](../scripts/eval_config_verification_singleturn.py))
- [x] Makefile integration for E1 and E2
- [x] Model routing updates in all scripts
- [x] Documentation updates (CLAUDE.md, WARP.md, E2 README)

### 🚧 In Progress
- None currently

### 📋 Planned
- [ ] E3-E6 evaluation scripts (when they exist)
- [ ] Advanced features (Phase 6): smart threshold adjustment, error pattern recognition, cost estimation

## Phase 1: E2 Multi-Turn Evaluation (scripts/eval_config_verification.py)

**Complexity**: Medium (async evaluation loop)
**Estimated Time**: 45-60 minutes

### Implementation Steps

1. **Add Command-Line Argument**
   ```python
   parser.add_argument(
       "--max-consecutive-errors",
       type=int,
       default=3,
       help="Stop evaluation after this many consecutive errors (default: 3). "
            "Set to 0 to disable early stopping.",
   )
   ```

2. **Initialize Error Tracker per Model**
   - Location: After client initialization (line ~395)
   - Before the dataset iteration loop
   ```python
   # Initialize error tracker for early stopping
   error_tracker = None
   if args.max_consecutive_errors > 0:
       window_size = max(5, args.max_consecutive_errors)
       error_tracker = ErrorTracker(
           max_consecutive_errors=args.max_consecutive_errors,
           window_size=window_size
       )
   ```

3. **Wrap Multi-Turn Evaluation Call**
   - Location: Inside the dataset loop (line ~444)
   - Wrap the `asyncio.run(run_multiturn_evaluation(...))` call
   ```python
   try:
       # Run multi-turn evaluation
       result = asyncio.run(
           run_multiturn_evaluation(
               client,
               env,
               effective_model,
               question,
               answer,
               max_turns=args.max_turns,
               temperature=args.temperature,
               max_tokens=args.max_tokens,
               fixture_path=fixture_path,
           )
       )

       # Check if result contains an error
       if "error" in result:
           if error_tracker:
               error_tracker.record_error(result["error"], index=i)
       else:
           if error_tracker:
               error_tracker.record_success()

   except EarlyStopError as e:
       print(f"\n✗ Early stopping triggered for {model}:")
       print(f"  {e}")
       if error_tracker:
           stats = error_tracker.get_stats()
           print(f"  Stats: {stats['total_errors']}/{stats['total_samples']} samples failed")
       break  # Exit the dataset loop
   ```

4. **Update Metadata**
   - Add `max_consecutive_errors` to metadata dict (line ~403)

5. **Testing Checklist**
   - [ ] Test with invalid model (should stop after 3 errors)
   - [ ] Test with valid model (should complete normally)
   - [ ] Test with `--max-consecutive-errors 0` (should never stop)
   - [ ] Test with `--max-consecutive-errors 1` (very aggressive stopping)
   - [ ] Verify async flow doesn't interfere with error tracking

### Challenges & Considerations

- **Async Complexity**: The multi-turn evaluation uses async/await. Need to ensure error tracking doesn't interfere with async flow.
- **Tool Call Errors**: Tool-based environments might have different error patterns (tool execution failures vs API failures). Need to decide what counts as a "failure" worthy of stopping.
- **Partial Successes**: If a model calls tools successfully but produces a bad final answer, should that count as success or failure? Recommendation: Only track API/completion errors, not reward quality.

## Phase 2: E2 Single-Turn Evaluation (scripts/eval_config_verification_singleturn.py)

**Complexity**: Low (similar to E1)
**Estimated Time**: 30 minutes

### Implementation Steps

Same pattern as E1, simplified because no async:

1. Add `--max-consecutive-errors` argument
2. Initialize ErrorTracker before dataset loop
3. Wrap the `client.chat.completions.create()` call
4. Track success/error appropriately
5. Catch and handle `EarlyStopError`
6. Update metadata

### Testing Checklist
- [ ] Same as E1 tests
- [ ] Verify tool inclusion doesn't affect error tracking

## Phase 3: E3-E6 Evaluation Scripts

**Complexity**: TBD (depends on environment implementation status)
**Estimated Time**: 30-45 minutes per environment

### Current Status
- E3 (code-vulnerability): Alpha/Preview - likely has basic eval script
- E4 (phishing-detection): Alpha/Preview - likely has basic eval script
- E5 (redteam-attack): Alpha/Preview - may have eval script
- E6 (redteam-defense): Alpha/Preview - may have eval script

### Implementation Strategy

**For Each Environment:**

1. **Discovery Phase**
   - Check if eval script exists in `scripts/`
   - Identify script name pattern (e.g., `eval_code_vulnerability.py`)
   - Review script structure and complexity

2. **Integration Phase**
   - Follow E1 pattern for SingleTurnEnv
   - Follow E2 pattern for ToolEnv or MultiTurnEnv
   - Add error tracking around main evaluation loop
   - Update metadata and documentation

3. **Testing Phase**
   - Test with invalid models
   - Test with valid models
   - Verify environment-specific behaviors (tools, multi-turn, etc.)

### Deferred Until Environments Are Production-Ready
- E3-E6 are currently WIP/Alpha
- Wait until each environment reaches production-ready status
- Prioritize based on usage patterns

## Phase 4: Makefile Integration

**Complexity**: Low
**Estimated Time**: 20 minutes

### Implementation Steps

1. **Add Make Variable**
   ```makefile
   # Default error threshold for evaluations
   MAX_CONSECUTIVE_ERRORS ?= 3
   ```

2. **Update eval-e1 Target**
   ```makefile
   eval-e1: venv
       @if [ -z "$(MODELS)" ]; then \
           $(ECHO) "$(RED)Error: Provide MODELS=\"gpt-5-mini,gpt-4.1-mini\"$(NC)"; \
           exit 1; \
       fi
       @N=$${N:-10}; \
       MAX_ERRORS=$${MAX_CONSECUTIVE_ERRORS:-3}; \
       $(ECHO) "$(YELLOW)Evaluating E1 (network-logs) for models: $(MODELS) (N=$$N, max_errors=$$MAX_ERRORS)$(NC)"; \
       $(ACTIVATE) && uv run python scripts/eval_network_logs.py \
           --models "$(MODELS)" \
           --num-examples $$N \
           --max-consecutive-errors $$MAX_ERRORS
   ```

3. **Update eval-e2 Target** (similar pattern)

4. **Update Help Text**
   ```makefile
   @$(ECHO) "  make eval-e1 MODELS=\"...\" N=10 MAX_CONSECUTIVE_ERRORS=3"
   @$(ECHO) "    MAX_CONSECUTIVE_ERRORS: Error threshold (default: 3, 0 to disable)"
   ```

5. **Update Documentation**
   - Add examples to CLAUDE.md
   - Add examples to WARP.md
   - Add to README.md

### Testing Checklist
- [ ] Test default behavior (MAX_CONSECUTIVE_ERRORS=3)
- [ ] Test custom threshold: `make eval-e1 MODELS="..." MAX_CONSECUTIVE_ERRORS=5`
- [ ] Test disabled: `make eval-e1 MODELS="..." MAX_CONSECUTIVE_ERRORS=0`
- [ ] Verify backwards compatibility (old command syntax still works)

## Phase 5: Documentation & Communication

**Complexity**: Low
**Estimated Time**: 30 minutes

### Updates Required

1. **README.md**
   - Add section on early failure detection (already done for E1)
   - Extend to cover all environments once integrated
   - Add troubleshooting guide

2. **CLAUDE.md**
   - Update quick commands with MAX_CONSECUTIVE_ERRORS examples
   - Add to "Common vars" section

3. **WARP.md**
   - Mirror CLAUDE.md updates

4. **Environment-Specific READMEs**
   - `environments/sv-env-network-logs/README.md` (already updated)
   - `environments/sv-env-config-verification/README.md` (update after Phase 1)
   - E3-E6 READMEs (update as they become production-ready)

5. **New Documentation**
   - Create `docs/evaluation-guide.md` with best practices
   - Include section on early stopping and when to adjust thresholds
   - Add common error patterns and how to diagnose them

### Communication Plan
- Announce in project updates when each phase is complete
- Add to changelog
- Update any external documentation or blog posts

## Phase 6: Advanced Features (Optional/Future)

**Complexity**: Medium
**Estimated Time**: 2-3 hours

### Potential Enhancements

1. **Smart Threshold Adjustment**
   - Automatically increase threshold for expensive models
   - Decrease threshold for cheap models
   - Configuration via model-specific settings

2. **Error Pattern Recognition**
   - Detect specific error types (auth, rate limit, invalid model)
   - Provide targeted error messages and fixes
   - Auto-retry for transient errors (network issues)

3. **Cost Estimation**
   - Track estimated cost per sample
   - Warn when projected costs exceed threshold
   - Integrate with OpenAI/OpenRouter cost APIs

4. **Progress Reporting**
   - Live progress bar with error rate
   - ETA based on current throughput
   - Option to pause/resume evaluations

5. **Error Recovery**
   - Checkpoint progress and resume from last good sample
   - Save partial results even when early stopping
   - Option to skip failed samples and continue

6. **Integration with Weave**
   - Log error tracking stats to Weave
   - Visualize error rates over time
   - Alert on anomalous error patterns

## Implementation Checklist

### Phase 1: E2 Multi-Turn (Priority: High) ✅ COMPLETED
- [x] Add --max-consecutive-errors argument
- [x] Initialize ErrorTracker
- [x] Integrate with async evaluation loop
- [x] Handle EarlyStopError
- [x] Update metadata
- [x] Test with invalid model
- [x] Test threshold variations
- [x] Update documentation

### Phase 2: E2 Single-Turn (Priority: High) ✅ COMPLETED
- [x] Add --max-consecutive-errors argument
- [x] Initialize ErrorTracker
- [x] Wrap completion calls
- [x] Handle EarlyStopError (nested try-except for proper exception handling)
- [x] Update metadata
- [x] Test with invalid model
- [x] Update documentation

### Phase 3: E3-E6 (Priority: Medium - Deferred)
- [ ] E3: Assess readiness and implementation needs
- [ ] E4: Assess readiness and implementation needs
- [ ] E5: Assess readiness and implementation needs
- [ ] E6: Assess readiness and implementation needs

### Phase 4: Makefile (Priority: Medium) ✅ COMPLETED
- [x] Add MAX_CONSECUTIVE_ERRORS variable
- [x] Update eval-e1 target
- [x] Update eval-e2 target
- [x] Update help text
- [x] Test all variations
- [x] Document in CLAUDE.md
- [x] Document in WARP.md

### Phase 5: Documentation (Priority: High) ✅ COMPLETED
- [x] Update CLAUDE.md with new flags and examples
- [x] Update WARP.md with new flags and examples
- [x] Update E2 environment README with early stopping section
- [x] Document in Makefile help text
- Note: README.md and docs/evaluation-guide.md updates deferred (not critical)

### Phase 6: Advanced Features (Priority: Low - Future)
- [ ] Design smart threshold system
- [ ] Implement error pattern recognition
- [ ] Add cost estimation
- [ ] Build progress reporting
- [ ] Create error recovery system
- [ ] Integrate with Weave logging

## Risk Assessment

### Low Risk
- ✅ Phase 1-2: Similar to E1, well-understood patterns
- ✅ Phase 4: Simple Makefile changes
- ✅ Phase 5: Documentation only

### Medium Risk
- ⚠️ Phase 1 async integration: Needs careful testing to ensure no deadlocks
- ⚠️ Phase 3: Unknown complexity until environments are production-ready

### High Risk
- ❌ Phase 6: Significant scope, may interfere with existing systems

## Success Criteria

### Phase 1-2 Complete ✅
- [x] E2 evaluation stops after N consecutive errors
- [x] No regressions in existing functionality
- [x] All tests pass
- [x] Documentation updated
- **Verification**: Tested with invalid models; early stopping triggers correctly after threshold

### Phase 4 Complete ✅
- [x] Make commands support MAX_CONSECUTIVE_ERRORS
- [x] Backwards compatible (default value preserves existing behavior)
- [x] Help text updated
- **Verification**: `make eval-e2 MODELS="invalid" MAX_CONSECUTIVE_ERRORS=2` works correctly

### Full Rollout Complete (E1 & E2) ✅
- [x] All production environments (E1, E2) support early stopping
- [x] Consistent behavior across all eval scripts
- [x] Comprehensive documentation (CLAUDE.md, WARP.md, AGENTS.md, E2 README)
- **Next**: E3-E6 when they reach production-ready status

## Timeline

**Original Estimate:**
- Phase 1: 1 hour (E2 multi-turn)
- Phase 2: 30 minutes (E2 single-turn)
- Phase 4: 30 minutes (Makefile)
- Phase 5: 30 minutes (Documentation)
- **Total: 2.5 hours for critical path**

**Actual Time Spent:** ✅
- Phase 1: ~45 minutes (E2 multi-turn integration and testing)
- Phase 2: ~40 minutes (E2 single-turn integration, testing, and fix for nested exception handling)
- Phase 4: ~20 minutes (Makefile updates)
- Phase 5: ~45 minutes (Documentation across CLAUDE.md, WARP.md, AGENTS.md, E2 README)
- **Total: ~2.5 hours** (matched estimate)

**Deferred for Future:**
- Phase 3 (E3-E6): 2-3 hours (when environments reach production status)
- Phase 6 (Advanced Features): 2-3 hours (future enhancements)

## Dependencies

### Required Before Implementation
- ✅ Core ErrorTracker utility (completed)
- ✅ Test suite (completed)
- ✅ E1 integration as reference (completed)

### Completed Dependencies
- ✅ Phase 1: E2 multi-turn async patterns understood and integrated
- ✅ Phase 2: E2 single-turn script structure integrated
- ✅ Phase 4: Makefile updates applied
- ✅ Phase 5: Documentation updated across all files

### Outstanding Dependencies
- ⏳ Phase 3: E3-E6 production readiness (deferred)
- ⏳ Phase 6: Advanced requirements gathering (future work)

## Notes & Decisions

### Design Decisions
1. **Default threshold of 3**: Balances cost savings with tolerance for transient errors ✅
2. **Track completion errors only**: Don't stop on low reward scores (that's a quality issue, not a config issue) ✅
3. **Per-model tracking**: Reset error tracker for each model in batch runs ✅
4. **No automatic retry**: Keep logic simple; users can re-run if needed ✅

### Implementation Insights

#### Phase 2 Challenge: Nested Exception Handling
**Issue**: When `error_tracker.record_error()` raises `EarlyStopError` inside an `except` block, the exception wasn't being caught.

**Solution**: Implemented nested try-except pattern:
```python
try:
    try:
        # API call
        resp = client.chat.completions.create(**kwargs)
        if error_tracker:
            error_tracker.record_success()
    except Exception as e:
        # Track error (may raise EarlyStopError)
        if error_tracker:
            error_tracker.record_error(str(e), index=i)
except EarlyStopError as e:
    # Handle early stopping
    print(f"✗ Early stopping triggered...")
    break
```

This pattern ensures that `EarlyStopError` raised from within the inner exception handler is properly caught by the outer handler.

#### Testing Approach
- Used invalid model names to trigger consecutive API errors
- Verified threshold behavior with different values (2, 3, 5)
- Tested via both direct script invocation and Makefile
- Confirmed metadata includes `max_consecutive_errors` setting

### Open Questions (Resolved)
1. Should tool execution failures count toward error threshold?
   - **Decision**: ✅ No, only API/completion errors. Tool failures are environment-specific and don't indicate model misconfiguration.
   - **Implementation**: Tool errors in E2 return error results but don't trigger early stopping.

2. Should we checkpoint progress for resume capability?
   - **Decision**: ✅ Deferred to Phase 6. Current scope is early stopping only; checkpointing is a separate feature.

3. Should error threshold be configurable per-model in batch runs?
   - **Decision**: ✅ No, use single threshold for simplicity. Users can run models separately if different thresholds are needed.

4. How to handle rate limiting errors (429)?
   - **Decision**: ⏳ Deferred to Phase 6. For now, rate limit errors count toward the threshold (user should adjust limits or wait).

## References

- Core implementation: [scripts/eval_utils.py](../scripts/eval_utils.py)
- Test suite: [scripts/eval_utils_test.py](../scripts/eval_utils_test.py)
- E1 integration: [scripts/eval_network_logs.py](../scripts/eval_network_logs.py)
- E2 multi-turn: [scripts/eval_config_verification.py](../scripts/eval_config_verification.py)
- E2 single-turn: [scripts/eval_config_verification_singleturn.py](../scripts/eval_config_verification_singleturn.py)

---

**Last Updated**: 2025-10-18
**Status**: Phases 1, 2, 4, and 5 completed. E2 multi-turn and single-turn evaluations now support early stopping.
**Next Review**: When E3-E6 reach production-ready status
