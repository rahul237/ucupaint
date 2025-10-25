"""
Performance Optimization Examples
Real-world examples showing how to integrate performance features
"""

import bpy
from bpy.props import FloatProperty, EnumProperty
from .performance_integration import (
    optimized_update_callback,
    BatchUpdateContext,
    pooled_node_creation,
    pooled_node_deletion,
    cached_layer_operation,
    smart_reconnect,
    smart_rearrange,
    profile,
    print_performance_report
)


# ============================================================================
# EXAMPLE 1: Optimizing Property Update Callbacks
# ============================================================================

# BEFORE: Traditional update callback
def old_update_layer_opacity(self, context):
    """Traditional approach - triggers on every change"""
    from .node_connections import reconnect_layer_nodes
    from .node_arrangements import rearrange_layer_nodes

    reconnect_layer_nodes(self)
    rearrange_layer_nodes(self)


# AFTER: Optimized update callback
@optimized_update_callback('layer_opacity', debounce_delay=0.1)
def new_update_layer_opacity(self, context):
    """Optimized approach - debounced and batch-aware"""
    from .node_connections import reconnect_layer_nodes
    from .node_arrangements import rearrange_layer_nodes

    reconnect_layer_nodes(self)
    rearrange_layer_nodes(self)


# Usage in PropertyGroup:
# opacity : FloatProperty(
#     name='Opacity',
#     default=1.0,
#     min=0.0,
#     max=1.0,
#     update=new_update_layer_opacity  # Use optimized version
# )


# ============================================================================
# EXAMPLE 2: Batch Operations in Operators
# ============================================================================

class EXAMPLE_OT_AddMultipleLayers(bpy.types.Operator):
    """Example operator showing batch operations"""
    bl_idname = "example.add_multiple_layers"
    bl_label = "Add Multiple Layers"

    count: bpy.props.IntProperty(name="Count", default=10, min=1, max=100)

    @profile("add_multiple_layers_execute")
    def execute(self, context):
        from . import Layer
        from .common import get_active_ypaint_node

        node = get_active_ypaint_node()
        if not node:
            return {'CANCELLED'}

        tree = node.node_tree

        # Use batch context to prevent redundant updates
        with BatchUpdateContext():
            for i in range(self.count):
                Layer.add_new_layer(
                    tree,
                    layer_name=f'Layer {i}',
                    layer_type='COLOR',
                    channel_idx=0,
                    blend_type='MIX',
                    normal_blend_type='MIX',
                    normal_map_type='BUMP_MAP',
                    texcoord_type='UV'
                )
        # All updates applied here in single batch

        self.report({'INFO'}, f"Added {self.count} layers")
        return {'FINISHED'}


# ============================================================================
# EXAMPLE 3: Node Pooling
# ============================================================================

def create_layer_nodes_old(tree, layer):
    """Old approach - creates new nodes"""
    mix = tree.nodes.new('ShaderNodeMixRGB')
    tex = tree.nodes.new('ShaderNodeTexImage')

    # ... configure nodes

    # Later deletion
    tree.nodes.remove(mix)
    tree.nodes.remove(tex)


def create_layer_nodes_new(tree, layer):
    """New approach - uses pooling"""
    mix = pooled_node_creation(tree, 'ShaderNodeMixRGB')
    tex = pooled_node_creation(tree, 'ShaderNodeTexImage')

    # ... configure nodes

    # Later return to pool
    pooled_node_deletion(mix)
    pooled_node_deletion(tex)


# ============================================================================
# EXAMPLE 4: Caching Expensive Operations
# ============================================================================

# BEFORE: Expensive lookup without caching
def get_layer_tree_old(layer):
    """Expensive operation called frequently"""
    from .common import get_tree
    # This might involve node tree traversal
    return get_tree(layer)


# AFTER: Cached version
@cached_layer_operation('layer_tree')
def get_layer_tree_new(layer):
    """Cached - only computed once per layer version"""
    from .common import get_tree
    return get_tree(layer)


# Usage:
# tree = get_layer_tree_new(layer)  # First call - cache miss, computes
# tree = get_layer_tree_new(layer)  # Second call - cache hit, instant


# ============================================================================
# EXAMPLE 5: Smart Reconnect/Rearrange Wrappers
# ============================================================================

# Wrap existing functions to respect batch mode
@smart_reconnect
def reconnect_layer_nodes_optimized(layer):
    """
    This will automatically:
    - Skip if in batch mode (mark dirty instead)
    - Profile execution time in developer mode
    - Respect halt flags
    """
    from .node_connections import reconnect_layer_nodes
    reconnect_layer_nodes(layer)


@smart_rearrange
def rearrange_layer_nodes_optimized(layer):
    """
    This will automatically:
    - Skip if in batch mode (mark dirty instead)
    - Profile execution time in developer mode
    - Respect halt flags
    """
    from .node_arrangements import rearrange_layer_nodes
    rearrange_layer_nodes(layer)


# ============================================================================
# EXAMPLE 6: Complex Operator with Multiple Optimizations
# ============================================================================

class EXAMPLE_OT_OptimizedLayerOperation(bpy.types.Operator):
    """Example showing multiple optimization techniques"""
    bl_idname = "example.optimized_layer_op"
    bl_label = "Optimized Layer Operation"

    @profile("optimized_layer_operation")
    def execute(self, context):
        from .common import get_active_ypaint_node

        node = get_active_ypaint_node()
        if not node:
            return {'CANCELLED'}

        tree = node.node_tree
        yp = tree.yp

        # Use batch context for multiple operations
        with BatchUpdateContext():
            for layer in yp.layers:
                # Use cached operations
                layer_tree = get_layer_tree_new(layer)

                # Modify properties (won't trigger individual updates)
                layer.opacity *= 0.9

                # Use pooled node creation if needed
                if layer.type == 'IMAGE':
                    temp_node = pooled_node_creation(layer_tree, 'ShaderNodeMath')
                    # ... use temp_node
                    pooled_node_deletion(temp_node)

        # Print performance stats in developer mode
        if context.preferences.addons[__package__.split('.')[0]].preferences.developer_mode:
            print_performance_report()

        return {'FINISHED'}


