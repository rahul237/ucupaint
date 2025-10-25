"""
Performance optimization module for Ucupaint
Provides dirty-flag system, update batching, node pooling, and performance monitoring
"""

import bpy
import time
from mathutils import Vector
from collections import defaultdict
from typing import Set, Dict, Optional, Callable, Any, List, Tuple

# Dirty flag constants
class DirtyFlags:
    """Bit flags for tracking what needs updating"""
    NONE = 0
    CONNECTIONS = 1 << 0      # Node connections need updating
    ARRANGEMENT = 1 << 1      # Node positions need rearranging
    UI = 1 << 2               # UI needs refreshing
    SPECIFIC_LAYER = 1 << 3   # Specific layer(s) need updating
    SPECIFIC_MASK = 1 << 4    # Specific mask(s) need updating
    CHANNEL = 1 << 5          # Channel configuration changed
    ALL = (1 << 6) - 1        # All flags set


class PerformanceTracker:
    """
    Tracks dirty state and batches updates to prevent redundant operations
    """

    def __init__(self):
        self.dirty_flags = DirtyFlags.NONE
        self.dirty_layers: Set[int] = set()
        self.dirty_masks: Dict[int, Set[int]] = defaultdict(set)  # layer_idx -> mask_indices
        self.batch_mode = False
        self.batch_depth = 0

    def mark_dirty(self, flag: int, layer_idx: Optional[int] = None, mask_idx: Optional[int] = None):
        """Mark something as needing update"""
        self.dirty_flags |= flag

        if layer_idx is not None:
            self.dirty_layers.add(layer_idx)
            if mask_idx is not None:
                self.dirty_masks[layer_idx].add(mask_idx)

    def begin_batch(self):
        """Start batching updates - don't apply until end_batch"""
        self.batch_depth += 1
        self.batch_mode = True

    def end_batch(self, apply_updates: bool = True):
        """End batch mode and optionally apply pending updates"""
        self.batch_depth = max(0, self.batch_depth - 1)
        if self.batch_depth == 0:
            self.batch_mode = False
            if apply_updates:
                return self.get_pending_updates()
        return None

    def get_pending_updates(self):
        """Get what needs updating and clear dirty state"""
        result = {
            'flags': self.dirty_flags,
            'layers': list(self.dirty_layers),
            'masks': dict(self.dirty_masks)
        }
        self.clear()
        return result

    def clear(self):
        """Clear all dirty flags"""
        self.dirty_flags = DirtyFlags.NONE
        self.dirty_layers.clear()
        self.dirty_masks.clear()

    def is_dirty(self, flag: int) -> bool:
        """Check if a specific flag is set"""
        return (self.dirty_flags & flag) != 0


class UpdateBatcher:
    """
    Debounces property updates using timers to batch rapid changes
    """

    def __init__(self):
        self.pending_updates: Dict[str, float] = {}  # update_type -> scheduled_time
        self.update_callbacks: Dict[str, Callable] = {}
        self.timer_registered = False
        self.default_delay = 0.1  # 100ms default debounce

    def schedule_update(self, update_type: str, callback: Callable, delay: Optional[float] = None):
        """Schedule an update to run after delay seconds"""
        if delay is None:
            delay = self.default_delay

        self.pending_updates[update_type] = time.time() + delay
        self.update_callbacks[update_type] = callback

        if not self.timer_registered:
            bpy.app.timers.register(self._process_updates, first_interval=delay)
            self.timer_registered = True

    def _process_updates(self):
        """Process any updates that are ready"""
        current_time = time.time()
        ready_updates = [k for k, v in self.pending_updates.items() if v <= current_time]

        for update_type in ready_updates:
            callback = self.update_callbacks.get(update_type)
            if callback:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in debounced update '{update_type}': {e}")

            del self.pending_updates[update_type]
            if update_type in self.update_callbacks:
                del self.update_callbacks[update_type]

        # Continue timer if there are pending updates
        if self.pending_updates:
            return 0.05  # Check again in 50ms
        else:
            self.timer_registered = False
            return None

    def cancel_update(self, update_type: str):
        """Cancel a pending update"""
        if update_type in self.pending_updates:
            del self.pending_updates[update_type]
        if update_type in self.update_callbacks:
            del self.update_callbacks[update_type]

    def flush_all(self):
        """Immediately execute all pending updates"""
        for update_type, callback in list(self.update_callbacks.items()):
            try:
                callback()
            except Exception as e:
                print(f"Error flushing update '{update_type}': {e}")

        self.pending_updates.clear()
        self.update_callbacks.clear()
        self.timer_registered = False


