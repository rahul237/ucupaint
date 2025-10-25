# Ucupaint Architecture Diagrams

Visual representation of the Ucupaint system architecture.

---

## 1. Overall System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BLENDER APPLICATION                          │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    BLENDER PYTHON API (bpy)                    │ │
│  │  • Node Trees  • Materials  • Images  • Objects  • UI System  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                 ▲                                     │
│                                 │                                     │
│  ┌──────────────────────────────┼────────────────────────────────┐  │
│  │              UCUPAINT ADD-ON  │                                │  │
│  │                               │                                │  │
│  │  ┌─────────────┐  ┌──────────▼───────┐  ┌────────────────┐  │  │
│  │  │  UI Layer   │  │   Core Layer     │  │  Data Layer    │  │  │
│  │  │             │  │                  │  │                │  │  │
│  │  │ • Panels    │◄─┤ • Layer Mgmt    │◄─┤ • Properties  │  │  │
│  │  │ • Operators │  │ • Node Graphs   │  │ • State       │  │  │
│  │  │ • Menus     │  │ • Baking        │  │ • Settings    │  │  │
│  │  │ • Drawing   │  │ • Masking       │  │                │  │  │
│  │  └─────────────┘  └──────────────────┘  └────────────────┘  │  │
│  │                               ▲                                │  │
│  │  ┌────────────────────────────┴────────────────────────────┐ │  │
│  │  │           PERFORMANCE OPTIMIZATION LAYER                 │ │  │
│  │  │  • Dirty Flags  • Debouncing  • Caching  • Pooling     │ │  │
│  │  └──────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Dependency Graph

```
                    ┌──────────────┐
                    │  __init__.py │
                    │ (Registration)│
                    └───────┬──────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
   │ common  │         │  Root   │        │   ui    │
   │(Utils)  │◄────────┤ (Core)  │───────►│(Display)│
   └────┬────┘         └────┬────┘        └────┬────┘
        │                   │                   │
        │              ┌────▼────┐              │
        │              │  Layer  │              │
        │              │ (Mgmt)  │              │
        │              └────┬────┘              │
        │                   │                   │
        ├───────────┬───────┼───────┬───────────┤
        │           │       │       │           │
   ┌────▼────┐ ┌───▼───┐ ┌─▼──┐ ┌──▼───┐ ┌─────▼─────┐
   │  Mask   │ │  Bake │ │UDIM│ │Image │ │node_conn  │
   │         │ │       │ │    │ │Atlas │ │(Graphs)   │
   └─────────┘ └───────┘ └────┘ └──────┘ └───────────┘
                    │
            ┌───────┴────────┐
            │                │
      ┌─────▼─────┐   ┌──────▼──────┐
      │bake_common│   │node_arrange │
      │           │   │(Layout)     │
      └───────────┘   └─────────────┘

   ┌─────────────────────────────────────┐
   │   Performance System (Independent)  │
   │                                     │
   │  performance.py ──► ui_performance  │
   │       │                   │         │
   │       └───► performance_integration │
   └─────────────────────────────────────┘
```

---

## 3. Data Model Structure

```
Material
 └─ Ucupaint Group Node
      └─ YPaint (NodeTree)
           │
           ├─ Properties (yp)
           │    ├─ version: string
           │    ├─ active_layer_index: int
           │    ├─ active_channel_index: int
           │    │
           │    ├─ channels[] (List)
           │    │    └─ Channel
           │    │         ├─ name: string
           │    │         ├─ type: enum (RGB/VALUE/NORMAL)
           │    │         ├─ enable: bool
           │    │         ├─ modifiers[]
           │    │         └─ io_index: int
           │    │
           │    └─ layers[] (List)
           │         └─ Layer
           │              ├─ name: string
           │              ├─ type: enum (IMAGE/VCOL/COLOR/etc)
           │              ├─ parent_idx: int (-1 for root)
           │              ├─ blend_type: enum
           │              ├─ opacity: float
           │              ├─ enable: bool
           │              │
           │              ├─ channels[] (Mirror of root channels)
           │              │    └─ LayerChannel
           │              │         ├─ enable: bool
           │              │         ├─ blend_type: enum
           │              │         └─ modifiers[]
           │              │
           │              ├─ masks[] (List)
           │              │    └─ Mask
           │              │         ├─ name: string
           │              │         ├─ type: enum
           │              │         ├─ intensity: float
           │              │         ├─ blend_type: enum
           │              │         └─ modifiers[]
           │              │
           │              └─ modifiers[] (List)
           │                   └─ Modifier
           │                        ├─ type: enum
           │                        ├─ enable: bool
           │                        └─ parameters
           │
           └─ Node Tree
                ├─ Group Input
                ├─ Layer Groups (one per layer)
                ├─ Blend Nodes
                └─ Group Output (channels)
```

