"""
Incremental UI update system for Ucupaint
Provides selective UI updates instead of full rebuilds
"""

import bpy
from typing import Set, Optional, List, Tuple
from .performance import get_performance_tracker, get_update_batcher, profile, DirtyFlags


class UIUpdateManager:
    """
    Manages incremental UI updates to avoid full rebuilds
    """

    def __init__(self):
        self.dirty_items: Set[Tuple[str, int]] = set()  # (item_type, index)
        self.full_update_needed = False
        self.last_tree_name = ""
        self.last_layer_idx = -1
        self.last_channel_idx = -1
        self.last_bake_target_idx = -1

    def mark_dirty(self, item_type: str, index: int = -1):
        """Mark a specific UI item as needing update"""
        self.dirty_items.add((item_type, index))

    def needs_full_update(self) -> bool:
        """Check if a full UI update is needed"""
        return self.full_update_needed

    def request_full_update(self):
        """Request a full UI rebuild"""
        self.full_update_needed = True
        self.dirty_items.clear()

    @profile("update_yp_ui_incremental")
    def update_yp_ui_incremental(self, node=None, yp=None):
        """
        Update only changed UI elements instead of full rebuild
        Falls back to full update when necessary
        """
        if node is None:
            from .common import get_active_ypaint_node
            node = get_active_ypaint_node()

        if not node or node.type != 'GROUP':
            return

        if yp is None:
            tree = node.node_tree
            yp = tree.yp
        else:
            tree = yp.id_data

        ypui = bpy.context.window_manager.ypui

        # Check if major context changed (requires full update)
        context_changed = (
            ypui.tree_name != tree.name or
            ypui.layer_idx != yp.active_layer_index or
            ypui.channel_idx != yp.active_channel_index or
            ypui.bake_target_idx != yp.active_bake_target_index or
            ypui.need_update
        )

        if context_changed or self.full_update_needed:
            # Fall back to full update
            self._full_update(node, tree, yp, ypui)
            self.full_update_needed = False
            self.dirty_items.clear()
            return

        # Incremental updates for dirty items
        if self.dirty_items:
            self._apply_incremental_updates(yp, ypui)
            self.dirty_items.clear()

    def _full_update(self, node, tree, yp, ypui):
        """Perform full UI update (existing behavior)"""
        # Import here to avoid circular dependency
        from . import ui

        # Store current state
        self.last_tree_name = tree.name
        self.last_layer_idx = yp.active_layer_index
        self.last_channel_idx = yp.active_channel_index
        self.last_bake_target_idx = yp.active_bake_target_index

        # Call existing full update function
        ui.update_yp_ui()

    @profile("apply_incremental_ui_updates")
    def _apply_incremental_updates(self, yp, ypui):
        """Apply only the incremental UI updates"""
        for item_type, index in self.dirty_items:
            if item_type == 'layer':
                self._update_layer_ui(yp, ypui, index)
            elif item_type == 'channel':
                self._update_channel_ui(yp, ypui, index)
            elif item_type == 'mask':
                # Mask updates are part of layer updates
                layer_idx = index // 1000  # Encoded as layer_idx * 1000 + mask_idx
                self._update_layer_ui(yp, ypui, layer_idx)
            elif item_type == 'bake_target':
                self._update_bake_target_ui(yp, ypui, index)

    def _update_layer_ui(self, yp, ypui, layer_idx: int):
        """Update UI for a specific layer"""
        if layer_idx < 0 or layer_idx >= len(yp.layers):
            return

        if layer_idx != yp.active_layer_index:
            # Not the active layer, limited update needed
            return

        layer = yp.layers[layer_idx]

        # Update layer UI properties
        ypui.layer_ui.expand_content = layer.expand_content
        ypui.layer_ui.expand_vector = layer.expand_vector
        ypui.layer_ui.expand_source = layer.expand_source
        ypui.layer_ui.expand_masks = layer.expand_masks
        ypui.layer_ui.expand_channels = layer.expand_channels

        # Update modifiers if count changed
        if len(ypui.layer_ui.modifiers) != len(layer.modifiers):
            ypui.layer_ui.modifiers.clear()
            for mod in layer.modifiers:
                m = ypui.layer_ui.modifiers.add()
                m.expand_content = mod.expand_content

        # Update masks if count changed
        if len(ypui.layer_ui.masks) != len(layer.masks):
            ypui.layer_ui.masks.clear()
            for i, mask in enumerate(layer.masks):
                m = ypui.layer_ui.masks.add()
                m.expand_content = mask.expand_content
                m.expand_channels = mask.expand_channels
                m.expand_source = mask.expand_source
                m.expand_vector = mask.expand_vector

                for mch in mask.channels:
                    mc = m.channels.add()
                    mc.expand_content = mch.expand_content

                for mod in mask.modifiers:
                    mm = m.modifiers.add()
                    mm.expand_content = mod.expand_content

    def _update_channel_ui(self, yp, ypui, channel_idx: int):
        """Update UI for a specific channel"""
        if channel_idx < 0 or channel_idx >= len(yp.channels):
            return

        if channel_idx != yp.active_channel_index:
            # Not the active channel
            return

        channel = yp.channels[channel_idx]

        # Update channel UI properties
        ypui.channel_ui.expand_content = channel.expand_content
        ypui.channel_ui.expand_base_vector = channel.expand_base_vector
        ypui.channel_ui.expand_subdiv_settings = channel.expand_subdiv_settings
        ypui.channel_ui.expand_parallax_settings = channel.expand_parallax_settings
        ypui.channel_ui.expand_alpha_settings = channel.expand_alpha_settings
        ypui.channel_ui.expand_bake_to_vcol_settings = channel.expand_bake_to_vcol_settings
        ypui.channel_ui.expand_input_bump_settings = channel.expand_input_bump_settings
        ypui.channel_ui.expand_smooth_bump_settings = channel.expand_smooth_bump_settings

        # Update modifiers if count changed
        if len(ypui.channel_ui.modifiers) != len(channel.modifiers):
            ypui.channel_ui.modifiers.clear()
            for i, mod in enumerate(channel.modifiers):
                m = ypui.channel_ui.modifiers.add()
                m.expand_content = mod.expand_content

    def _update_bake_target_ui(self, yp, ypui, target_idx: int):
        """Update UI for a specific bake target"""
        if target_idx < 0 or target_idx >= len(yp.bake_targets):
            return

        if target_idx != yp.active_bake_target_index:
            return

        bt = yp.bake_targets[target_idx]

        # Update bake target UI properties
        ypui.bake_target_ui.expand_content = bt.expand_content
        ypui.bake_target_ui.expand_r = bt.expand_r
        ypui.bake_target_ui.expand_g = bt.expand_g
        ypui.bake_target_ui.expand_b = bt.expand_b
        ypui.bake_target_ui.expand_a = bt.expand_a


