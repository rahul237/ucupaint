"""
Integration helpers for performance optimizations
Provides easy-to-use wrappers for existing code to adopt performance features
"""

import bpy
from functools import wraps
from typing import Callable, Optional
from .performance import (
    get_performance_tracker,
    get_update_batcher,
    get_node_pool,
    get_layer_cache,
    get_performance_monitor,
    batch_updates,
    DirtyFlags,
    profile
)
from .ui_performance import (
    get_ui_update_manager,
    schedule_ui_update,
    mark_layer_dirty,
    mark_channel_dirty,
    mark_mask_dirty,
    request_full_ui_update
)


def optimized_update_callback(update_type: str = 'generic', debounce_delay: float = 0.1):
    """
    Decorator to optimize property update callbacks

    Usage:
        @optimized_update_callback('layer_blend')
        def update_layer_blend(self, context):
            # Your update logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, context):
            tracker = get_performance_tracker()

            # Skip if in batch mode
            if tracker.batch_mode:
                # Just mark dirty, don't execute
                tracker.mark_dirty(DirtyFlags.CONNECTIONS)
                return None

            # Use debouncing for frequent updates
            batcher = get_update_batcher()

            def do_update():
                return func(self, context)

            batcher.schedule_update(f'{update_type}_{id(self)}', do_update, debounce_delay)
            return None

        return wrapper
    return decorator


def smart_reconnect(reconnect_func: Callable):
    """
    Wrapper for reconnect functions to use dirty flags

    Usage:
        @smart_reconnect
        def reconnect_layer_nodes(layer):
            # Your reconnect logic
            pass
    """
    @wraps(reconnect_func)
    def wrapper(*args, **kwargs):
        tracker = get_performance_tracker()

        # Skip if halted or in batch mode
        if tracker.batch_mode:
            # Mark as needing reconnect
            tracker.mark_dirty(DirtyFlags.CONNECTIONS)
            return

        # Profile the reconnect operation
        monitor = get_performance_monitor()
        func_name = f'reconnect_{reconnect_func.__name__}'

        with monitor.profile(func_name):
            return reconnect_func(*args, **kwargs)

    return wrapper


def smart_rearrange(rearrange_func: Callable):
    """
    Wrapper for rearrange functions to use dirty flags

    Usage:
        @smart_rearrange
        def rearrange_layer_nodes(layer):
            # Your rearrange logic
            pass
    """
    @wraps(rearrange_func)
    def wrapper(*args, **kwargs):
        tracker = get_performance_tracker()

        # Skip if halted or in batch mode
        if tracker.batch_mode:
            # Mark as needing rearrange
            tracker.mark_dirty(DirtyFlags.ARRANGEMENT)
            return

        # Profile the rearrange operation
        monitor = get_performance_monitor()
        func_name = f'rearrange_{rearrange_func.__name__}'

        with monitor.profile(func_name):
            return rearrange_func(*args, **kwargs)

    return wrapper


def cached_layer_operation(cache_key: str):
    """
    Decorator to cache layer operations

    Usage:
        @cached_layer_operation('layer_tree')
        def get_layer_tree(layer):
            # Expensive operation
            return tree
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(layer, *args, **kwargs):
            cache = get_layer_cache()

            def getter(l):
                return func(l, *args, **kwargs)

            return cache.get(layer, cache_key, getter)

        return wrapper
    return decorator


def pooled_node_creation(tree, node_type: str):
    """
    Create a node using the pool instead of tree.nodes.new()

    Usage:
        node = pooled_node_creation(tree, 'ShaderNodeMixRGB')
    """
    pool = get_node_pool()
    return pool.acquire(tree, node_type)


def pooled_node_deletion(node):
    """
    Return a node to the pool instead of deleting

    Usage:
        pooled_node_deletion(node)
    """
    pool = get_node_pool()
    pool.release(node)


