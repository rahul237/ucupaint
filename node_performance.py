"""
Node performance optimizations
Integrates node pooling into node creation/deletion hotspots
"""

import bpy
from .performance_integration import (
    pooled_node_creation,
    pooled_node_deletion,
    profile,
    get_node_pool
)
from .performance import get_performance_monitor


# ============================================================================
# OPTIMIZED NODE OPERATIONS
# ============================================================================

@profile("create_node_optimized")
def create_node_optimized(tree, node_type, name=''):
    """
    Create a node using pooling for better performance

    Args:
        tree: Node tree
        node_type: Type of node to create (e.g., 'ShaderNodeMixRGB')
        name: Optional name for the node

    Returns:
        Created node
    """
    node = pooled_node_creation(tree, node_type)

    if name:
        node.name = name

    return node


@profile("delete_node_optimized")
def delete_node_optimized(tree, node):
    """
    Delete a node using pooling (returns to pool instead of deleting)

    Args:
        tree: Node tree
        node: Node to delete
    """
    if node:
        pooled_node_deletion(node)


def create_mix_node_optimized(tree, blend_type='MIX', name=''):
    """Create a Mix node with pooling"""
    from .common import is_bl_newer_than

    if is_bl_newer_than(3, 4):
        node = create_node_optimized(tree, 'ShaderNodeMix', name)
        node.data_type = 'RGBA'
        node.blend_type = blend_type
        node.clamp_result = False
    else:
        node = create_node_optimized(tree, 'ShaderNodeMixRGB', name)
        node.blend_type = blend_type
        node.use_clamp = False

    return node


def create_math_node_optimized(tree, operation='ADD', name=''):
    """Create a Math node with pooling"""
    node = create_node_optimized(tree, 'ShaderNodeMath', name)
    node.operation = operation
    node.use_clamp = False
    return node


def create_image_node_optimized(tree, image=None, name=''):
    """Create an Image Texture node with pooling"""
    node = create_node_optimized(tree, 'ShaderNodeTexImage', name)
    if image:
        node.image = image
    return node


def create_value_node_optimized(tree, value=0.0, name=''):
    """Create a Value node with pooling"""
    node = create_node_optimized(tree, 'ShaderNodeValue', name)
    node.outputs[0].default_value = value
    return node


def create_rgb_node_optimized(tree, color=(1, 1, 1, 1), name=''):
    """Create an RGB node with pooling"""
    node = create_node_optimized(tree, 'ShaderNodeRGB', name)
    node.outputs[0].default_value = color
    return node


# ============================================================================
# BATCH NODE OPERATIONS
# ============================================================================

@profile("create_nodes_batch")
def create_nodes_batch(tree, node_specs):
    """
    Create multiple nodes efficiently

    Args:
        tree: Node tree
        node_specs: List of tuples (node_type, name)

    Returns:
        List of created nodes

    Example:
        specs = [
            ('ShaderNodeMixRGB', 'Mix 1'),
            ('ShaderNodeTexImage', 'Image 1'),
            ('ShaderNodeMath', 'Math 1'),
        ]
        nodes = create_nodes_batch(tree, specs)
    """
    nodes = []
    for node_type, name in node_specs:
        node = create_node_optimized(tree, node_type, name)
        nodes.append(node)

    return nodes


@profile("delete_nodes_batch")
def delete_nodes_batch(tree, nodes):
    """
    Delete multiple nodes efficiently

    Args:
        tree: Node tree
        nodes: List of nodes to delete
    """
    for node in nodes:
        if node:
            delete_node_optimized(tree, node)


# ============================================================================
# NODE POOL MANAGEMENT
# ============================================================================

def clear_tree_node_pool(tree, node_type=None):
    """
    Clear node pool for a tree

    Args:
        tree: Node tree
        node_type: Optional specific node type to clear
    """
    pool = get_node_pool()
    pool.clear_pool(tree, node_type)


def get_node_pool_stats():
    """Get node pooling statistics"""
    pool = get_node_pool()
    return pool.get_stats()