# Global instance
_ui_update_manager: Optional[UIUpdateManager] = None


def get_ui_update_manager() -> UIUpdateManager:
    """Get global UI update manager instance"""
    global _ui_update_manager
    if _ui_update_manager is None:
        _ui_update_manager = UIUpdateManager()
    return _ui_update_manager


@profile("debounced_ui_update")
def schedule_ui_update(delay: float = 0.1):
    """
    Schedule a debounced UI update
    Multiple rapid calls will be batched into a single update
    """
    batcher = get_update_batcher()
    ui_manager = get_ui_update_manager()

    def do_update():
        ui_manager.update_yp_ui_incremental()

    batcher.schedule_update('ui_refresh', do_update, delay)


def mark_layer_dirty(layer_idx: int, schedule_update: bool = True):
    """Mark a layer as dirty and optionally schedule UI update"""
    ui_manager = get_ui_update_manager()
    ui_manager.mark_dirty('layer', layer_idx)

    perf_tracker = get_performance_tracker()
    perf_tracker.mark_dirty(DirtyFlags.SPECIFIC_LAYER, layer_idx=layer_idx)

    if schedule_update:
        schedule_ui_update()


def mark_channel_dirty(channel_idx: int, schedule_update: bool = True):
    """Mark a channel as dirty and optionally schedule UI update"""
    ui_manager = get_ui_update_manager()
    ui_manager.mark_dirty('channel', channel_idx)

    perf_tracker = get_performance_tracker()
    perf_tracker.mark_dirty(DirtyFlags.CHANNEL)

    if schedule_update:
        schedule_ui_update()


def mark_mask_dirty(layer_idx: int, mask_idx: int, schedule_update: bool = True):
    """Mark a mask as dirty and optionally schedule UI update"""
    ui_manager = get_ui_update_manager()
    # Encode layer and mask index together
    combined_idx = layer_idx * 1000 + mask_idx
    ui_manager.mark_dirty('mask', combined_idx)

    perf_tracker = get_performance_tracker()
    perf_tracker.mark_dirty(DirtyFlags.SPECIFIC_MASK, layer_idx=layer_idx, mask_idx=mask_idx)

    if schedule_update:
        schedule_ui_update()


def request_full_ui_update():
    """Request a full UI rebuild"""
    ui_manager = get_ui_update_manager()
    ui_manager.request_full_update()
    schedule_ui_update(delay=0.05)  # Faster for full updates


def register():
    """Register UI performance module"""
    global _ui_update_manager
    _ui_update_manager = UIUpdateManager()
    print("INFO: Ucupaint UI performance module registered")


def unregister():
    """Unregister UI performance module"""
    global _ui_update_manager
    _ui_update_manager = None
    print("INFO: Ucupaint UI performance module unregistered")