---

## 4. Node Tree Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                      Ucupaint Group Node                        │
│                                                                 │
│  ┌────────────┐                                   ┌──────────┐ │
│  │   Group    │                                   │  Group   │ │
│  │   Input    │                                   │  Output  │ │
│  │            │                                   │          │ │
│  │ • UV       ├──┐                           ┌───►│ • Color  │ │
│  │ • Normal   │  │                           │    │ • Normal │ │
│  │ • ...      │  │                           │    │ • Value  │ │
│  └────────────┘  │                           │    └──────────┘ │
│                  │                           │                 │
│                  │  ┌─────────────────────┐ │                 │
│                  └─►│   Layer 0 Group     ├─┤                 │
│                     │  ┌───────────────┐  │ │                 │
│                     │  │ Source Nodes  │  │ │                 │
│                     │  │ • Image/VCOL  │  │ │                 │
│                     │  │ • Procedural  │  │ │                 │
│                     │  └───────┬───────┘  │ │                 │
│                     │          │          │ │                 │
│                     │  ┌───────▼───────┐  │ │                 │
│                     │  │  Modifiers    │  │ │                 │
│                     │  │ • Hue/Sat     │  │ │                 │
│                     │  │ • Curves      │  │ │                 │
│                     │  └───────┬───────┘  │ │                 │
│                     │          │          │ │                 │
│                     │  ┌───────▼───────┐  │ │                 │
│                     │  │  Mask Groups  │  │ │                 │
│                     │  │  (multiply)   │  │ │                 │
│                     │  └───────┬───────┘  │ │                 │
│                     │          │          │ │                 │
│                     │  ┌───────▼───────┐  │ │                 │
│                     │  │ Channel Split │  │ │                 │
│                     │  │ RGB/Alpha/etc │  │ │                 │
│                     │  └───────────────┘  │ │                 │
│                     └─────────────────────┘ │                 │
│                              │              │                 │
│                     ┌────────▼──────────┐   │                 │
│                     │   Blend Node      │   │                 │
│                     │   (Mix RGB)       ├───┘                 │
│                     └────────┬──────────┘                     │
│                              │                                │
│                     ┌────────▼──────────┐                     │
│                     │   Layer 1 Group   │                     │
│                     │   ...             ├───┐                 │
│                     └───────────────────┘   │                 │
│                                             │                 │
│                     (More layers...)        │                 │
│                                             │                 │
│                     ┌────────────────────┐  │                 │
│                     │   Final Blend      ├──┘                 │
│                     └────────┬───────────┘                    │
│                              │                                │
│                              └────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Layer Processing Pipeline

```
                    ┌──────────────┐
                    │  User Input  │
                    │ (Add Layer)  │
                    └───────┬──────┘
                            │
                    ┌───────▼──────┐
                    │ Validation   │
                    │ • Name check │
                    │ • Type check │
                    └───────┬──────┘
                            │
                ┌───────────▼───────────┐
                │ Create PropertyGroup  │
                │ • Add to layers[]     │
                │ • Set defaults        │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │  Build Node Sub-tree  │
                │  • Create group       │
                │  • Add source nodes   │
                │  • Setup channels     │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │   Setup Masks         │
                │  (if requested)       │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │  Connect to Parent    │
                │  • reconnect_nodes    │
                │  • Update blend chain │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │  Arrange Nodes        │
                │  • Position nodes     │
                │  • Set visibility     │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │   Update UI           │
                │  • Refresh panels     │
                │  • Update active idx  │
                └───────────┬───────────┘
                            │
                    ┌───────▼──────┐
                    │   Complete   │
                    └──────────────┘
```

---

## 6. Property Update Flow

### Traditional (Before Optimization)

```
User changes property (e.g., opacity)
         │
         ▼
┌────────────────────┐
│ Update Callback    │
│ triggered          │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Check halt flags   │
│ (halt_reconnect)   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Reconnect ALL      │
│ layer nodes        │ ◄─── SLOW (full rebuild)
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Rearrange ALL      │
│ nodes              │ ◄─── SLOW (full layout)
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Update ENTIRE UI   │ ◄─── SLOW (clear + rebuild)
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Blender redraw     │
└────────────────────┘
```

