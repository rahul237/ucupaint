bl_info = {
    "name": "Ucupaint",
    "author": "Yusuf Umar, Agni Rakai Sahakarya, Jan Bláha, Ahmad Rifai, morirain, Patrick W. Crawford, neomonkeus, Kareem Haddad, passivestar, Przemysław Bągard",
    "version": (2, 4, 0),
    "blender": (2, 80, 0),
    "location": "Node Editor > Properties > Ucupaint",
    "warning": "",
    "description": "Special node to manage painting layers for Cycles and Eevee materials",
    "wiki_url": "https://ucupumar.github.io/ucupaint-wiki/",
    "doc_url": "https://ucupumar.github.io/ucupaint-wiki/",
    "category": "Node",
}

if "bpy" in locals():
    import imp
    imp.reload(Localization)
    imp.reload(BaseOperator)
    imp.reload(performance)
    imp.reload(ui_performance)
    imp.reload(layer_performance)
    imp.reload(node_performance)
    imp.reload(image_ops)
    imp.reload(common)
    imp.reload(bake_common)
    imp.reload(modifier_common)
    imp.reload(lib)
    imp.reload(Decal)
    imp.reload(ui)
    imp.reload(subtree)
    imp.reload(transition_common)
    imp.reload(input_outputs)
    imp.reload(node_arrangements)
    imp.reload(node_connections)
    imp.reload(preferences)
    imp.reload(vector_displacement_lib)
    imp.reload(vector_displacement)
    imp.reload(vcol_editor)
    imp.reload(transition)
    imp.reload(BakeTarget)
    imp.reload(BakeInfo)
    imp.reload(UDIM)
    imp.reload(ImageAtlas)
    imp.reload(MaskModifier)
    imp.reload(Mask)
    imp.reload(Modifier)
    imp.reload(NormalMapModifier)
    imp.reload(Layer)
    imp.reload(ListItem)
    imp.reload(Bake)
    imp.reload(BakeToLayer)
    imp.reload(Root)
    imp.reload(versioning)
    imp.reload(addon_updater_ops)
    imp.reload(Test)
else:
    from . import Localization
    from . import BaseOperator, performance, ui_performance, layer_performance, node_performance, image_ops, common, bake_common, modifier_common, lib, Decal, ui, subtree, transition_common, input_outputs, node_arrangements, node_connections, preferences
    from . import vector_displacement_lib, vector_displacement
    from . import vcol_editor, transition, BakeTarget, BakeInfo, UDIM, ImageAtlas, MaskModifier, Mask, Modifier, NormalMapModifier, Layer, ListItem, Bake, BakeToLayer, Root, versioning
    from . import addon_updater_ops
    from . import Test

import bpy 

def register():
    Localization.register_module(ui)

    # Register performance modules first
    performance.register()
    ui_performance.register()

    image_ops.register()

    # Register other core modules
    # (layer_performance and node_performance will be registered after Layer/subtree)
    preferences.register()
    lib.register()
    Decal.register()
    ui.register()
    vcol_editor.register()
    transition.register()
    vector_displacement.register()
    BakeTarget.register()
    BakeInfo.register()
    UDIM.register()
    ImageAtlas.register()
    MaskModifier.register()
    Mask.register()
    Modifier.register()
    NormalMapModifier.register()
    Layer.register()
    ListItem.register()
    Bake.register()
    BakeToLayer.register()
    Root.register()
    versioning.register()
    addon_updater_ops.register()
    Test.register()

    # Apply performance optimizations after core modules are loaded
    layer_performance.register()
    node_performance.register()

    print('INFO: ' + common.get_addon_title() + ' ' + common.get_current_version_str() + ' is registered!')
    print('INFO: Performance optimizations enabled')
    print('INFO: - Optimized update callbacks active')
    print('INFO: - Node pooling active')
    print('INFO: - UI debouncing active')

def unregister():
    Localization.unregister_module(ui)

    image_ops.unregister()
    preferences.unregister()
    lib.unregister()
    Decal.unregister()
    ui.unregister()
    vcol_editor.unregister()
    transition.unregister()
    vector_displacement.unregister()
    BakeTarget.unregister()
    BakeInfo.unregister()
    UDIM.unregister()
    ImageAtlas.unregister()
    MaskModifier.unregister()
    Mask.unregister()
    Modifier.unregister()
    NormalMapModifier.unregister()
    Layer.unregister()
    ListItem.unregister()
    Bake.unregister()
    BakeToLayer.unregister()
    Root.unregister()
    versioning.unregister()
    addon_updater_ops.unregister()
    Test.unregister()

    # Unregister performance optimizations first
    node_performance.unregister()
    layer_performance.unregister()

    # Unregister performance modules last
    ui_performance.unregister()
    performance.unregister()

    print('INFO: ' + common.get_addon_title() + ' ' + common.get_current_version_str() + ' is unregistered!')

if __name__ == "__main__":
    register()
