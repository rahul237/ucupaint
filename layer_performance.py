"""
Performance-optimized layer update callbacks
Replaces bottleneck update functions with optimized versions
"""

import bpy
import time
import re
from .performance_integration import optimized_update_callback, profile
from .common import get_tree, get_layer_source, get_channel_source
from .node_connections import reconnect_layer_nodes, reconnect_yp_nodes
from .node_arrangements import rearrange_layer_nodes, rearrange_yp_nodes


# ============================================================================
# OPTIMIZED UPDATE CALLBACKS
# These replace the slow update callbacks in Layer.py
# ============================================================================

@optimized_update_callback('blend_type', debounce_delay=0.1)
@profile("update_blend_type_optimized")
def update_blend_type_optimized(self, context):
    """Optimized version of update_blend_type with debouncing"""
    from .Layer import (
        check_all_layer_channel_io_and_nodes,
        check_uv_nodes
    )

    T = time.time()
    wm = context.window_manager
    yp = self.id_data.yp

    if yp.halt_update:
        return

    m = re.match(r'yp\.layers\[(\d+)\]\.channels\[(\d+)\]', self.path_from_id())
    layer = yp.layers[int(m.group(1))]
    tree = get_tree(layer)
    ch_index = int(m.group(2))
    root_ch = yp.channels[ch_index]

    check_all_layer_channel_io_and_nodes(layer, tree, self)
    check_uv_nodes(yp)

    # Reconnect all layer channels if normal channel is updated
    if root_ch.type == 'NORMAL':
        reconnect_layer_nodes(layer)
    else:
        reconnect_layer_nodes(layer, ch_index)

    rearrange_layer_nodes(layer)
    reconnect_yp_nodes(self.id_data)
    rearrange_yp_nodes(self.id_data)

    print('INFO: Layer', layer.name, 'blend type is changed in',
          '{:0.2f}'.format((time.time() - T) * 1000), 'ms! (optimized)')
    wm.yptimer.time = str(time.time())


@optimized_update_callback('layer_enable', debounce_delay=0.1)
@profile("update_layer_enable_optimized")
def update_layer_enable_optimized(self, context):
    """Optimized version of update_layer_enable with debouncing"""
    from .Layer import (
        check_all_layer_channel_io_and_nodes,
        check_uv_nodes,
        check_start_end_root_ch_nodes,
        update_displacement_height_ratio,
        get_root_height_channel
    )

    T = time.time()
    yp = self.id_data.yp

    if yp.halt_update:
        return

    layer = self
    tree = get_tree(layer)

    height_root_ch = get_root_height_channel(yp)
    if height_root_ch:
        update_displacement_height_ratio(height_root_ch)

    check_uv_nodes(yp)
    check_all_layer_channel_io_and_nodes(layer, tree)
    check_start_end_root_ch_nodes(layer.id_data)

    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)

    if yp.layer_preview_mode:
        yp.layer_preview_mode = yp.layer_preview_mode
    else:
        reconnect_yp_nodes(layer.id_data)
        rearrange_yp_nodes(layer.id_data)

    context.window_manager.yptimer.time = str(time.time())
    print('INFO: Layer', layer.name, 'is updated in',
          '{:0.2f}'.format((time.time() - T) * 1000), 'ms! (optimized)')


@optimized_update_callback('write_height', debounce_delay=0.15)
@profile("update_write_height_optimized")
def update_write_height_optimized(self, context):
    """Optimized version of update_write_height"""
    from .Layer import (
        check_all_layer_channel_io_and_nodes,
        check_uv_nodes,
        check_start_end_root_ch_nodes,
        update_displacement_height_ratio
    )

    yp = self.id_data.yp
    if yp.halt_update:
        return

    m = re.match(r'yp\.layers\[(\d+)\]\.channels\[(\d+)\]', self.path_from_id())
    layer = yp.layers[int(m.group(1))]
    ch_index = int(m.group(2))
    root_ch = yp.channels[ch_index]
    tree = get_tree(layer)

    check_all_layer_channel_io_and_nodes(layer, tree, self)
    update_displacement_height_ratio(root_ch)
    check_start_end_root_ch_nodes(self.id_data)
    check_uv_nodes(yp)

    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)
    reconnect_yp_nodes(self.id_data)
    rearrange_yp_nodes(self.id_data)


@optimized_update_callback('voronoi_feature', debounce_delay=0.1)
def update_voronoi_feature_optimized(self, context):
    """Optimized voronoi feature update"""
    yp = self.id_data.yp
    if yp.halt_update:
        return

    layer = self
    if layer.type != 'VORONOI':
        return

    source = get_layer_source(layer)
    source.feature = layer.voronoi_feature

    reconnect_layer_nodes(layer)
    rearrange_layer_nodes(layer)