class NodePool:
    """
    Pools shader nodes for reuse instead of constant creation/deletion
    """

    def __init__(self, max_pool_size: int = 100):
        self.pools: Dict[str, List[Any]] = defaultdict(list)  # node_type -> [nodes]
        self.max_pool_size = max_pool_size
        self.stats = {'hits': 0, 'misses': 0, 'releases': 0}

    def acquire(self, tree, node_type: str):
        """Get a node from pool or create new one"""
        pool = self.pools.get(node_type, [])

        if pool:
            node = pool.pop()
            node.hide = False
            node.mute = False
            # Move back to visible area
            if node.location.x < -9000:
                node.location = Vector((0, 0))
            self.stats['hits'] += 1
            return node
        else:
            self.stats['misses'] += 1
            return tree.nodes.new(node_type)

    def release(self, node):
        """Return a node to the pool for reuse"""
        node_type = node.bl_idname
        pool = self.pools[node_type]

        # Don't pool too many nodes
        if len(pool) < self.max_pool_size:
            # Hide and move off-screen
            node.hide = True
            node.location = Vector((-10000, -10000))
            pool.append(node)
            self.stats['releases'] += 1
        else:
            # Pool is full, actually delete
            try:
                node.id_data.nodes.remove(node)
            except:
                pass

    def clear_pool(self, tree, node_type: Optional[str] = None):
        """Clear pool and delete nodes"""
        if node_type:
            # Clear specific type
            for node in self.pools.get(node_type, []):
                try:
                    tree.nodes.remove(node)
                except:
                    pass
            self.pools[node_type] = []
        else:
            # Clear all
            for nodes in self.pools.values():
                for node in nodes:
                    try:
                        tree.nodes.remove(node)
                    except:
                        pass
            self.pools.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get pooling statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        return {
            **self.stats,
            'total_requests': total,
            'hit_rate': hit_rate,
            'pool_sizes': {k: len(v) for k, v in self.pools.items()}
        }


class LayerCache:
    """
    Caches frequently accessed layer data to avoid repeated lookups
    """

    def __init__(self):
        self._cache: Dict[Tuple[int, str], Any] = {}
        self._version = 0
        self.stats = {'hits': 0, 'misses': 0}

    def get(self, layer, key: str, getter: Callable):
        """Get cached value or compute and cache it"""
        cache_key = (layer.as_pointer(), self._version, key)

        if cache_key in self._cache:
            self.stats['hits'] += 1
            return self._cache[cache_key]
        else:
            self.stats['misses'] += 1
            value = getter(layer)
            self._cache[cache_key] = value
            return value

    def invalidate(self, layer=None):
        """Invalidate cache for specific layer or all"""
        if layer is None:
            # Invalidate all by incrementing version
            self._version += 1
            self._cache.clear()
        else:
            # Invalidate specific layer
            layer_ptr = layer.as_pointer()
            keys_to_delete = [k for k in self._cache.keys() if k[0] == layer_ptr]
            for key in keys_to_delete:
                del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        return {
            **self.stats,
            'total_requests': total,
            'hit_rate': hit_rate,
            'cache_size': len(self._cache),
            'version': self._version
        }