class BatchUpdateContext:
    """
    Context manager for batching multiple operations

    Usage:
        with BatchUpdateContext():
            # Multiple operations that would normally trigger updates
            layer.blend_type = 'MIX'
            layer.opacity = 0.5
            # ... more changes
        # Updates applied here automatically
    """

    def __init__(self, apply_on_exit: bool = True):
        self.apply_on_exit = apply_on_exit
        self.tracker = get_performance_tracker()
        self.batcher = get_update_batcher()

    def __enter__(self):
        self.tracker.begin_batch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        updates = self.tracker.end_batch(apply_updates=self.apply_on_exit)

        if updates and self.apply_on_exit:
            self._apply_batched_updates(updates)

        return False

    def _apply_batched_updates(self, updates):
        """Apply all batched updates"""
        flags = updates['flags']

        # Import here to avoid circular dependency
        from . import node_connections, node_arrangements

        # Apply specific layer updates
        for layer_idx in updates['layers']:
            try:
                # Get the yp tree
                from .common import get_active_ypaint_node
                node = get_active_ypaint_node()
                if node:
                    yp = node.node_tree.yp
                    if layer_idx < len(yp.layers):
                        layer = yp.layers[layer_idx]

                        if flags & DirtyFlags.CONNECTIONS:
                            node_connections.reconnect_layer_nodes(layer)

                        if flags & DirtyFlags.ARRANGEMENT:
                            node_arrangements.rearrange_layer_nodes(layer)

                        if flags & DirtyFlags.UI:
                            mark_layer_dirty(layer_idx, schedule_update=True)
            except Exception as e:
                print(f"Error applying batched updates for layer {layer_idx}: {e}")

        # Apply global updates
        if flags & DirtyFlags.CONNECTIONS:
            try:
                from .common import get_active_ypaint_node
                node = get_active_ypaint_node()
                if node:
                    node_connections.reconnect_yp_nodes(node.node_tree)
            except Exception as e:
                print(f"Error reconnecting yp nodes: {e}")

        if flags & DirtyFlags.ARRANGEMENT:
            try:
                from .common import get_active_ypaint_node
                node = get_active_ypaint_node()
                if node:
                    node_arrangements.rearrange_yp_nodes(node.node_tree)
            except Exception as e:
                print(f"Error rearranging yp nodes: {e}")

        if flags & DirtyFlags.UI:
            request_full_ui_update()


def get_performance_stats():
    """
    Get comprehensive performance statistics

    Returns:
        dict: Performance statistics from all systems
    """
    monitor = get_performance_monitor()
    pool = get_node_pool()
    cache = get_layer_cache()

    return {
        'profiling': monitor.get_stats(),
        'node_pool': pool.get_stats(),
        'layer_cache': cache.get_stats()
    }


def print_performance_report():
    """Print a comprehensive performance report"""
    stats = get_performance_stats()

    print("\n" + "="*80)
    print(" UCUPAINT PERFORMANCE REPORT")
    print("="*80)

    # Node pool stats
    pool_stats = stats['node_pool']
    print(f"\nNode Pool:")
    print(f"  Total requests: {pool_stats['total_requests']}")
    print(f"  Cache hits: {pool_stats['hits']} ({pool_stats['hit_rate']:.1f}%)")
    print(f"  Cache misses: {pool_stats['misses']}")
    print(f"  Releases: {pool_stats['releases']}")
    print(f"  Current pool sizes: {pool_stats['pool_sizes']}")

    # Layer cache stats
    cache_stats = stats['layer_cache']
    print(f"\nLayer Cache:")
    print(f"  Total requests: {cache_stats['total_requests']}")
    print(f"  Cache hits: {cache_stats['hits']} ({cache_stats['hit_rate']:.1f}%)")
    print(f"  Cache misses: {cache_stats['misses']}")
    print(f"  Cache size: {cache_stats['cache_size']} entries")

    # Profiling stats
    monitor = get_performance_monitor()
    if monitor.enabled:
        print("\nTop 10 Slowest Operations:")
        monitor.print_stats(top_n=10)
    else:
        print("\nProfiling: Disabled (enable Developer Mode in preferences)")

    print("="*80 + "\n")


# Example integration for existing update functions
def integrate_performance_into_update(original_update_func: Callable,
                                      layer_idx: Optional[int] = None,
                                      channel_idx: Optional[int] = None,
                                      mask_idx: Optional[int] = None):
    """
    Wrap an existing update function with performance optimizations

    This is a helper for gradually migrating existing code
    """
    @wraps(original_update_func)
    def wrapper(self, context):
        tracker = get_performance_tracker()

        # Skip if batching
        if tracker.batch_mode:
            if layer_idx is not None:
                tracker.mark_dirty(DirtyFlags.SPECIFIC_LAYER, layer_idx=layer_idx)
            if channel_idx is not None:
                tracker.mark_dirty(DirtyFlags.CHANNEL)
            return None

        # Use debouncing
        batcher = get_update_batcher()

        def do_update():
            result = original_update_func(self, context)

            # Mark UI dirty
            if layer_idx is not None:
                mark_layer_dirty(layer_idx, schedule_update=True)
            elif channel_idx is not None:
                mark_channel_dirty(channel_idx, schedule_update=True)
            elif mask_idx is not None and layer_idx is not None:
                mark_mask_dirty(layer_idx, mask_idx, schedule_update=True)

            return result

        update_id = f'update_{id(self)}_{original_update_func.__name__}'
        batcher.schedule_update(update_id, do_update, delay=0.1)
        return None

    return wrapper


# Convenience exports
__all__ = [
    'optimized_update_callback',
    'smart_reconnect',
    'smart_rearrange',
    'cached_layer_operation',
    'pooled_node_creation',
    'pooled_node_deletion',
    'BatchUpdateContext',
    'get_performance_stats',
    'print_performance_report',
    'integrate_performance_into_update',
    'batch_updates',
    'profile'
]
