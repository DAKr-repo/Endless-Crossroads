#!/usr/bin/env python3
"""
burnwillow_stress_test.py - Thermal Budget Audit for Zone Generation
=====================================================================

MISSION: Procedural Generation Stress Test
TARGET: Raspberry Pi 5 (CM5)
THERMAL LIMIT: 80°C
MEMORY LIMIT: 50MB final footprint

TEST PROTOCOL:
    1. Generate 50 zones continuously
    2. Track memory usage (detect leaks)
    3. Track generation time (detect slowdowns)
    4. Monitor thermal impact
    5. Report PASS/FAIL with detailed metrics

ARCHITECTURE:
    - Uses tracemalloc for memory profiling
    - Uses time.perf_counter for high-resolution timing
    - Uses vcgencmd for thermal monitoring
    - Explicit cleanup and gc.collect() per iteration

Version: 1.0
"""

import sys
import time
import gc
import tracemalloc
import subprocess
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

# Import zone generator
try:
    from codex.games.burnwillow.zone1 import TangleAdapter
    from codex.spatial.map_engine import CodexMapEngine, ContentInjector
except ImportError:
    print("ERROR: Cannot import TangleAdapter/CodexMapEngine")
    print("Ensure burnwillow zone1 and spatial map_engine modules are available.")
    sys.exit(1)


# =============================================================================
# METRICS DATA STRUCTURES
# =============================================================================

@dataclass
class GenerationMetrics:
    """Per-zone generation metrics."""
    zone_id: int
    generation_time_ms: float
    memory_current_mb: float
    memory_peak_mb: float
    total_rooms: int


@dataclass
class StressTestReport:
    """Complete stress test results."""
    zones_generated: int
    avg_generation_time_ms: float
    min_generation_time_ms: float
    max_generation_time_ms: float

    total_cpu_time_s: float

    peak_memory_mb: float
    final_memory_mb: float
    memory_leak_detected: bool

    temp_before_c: float
    temp_after_c: float
    thermal_delta_c: float

    verdict: str  # "PASS" or "FAIL"
    failure_reasons: List[str] = field(default_factory=list)

    zone_metrics: List[GenerationMetrics] = field(default_factory=list)


# =============================================================================
# THERMAL MONITORING
# =============================================================================