class PerformanceMonitor:
    """
    Monitors and profiles function performance
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.max_samples = 1000  # Keep last N samples

    def profile(self, name: str):
        """Decorator to profile function execution time"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = time.time() - start
                    self.record_timing(name, elapsed)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper
        return decorator

    def record_timing(self, name: str, elapsed: float):
        """Record a timing sample"""
        timings = self.timings[name]
        timings.append(elapsed)

        # Keep only recent samples
        if len(timings) > self.max_samples:
            timings.pop(0)

        self.call_counts[name] += 1

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if name:
            timings = self.timings.get(name, [])
            if not timings:
                return {}

            return {
                'count': self.call_counts[name],
                'total': sum(timings),
                'mean': sum(timings) / len(timings),
                'min': min(timings),
                'max': max(timings),
                'recent': timings[-10:] if len(timings) > 10 else timings
            }
        else:
            # Return all stats
            return {
                func_name: self.get_stats(func_name)
                for func_name in self.timings.keys()
            }

    def print_stats(self, top_n: int = 10):
        """Print top N slowest functions"""
        stats = []
        for name in self.timings.keys():
            func_stats = self.get_stats(name)
            if func_stats:
                stats.append((name, func_stats['total'], func_stats['mean'], func_stats['count']))

        stats.sort(key=lambda x: x[1], reverse=True)

        print("\n=== Performance Stats (Top {}) ===".format(top_n))
        print(f"{'Function':<40} {'Total (s)':<12} {'Mean (ms)':<12} {'Calls':<10}")
        print("-" * 80)

        for name, total, mean, count in stats[:top_n]:
            print(f"{name:<40} {total:<12.4f} {mean*1000:<12.4f} {count:<10}")

    def reset(self):
        """Reset all statistics"""
        self.timings.clear()
        self.call_counts.clear()


# Global instances (initialized on module load)
_perf_tracker: Optional[PerformanceTracker] = None
_update_batcher: Optional[UpdateBatcher] = None
_node_pool: Optional[NodePool] = None
_layer_cache: Optional[LayerCache] = None
_perf_monitor: Optional[PerformanceMonitor] = None


def get_performance_tracker() -> PerformanceTracker:
    """Get global performance tracker instance"""
    global _perf_tracker
    if _perf_tracker is None:
        _perf_tracker = PerformanceTracker()
    return _perf_tracker


def get_update_batcher() -> UpdateBatcher:
    """Get global update batcher instance"""
    global _update_batcher
    if _update_batcher is None:
        _update_batcher = UpdateBatcher()
    return _update_batcher


def get_node_pool() -> NodePool:
    """Get global node pool instance"""
    global _node_pool
    if _node_pool is None:
        _node_pool = NodePool()
    return _node_pool


def get_layer_cache() -> LayerCache:
    """Get global layer cache instance"""
    global _layer_cache
    if _layer_cache is None:
        _layer_cache = LayerCache()
    return _layer_cache


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _perf_monitor
    if _perf_monitor is None:
        # Check if developer mode is enabled
        try:
            ypup = bpy.context.preferences.addons.get(__package__.split('.')[0])
            enabled = ypup.preferences.developer_mode if ypup else False
        except:
            enabled = False
        _perf_monitor = PerformanceMonitor(enabled=enabled)
    return _perf_monitor


def reset_all_performance_systems():
    """Reset all performance tracking systems"""
    global _perf_tracker, _update_batcher, _node_pool, _layer_cache, _perf_monitor

    if _update_batcher:
        _update_batcher.flush_all()

    _perf_tracker = None
    _update_batcher = None
    _node_pool = None
    _layer_cache = None
    _perf_monitor = None


# Decorator for easy profiling
def profile(name: str):
    """Convenience decorator for profiling"""
    return get_performance_monitor().profile(name)


# Context manager for batch operations
class batch_updates:
    """Context manager for batching updates"""

    def __init__(self, apply_on_exit: bool = True):
        self.apply_on_exit = apply_on_exit
        self.tracker = get_performance_tracker()

    def __enter__(self):
        self.tracker.begin_batch()
        return self.tracker

    def __exit__(self, exc_type, exc_val, exc_tb):
        result = self.tracker.end_batch(apply_updates=self.apply_on_exit)
        if result and self.apply_on_exit:
            # This is where we'd apply the batched updates
            # Will be implemented when integrating with existing code
            pass
        return False


def register():
    """Register performance module"""
    # Initialize global instances
    get_performance_tracker()
    get_update_batcher()
    get_node_pool()
    get_layer_cache()
    get_performance_monitor()

    print("INFO: Ucupaint performance module registered")


def unregister():
    """Unregister performance module"""
    reset_all_performance_systems()
    print("INFO: Ucupaint performance module unregistered")