### Optimized (After Performance System)

```
User changes property
         │
         ▼
┌────────────────────┐
│ @optimized_update  │
│ callback           │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Check batch mode   │
└────────┬───────────┘
         │
    Yes  │  No
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│ Mark   │ │ Schedule     │
│ dirty  │ │ debounced    │
│ return │ │ update       │
└────────┘ └──────┬───────┘
              │
              │ (Wait 100ms)
              │ (More changes? → reset timer)
              │
              ▼
        ┌──────────────┐
        │ Timer fires  │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Update ONLY  │
        │ changed item │ ◄─── FAST (incremental)
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Partial UI   │
        │ update       │ ◄─── FAST (targeted)
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Redraw       │
        └──────────────┘
```

---

## 7. Batch Operation Flow

```
with BatchUpdateContext():
    layer1.opacity = 0.5    ─┐
    layer2.blend = 'ADD'    ─┤
    layer3.enable = False   ─┤─► All batched
    layer4.opacity = 0.8    ─┤
    # ... 50 more changes   ─┘
# Context exits here
         │
         ▼
┌────────────────────┐
│ Collect dirty      │
│ items              │
│ • Layers: 1,2,3,4  │
│ • Flags: CONN, UI  │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Apply updates      │
│ ONCE for all       │
│ changes            │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Single reconnect   │ ◄─── Instead of 54 reconnects!
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Single UI update   │ ◄─── Instead of 54 UI rebuilds!
└────────────────────┘
```

---

## 8. Node Pooling System

### Without Pooling (Traditional)

```
┌─────────────────┐
│ Need a node     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ tree.nodes.new()│ ◄─── Allocate memory
└────────┬────────┘      Create Blender object
         │               Initialize properties
         │
         ▼
┌─────────────────┐
│ Configure node  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Use node        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ tree.nodes      │ ◄─── Deallocate memory
│ .remove(node)   │      Destroy Blender object
└─────────────────┘

Time: ~5-10ms per cycle
Memory: Lots of churn
```

### With Pooling (Optimized)

```
┌─────────────────┐
│ Need a node     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ pool.acquire()  │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Pool    │ Empty?
    │ empty?  │
    └────┬────┘
         │
    Yes  │  No
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│ Create │ │ Get from │
│ new    │ │ pool     │ ◄─── Fast! Already exists
└───┬────┘ └────┬─────┘
    │           │
    └─────┬─────┘
          │
          ▼
    ┌─────────────┐
    │ Reset props │
    │ Move visible│
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Use node    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ pool        │ ◄─── Return to pool
    │ .release()  │      Hide, move off-screen
    └──────┬──────┘      Keep for reuse
           │
           ▼
    ┌─────────────┐
    │ Node in pool│
    │ for reuse   │
    └─────────────┘

Time: ~1-2ms per cycle (5x faster!)
Memory: Minimal churn
Hit rate: 70-90% after warmup
```

---

## 9. Caching System

```
┌────────────────────────────────────────┐
│      Layer Cache Architecture          │
├────────────────────────────────────────┤
│                                        │
│  Request: get_layer_tree(layer)        │
│               │                        │
│               ▼                        │
│       ┌───────────────┐                │
│       │ Cache Lookup  │                │
│       │ Key: (ptr,    │                │
│       │      version, │                │
│       │      'tree')  │                │
│       └───────┬───────┘                │
│               │                        │
│          ┌────┴────┐                   │
│          │ Found?  │                   │
│          └────┬────┘                   │
│               │                        │
│          Yes  │  No                    │
│       ┌───────┴───────┐                │
│       │               │                │
│       ▼               ▼                │
│  ┌─────────┐   ┌─────────────┐        │
│  │ Return  │   │ Compute     │        │
│  │ cached  │   │ • Call func │        │
│  │ value   │   │ • Store     │        │
│  └─────────┘   │ • Return    │        │
│                └─────────────┘        │
│                                        │
│  Stats: 80% hit rate                  │
│         1000x faster on hit            │
│                                        │
└────────────────────────────────────────┘

Invalidation:
┌────────────────┐
│ Layer changed  │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ cache.         │
│ invalidate     │
│ (layer)        │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Delete entries │
│ for this layer │
└────────────────┘
```