# ============================================================================
# EXAMPLE 7: Incremental UI Updates
# ============================================================================

def update_layer_property_with_ui(layer, layer_idx):
    """Example showing how to update UI incrementally"""
    from .ui_performance import mark_layer_dirty, schedule_ui_update

    # Modify layer property
    layer.some_property = new_value

    # Mark only this layer's UI as dirty
    mark_layer_dirty(layer_idx, schedule_update=True)
    # UI update is debounced automatically


# ============================================================================
# EXAMPLE 8: Performance Monitoring
# ============================================================================

class EXAMPLE_OT_ShowPerformanceReport(bpy.types.Operator):
    """Show performance statistics in console"""
    bl_idname = "example.show_performance_report"
    bl_label = "Show Performance Report"

    def execute(self, context):
        # Print comprehensive report to console
        print_performance_report()

        self.report({'INFO'}, "Performance report printed to console")
        return {'FINISHED'}


# ============================================================================
# EXAMPLE 9: Custom Profiling
# ============================================================================

@profile("expensive_calculation")
def expensive_calculation(data):
    """This function will be profiled automatically"""
    result = 0
    for i in range(len(data)):
        result += data[i] * 2
    return result


@profile("my_custom_function")
def my_custom_function():
    """Profile your own functions to find bottlenecks"""
    # Your code here
    pass


# ============================================================================
# EXAMPLE 10: Migration Helper
# ============================================================================

def migrate_existing_update_callback():
    """
    Example of how to migrate an existing update callback
    without changing the original function
    """
    from .performance_integration import integrate_performance_into_update

    # Original function (don't modify)
    def original_update(self, context):
        # Original logic
        pass

    # Wrap it with performance features
    optimized_update = integrate_performance_into_update(
        original_update,
        layer_idx=0  # If this is a layer update
    )

    # Now use optimized_update instead of original_update
    return optimized_update


# ============================================================================
# EXAMPLE 11: Conditional Batching
# ============================================================================

def smart_layer_modification(layers, use_batching=True):
    """
    Example showing conditional batching based on operation count
    """
    if use_batching and len(layers) > 5:
        # Use batching for many layers
        with BatchUpdateContext():
            for layer in layers:
                modify_layer(layer)
    else:
        # Don't batch for few layers (overhead not worth it)
        for layer in layers:
            modify_layer(layer)


def modify_layer(layer):
    """Helper function"""
    layer.opacity *= 0.95


# ============================================================================
# EXAMPLE 12: Performance-Aware Property Group
# ============================================================================

class EXAMPLE_PG_PerformanceAwareLayer(bpy.types.PropertyGroup):
    """Example PropertyGroup using all optimization features"""

    # Optimized update callback
    @staticmethod
    @optimized_update_callback('blend_type', debounce_delay=0.1)
    def update_blend_type(self, context):
        reconnect_layer_nodes_optimized(self)

    @staticmethod
    @optimized_update_callback('opacity', debounce_delay=0.05)
    def update_opacity(self, context):
        # Faster debounce for smooth scrubbing
        reconnect_layer_nodes_optimized(self)

    blend_type: EnumProperty(
        name='Blend Type',
        items=[('MIX', 'Mix', ''), ('ADD', 'Add', '')],
        update=update_blend_type
    )

    opacity: FloatProperty(
        name='Opacity',
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_opacity
    )


# ============================================================================
# Registration
# ============================================================================

classes = (
    EXAMPLE_OT_AddMultipleLayers,
    EXAMPLE_OT_OptimizedLayerOperation,
    EXAMPLE_OT_ShowPerformanceReport,
    EXAMPLE_PG_PerformanceAwareLayer,
)


def register():
    """Register example classes"""
    # Uncomment to enable examples:
    # for cls in classes:
    #     bpy.utils.register_class(cls)
    pass


def unregister():
    """Unregister example classes"""
    # Uncomment if examples are registered:
    # for cls in reversed(classes):
    #     bpy.utils.unregister_class(cls)
    pass


# ============================================================================
# NOTES FOR DEVELOPERS
# ============================================================================

"""
Key Takeaways:

1. Use @optimized_update_callback for all property updates
   - Prevents redundant updates
   - Automatic debouncing
   - Respects batch mode

2. Use BatchUpdateContext for multiple operations
   - Wrap operator execute() methods
   - Wrap functions that modify multiple properties
   - Massive speedup for bulk operations

3. Use pooled_node_creation/deletion for nodes
   - Especially in loops or frequently called code
   - 30-50% performance improvement
   - Automatic statistics tracking

4. Use @cached_layer_operation for expensive lookups
   - Layer tree lookups
   - Node graph traversals
   - Any repeated expensive calculation

5. Use @profile for bottleneck identification
   - Profile suspicious functions
   - Enable Developer Mode to see results
   - Use print_performance_report() for analysis

6. Gradual Migration Strategy:
   - Start with high-frequency update callbacks
   - Add batching to operators
   - Replace node operations in hot paths
   - Cache expensive lookups
   - Profile and iterate

Remember: Performance optimization is iterative!
- Measure first (use @profile)
- Optimize high-impact areas
- Measure again
- Repeat
"""