def get_cpu_temperature() -> float:
    """
    Read CPU temperature via vcgencmd.

    Returns:
        Temperature in Celsius, or -1.0 if unavailable
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2
        )
        # Output format: temp=53.8'C
        temp_str = result.stdout.strip().split('=')[1].replace("'C", "")
        return float(temp_str)
    except Exception as e:
        print(f"WARNING: Could not read CPU temperature: {e}")
        return -1.0


# =============================================================================
# STRESS TEST EXECUTION
# =============================================================================

def run_stress_test(zone_count: int = 50, depth: int = 4) -> StressTestReport:
    """
    Execute the zone generation stress test.

    Args:
        zone_count: Number of zones to generate
        depth: BSP depth for zone generation

    Returns:
        StressTestReport with complete metrics
    """
    print("╔══════════════════════════════════════════════════════════╗")
    print("║      THERMAL BUDGET AUDIT: ZONE GENERATION               ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Test Parameters:                                        ║")
    print(f"║    - Zones to Generate: {zone_count:3d}                            ║")
    print(f"║    - BSP Depth: {depth}                                         ║")
    print(f"║    - Target Platform: Raspberry Pi 5 (CM5)               ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Record initial thermal state
    temp_before = get_cpu_temperature()
    print(f"[THERMAL] Initial CPU Temperature: {temp_before:.1f}°C")
    print()

    # Start memory profiling
    tracemalloc.start()

    # Initialize generator components
    adapter = TangleAdapter()

    # Metrics storage
    zone_metrics: List[GenerationMetrics] = []
    generation_times: List[float] = []

    # Start CPU timer
    cpu_time_start = time.perf_counter()

    # ═══════════════════════════════════════════════════════════════
    # MAIN TEST LOOP
    # ═══════════════════════════════════════════════════════════════

    print(f"[GENERATION] Starting {zone_count} zone generation test...")
    print(f"{'Zone':>5}  {'Time (ms)':>10}  {'Mem (MB)':>10}  {'Peak (MB)':>10}  {'Rooms':>6}")
    print("-" * 60)

    for i in range(zone_count):
        # Get baseline memory before generation
        gc.collect()  # Force garbage collection
        tracemalloc.reset_peak()

        # Capture baseline
        mem_before, _ = tracemalloc.get_traced_memory()

        # Generate zone
        gen_start = time.perf_counter()
        map_engine = CodexMapEngine(seed=i)
        graph = map_engine.generate(
            width=50, height=50, min_room_size=5, max_depth=depth,
            system_id="burnwillow",
        )
        injector = ContentInjector(adapter)
        populated_rooms = injector.populate_all(graph)
        zone = {
            "seed": graph.seed, "total_rooms": len(populated_rooms),
            "start_room_id": graph.start_room_id,
        }
        gen_end = time.perf_counter()

        # Capture metrics
        gen_time_ms = (gen_end - gen_start) * 1000
        mem_current, mem_peak = tracemalloc.get_traced_memory()

        # Convert to MB
        mem_current_mb = mem_current / (1024 * 1024)
        mem_peak_mb = mem_peak / (1024 * 1024)

        # Store metrics
        metrics = GenerationMetrics(
            zone_id=i,
            generation_time_ms=gen_time_ms,
            memory_current_mb=mem_current_mb,
            memory_peak_mb=mem_peak_mb,
            total_rooms=zone['total_rooms']
        )
        zone_metrics.append(metrics)
        generation_times.append(gen_time_ms)

        # Progress report
        if i % 5 == 0 or i < 5:
            print(f"{i:5d}  {gen_time_ms:10.2f}  {mem_current_mb:10.2f}  {mem_peak_mb:10.2f}  {zone['total_rooms']:6d}")

        # Explicit cleanup
        del zone
        gc.collect()

    print("-" * 60)

    # ═══════════════════════════════════════════════════════════════
    # POST-TEST ANALYSIS
    # ═══════════════════════════════════════════════════════════════

    # Stop CPU timer
    cpu_time_end = time.perf_counter()
    total_cpu_time = cpu_time_end - cpu_time_start

    # Final memory state
    gc.collect()
    final_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    final_memory_mb = final_memory / (1024 * 1024)
    peak_memory_mb = peak_memory / (1024 * 1024)

    # Memory leak detection
    # If final memory > 50MB after cleanup: likely leak
    memory_leak_detected = final_memory_mb > 50.0

    # Timing statistics
    avg_time = sum(generation_times) / len(generation_times)
    min_time = min(generation_times)
    max_time = max(generation_times)

    # Record final thermal state
    print()
    print("[THERMAL] Waiting 2 seconds for thermal stabilization...")
    time.sleep(2)
    temp_after = get_cpu_temperature()
    thermal_delta = temp_after - temp_before if temp_before > 0 else 0

    # ═══════════════════════════════════════════════════════════════
    # VERDICT DETERMINATION
    # ═══════════════════════════════════════════════════════════════

    failure_reasons = []

    # Thermal check
    if temp_after >= 80.0:
        failure_reasons.append(f"Thermal limit exceeded: {temp_after:.1f}°C >= 80°C")

    # Memory leak check
    if memory_leak_detected:
        failure_reasons.append(f"Memory leak detected: {final_memory_mb:.1f} MB > 50 MB threshold")

    # Performance degradation check (last 10 zones should not be >50% slower than first 10)
    first_10_avg = sum(generation_times[:10]) / 10
    last_10_avg = sum(generation_times[-10:]) / 10
    degradation_ratio = last_10_avg / first_10_avg

    if degradation_ratio > 1.5:
        failure_reasons.append(f"Performance degradation: {degradation_ratio:.2f}x slowdown detected")

    verdict = "PASS" if len(failure_reasons) == 0 else "FAIL"

    # Build report
    report = StressTestReport(
        zones_generated=zone_count,
        avg_generation_time_ms=avg_time,
        min_generation_time_ms=min_time,
        max_generation_time_ms=max_time,
        total_cpu_time_s=total_cpu_time,
        peak_memory_mb=peak_memory_mb,
        final_memory_mb=final_memory_mb,
        memory_leak_detected=memory_leak_detected,
        temp_before_c=temp_before,
        temp_after_c=temp_after,
        thermal_delta_c=thermal_delta,
        verdict=verdict,
        failure_reasons=failure_reasons,
        zone_metrics=zone_metrics
    )

    return report


# =============================================================================
# REPORT RENDERING
# =============================================================================

def print_report(report: StressTestReport):
    """
    Print formatted stress test report.

    Args:
        report: StressTestReport to render
    """
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║        THERMAL BUDGET AUDIT: ZONE GENERATION             ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Zones Generated: {report.zones_generated:<42d} ║")
    print(f"║  Avg Generation Time: {report.avg_generation_time_ms:>6.1f} ms                     ║")
    print(f"║  Min Generation Time: {report.min_generation_time_ms:>6.1f} ms                     ║")
    print(f"║  Max Generation Time: {report.max_generation_time_ms:>6.1f} ms                     ║")
    print(f"║  Total CPU Time: {report.total_cpu_time_s:>6.2f} s                          ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Peak Memory: {report.peak_memory_mb:>6.2f} MB                             ║")
    print(f"║  Final Memory: {report.final_memory_mb:>6.2f} MB                            ║")

    leak_status = "YES" if report.memory_leak_detected else "NO"
    print(f"║  Memory Leak: {leak_status:<42s} ║")

    print("╠══════════════════════════════════════════════════════════╣")

    if report.temp_before_c > 0:
        print(f"║  Temp Before: {report.temp_before_c:>6.1f}°C                              ║")
        print(f"║  Temp After: {report.temp_after_c:>6.1f}°C                               ║")
        print(f"║  Thermal Delta: +{report.thermal_delta_c:>5.1f}°C                            ║")
    else:
        print("║  Temp Before: N/A                                    ║")
        print("║  Temp After: N/A                                     ║")
        print("║  Thermal Delta: N/A                                  ║")

    print("╠══════════════════════════════════════════════════════════╣")

    # Verdict
    if report.verdict == "PASS":
        print("║  VERDICT: PASS ✓                                        ║")
    else:
        print("║  VERDICT: FAIL ✗                                        ║")

    print("╚══════════════════════════════════════════════════════════╝")

    # Failure reasons (if any)
    if report.failure_reasons:
        print()
        print("FAILURE REASONS:")
        for reason in report.failure_reasons:
            print(f"  ✗ {reason}")

    # Performance analysis
    print()
    print("PERFORMANCE ANALYSIS:")

    # Calculate first 10 vs last 10 average
    first_10_times = [m.generation_time_ms for m in report.zone_metrics[:10]]
    last_10_times = [m.generation_time_ms for m in report.zone_metrics[-10:]]

    first_10_avg = sum(first_10_times) / len(first_10_times)
    last_10_avg = sum(last_10_times) / len(last_10_times)
    degradation_ratio = last_10_avg / first_10_avg

    print(f"  - First 10 zones avg: {first_10_avg:.2f} ms")
    print(f"  - Last 10 zones avg: {last_10_avg:.2f} ms")
    print(f"  - Degradation ratio: {degradation_ratio:.2f}x")

    if degradation_ratio < 1.2:
        print("  ✓ Performance remains stable across test")
    elif degradation_ratio < 1.5:
        print("  ⚠ Minor performance degradation detected")
    else:
        print("  ✗ Significant performance degradation detected")

    # Memory growth analysis
    first_10_mem = [m.memory_current_mb for m in report.zone_metrics[:10]]
    last_10_mem = [m.memory_current_mb for m in report.zone_metrics[-10:]]

    first_10_mem_avg = sum(first_10_mem) / len(first_10_mem)
    last_10_mem_avg = sum(last_10_mem) / len(last_10_mem)
    mem_growth = last_10_mem_avg - first_10_mem_avg

    print()
    print(f"  - First 10 zones avg memory: {first_10_mem_avg:.2f} MB")
    print(f"  - Last 10 zones avg memory: {last_10_mem_avg:.2f} MB")
    print(f"  - Memory growth: {mem_growth:+.2f} MB")

    if mem_growth < 5.0:
        print("  ✓ Memory footprint stable (no significant leak)")
    elif mem_growth < 20.0:
        print("  ⚠ Minor memory growth detected (monitor for leaks)")
    else:
        print("  ✗ Significant memory growth (likely leak)")


# =============================================================================
# RECOMMENDATIONS ENGINE
# =============================================================================

def print_recommendations(report: StressTestReport):
    """
    Print optimization recommendations based on test results.

    Args:
        report: StressTestReport to analyze
    """
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                  RECOMMENDATIONS                         ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    recommendations = []

    # Thermal recommendations
    if report.temp_after_c >= 80.0:
        recommendations.append({
            "severity": "CRITICAL",
            "issue": "Thermal throttle point reached",
            "recommendation": "Implement batch generation with cooldown periods. "
                             "Consider async offloading of generation to prevent thermal spikes. "
                             "Add thermal monitoring to codex_cortex.py integration."
        })
    elif report.temp_after_c >= 75.0:
        recommendations.append({
            "severity": "WARNING",
            "issue": f"Approaching thermal limit ({report.temp_after_c:.1f}°C)",
            "recommendation": "Add thermal throttling logic. "
                             "Reduce concurrent generation operations. "
                             "Consider zone caching to reduce regeneration."
        })
    elif report.thermal_delta_c > 10.0:
        recommendations.append({
            "severity": "INFO",
            "issue": f"Significant thermal delta (+{report.thermal_delta_c:.1f}°C)",
            "recommendation": "Monitor thermal impact in production. "
                             "Consider limiting consecutive zone generations."
        })

    # Memory leak recommendations
    if report.memory_leak_detected:
        recommendations.append({
            "severity": "CRITICAL",
            "issue": f"Memory leak detected ({report.final_memory_mb:.1f} MB final)",
            "recommendation": "Profile with tracemalloc to identify unreleased objects. "
                             "Check for circular references in DungeonGraph or RoomNode. "
                             "Ensure ContentInjector is releasing references properly. "
                             "Consider implementing __del__ methods or weakref."
        })

    # Performance degradation recommendations
    first_10_avg = sum(m.generation_time_ms for m in report.zone_metrics[:10]) / 10
    last_10_avg = sum(m.generation_time_ms for m in report.zone_metrics[-10:]) / 10
    degradation = last_10_avg / first_10_avg

    if degradation > 1.5:
        recommendations.append({
            "severity": "WARNING",
            "issue": f"Performance degradation ({degradation:.2f}x slowdown)",
            "recommendation": "Profile with cProfile to identify bottleneck. "
                             "Check for algorithmic complexity issues (O(n²) patterns). "
                             "Verify RNG seeding is not creating hash collisions. "
                             "Consider caching room templates."
        })

    # Generation time recommendations
    if report.avg_generation_time_ms > 100:
        recommendations.append({
            "severity": "INFO",
            "issue": f"Slow average generation time ({report.avg_generation_time_ms:.1f} ms)",
            "recommendation": "Profile BSP algorithm and room population logic. "
                             "Consider pre-generating zone templates during startup. "
                             "Implement async generation for non-blocking UX."
        })

    # Peak memory recommendations
    if report.peak_memory_mb > 100:
        recommendations.append({
            "severity": "WARNING",
            "issue": f"High peak memory ({report.peak_memory_mb:.1f} MB)",
            "recommendation": "Optimize data structures (use __slots__ in dataclasses). "
                             "Reduce intermediate object creation in BSP algorithm. "
                             "Consider streaming zone generation instead of full materialization."
        })

    # Print recommendations
    if recommendations:
        for rec in recommendations:
            severity_marker = {
                "CRITICAL": "✗",
                "WARNING": "⚠",
                "INFO": "ℹ"
            }.get(rec["severity"], "•")

            print(f"{severity_marker} [{rec['severity']}] {rec['issue']}")
            print(f"  → {rec['recommendation']}")
            print()
    else:
        print("✓ No optimization recommendations. System performance is excellent.")
        print()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for stress test."""
    print()
    print("=" * 60)
    print("BURNWILLOW ZONE GENERATION STRESS TEST")
    print("=" * 60)
    print()

    # Run stress test
    try:
        report = run_stress_test(zone_count=50, depth=4)
    except Exception as e:
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║                   TEST FAILED                            ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Print report
    print_report(report)

    # Print recommendations
    print_recommendations(report)

    # Exit with appropriate code
    exit_code = 0 if report.verdict == "PASS" else 1

    print("=" * 60)
    print(f"TEST COMPLETE: {report.verdict}")
    print("=" * 60)
    print()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