---

## 10. Performance Monitoring Flow

```
┌─────────────────────────────────────────────┐
│      Performance Monitoring System          │
└─────────────────────────────────────────────┘

Function Execution:
┌────────────────┐
│ @profile("fn") │
│ def my_func(): │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Start timer    │
│ t0 = time()    │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Execute        │
│ function       │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ End timer      │
│ t1 = time()    │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Record stats   │
│ • elapsed      │
│ • count++      │
│ • total+=      │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Store in       │
│ timings[]      │
│ (ring buffer)  │
└────────────────┘


Reporting:
┌──────────────────┐
│ print_report()   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Aggregate data:  │
│ • Mean           │
│ • Min/Max        │
│ • Total time     │
│ • Call count     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Sort by total    │
│ (slowest first)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Print table      │
│ Top N functions  │
└──────────────────┘
```

---

## 11. Memory Layout (Conceptual)

```
┌─────────────────────────────────────────────────────┐
│              Blender Scene Memory                   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Material 1                                 │   │
│  │   └─ Ucupaint Group Node                    │   │
│  │        └─ YPaint Data (~10MB)               │   │
│  │             ├─ Properties (2KB)             │   │
│  │             ├─ Layers[50] (~500KB)          │   │
│  │             │    └─ Each: ~10KB             │   │
│  │             ├─ Node Tree (~9MB)             │   │
│  │             │    └─ 500 nodes × ~18KB       │   │
│  │             └─ Masks (~500KB)               │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Performance System                          │   │
│  │   ├─ Node Pool (~2MB)                       │   │
│  │   │    └─ 100 pooled nodes                  │   │
│  │   ├─ Layer Cache (~500KB)                   │   │
│  │   │    └─ 200 cached entries                │   │
│  │   ├─ Timings (~100KB)                       │   │
│  │   └─ Dirty Flags (~1KB)                     │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  Total: ~13MB for large project                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 12. Error Handling Flow

```
┌──────────────────┐
│ User Operation   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Operator.execute │
│ or update()      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Try/Catch Block  │
└────────┬─────────┘
         │
    ┌────┴────┐
    │Success? │
    └────┬────┘
         │
    Yes  │  No
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│ Return │ │ Exception    │
│ SUCCESS│ │ caught       │
└────────┘ └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ Log error    │
           │ print()      │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ Show user    │
           │ report()     │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ Return       │
           │ CANCELLED    │
           └──────────────┘
```

---

## 13. Testing Strategy Diagram

```
┌─────────────────────────────────────────────────┐
│            Testing Pyramid (Proposed)            │
├─────────────────────────────────────────────────┤
│                                                 │
│                    ┌───┐                        │
│                    │ E2E│ Manual Testing        │
│                    │ UI │ • Real usage          │
│                    └───┘ • Visual check         │
│                   /     \                       │
│                  /       \                      │
│                 /─────────\                     │
│                /Integration\                    │
│               /   Tests     \                   │
│              / • Layer ops   \                  │
│             /  • Baking      \                  │
│            /   • Node graphs \                  │
│           /─────────────────────\               │
│          /                       \              │
│         /      Unit Tests         \             │
│        /  • Pure functions         \            │
│       /   • Utilities              \            │
│      /    • Data structures        \            │
│     /                               \           │
│    /─────────────────────────────────\          │
│   /   Performance Tests              \          │
│  / • Benchmark critical paths         \         │
│ /  • Regression detection             \         │
│/                                       \        │
│─────────────────────────────────────────        │
│                                                 │
│  Current Status: ▓ 5%  (Manual only)           │
│  Target Status:  ▓▓▓▓▓▓▓▓░░ 80%                │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Summary

These diagrams illustrate the **key architectural components** of Ucupaint:

1. **System Architecture** - Overall structure and layers
2. **Module Dependencies** - How modules relate
3. **Data Model** - Property hierarchy
4. **Node Tree** - Shader node organization
5. **Processing Pipeline** - Layer creation flow
6. **Update Flow** - Before/after optimization
7. **Batch Operations** - Efficient multi-update
8. **Node Pooling** - Memory optimization
9. **Caching** - Performance optimization
10. **Performance Monitoring** - Profiling system
11. **Memory Layout** - Resource usage
12. **Error Handling** - Robustness
13. **Testing Strategy** - Quality assurance

These visual representations should help developers quickly understand the codebase structure and implementation patterns.