@optimized_update_callback('layer_channel_voronoi', debounce_delay=0.1)
def update_layer_channel_voronoi_feature_optimized(self, context):
    """Optimized layer channel voronoi update"""
    yp = self.id_data.yp
    if yp.halt_update:
        return

    m = re.match(r'yp\.layers\[(\d+)\]\.channels\[(\d+)\]', self.path_from_id())
    layer = yp.layers[int(m.group(1))]
    ch = self

    source = None
    if ch.override_type == 'VORONOI':
        source = get_channel_source(ch)

    if not source:
        tree = get_tree(layer)
        source = tree.nodes.get(ch.cache_voronoi)

    if source:
        source.feature = ch.voronoi_feature


# ============================================================================
# HELPER FUNCTION TO REPLACE UPDATE CALLBACKS
# ============================================================================

def apply_optimized_callbacks():
    """
    Replace slow update callbacks with optimized versions
    Call this during registration to monkey-patch the updates

    IMPORTANT: This is a temporary solution until the source files
    can be properly refactored. This allows us to get performance
    improvements without modifying the original files.
    """
    try:
        from . import Layer

        # Replace critical update callbacks
        # Note: These are monkey patches - ideally Layer.py should import these directly

        # Store originals for potential restoration
        if not hasattr(Layer, '_original_callbacks'):
            Layer._original_callbacks = {
                'update_blend_type': Layer.update_blend_type,
                'update_layer_enable': Layer.update_layer_enable,
                'update_write_height': Layer.update_write_height,
                'update_voronoi_feature': Layer.update_voronoi_feature,
                'update_layer_channel_voronoi_feature': Layer.update_layer_channel_voronoi_feature,
            }

        # Apply optimized versions
        Layer.update_blend_type = update_blend_type_optimized
        Layer.update_layer_enable = update_layer_enable_optimized
        Layer.update_write_height = update_write_height_optimized
        Layer.update_voronoi_feature = update_voronoi_feature_optimized
        Layer.update_layer_channel_voronoi_feature = update_layer_channel_voronoi_feature_optimized

        print("INFO: Applied optimized layer update callbacks")

    except Exception as e:
        print(f"WARNING: Could not apply optimized callbacks: {e}")
        # Fail gracefully - original callbacks will still work


def restore_original_callbacks():
    """Restore original update callbacks (for debugging or uninstall)"""
    try:
        from . import Layer

        if hasattr(Layer, '_original_callbacks'):
            for name, func in Layer._original_callbacks.items():
                setattr(Layer, name, func)

            delattr(Layer, '_original_callbacks')
            print("INFO: Restored original layer update callbacks")

    except Exception as e:
        print(f"WARNING: Could not restore original callbacks: {e}")


# ============================================================================
# BATCH OPERATION HELPERS
# ============================================================================

def add_layer_batch(group_tree, layer_configs):
    """
    Add multiple layers efficiently using batching

    Args:
        group_tree: The Ucupaint group tree
        layer_configs: List of dicts with layer parameters

    Example:
        configs = [
            {'name': 'Layer 1', 'type': 'COLOR', ...},
            {'name': 'Layer 2', 'type': 'IMAGE', ...},
        ]
        add_layer_batch(tree, configs)
    """
    from .performance_integration import BatchUpdateContext
    from .Layer import add_new_layer

    with BatchUpdateContext():
        layers = []
        for config in layer_configs:
            layer = add_new_layer(group_tree, **config)
            layers.append(layer)

    return layers


def remove_layers_batch(yp, layer_indices):
    """
    Remove multiple layers efficiently using batching

    Args:
        yp: YPaint data
        layer_indices: List of layer indices to remove (sorted descending)
    """
    from .performance_integration import BatchUpdateContext
    from .Layer import remove_layer

    # Sort descending to remove from end first (preserves indices)
    layer_indices = sorted(layer_indices, reverse=True)

    with BatchUpdateContext():
        for idx in layer_indices:
            remove_layer(yp, idx)


def duplicate_layers_batch(yp, layer_indices):
    """
    Duplicate multiple layers efficiently using batching

    Args:
        yp: YPaint data
        layer_indices: List of layer indices to duplicate

    Returns:
        List of new layer indices
    """
    from .performance_integration import BatchUpdateContext
    from .Layer import duplicate_layer

    new_indices = []
    with BatchUpdateContext():
        for idx in layer_indices:
            new_idx = duplicate_layer(yp, idx)
            new_indices.append(new_idx)

    return new_indices


# ============================================================================
# REGISTRATION
# ============================================================================

def register():
    """Register optimized callbacks"""
    # Apply monkey patches
    apply_optimized_callbacks()
    print("INFO: Layer performance module registered")


def unregister():
    """Unregister optimized callbacks"""
    # Restore originals
    restore_original_callbacks()
    print("INFO: Layer performance module unregistered")