def print_node_pool_stats():
    """Print node pooling statistics"""
    stats = get_node_pool_stats()

    print("\n=== Node Pool Statistics ===")
    print(f"Total requests: {stats['total_requests']}")
    print(f"Cache hits: {stats['hits']} ({stats['hit_rate']:.1f}%)")
    print(f"Cache misses: {stats['misses']}")
    print(f"Releases: {stats['releases']}")
    print("\nPool sizes by type:")
    for node_type, size in stats['pool_sizes'].items():
        print(f"  {node_type}: {size} nodes")
    print("="*30 + "\n")


# ============================================================================
# SMART NODE CREATION WRAPPERS
# ============================================================================

def check_new_node_optimized(tree, entity, prop_name, node_type, label='', hard_update=False):
    """
    Optimized version of check_new_node that uses pooling

    Creates a node if it doesn't exist, updates it if it does
    Uses node pooling for better performance
    """
    node_name = getattr(entity, prop_name)
    node = tree.nodes.get(node_name)

    if not node or hard_update:
        if node and hard_update:
            delete_node_optimized(tree, node)

        node = create_node_optimized(tree, node_type)
        setattr(entity, prop_name, node.name)

        if label:
            node.label = label

    return node


def new_node_optimized(tree, entity, prop_name, node_type, label=''):
    """
    Optimized version of new_node that uses pooling

    Always creates a new node, using pooling for better performance
    """
    node = create_node_optimized(tree, node_type)
    setattr(entity, prop_name, node.name)

    if label:
        node.label = label

    return node


def remove_node_optimized(tree, entity, prop_name, remove_data=True):
    """
    Optimized version of remove_node that uses pooling

    Args:
        tree: Node tree
        entity: Entity with the node property
        prop_name: Property name containing node name
        remove_data: If True, returns node to pool; if False, keeps node hidden
    """
    node_name = getattr(entity, prop_name, '')
    if not node_name:
        return

    node = tree.nodes.get(node_name)
    if node:
        if remove_data:
            delete_node_optimized(tree, node)
        else:
            # Just hide it
            node.hide = True
            node.location = (-10000, -10000)

    setattr(entity, prop_name, '')


# ============================================================================
# MONKEY PATCH HELPERS
# ============================================================================

def apply_node_pool_optimizations():
    """
    Apply node pooling optimizations to common functions

    This monkey-patches frequently used node creation functions
    to use pooling automatically
    """
    try:
        from . import subtree

        # Store originals
        if not hasattr(subtree, '_original_node_funcs'):
            subtree._original_node_funcs = {}

            # Check if these functions exist before storing
            if hasattr(subtree, 'check_new_node'):
                subtree._original_node_funcs['check_new_node'] = subtree.check_new_node
            if hasattr(subtree, 'new_node'):
                subtree._original_node_funcs['new_node'] = subtree.new_node
            if hasattr(subtree, 'remove_node'):
                subtree._original_node_funcs['remove_node'] = subtree.remove_node

        # Apply optimized versions
        if hasattr(subtree, 'check_new_node'):
            subtree.check_new_node = check_new_node_optimized
        if hasattr(subtree, 'new_node'):
            subtree.new_node = new_node_optimized
        if hasattr(subtree, 'remove_node'):
            subtree.remove_node = remove_node_optimized

        print("INFO: Applied node pooling optimizations")

    except Exception as e:
        print(f"WARNING: Could not apply node pooling optimizations: {e}")


def restore_original_node_functions():
    """Restore original node functions"""
    try:
        from . import subtree

        if hasattr(subtree, '_original_node_funcs'):
            for name, func in subtree._original_node_funcs.items():
                setattr(subtree, name, func)

            delattr(subtree, '_original_node_funcs')
            print("INFO: Restored original node functions")

    except Exception as e:
        print(f"WARNING: Could not restore original node functions: {e}")


# ============================================================================
# REGISTRATION
# ============================================================================

def register():
    """Register node performance optimizations"""
    # Apply monkey patches
    apply_node_pool_optimizations()
    print("INFO: Node performance module registered")


def unregister():
    """Unregister node performance optimizations"""
    # Restore originals
    restore_original_node_functions()
    print("INFO: Node performance module unregistered")
