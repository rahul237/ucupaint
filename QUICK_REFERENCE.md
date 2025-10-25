# Ucupaint Developer Quick Reference

Fast lookup guide for common development tasks and code patterns.

---

## Table of Contents

1. [Common Code Patterns](#common-code-patterns)
2. [File Location Guide](#file-location-guide)
3. [Key Functions Reference](#key-functions-reference)
4. [Property System](#property-system)
5. [Node Operations](#node-operations)
6. [Performance Optimization](#performance-optimization)
7. [Debugging Tips](#debugging-tips)
8. [Code Snippets](#code-snippets)

---

## Common Code Patterns

### Get Active Ucupaint Node

```python
from .common import get_active_ypaint_node

node = get_active_ypaint_node()
if not node:
    return  # No active node

tree = node.node_tree
yp = tree.yp  # Main data structure
```

### Get Current Layer

```python
yp = tree.yp
if yp.active_layer_index >= len(yp.layers):
    return  # Invalid index

layer = yp.layers[yp.active_layer_index]
```

### Iterate Layers

```python
# Simple iteration
for layer in yp.layers:
    print(layer.name)

# With index
for i, layer in enumerate(yp.layers):
    print(f"{i}: {layer.name}")

# Only enabled layers
enabled_layers = [l for l in yp.layers if l.enable]
```

### Get Layer Tree

```python
from .common import get_tree

layer_tree = get_tree(layer)
```

### Check Blender Version

```python
from .common import is_bl_newer_than

if is_bl_newer_than(3, 5):
    # Use newer features
    pass
else:
    # Fallback
    pass
```

---

## File Location Guide

### Where to Find Specific Functionality

| Functionality | File | Key Functions |
|---------------|------|---------------|
| **Layer Creation** | `Layer.py` | `add_new_layer()`, `duplicate_layer()` |
| **Layer Deletion** | `Layer.py` | `remove_layer()` |
| **Mask Operations** | `Mask.py` | `add_new_mask()`, `remove_mask()` |
| **Baking** | `Bake.py`, `bake_common.py` | `bake_target_channel_to_image()` |
| **Node Connections** | `node_connections.py` | `reconnect_layer_nodes()`, `create_link()` |
| **Node Layout** | `node_arrangements.py` | `rearrange_layer_nodes()` |
| **UI Panels** | `ui.py` | Panel classes, `update_yp_ui()` |
| **Utilities** | `common.py` | Helper functions |
| **Root Tree** | `Root.py` | `create_new_group_tree()`, channel mgmt |
| **Sub-trees** | `subtree.py` | Sub-tree operations |
| **Modifiers** | `Modifier.py`, `MaskModifier.py` | Modifier creation/mgmt |
| **UDIM** | `UDIM.py` | UDIM tile operations |
| **Image Atlas** | `ImageAtlas.py` | Texture packing |
| **Preferences** | `preferences.py` | User settings |
| **Versioning** | `versioning.py` | Compatibility updates |
| **Performance** | `performance.py` | Optimization systems |

---

## Key Functions Reference

### Layer Management

```python
# Add layer
from .Layer import add_new_layer

add_new_layer(
    group_tree=tree,
    layer_name='My Layer',
    layer_type='IMAGE',  # or 'VCOL', 'COLOR', etc.
    channel_idx=0,
    blend_type='MIX',
    normal_blend_type='MIX',
    normal_map_type='BUMP_MAP',
    texcoord_type='UV',
    uv_name='',
    image=None,
    vcol=None
)

# Remove layer
from .Layer import remove_layer
remove_layer(yp, layer_idx)

# Move layer
from .Layer import move_layer
move_layer(yp, from_idx, to_idx)

# Duplicate layer
from .Layer import duplicate_layer
duplicate_layer(yp, layer_idx)
```

### Mask Management

```python
# Add mask
from .Mask import add_new_mask

add_new_mask(
    layer,
    mask_name='Mask',
    mask_type='IMAGE',
    texcoord_type='UV'
)

# Remove mask
from .Mask import remove_mask
remove_mask(layer, mask_idx)
```

### Node Operations

```python
# Create link
from .node_connections import create_link
create_link(tree, output_socket, input_socket)

# Break link
from .node_connections import break_link
break_link(tree, output_socket, input_socket)

# Reconnect layer
from .node_connections import reconnect_layer_nodes
reconnect_layer_nodes(layer)

# Rearrange nodes
from .node_arrangements import rearrange_layer_nodes
rearrange_layer_nodes(layer)
```

### Tree Management

```python
# Create new Ucupaint tree
from .Root import create_new_group_tree
tree = create_new_group_tree(material, name='My Tree')

# Add channel
from .Root import create_new_yp_channel
create_new_yp_channel(
    group_tree=tree,
    name='My Channel',
    channel_type='RGB',  # or 'VALUE', 'NORMAL'
    non_color=True,
    enable=True
)
```

### UI Updates

```python
# Traditional (full update)
from .ui import update_yp_ui
update_yp_ui()

# Optimized (incremental)
from .ui_performance import mark_layer_dirty, schedule_ui_update
mark_layer_dirty(layer_idx)
schedule_ui_update()

# Force full update
from .ui_performance import request_full_ui_update
request_full_ui_update()
```

---

## Property System

### Layer Properties

```python
# Common layer properties
layer.name                  # string
layer.type                  # enum: IMAGE, VCOL, COLOR, etc.
layer.enable                # bool
layer.blend_type            # enum: MIX, ADD, MULTIPLY, etc.
layer.opacity               # float 0-1
layer.parent_idx            # int (-1 for root)

# Layer channels (mirror of root channels)
layer.channels[i].enable
layer.channels[i].blend_type

# Layer masks
layer.masks                 # collection
layer.masks[i].intensity    # float 0-1
layer.masks[i].blend_type

# Layer modifiers
layer.modifiers             # collection
layer.modifiers[i].type     # enum
layer.modifiers[i].enable   # bool
```

### Root (YPaint) Properties

```python
yp.version                  # string
yp.active_layer_index       # int
yp.active_channel_index     # int
yp.halt_reconnect           # bool (optimization flag)
yp.halt_update              # bool (optimization flag)

# Collections
yp.layers                   # layers collection
yp.channels                 # channels collection
yp.bake_targets             # bake targets collection
```

### Update Callbacks

```python
# Define update callback
def update_my_property(self, context):
    # Your update logic
    from .node_connections import reconnect_layer_nodes
    reconnect_layer_nodes(self)

# Use in PropertyGroup
class MyPropertyGroup(bpy.types.PropertyGroup):
    my_prop: FloatProperty(
        name='My Property',
        default=1.0,
        update=update_my_property
    )
```

---

## Node Operations

### Node Creation (Traditional)

```python
# Create node
node = tree.nodes.new('ShaderNodeMixRGB')
node.name = 'My Mix Node'
node.location = (0, 0)
node.blend_type = 'MIX'

# Delete node
tree.nodes.remove(node)
```

### Node Creation (Optimized with Pooling)

```python
from .performance_integration import (
    pooled_node_creation,
    pooled_node_deletion
)

# Acquire from pool
node = pooled_node_creation(tree, 'ShaderNodeMixRGB')
node.blend_type = 'MIX'
# ... use node

# Return to pool when done
pooled_node_deletion(node)
```

### Node Connections

```python
# Get sockets
output = node1.outputs['Color']
input = node2.inputs['Color']

# Create connection
tree.links.new(output, input)

# Or using helper
from .node_connections import create_link
create_link(tree, output, input)

# Break all connections to input
for link in input.links:
    tree.links.remove(link)
```

### Node Naming Convention

```python
# Layer group names
layer_group_name = '.yP Layer ' + layer.name

# Mask group names
mask_group_name = '.yP Mask ' + mask.name

# Check if node is Ucupaint node
if node.name.startswith('.yP'):
    # This is a Ucupaint node
    pass
```

---

## Performance Optimization

### Batch Operations

```python
from .performance_integration import BatchUpdateContext

# Batch multiple operations
with BatchUpdateContext():
    layer1.opacity = 0.5
    layer2.blend_type = 'ADD'
    layer3.enable = False
    # ... many more changes
# All updates applied once here
```

### Debounced Updates

```python
from .performance_integration import optimized_update_callback

@optimized_update_callback('my_update', debounce_delay=0.1)
def update_my_property(self, context):
    # This will be debounced
    reconnect_layer_nodes(self)
```

### Caching

```python
from .performance_integration import cached_layer_operation

@cached_layer_operation('my_data')
def get_expensive_data(layer):
    # Expensive calculation
    return result

# Use it
data = get_expensive_data(layer)  # Cached after first call
```

### Performance Monitoring

```python
from .performance_integration import profile, print_performance_report

@profile("my_function")
def my_function():
    # Your code
    pass

# Later, print stats
print_performance_report()
```

### Cache Invalidation

```python
from .performance import get_layer_cache

cache = get_layer_cache()

# Invalidate specific layer
cache.invalidate(layer)

# Invalidate all
cache.invalidate()
```

---

## Debugging Tips

### Enable Developer Mode

```python
# In Blender preferences
bpy.context.preferences.addons['ucupaint'].preferences.developer_mode = True
```

### Print Debug Info

```python
# Print layer info
print(f"Layer: {layer.name}")
print(f"  Type: {layer.type}")
print(f"  Blend: {layer.blend_type}")
print(f"  Enabled: {layer.enable}")
print(f"  Masks: {len(layer.masks)}")

# Print tree info
print(f"Tree nodes: {len(tree.nodes)}")
print(f"Tree links: {len(tree.links)}")

# Print performance stats
from .performance_integration import get_performance_stats
stats = get_performance_stats()
print(stats)
```

### Check Halt Flags

```python
yp = tree.yp

print(f"Halt reconnect: {yp.halt_reconnect}")
print(f"Halt update: {yp.halt_update}")

# Temporarily disable halting
yp.halt_reconnect = False
# ... your operation
yp.halt_reconnect = True
```

### Trace Property Changes

```python
def debug_update(self, context):
    import traceback
    print(f"\n=== Property Update: {self.name} ===")
    traceback.print_stack()
    # ... actual update logic
```

### Find Memory Leaks

```python
import gc

# Before operation
gc.collect()
before = len(gc.get_objects())

# Your operation
# ...

# After operation
gc.collect()
after = len(gc.get_objects())

print(f"Object delta: {after - before}")
```

---

## Code Snippets

### Custom Operator Template

```python
import bpy
from bpy.types import Operator
from .common import get_active_ypaint_node
from .performance_integration import BatchUpdateContext, profile

class YPLAYER_OT_my_operation(Operator):
    bl_idname = "yplayer.my_operation"
    bl_label = "My Operation"
    bl_description = "Description of operation"
    bl_options = {'REGISTER', 'UNDO'}

    @profile("my_operation_execute")
    def execute(self, context):
        # Get active node
        node = get_active_ypaint_node()
        if not node:
            self.report({'ERROR'}, "No active Ucupaint node")
            return {'CANCELLED'}

        tree = node.node_tree
        yp = tree.yp

        # Batch operations
        with BatchUpdateContext():
            # Your operations here
            for layer in yp.layers:
                layer.opacity *= 0.9

        self.report({'INFO'}, "Operation complete")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(YPLAYER_OT_my_operation)

def unregister():
    bpy.utils.unregister_class(YPLAYER_OT_my_operation)
```

### Custom Panel Template

```python
import bpy
from bpy.types import Panel
from .common import get_active_ypaint_node

class YPLAYER_PT_my_panel(Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Ucupaint'
    bl_label = "My Panel"

    @classmethod
    def poll(cls, context):
        return get_active_ypaint_node() is not None

    def draw(self, context):
        layout = self.layout
        node = get_active_ypaint_node()

        if not node:
            return

        tree = node.node_tree
        yp = tree.yp

        # Draw UI
        col = layout.column()
        col.label(text=f"Layers: {len(yp.layers)}")

        for layer in yp.layers:
            row = col.row()
            row.prop(layer, 'enable', text='')
            row.label(text=layer.name)
```

### Custom Property Group Template

```python
import bpy
from bpy.props import StringProperty, FloatProperty, BoolProperty
from bpy.types import PropertyGroup
from .performance_integration import optimized_update_callback

@optimized_update_callback('my_property', debounce_delay=0.1)
def update_my_property(self, context):
    # Your update logic
    from .node_connections import reconnect_layer_nodes
    reconnect_layer_nodes(self)

class MyPropertyGroup(PropertyGroup):
    my_string: StringProperty(
        name='My String',
        default='Default'
    )

    my_float: FloatProperty(
        name='My Float',
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_my_property
    )

    my_bool: BoolProperty(
        name='My Bool',
        default=False,
        update=update_my_property
    )

def register():
    bpy.utils.register_class(MyPropertyGroup)
    bpy.types.Material.my_pg = bpy.props.PointerProperty(type=MyPropertyGroup)

def unregister():
    del bpy.types.Material.my_pg
    bpy.utils.unregister_class(MyPropertyGroup)
```

### Iterate with Performance Profiling

```python
from .performance_integration import profile

@profile("process_all_layers")
def process_all_layers(yp):
    for i, layer in enumerate(yp.layers):
        process_single_layer(layer, i)

@profile("process_single_layer")
def process_single_layer(layer, index):
    # Process layer
    pass
```

### Safe Node Tree Access

```python
def safe_get_node(tree, node_name):
    """Safely get node, return None if not found"""
    try:
        return tree.nodes.get(node_name)
    except (AttributeError, KeyError):
        return None

# Use it
node = safe_get_node(tree, 'My Node')
if node:
    # Use node
    pass
```

---

## Common Enumerations

### Layer Types
```python
IMAGE, BRICK, CHECKER, GRADIENT, MAGIC, MUSGRAVE, NOISE,
VORONOI, WAVE, VCOL, BACKGROUND, COLOR, GROUP, HEMI,
GABOR, EDGE_DETECT, AO
```

### Blend Types
```python
MIX, ADD, SUBTRACT, MULTIPLY, SCREEN, OVERLAY, DIFFERENCE,
DIVIDE, DARKEN, LIGHTEN, HUE, SATURATION, VALUE, COLOR,
SOFT_LIGHT, LINEAR_LIGHT, DODGE, BURN, EXCLUSION
```

### Channel Types
```python
RGB, VALUE, NORMAL
```

### Normal Map Types
```python
BUMP_MAP, NORMAL_MAP, BUMP_NORMAL_MAP, VECTOR_DISPLACEMENT_MAP
```

### Modifier Types
```python
INVERT, RGB_TO_INTENSITY, INTENSITY_TO_RGB, OVERRIDE_COLOR,
COLOR_RAMP, RGB_CURVE, HUE_SATURATION, BRIGHT_CONTRAST,
MULTIPLIER, MATH
```

---

## Useful Constants

```python
from .common import (
    LAYERGROUP_PREFIX,    # '.yP Layer '
    MASKGROUP_PREFIX,     # '.yP Mask '
    MAX_VERTEX_DATA,      # 8
    TREE_START,           # 'Group Input'
    TREE_END,             # 'Group Output'
)
```

---

## Quick Checklist for New Features

- [ ] Define PropertyGroup with properties
- [ ] Add update callbacks (with @optimized_update_callback)
- [ ] Create operator class
- [ ] Add panel for UI
- [ ] Update node connections if needed
- [ ] Update node arrangements if needed
- [ ] Add to registration in module
- [ ] Test with small project
- [ ] Test with large project (50+ layers)
- [ ] Check performance stats
- [ ] Update documentation

---

## Getting Help

1. **Check existing code** - Look for similar functionality
2. **Read documentation** - PERFORMANCE_GUIDE.md, CODEBASE_ANALYSIS_REPORT.md
3. **Enable debug mode** - Developer preferences
4. **Use profiling** - print_performance_report()
5. **Check console** - Blender console for errors

---

## Performance Checklist

When writing new code:

- [ ] Use BatchUpdateContext for multiple operations
- [ ] Decorate update callbacks with @optimized_update_callback
- [ ] Use pooled_node_creation instead of tree.nodes.new()
- [ ] Cache expensive operations with @cached_layer_operation
- [ ] Profile with @profile decorator
- [ ] Avoid nested layer iterations
- [ ] Check halt flags before reconnecting
- [ ] Invalidate cache after structural changes

---

**Last Updated:** October 15, 2025
**Ucupaint Version:** 2.4.0
